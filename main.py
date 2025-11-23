from fastapi import FastAPI, UploadFile, File
import base64
import requests
import json

app = FastAPI()

DEEPSEEK_API_KEY = "YOUR_KEY"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

@app.post("/verify")
async def verify(file: UploadFile = File(...)):

    # Read image bytes
    image_bytes = await file.read()
    
    # Encode to base64 (raw image, NOT data URL)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": "deepseek-vl2",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Is this an identity document? Return JSON only: {is_id: bool, confidence: number, type: string}"
                    },
                    {
                        "type": "image",
                        "image": {
                            "base64": image_b64
                        }
                    }
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(DEEPSEEK_URL, json=payload, headers=headers)

    return {"deepseek_raw": response.json()}
