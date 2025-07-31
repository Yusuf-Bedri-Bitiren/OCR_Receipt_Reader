# # Author(s): Yaman Türköz, Yusuf Bedri Bitiren
#
# Makbuz ve fatura görüntülerinden otomatik veri çıkarımı için OCR tabanlı iş akışı.
#
# Bu script şu işlemleri yapar:
# - Görüntüyü isteğe bağlı olarak derin öğrenmeye dayalı autocrop ile kırpar.
# - OCR öncesi görüntü ön işleme (binarizasyon, gürültü azaltma vb.) uygulanabilir (processImage modülü kullanılır).
# - Tesseract OCR ile farklı Sayfa Segmentasyon Modu (PSM) ayarlarında metin çıkarımı yapılır.
# - postProcess.py ile ham metin işlenir.
# - Farklı PSM ve ön işleme kombinasyonlarından elde edilen sonuçlar birleştirilir, eksik alanlar tamamlanır.
# - Test modu ile detaylı ara çıktı dosyaları oluşturulur.
# - Sonuçlar JSON formatında kaydedilir.

from autocrop_kh import autocrop
from PIL import Image
import pytesseract
import torch
import os
import json
from processImage import *
from postProcess import *

print(">>> Kod başladı <<<")

# Tesseract konumu (kendi Tesseract directory'nizi yazmanız gerekiyor)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# PIL Image nesnesinden OCR ile metin çıkarır
# config_psm parametresi ile Tesseract'ın Sayfa Segmentasyon Modu ayarlanabilir
def extract_text_from_image(image, config_psm = 6):
    custom_config = f'--oem 3 --psm {config_psm} -l tur'
    text = pytesseract.image_to_string(image, config=custom_config)
    return text

# Makbuz/fatura iş akışını çalıştırır:
# - İstenirse kırpma (crop) yapılır,
# - İstenirse OCR öncesi ön işleme yapılır,
# - Farklı PSM modlarında OCR yapılır,
# - Çıkarılan metin alanları regex ile analiz edilir,
# - Alt kalemler çıkarılır (sadece makbuzlar için),
# - Test aktifse OCR çıktıları dosyaya kaydedilir.
def run_receipt_pipeline(image_path, test_active = False, crop = True, pre_process = False, psm_values = [11, 4, 6, 3], isReceipt = False):

    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "models", "autocrop_model_v2.pth")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if crop:                                                # 1. Kırp
        cropped_array = autocrop(img_path=image_path, model_path=model_path, device=device)
        cropped_img = convert_to_pil(cropped_array)         # 2. Görüntüyü uygun formata çevir
    else:
        cropped_img = Image.open(image_path).convert("RGB")  # Croplamıyorsak dümdüz açıyoruz

    if pre_process:
        cropped_img = preprocess_for_ocr(cropped_img)   # Yeni: OCR öncesi preprocess et

    psm_results = []                                    
    component_results = []                             

    if test_active: # Test aktif ise sonuçları kaydet
        output_folder = os.path.join(current_dir, "ocr_outputs")      

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    for value in psm_values:
        text = extract_text_from_image(cropped_img, value)      # 3. OCR işlemi (signature'deki psm_values ile tek tek)
        psm_results.append(extract_fields(text, isReceipt))                # 4. Alanları regex ile ayıkla 
        if value != 11 and isReceipt: component_results.append(parse_items(text, test_active))       # Alt kalemleri çıkar ve ekle, 11 alt kalem için kötü
        if test_active:
            iteration = (int(crop) * 2) + int(pre_process) + 1
            filename = f"output_ite_{iteration}_psm_{value}.txt"
            
            with open(os.path.join(output_folder, filename), 'w', encoding='utf-8') as file:
                file.write(text)
                
    return psm_results, component_results

