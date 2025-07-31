from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from main import run  # 'main.py' içindeki run(path) fonksiyonunu içe aktarıyoruz

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/ocr', methods=['POST'])
def ocr():
    if 'image' not in request.files:
        return jsonify({'error': 'Gönderilen istek "image" dosyası içermiyor.'}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'Dosya adı boş.'}), 400

    # Dosyayı kaydet
    temp_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
    image_file.save(temp_path)

    try:
        result = run(temp_path, test=False)  # test=True olursa debug dosyaları da yaratır
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)