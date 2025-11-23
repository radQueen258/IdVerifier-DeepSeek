from fastapi import FastAPI, UploadFile, File
import base64
import requests

app = FastAPI()

DEEPSEEK_API_KEY = "sk-3a178833406748dea5ea5e581b3e2e13"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

@app.post("/verify")
async def verify(file: UploadFile = File(...)):

    # Read image bytes
    image_bytes = await file.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # DeepSeek-VL2 uses special message format
    payload = {
        "model": "deepseek-vl2",
        "messages": [
            {
                "role": "user",
                "content": (
                    "<image>\n"
                    "Is this an identity document? "
                    "Reply ONLY in this JSON format:\n"
                    "{\"is_id\": true/false, \"confidence\": number, \"type\": \"id card/passport/license/unknown\"}."
                ),
                "images": [image_b64]
            },
            {
                "role": "assistant",
                "content": ""
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(DEEPSEEK_URL, json=payload, headers=headers)
    return response.json()