# Verilen görüntü dosyası için tüm senaryoları çalıştırır:
# - OCR çıktısına göre belge türünü tahmin eder (fiş veya fatura),
# - Kırpma ve ön işleme kombinasyonlarını dener,
# - Tüm PSM değerlerinde OCR yapar,
# - Tüm sonuçları birleştirir,
# - Gerekli alanlar yoksa None atar,
# - Alt kalemleri en iyi toplam tutara göre seçer veya en sık tekrar edenleri bulur,
# - Test modundaysa detaylı çıktı verir,
# - Sonuçları JSON olarak results.txt'ye kaydeder.
def run(image_path, test=False):
    all_results = []  
    all_components = []

    isReceipt = is_receipt(extract_text_from_image(image_path, 3)) | is_receipt(extract_text_from_image(image_path, 6)) | is_receipt(extract_text_from_image(image_path, 4)) | is_receipt(extract_text_from_image(image_path, 11))
    if test: print(f"This is a receipt: {isReceipt}")

    # Dört farklı işlem senaryosunu çalıştırıp sonuçları biriktir
    psm_results_1, component_results_1 = run_receipt_pipeline(image_path, test, False, False, isReceipt= isReceipt)  # Uncropped, unprocessed
    all_results.extend(psm_results_1)
    if isReceipt: all_components.extend(component_results_1)

    psm_results_2, component_results_2 = run_receipt_pipeline(image_path, test, False, True, isReceipt= isReceipt)   # Uncropped, processed
    all_results.extend(psm_results_2)
    if isReceipt: all_components.extend(component_results_2)

    psm_results_3, component_results_3 = run_receipt_pipeline(image_path, test, True, False, isReceipt= isReceipt)   # Cropped, unprocessed
    all_results.extend(psm_results_3)
    if isReceipt: all_components.extend(component_results_3) 

    psm_results_4, component_results_4 = run_receipt_pipeline(image_path, test, True, True, isReceipt= isReceipt)    # Cropped, processed (skip if bad)
    all_results.extend(psm_results_4)
    if isReceipt: all_components.extend(component_results_4)
    
    final_results = merge_field_results(all_results)

    # Gerekli alanları kontrol et, yoksa None ata
    if isReceipt: must_exist = ["Tarih", "Fiş No", "Toplam", "Belge Türü"]
    if not isReceipt: must_exist = ["Tarih", "Fatura No", "Toplam", "Belge Türü", "KDV Oranı"]

    for field in must_exist:
        if field not in final_results:
            final_results[field] = None

    if isReceipt and final_results["Toplam"] != None:
        final_results["Alt Kalemler"] = find_best_components(all_components, final_results["Toplam"], test)

    if isReceipt and final_results["Toplam"] is None:
        final_results["Alt Kalemler"] = find_most_common_components_by_sum(all_components)
        if final_results["Alt Kalemler"]:
            final_results["Toplam"] = round(sum(i["Harcama Tutarı"] for i in final_results["Alt Kalemler"]), 2)

    if test:
        print("\nGrouped results by field:\n")

        def print_grouped_field(field_name):  #Güzel formatlı outputları gösteren fonksiyon, test açıksa çağrılıyor
            values = []
            for i, result in enumerate(all_results):
                if field_name in result:
                    model_idx = i // 4 + 1
                    psm_idx = [11, 4, 6, 3][i % 4]
                    values.append(f"  Model {model_idx} - PSM {psm_idx}: {result[field_name]}")
            if values:
                print(f"{field_name} values:")
                print('\n'.join(values))
            else:
                print(f"{field_name} values: None")
            print()

        for field in final_results:
            print_grouped_field(field)        

        print("Final merged result:\n")
        for key, val in final_results.items():
            if key != "Alt Kalemler":
                print(f" {key}: {val}")
            else:
                print(f" {key}:")
                for item in val:
                    name = item.get("Masraf Açıklama", "Unnamed")
                    kdv = item.get("KDV Oranı", "-")
                    amount = item.get("Harcama Tutarı", "-")
                    print(f"   - {name} | KDV: %{kdv} | Tutar: {amount:.2f}")
        print("\n")

    # Sonuçları results.txt dosyasına JSON olarak kaydet ve döndür
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.txt")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)

    return final_results

    
if __name__ == "__main__":
    image_path = "Karel/receipts/S1.jpg"  #Fotoğraf directory'si

    run(image_path, True)