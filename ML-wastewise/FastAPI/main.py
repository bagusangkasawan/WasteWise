from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import os
import shutil
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env and configure Gemini API
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Load model tanpa compile (untuk inference)
model = load_model('../save-model/model_dense.keras', compile=False)

class_names = ['Alas Kaki', 'Daun', 'Kaca', 'Kain Pakaian', 'Kardus', 'Kayu',
               'Kertas', 'Logam', 'Plastik', 'Sampah Elektronik', 'Sampah makanan', 'Sterofoam']

golongan_mapping = {
    "Alas Kaki": "Anorganik",
    "Daun": "Organik",
    "Kaca": "Anorganik",
    "Kain Pakaian": "Anorganik",
    "Kardus": "Organik",
    "Kayu": "Organik",
    "Kertas": "Organik",
    "Logam": "Anorganik",
    "Plastik": "Anorganik",
    "Sampah Elektronik": "Anorganik",
    "Sampah makanan": "Organik",
    "Sterofoam": "Anorganik"
}

def get_saran_gemini(nama_sampah):
    try:
        prompt = f'Berikan saya saran pengolahan sampah yang baik untuk jenis : {nama_sampah}, langsung berikan jawaban untuk user.'
        model_gemini = genai.GenerativeModel('gemini-2.0-flash-lite')
        response = model_gemini.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f'Gagal mendapatkan saran dari Gemini: {str(e)}'

def predict_image(file_path):
    img = image.load_img(file_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) / 255.0
    pred = model.predict(img_array)
    idx = np.argmax(pred)
    class_label = class_names[idx]
    confidence = float(np.max(pred)) * 100
    golongan = golongan_mapping.get(class_label, "Tidak diketahui")
    saran = get_saran_gemini(class_label)

    return {
        "Jenis Sampah": class_label,
        "Kategori": golongan,
        "Probabilitas": f"{confidence:.1f}%",
        "Rekomendasi pengolahan": saran
    }

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/klasifikasi-sampah")
async def classify_waste(request: Request, file: UploadFile = File(...)):
    temp_file = f"temp_{file.filename}"
    with open(temp_file, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        result = predict_image(temp_file)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        os.remove(temp_file)

    return templates.TemplateResponse("index.html", {"request": request, "result": result})
