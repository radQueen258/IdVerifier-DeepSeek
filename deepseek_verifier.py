from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import base64
import requests
import json

app = FastAPI(title="ID Card Verifier via DeepSeek")

DEEPSEEK_API_KEY = "sk-a42aa6f136b44e66a5f4340d8dd03b2c"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

class VerificationResponse(BaseModel):
    is_id_card: bool
    confidence: float
    type: str


@app.post("/verify", response_model=VerificationResponse)
async def verify(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid image"})

    payload = {
        "model": "deepseek-ai/deepseek-vl2",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Analyze the image and answer ONLY in JSON format:\n"
                            "{ \"is_id_card\": true/false, "
                            "\"confidence\": number between 0 and 1, "
                            "\"type\": \"id card\" | \"passport\" | \"driver license\" | \"unknown\" }\n"
                            "Do not include explanations."
                        )
                    },
                    {
                        "type": "input_image",
                        "image": image_base64
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
    result = response.json()

    text = result["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(text)
        return parsed
    except:
        return JSONResponse(status_code=500, content={"error": "Model returned invalid JSON", "raw": text})
