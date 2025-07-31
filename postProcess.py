# Author(s): Yaman Türköz, Yusuf Bedri Bitiren
#
# Ham metinden alınan verilerin temizlenmesi, düzeltilmesi ve yapılandırılması için fonksiyonlar içerir.
# 
# - OCR'dan kaynaklanan karakter ve format hatalarını düzeltmek (örn. O → 0, tarih ayracı normalizasyonu)
# - Tarih ve sayı değerlerini doğru formata çevirmek ve parse etmek
# - Regex tabanlı alan çıkarımı (Tarih, Toplam, Fiş No, Fatura No vb.)
# - Farklı belge türleri (Fiş/Fatura) için alanları ayırt etmek ve ilgili bilgileri toplamak
# - Alt kalem (masraf kalemleri) satırlarını ayıklamak ve doğruluk için en uygun alt kalem listesini seçmek
# - OCR sonuçları arasında tutarlılık sağlamak için oylama ve doğrulama mekanizmaları kullanmak
#
# Not: Bazı regexler yorumda, ileride ihtiyaç halinde aktif edilebilir.

import regex as re
from collections import defaultdict, Counter

# OCR'da sıkça karışan karakterleri düzeltir (örn: O → 0, I → 1)
# Tarih formatları için / ve - işaretlerini . ile değiştirir
def fix_common_ocr_errors(text: str) -> str:
    replacements = {
        'O': '0',
        'o': '0',
        'I': '1',
        'i': '1',
        'İ': '1',
        'l': '1',
        'S': '5',
        'B': '8',
        '/': '.',    # 12/12/2025 → 12.12.2025
        '-': '.'     # 12-12-2025 → 12.12.2025
    }
    return ''.join(replacements.get(char, char) for char in text)


# OCR sonrası rakamları (1.342,25) düzeltip, Türkçe/İngilizce ondalık ayracını doğru biçime çevirir ve float şeklinde döndürür
def fix_and_parse_float(s):
    s = fix_common_ocr_errors(s)
    s = s.replace(' ', '')

    if '.' in s and ',' in s:
        if s.rfind('.') > s.rfind(','):
            s = s.replace(',', '')
        else:
            s = s.replace('.', '')
            s = s.replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    elif '.' in s:
        pass

    while len(s) > 0 and not s[-1].isdigit():
        s = s[:-1]

    if s == '':
        return None

    try:
        return float(s)
    except ValueError:
        return None


# OCR'dan gelen tarihlerin (DD.MM.YYYY) yıl ve gün kısmındaki hataları düzeltir ve olası düzgün tarihleri tahmin eder
def fix_date_ocr_errors(date_str: str) -> str:
    if len(date_str) != 10:
        return date_str

    day, month, year = date_str[:2], date_str[3:5], date_str[6:]

    if not year.startswith("20"):  # Yılı '20' ile başlat
        year = "20" + year[2:]

    if year[2] not in {"0", "1", "2"}:  # Yılın 3. hanesi --> 2
        year = year[:2] + "2" + year[3:]

    if day[0] not in {"0", "1", "2", "3"}:  # Günün ilk hanesi --> 0
        day = "0" + day[1:]

    return f"{day}.{month}.{year}"


# def merge_field_results(results):     # Sonuçlar arası oy verme sistemi ilk taslağı, eğer aşağıdaki oy verme sistemi çalışmazsa -
#     field_values = defaultdict(list)  # alternatif olarak düşünülebilir.

#     for fields in results:
#         for key, val in fields.items():
#             if val:
#                 field_values[key].append(val)

#     final_fields = {}
#     for key, values in field_values.items():
#         counter = Counter(values)
#         most_common_val, freq = counter.most_common(1)[0]
#         final_fields[key] = most_common_val

#     return final_fields

# OCR sonuçlarındaki alanları oylama sistemi ile birleştirir
# Başına Tesseract tarafından sık sık * yerine yanlış eklenen 1 ve 4'leri tespit edip düzgün olanları seçer.
def merge_field_results(results):
    field_values = defaultdict(list)

    for fields in results:
        for key, val in fields.items():
            if val:
                field_values[key].append(val)

    final_fields = {}

    for key, values in field_values.items():
        counter = Counter(values)
        most_common = counter.most_common()
        most_common_val, freq = most_common[0]

        alt_candidates = set(values)

        override_applied = False  # Override sadece 4lü ve 4süz version birde fazla karşılaşırsa uygulanır
        for val in alt_candidates:
            if isinstance(val, float):
                val_str = f"{val:.2f}"
                for other_val in alt_candidates:
                    if isinstance(other_val, float):
                        other_str = f"{other_val:.2f}"
                        if other_str[0] in {"4", "1"} and other_str[1:] == val_str:
                            top_two_values = [item[0] for item in most_common[:2]]
                            if val in top_two_values and counter[val] >= 2:
                                final_fields[key] = val
                                override_applied = True
                                break
                if override_applied:
                    break

        if not override_applied:
            final_fields[key] = most_common_val

    return final_fields


