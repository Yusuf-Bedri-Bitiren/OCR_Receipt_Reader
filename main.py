from autocrop_kh import autocrop
from PIL import Image
import pytesseract
import torch
import os
import json
import time, functools
from processImage import *
from postProcess import *

print(">>> Kod başladı <<<")

# Tesseract konumu
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def timed(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        print(f"[TIMING] {fn.__name__:25s}: {time.time() - start:.3f}s")
        return result
    return wrapper

# OCR fonksiyonu
@timed
def extract_text_from_image(image, config_psm = 6):  # Takes a PIL Image directly
    custom_config = f'--oem 3 --psm {config_psm} -l tur'
    text = pytesseract.image_to_string(image, config=custom_config)
    return text

# Asıl işlem akışı main yerine burada, test sistemi çalışsın diye
def run_receipt_pipeline(image_path, test_active = False, crop = True, pre_process = False, psm_values = [11, 4, 6, 3], isReceipt = False):

    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "models", "autocrop_model_v2.pth") #TODO bu kısım run() a alınabilir
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if crop:                                                # 1. Kırp
        cropped_array = autocrop(img_path=image_path, model_path=model_path, device=device)
        cropped_img = convert_to_pil(cropped_array)         # 2. Görüntüyü uygun formata çevir
    else:
        cropped_img = Image.open(image_path).convert("RGB")  # Croplamıyorsak dümdüz açıyoruz

    if pre_process:
        cropped_img = preprocess_for_ocr(cropped_img)   # Yeni: OCR öncesi preprocess et

    psm_results = []                                    # Muhtemelen yüksek kalite fotoğraflar için fazlasına gerek yok
    component_results = []                              # dict listesi listesi

    if test_active:
        output_folder = os.path.join(current_dir, "ocr_outputs")     # Folder where results will be saved    

        if not os.path.exists(output_folder):    # Create the folder if it doesn't exist
            os.makedirs(output_folder)

    for value in psm_values:
        text = extract_text_from_image(cropped_img, value)      # 3. OCR işlemi (yukarıdaki psm_values ile tek tek)
        psm_results.append(extract_fields(text, isReceipt))                # 4. Alanları regex ile ayıkla 
        if value != 11 and isReceipt: component_results.append(parse_items(text, test_active))       # Alt kalemleri çıkar ve ekle, 11 alt kalem için kötü
        if test_active:
            iteration = (int(crop) * 2) + int(pre_process) + 1
            filename = f"output_ite_{iteration}_psm_{value}.txt"
            
            with open(os.path.join(output_folder, filename), 'w', encoding='utf-8') as file:
                file.write(text)

        # if test_active:
        #     print(f"\n[Fotoğraf işlendikten sonra OCR'dan Gelen Ham Metin (psm {value})]:\n")
        #     print(text)
                
    return psm_results, component_results

def run(image_path, test=False):
    all_results = []  
    all_components = []

    isReceipt = is_receipt(extract_text_from_image(image_path, 3)) | is_receipt(extract_text_from_image(image_path, 6)) | is_receipt(extract_text_from_image(image_path, 4)) | is_receipt(extract_text_from_image(image_path, 11))
    if test: print(f"This is a receipt: {isReceipt}")


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

    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.txt")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)

    return final_results

    
if __name__ == "__main__":
    image_path = "Karel/receipts/S24.jpg"    

    start_time = time.time()         

    # # Tüm senaryoları deneyip seçen fonksiyon
    run(image_path, True)

    # for i in range(1, 35):
    #     filename = f"S{i}.jpg"
    #     filepath = os.path.join("Karel/receipts", filename)

    #     if not os.path.exists(filepath):
    #         print(f"❌ Missing file: {filepath}")
    #         continue

    #     print(f"\n🧾 Testing {filename}...")
    #     run(filepath, False)    

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"\n⏱️ Total processing time: {elapsed:.2f} seconds\n")