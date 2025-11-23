from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import requests
import json
import re
import os

app = FastAPI(title="ID Card Verifier via DeepSeek")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-a42aa6f136b44e66a5f4340d8dd03b2c")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VerificationResponse(BaseModel):
    is_id_card: bool
    confidence: float
    type: str

@app.get("/")
async def health_check():
    return {"status": "healthy", "message": "ID Card Verification API using DeepSeek"}

@app.post("/verify", response_model=VerificationResponse)
async def verify(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and encode image
        image_bytes = await file.read()
        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="Image too large")
            
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a document verification expert. Analyze the image and respond with ONLY valid JSON format."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this image and determine if it's an identity document. "
                            "Respond with ONLY this JSON format, no other text:\n"
                            "{\n"
                            '  "is_id_card": true/false,\n'
                            '  "confidence": 0.85,\n'
                            '  "type": "id_card_front" | "id_card_back" | "passport" | "driver_license" | "other"\n'
                            "}"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        text = result["choices"][0]["message"]["content"]
        
        # Clean the response - extract JSON if there's extra text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            parsed = json.loads(json_str)
            
            # Validate required fields
            if all(key in parsed for key in ["is_id_card", "confidence", "type"]):
                return parsed
            else:
                raise ValueError("Missing required fields in response")
        else:
            raise ValueError("No JSON found in response")
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"DeepSeek API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON response from model: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
