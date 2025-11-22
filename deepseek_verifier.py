import requests
from fastapi import FastAPI, UploadFile, File
import base64

app = FastAPI()

DEEPSEEK_API_KEY = "sk-a42aa6f136b44e66a5f4340d8dd03b2c"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

@app.post("/verify")
async def verify(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{image_base64}"

    payload = {
        "model": "deepseek-vl2",
        "messages": [
            {
                "role": "user",
                "content": [
                    { "type": "text", "text": "Is this image an identity document? Respond in JSON." },
                    { "type": "image_url", "image_url": data_url }
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(DEEPSEEK_URL, json=payload, headers=headers)
    result = response.json()

    return result
