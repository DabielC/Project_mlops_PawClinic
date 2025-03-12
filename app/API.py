from fastapi import FastAPI, File, UploadFile, Form, Query, Depends
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

from torchvision import models, transforms
from PIL import Image
import torch
import io
import glob

import os
import shutil

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Define class mapping
map_class = {
    0: 'Dermatitis',
    1: 'demodicosis',
    2: 'Healthy',
    3: 'Hypersensitivity',
    4: 'Fungal_infections',
    5: 'ringworm'
}

# Load model
model_paths = glob.glob("./app/*.pth")  # ตรวจสอบว่า path ของไฟล์โมเดลถูกต้อง
model = models.mobilenet_v3_small(num_classes=len(map_class))

if model_paths:
    model_path = model_paths[0]
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    model.eval()
else:
    raise FileNotFoundError("ไม่พบไฟล์ .pth ในโฟลเดอร์ app")

# ทำให้โมเดลทำงานกับ CPU หรือ GPU
model = model.to(torch.device('cpu'))

# Define image preprocessing
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # Read image
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # Preprocess image
    image = transform(image).unsqueeze(0)  # Add batch dimension
    
    # Perform inference
    with torch.no_grad():
        outputs = model(image)
        probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
    
    scores = probabilities.tolist()
    predicted_class_idx = torch.argmax(probabilities).item()
    predicted_class = map_class[predicted_class_idx]
    
    # Return results
    return {
        "predicted_class": predicted_class, 
        "scores": {map_class[i]: scores[i] for i in range(len(scores))}
    }

from google import genai
from google.genai import types

generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_LOW_AND_ABOVE",  # Block most
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_LOW_AND_ABOVE",  # Block most
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_LOW_AND_ABOVE",  # Block most
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_CIVIC_INTEGRITY",
                threshold="BLOCK_LOW_AND_ABOVE",  # Block most
            ),
        ],
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text="""คุณคือสัตวแพทย์ที่จะตอบคำถามเกี่ยวกับน้องหมา"""),
        ],
    )

client = genai.Client(
        api_key="gemini_api_key -> put your key here",
    )


files = []
contents = []

def generate():
    response = client.models.generate_content(
    model="gemini-2.0-flash", contents=contents, config=generate_content_config)
    return response.text

def ask_model(text=None, image=None):
    global contents, files
    if text != None and image == None:
        contents.append(
            types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=text),
            ]
            )
        )
    elif text != None and image != None:
        image_file = client.files.upload(file=image)
        files.append(image_file)
        contents.append(
            types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=files[-1].uri,
                    mime_type=files[-1].mime_type,
                ),
                types.Part.from_text(text=text)
                ]
            )
        )
    output = generate()
    contents.append(
            types.Content(
            role="model",
            parts=[
                types.Part.from_text(text=output),
            ]
            )
        )
    
    return output

UPLOAD_FOLDER = "./app/uploads"  # กำหนดโฟลเดอร์อัปโหลด
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # สร้างโฟลเดอร์ถ้ายังไม่มี

@app.post("/chat")
async def chat(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    reset: Optional[int] = Form(None)
):
    global files, contents

    if reset == 1:
        files = []
        contents = []
        
        # ลบทั้งโฟลเดอร์ uploads แล้วสร้างใหม่
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)  # ลบโฟลเดอร์และไฟล์ทั้งหมดในนั้น
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # สร้างโฟลเดอร์ใหม่

        return {"message": "Chat history and uploaded files have been cleared."}

    # บันทึกไฟล์ลงโฟลเดอร์ก่อน (ถ้ามีไฟล์)
    file_path = None
    if file:
        image_bytes = await file.read()  # อ่านไฟล์เป็น byte
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")  # เปิดไฟล์ด้วย PIL

        # กำหนด path สำหรับบันทึกไฟล์
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        
        # บันทึกไฟล์โดยใช้ PIL
        image.save(file_path)  

    if text is None and file is None:
        return {"message": "No text input."}

    if text is None and file is not None:
        return {"message": "Please input Text together with Picture."}

    if text is not None and file is None:
        return {
            "message": "OK",
            "response": ask_model(text)
        }
    
    if text is not None and file is not None:
        return {
            "message": "OK",
            "response": ask_model(text, file_path),
        }
    
    