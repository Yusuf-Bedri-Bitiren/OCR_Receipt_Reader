# Author(s): Yaman Türköz, Yusuf Bedri Bitiren
#
# Makbuz ve faturaların OCR öncesi görüntü işleme aşamalarını içerir.
#
# Görüntüyü kırpma (crop), çözünürlük yükseltme (upscale), gürültü azaltma ve adaptif thresholding
# gibi adımlarla OCR performansını artırmayı hedefler.

from PIL import Image
import numpy as np
import cv2
import os
from autocrop_kh import autocrop
import torch

# NumPy dizisini PIL Image objesine çevirir, tip ve kanal uyumsuzluklarını giderir
def convert_to_pil(image_array):
    # if test_active: print(f"[DEBUG] Shape: {image_array.shape}, Dtype: {image_array.dtype}, Max: {np.max(image_array)}")

    if image_array.dtype in [np.float32, np.float64]:
        if np.max(image_array) > 1.5:  # 0-255 aralığında float ise uint8'e dönüştür
            image_array = np.clip(image_array, 0, 255).astype(np.uint8)
        else:                         # 0-1 aralığında float ise 255 ile çarpıp dönüştür
            image_array = (image_array * 255).astype(np.uint8)
    elif image_array.dtype != np.uint8:
        image_array = image_array.astype(np.uint8)

    if len(image_array.shape) == 2:  # Gri tonlu ise RGB kanalına çevir
        image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)

    return Image.fromarray(image_array)

# OCR için uygun şekilde görüntüyü ön işlemden geçirir:
# Yüksekliği düşükse büyütür, gri tonlamaya çevirir, adaptif eşikleme ve bulanıklaştırma uygular
def preprocess_for_ocr(pil_img: Image.Image) -> Image.Image:
        
    pil = upscale_image(pil_img) # Eğer belli bir çözünürlüğün altındaysa upscale ediyor

    img = np.array(pil.convert("L")) # PIL -> NumPy (grayscale)

    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10) # Adaptive Thresholding (yazıları netleştirir)
    
    img = cv2.medianBlur(img, 3)  # Gürültü azaltma

    return Image.fromarray(img) # NumPy -> PIL

# Görüntü belirlenen alt çözünürlüğün altındaysa belirli oranda büyütür
def upscale_image(pil_img: Image.Image, scale=2.0) -> Image.Image:
    if needs_upscale(pil_img):
        new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
        print("Upscale applied")
        return pil_img.resize(new_size, Image.LANCZOS)
    print("Upscale skipped")
    return pil_img

# Görüntünün eni veya boyu minimum piksel değerinin altındaysa True döner
def needs_upscale(pil_img: Image.Image, min_side=800) -> bool:
    """Return True if either side is below min_side px."""
    w, h = pil_img.size
    print(f"Image size {w} by {h}")
    return w < min_side or h < min_side

# Görüntüyü model ile kırpar ve gerekirse test için kaydeder
# CUDA destekliyse GPU üzerinde çalışır, yoksa CPU kullanır
# test_active True ise kırpılmış görüntüyü processed_receipts klasörüne kaydeder
def crop(image_path, test_active = False):    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "models", "autocrop_model_v2.pth")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    cropped_array = autocrop(img_path=image_path, model_path=model_path, device=device)
    cropped_img = convert_to_pil(cropped_array)

    if test_active:
        processed_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_receipts") 
        filename = os.path.basename(image_path)    
        processed_image_path = os.path.join(processed_dir, f"{os.path.splitext(filename)[0]}_cropped.jpg")
        cropped_img.save(processed_image_path)

        print(f"Processed image saved at: {processed_image_path}") 

    return cropped_img

# Normalde kullanılan bir foknskiyon değil, sadece debug için fotoğrafın işlenmiş halini gösteriyor
def openCV(image_path, test_active):

    img = Image.open(image_path)

    processed_img = preprocess_for_ocr(img)

    if test_active:
        processed_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_receipts")

        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir)

        filename = os.path.basename(image_path)
        processed_image_path = os.path.join(processed_dir, f"{os.path.splitext(filename)[0]}_processed.jpg")
        processed_img.save(processed_image_path)

        print(f"Processed image saved at: {processed_image_path}")

    return processed_img


if __name__ == "__main__":
    image_path = "Karel/receipts/S1.jpg"

    crop(image_path, True)

    openCV(image_path, True)