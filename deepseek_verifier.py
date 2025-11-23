from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import requests
import json
import re

app = FastAPI(title="ID Card Verifier via DeepSeek")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEEPSEEK_API_KEY = "sk-a42aa6f136b44e66a5f4340d8dd03b2c"  # Consider using environment variables
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

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
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    # Updated payload structure for DeepSeek VL
    payload = {
        "model": "deepseek-chat",  # Use deepseek-chat which supports vision
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

# Additional endpoint for batch verification
@app.post("/verify-batch")
async def verify_batch(files: list[UploadFile] = File(...)):
    """Verify multiple ID card images at once"""
    results = []
    
    for file in files:
        try:
            # Create a new UploadFile-like object for the single verify endpoint
            class SimpleUploadFile:
                def __init__(self, file):
                    self.file = file
                    self.filename = file.filename
                    self.content_type = file.content_type
                
                async def read(self):
                    return await self.file.read()
            
            result = await verify(SimpleUploadFile(file))
            results.append({
                "filename": file.filename,
                "result": result
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {"results": results}

# Enhanced verification with more details
class DetailedVerificationResponse(BaseModel):
    is_id_card: bool
    confidence: float
    type: str
    side: str
    features_found: list[str]
    quality_check: str

@app.post("/verify-detailed")
async def verify_detailed(file: UploadFile = File(...)):
    """Get more detailed verification results"""
    try:
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a document verification expert. Analyze ID documents thoroughly."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this identity document image thoroughly. "
                            "Respond with ONLY valid JSON:\n"
                            "{\n"
                            '  "is_id_card": true/false,\n'
                            '  "confidence": 0.0-1.0,\n'
                            '  "type": "id_card" | "passport" | "driver_license" | "other",\n'
                            '  "side": "front" | "back" | "unknown",\n'
                            '  "features_found": ["photo", "name", "id_number", "birth_date", "address", "barcode", "mrz"],\n'
                            '  "quality_check": "good" | "blurry" | "cropped" | "reflection"\n'
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
        "max_tokens": 1000
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
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise HTTPException(status_code=500, detail="No valid JSON in response")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
