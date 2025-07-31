import easyocr
from main import torch, np, Image, extract_text_from_image, re, Counter


easyocr_reader = easyocr.Reader(['tr'], gpu=torch.cuda.is_available())

def extract_text_easyocr(image: Image.Image):
    img = np.array(image.convert("RGB"))
    results = easyocr_reader.readtext(img)
    texts = [text for _, text, prob in results if prob > 0.25]
    return "\n".join(texts)

def extract_fatura_no_from_region_dynamic(pil_img: Image.Image):
    try:
        img = np.array(pil_img.convert("RGB"))
        results = easyocr_reader.readtext(img)

        for i, (bbox, text, prob) in enumerate(results):
            if prob < 0.3:
                continue
            cleaned = text.lower().replace(":", "").replace("ı", "i").replace(" ", "")
            
            if "faturano" in cleaned:
                # fatura no yazısının sol kutusu
                x_label = int(min([p[0] for p in bbox]))
                y_label_center = int((bbox[0][1] + bbox[2][1]) / 2)
                
                # Sağındaki kutuyu bul
                best_candidate = None
                min_dist = float('inf')
                for j, (bbox2, text2, prob2) in enumerate(results):
                    if i == j or prob2 < 0.3:
                        continue
                    x_candidate = int(min([p[0] for p in bbox2]))
                    y_candidate_center = int((bbox2[0][1] + bbox2[2][1]) / 2)

                    # Aynı satırda ve sağda olan kutu
                    if abs(y_candidate_center - y_label_center) < 30 and x_candidate > x_label:
                        dist = x_candidate - x_label
                        if dist < min_dist:
                            min_dist = dist
                            best_candidate = bbox2

                if best_candidate:
                    x1 = int(min(p[0] for p in best_candidate)) - 50
                    x2 = int(max(p[0] for p in best_candidate)) + 50
                    y1 = int(min(p[1] for p in best_candidate)) - 50
                    y2 = int(max(p[1] for p in best_candidate)) + 50

                    # Güvenli sınırlar
                    x1 = max(x1, 0)
                    y1 = max(y1, 0)
                    x2 = min(x2, pil_img.width)
                    y2 = min(y2, pil_img.height)

                    cropped_val = pil_img.crop((x1, y1, x2, y2))
                    cropped_val.save("debug_fatura_no_dynamic.jpg")

                    ocr_texts = []

                    # Tesseract ile farklı PSM değerlerinde dene
                    for psm in [6, 11, 3, 4]:
                        tess_text = extract_text_from_image(cropped_val, psm)
                        ocr_texts.append((tess_text, f"Tesseract PSM {psm}"))

                    # Tüm OCR çıktılarını debug.txt'ye yaz
                    with open("debug_fatura_no_dynamic_ocr.txt", "w", encoding="utf-8") as f:
                        for text, src in ocr_texts:
                            f.write(f"--- {src} ---\n{text}\n\n")

                    # Oylamayla en güvenilir sonucu bul
                    candidates = []
                    for text, _ in ocr_texts:
                        match = re.search(r"\b[A-Za-z]{3}[0-9]{13}\b", text)
                        if match:
                            candidates.append(match.group(0))

                    if candidates:
                        # En çok tekrar eden sonucu seç
                        return Counter(candidates).most_common(1)[0][0]

        return None
    except Exception as e:
        print(f"[HATA] Dinamik Fatura No tespiti başarısız: {e}")
        return None