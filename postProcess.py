import regex as re
from collections import defaultdict, Counter

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
        '/': '.',    # 12/12/2025 -> 12.12.2025
        '-': '.'     # 12-12-2025 -> 12.12.2025
    }
    return ''.join(replacements.get(char, char) for char in text)

def fix_and_parse_float(s):
    s = fix_common_ocr_errors(s)
    s = s.replace(' ', '')

    if '.' in s and ',' in s:           # Case 1: both exist — decide based on last separator
        if s.rfind('.') > s.rfind(','):             # Likely English-style: 1,234.56 → remove commas
            s = s.replace(',', '')
        else:                           # Likely Turkish-style: 1.234,56 → remove dots, convert comma to dot
            s = s.replace('.', '')
            s = s.replace(',', '.')
    elif ',' in s:                      # Case 2: only comma exists — likely decimal (Turkish-style)
        s = s.replace(',', '.')
    elif '.' in s:                      # Case 3: only dot exists — probably English-style, do nothing
        pass

    while len(s) > 0 and not s[-1].isdigit(): # Eğer son karakter sayı değilse onu kırp
        s = s[:-1]

    if s == '':
        return None

    try:
        return float(s)
    except ValueError:
        return None

def fix_date_ocr_errors(date_str: str) -> str: #   Fix common OCR year errors assuming format is always DD.MM.YYYY.

    if len(date_str) != 10:
        return date_str  # Not a valid dd.mm.yyyy

    day, month, year = date_str[:2], date_str[3:5], date_str[6:]
    
    if not year.startswith("20"): # Force year to start with '20'
        year = "20" + year[2:]

    if year[2] not in {"0", "1", "2"}:     # Fix second digit if clearly off (e.g. 2072 → 2022)
        year = year[:2] + "2" + year[3:]

    if day[0] not in {"0", "1", "2", "3"}: # Fix first digit of day to 0 if needed (e.g. 92.10.2019 -> 02.10.2019), obviously might not work
        day = "0" + day[1:]

    return f"{day}.{month}.{year}"

# def merge_field_results(results): # Dümdüz oy verme sistemi (4 ve 1 silme mantığı yok)
#     field_values = defaultdict(list)

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

def merge_field_results(results, extra_fatura_candidates=None):  # Düzgün çalışan baştan 4 silmeli versiyon
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

        override_applied = False         # Only apply override if the stripped version is in top 2 most common
        for val in alt_candidates:
            if isinstance(val, float):
                val_str = f"{val:.2f}"
                for other_val in alt_candidates:
                    if isinstance(other_val, float):
                        other_str = f"{other_val:.2f}"
                        if other_str[0] in {"4", "1"} and other_str[1:] == val_str: # Check: is this val among top 2 most frequent?
                            top_two_values = [item[0] for item in most_common[:2]]
                            if val in top_two_values and counter[val] >= 2:
                                final_fields[key] = val
                                override_applied = True
                                break
                if override_applied:
                    break

        if not override_applied:
            final_fields[key] = most_common_val
            
    if extra_fatura_candidates:
        counter = Counter(extra_fatura_candidates)
        most_common, freq = counter.most_common(1)[0]
        final_fields["Fatura No"] = most_common
    
    return final_fields