# OCR'dan alınan metinde belge türüne göre (Fiş/Fatura) ilgili alanları regex ile tespit eder,
# bulunan değerleri OCR hatalarını düzelterek normalize eder ve sonuçları döndürür.
def extract_fields(text, isReceipt = True):
    fields = {}

    # Ortak alanlar (Fiş veya Fatura fark etmeksizin aranan alanlar)
    common_fields = {
        "Tarih": re.search(r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b", text, re.IGNORECASE),
        "Toplam": re.search(
            r"(?<!ara\s)(?<!4ra\s)(?<!afa\s)"
            r"(?<!kdv(?:[’'`´]li?)?\s)(?<!kdu\s)(?<!kdy\s)(?<!kdi\s)(?<!kdw\s)(?<!kdn\s)(?<!kdx\s)"
            r"\btoplam(?:\s+tutar(?!ı))?\b[^\d]{0,3}[*x»:/-]?\s*([\dOolIıİi.,\s]{1,20}\d)",
            text,
            re.IGNORECASE
        ),
        # Aşağıdaki alanlar yorumda ama hazır (ileride aktif edilebilir)
        # "Toplam KDV": re.search(
        #     r"(?:toplam\s+kdv|topkdv|topkdu|TOPVP|topkov|topkdy|topkdi|ToOPKDV|TOPKÜV|topkdw|topkdı|topkvu|topkd|topkdvı)"
        #     r"[^\dO]{0,3}[*x»]?\s*([\dOolIıİi.,\s]{1,15}\d)",
        #     text,
        #     re.IGNORECASE
        # ),
        # "Ticaret Sicil No": re.search(
        #     r"(?:ticaret\s*sicil\s*no|t\.?\s*s\.?\s*no|tic\s*sic\s*no|tsn|sicil\s*no)"
        #     r"[^\d]{0,3}[*x»:]?\s*([\dOolIıİi]{6})\b",
        #     text,
        #     re.IGNORECASE
        # ),
        # "Mersis No": re.search(
        #     r"(?:mersis\s*no|mersis\s*number|mersis\s*nu|mers\s*no)"
        #     r"[^\d]{0,3}[*x»:]?\s*(\d{16})\b",
        #     text,
        #     re.IGNORECASE
        # ),
        # "ETTN": re.search(
        #     r"(?:[eEfF][\s.:,;_-]*[tT1İil][\s.:,;_-]*[tT1İil][\s.:,;_-]*[nNhHmM])"
        #     r"[\s.:,;_-]*[:\-]?\s*"
        #     r"([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
        #     text,
        #     re.IGNORECASE
        # ),
        # "Vergi Kimlik No": re.search(
        #     r"(?:vergi\s*kimlik\s*no|vkn)[^\dOolIıİ]{0,3}[*x»:]?\s*([0-9OolIıİ]{10})\b",
        #     text,
        #     re.IGNORECASE
        # ), 
    }

    # Sadece fişlerde aranan alanlar
    receipt_fields = {
        "Fiş No": re.search(
            r"(?:f[ıiİl1|][şs5]\s*no|fiş\s*no|fişno)"
            r"[^\d\n]{0,5}[\s\n]*([\d]{1,4})\b",
            text,
            re.IGNORECASE
        ),
    }

    # Sadece faturalar için aranan alanlar
    bill_fields = {}
    bill_fatura_no = re.search(
        r"(?:fatura\s*(?:no|nu|n[o0])|fat\s*no)[^\w\d]{0,4}[:\-]?\s*([A-ZİŞĞÜÇÖ]{1,4}[\s\-]?\d{10,16})",
        text,
        re.IGNORECASE
    )
    if not bill_fatura_no:
        # Fallback: Eğer yukarıdaki regex yakalamazsa alternatif olarak bu desen ile arar
        bill_fatura_no = re.search(
            r"\b[İIı]?\s*([A-ZİŞĞÜÇÖ]{3}\d{13})\b",
            text
        )
    if bill_fatura_no:
        bill_fields["Fatura No"] = bill_fatura_no

    # KDV oranı faturalarda bazen farklı satırlarda bulunabilir, ona göre geniş arama yapar
    bill_fields["KDV Oranı"] = re.search(
        r"kdv\s*oran[ıiİl1][^\d\n]{0,40}(?:\n[^\d\n]{0,40}){0,3}[^0-9]{0,10}(\d{1,2})\b",
        text,
        re.IGNORECASE
    )

    # İlk olarak ortak alanları ekliyoruz
    from_regex = {**common_fields}

    if isReceipt:
        from_regex.update(receipt_fields)
        fields["Belge Türü"] = "Fiş"
    else:
        from_regex.update(bill_fields)
        fields["Belge Türü"] = "Fatura"

    # Regex ile yakalanan değerleri işleyip OCR hatalarını temizleyerek alanlara ekler
    for key, match in from_regex.items():
        if match:
            raw_val = match.group(1)
            if key in ["Toplam", "Toplam KDV"]:
                val = fix_and_parse_float(raw_val)
                if val is not None:
                    fields[key] = val
            elif key == "KDV Oranı":
                fixed_val = fix_common_ocr_errors(raw_val)
                try:
                    val = int(fixed_val)
                    if val in [0, 1, 8, 10, 18, 20]:  # Geçerli KDV oranları
                        fields[key] = val
                except ValueError:
                    pass
            else:
                fixed_val = fix_common_ocr_errors(raw_val)
                if key == "Tarih":
                    fixed_val = fix_date_ocr_errors(fixed_val)
                elif key == "Vergi Kimlik No":
                    cleaned_vkn = re.sub(r"\D", "", fixed_val)
                    if cleaned_vkn == "5240008809":  # Karel’in kendi VKN’sini filtrele
                        continue
                    fixed_val = cleaned_vkn
                fields[key] = fixed_val

    return fields


# Alt kalemler (Ara Kalemler) listeleri arasından toplam tutara en yakın olanı seçer
def find_best_components(all_components, toplam_val, test = False):
    closest_components = None
    closest_diff = float("inf")

    for components in all_components:
        if not components:  # Boş sonuçları atla
            continue

        total = sum(item["Harcama Tutarı"] for item in components)
        diff = abs(total - toplam_val)

        if diff < closest_diff:
            closest_diff = diff
            closest_components = components

    return closest_components if closest_components is not None else []


# OCR metninden alt kalem (Ara Kalemler) satırlarını tespit eder, her birini isim, KDV oranı ve tutar olarak parse eder
def parse_items(text: str, test=False) -> list:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Sipariş Numarası veya Fiş No geçen satırı başlangıç olarak belirler, yoksa baştan başlar
    start_idx = next((i for i, l in enumerate(lines) if re.search(r"Sipariş\s+Numara(sı|si)", l, re.IGNORECASE)), -1)
    if start_idx < 0:
        start_idx = next((i for i, l in enumerate(lines) if re.search(r"F[İIıi1]?[İIıi1]?[İIıi1]?[ŞŞşsS]?\s*NO\s*:?\s*\d+", l, re.IGNORECASE)), -1)
    if start_idx < 0:
        start_idx = 0

    # Toplam kelimesi geçen satırı bitiş olarak belirler, bulunamazsa son satıra kadar alır
    end_idx = next((i for i, l in enumerate(lines) if re.search(r"\bToplam\b", l, re.IGNORECASE)), len(lines))
    if end_idx <= start_idx: end_idx = len(lines)

    item_lines = lines[start_idx+1:end_idx]
    if test: print(f"[DEBUG] Lines between {start_idx} and {end_idx} are selected for parsing.")
    items = []

    # Alt kalemlerin regex deseni (isim, KDV oranı, tutar)
    item_re = re.compile(
        r"^(.+?)\s+[&x\*]{0,3}\s*"
        r"(1|8|01|08|10|18| \
        11|18|101|108|110|118| \
        21|28|201|208|210|218| \
        41|48|401|408|410|418)"
        r"(?=\s).*?([\d.]+)\s*,\s*(\d{2})\D*$"
        # r"(?=\s|\W).*?([\d.]+)\s*,\s*(\d{2})\D*$"   # Alternatif bir regex, diğeri daha iyi çalışıyor
    )

    for line in item_lines:
        if re.match(r"^\d+\s*[Xx]\b", line): continue  # Bozuk hesaplama satırlarını (3 x 10.95 vs.) atla
        m = item_re.match(line)
        if not m: continue
        raw_name, rate_str, int_part, frac_part = m.groups()

        if len(raw_name.strip()) < 5:  # Çok kısa isimleri atla
            continue

        total = float(f"{int_part.replace('.', '')}.{frac_part}")
        name = raw_name.strip()
        kdv = int(rate_str[-2:]) if len(rate_str) == 3 else int(rate_str)
        items.append({
            "Masraf Açıklama": name,
            "KDV Oranı": kdv,
            "Harcama Tutarı": total
        })

    if test:
        for item in items:
            print(item)
        s = sum(i["Harcama Tutarı"] for i in items)
        print(f"[DEBUG] Parsed {len(items)} components. Sum: {s:.2f}")
        print("\n")

    return items

# Alt kalem listeleri arasından toplam tutarına göre en çok tekrar eden grubu döndürür
def find_most_common_components_by_sum(all_components):
    sum_to_components = defaultdict(list)

    for components in all_components:
        if not components:
            continue
        total = sum(item["Harcama Tutarı"] for item in components)
        sum_to_components[total].append(components)

    if not sum_to_components:
        return []

    most_common_sum = max(sum_to_components.items(), key=lambda x: len(x[1]))[0]
    
    return sum_to_components[most_common_sum][0]

# Metinde fiş karakterleri olup olmadığını kontrol ederek belge türünü tahmin eder
def is_receipt(text: str) -> bool:
    fis_no_regex = re.search(r"F[İIıi1]?[İIıi1]?[İIıi1]?[ŞŞşsS5]", text, re.IGNORECASE)
    return bool(fis_no_regex)