def extract_fields(text, isReceipt = True):
    fields = {}

    common_fields = {
        "Tarih": re.search(r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b", text, re.IGNORECASE),
        "Toplam": re.search(
            r"(?<!ara\s)(?<!4ra\s)(?<!afa\s)"
            r"(?<!kdv(?:[’'`´]li?)?\s)(?<!kdu\s)(?<!kdy\s)(?<!kdi\s)(?<!kdw\s)(?<!kdn\s)(?<!kdx\s)"
            r"\btoplam(?:\s+tutar(?!ı))?\b[^\d]{0,3}[*x»:/-]?\s*([\dOolIıİi.,\s]{1,20}\d)",
            text,
            re.IGNORECASE
        ),
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

    receipt_fields = {
        "Fiş No": re.search(
            r"(?:f[ıiİl1|][şs5]\s*no|fiş\s*no|fişno)"
            r"[^\d\n]{0,5}[\s\n]*([\d]{1,4})\b",
            text,
            re.IGNORECASE
        ),
    }

    bill_fields = {}
    # bill_fatura_no = re.search(
    #     r"(?:fatura\s*(?:no|nu|n[o0])|fat\s*no)[^\w\d]{0,4}[:\-]?\s*([A-ZİŞĞÜÇÖ]{1,4}[\s\-]?\d{10,16})",
    #     text,
    #     re.IGNORECASE
    # )
    # if not bill_fatura_no:
    #     bill_fatura_no = re.search(
    #         r"\b[İIı]?\s*([A-ZİŞĞÜÇÖ]{3}\d{13})\b",  # fallback regex
    #         text
    #     )
    bill_fatura_no = re.search(
        r"\b[İIı]?\s*([A-ZİŞĞÜÇÖ]{3}\d{13})\b",
        text,
        re.IGNORECASE
    )
    if bill_fatura_no:
        bill_fields["Fatura No"] = bill_fatura_no

    bill_fields["KDV Oranı"] = re.search(
        r"kdv\s*oran[ıiİl1][^\d\n]{0,40}(?:\n[^\d\n]{0,40}){0,3}[^0-9]{0,10}(\d{1,2})\b",
        text,
        re.IGNORECASE
    )

    from_regex = {**common_fields}  # Merge common + specific fields

    if isReceipt:
        from_regex.update(receipt_fields)
        fields["Belge Türü"] = "Fiş"
    else:
        from_regex.update(bill_fields)
        fields["Belge Türü"] = "Fatura"

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
                    if val in [0, 1, 8, 10, 18, 20]:
                        fields[key] = val
                except ValueError:
                    pass
            else:
                fixed_val = fix_common_ocr_errors(raw_val)
                if key == "Tarih":
                    fixed_val = fix_date_ocr_errors(fixed_val)
                elif key == "Vergi Kimlik No":
                    cleaned_vkn = re.sub(r"\D", "", fixed_val)  # Exclude Karel's own number, after removing any non-digit chars
                    if cleaned_vkn == "5240008809":
                        continue
                    fixed_val = cleaned_vkn
                fields[key] = fixed_val

    return fields

def find_best_components(all_components, toplam_val, test = False):
    closest_components = None
    closest_diff = float("inf")

    for components in all_components:
        if not components:  # Skip empty results
            continue

        total = sum(item["Harcama Tutarı"] for item in components)
        diff = abs(total - toplam_val)

        if diff < closest_diff:
            closest_diff = diff
            closest_components = components

    return closest_components if closest_components is not None else []

def parse_items(text: str, test=False) -> list:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    start_idx = next((i for i, l in enumerate(lines) if re.search(r"Sipariş\s+Numara(sı|si)", l, re.IGNORECASE)), -1)
    if start_idx < 0:
        start_idx = next((i for i, l in enumerate(lines) if re.search(r"F[İIıi1]?[İIıi1]?[İIıi1]?[ŞŞşsS]?\s*NO\s*:?\s*\d+", l, re.IGNORECASE)), -1)
    if start_idx < 0:
        start_idx = 0

    end_idx = next((i for i, l in enumerate(lines) if re.search(r"\bToplam\b", l, re.IGNORECASE)), len(lines))
    if end_idx <= start_idx: end_idx = len(lines)

    item_lines = lines[start_idx+1:end_idx]
    if test: print(f"[DEBUG] Lines between {start_idx} and {end_idx} are selected for parsing.")
    items = []

    item_re = re.compile(
        r"^(.+?)\s+[&x\*]{0,3}\s*"
        r"(1|8|01|08|10|18| \
        11|18|101|108|110|118| \
        21|28|201|208|210|218| \
        41|48|401|408|410|418)"
        r"(?=\s).*?([\d.]+)\s*,\s*(\d{2})\D*$"
        # r"(?=\s|\W).*?([\d.]+)\s*,\s*(\d{2})\D*$"                                
    )

    for line in item_lines:
        if re.match(r"^\d+\s*[Xx]\b", line): continue
        m = item_re.match(line)
        if not m: continue
        raw_name, rate_str, int_part, frac_part = m.groups()

        if len(raw_name.strip()) < 5:   #
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
        for item in items:         # Print each item in the list
            print(item)
        s = sum(i["Harcama Tutarı"] for i in items)         # Calculate the sum
        print(f"[DEBUG] Parsed {len(items)} components. Sum: {s:.2f}")
        print("\n")
        
    return items

def find_most_common_components_by_sum(all_components):
    sum_to_components = defaultdict(list)

    for components in all_components:
        if not components:
            continue
        total = sum(item["Harcama Tutarı"] for item in components)
        sum_to_components[total].append(components)

    if not sum_to_components:
        return []

    most_common_sum = max(sum_to_components.items(), key=lambda x: len(x[1]))[0]     # Find the sum value with the most occurrences
    
    return sum_to_components[most_common_sum][0]     # Return the first component list that had this sum

def is_receipt(text: str) -> bool:
    fis_no_regex = re.search(r"F[İIıi1]?[İIıi1]?[İIıi1]?[ŞŞşsS5]", text, re.IGNORECASE)
    return bool(fis_no_regex)