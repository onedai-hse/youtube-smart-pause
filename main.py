from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
import os
from typing import AsyncGenerator

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="YouTube Fact Checker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FactCheckRequest(BaseModel):
    statement: str

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

async def stream_perplexity_response(statement: str) -> AsyncGenerator[str, None]:
    """Stream response from Perplexity API"""
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        yield "Error: PERPLEXITY_API_KEY environment variable not set"
        return
    
    prompt = f"""Verify this claim using credible academic and news sources: "{statement}" 

Search for recent evidence, official statements, and expert analysis to determine accuracy. Answer in the same language as the statement."""

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system", 
                "content": "Provide clear, well-sourced fact-checking analysis. Structure responses with: verdict (True/False/Partially True/Unclear), evidence summary, source citations, and relevant context. "
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": True,
        "max_tokens": 1000
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                PERPLEXITY_API_URL,
                json=payload,
                headers=headers
            ) as response:
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"Error: API request failed with status {response.status_code}: {error_text.decode()}"
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        
                        if data.strip() == "[DONE]":
                            break
                            
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
                            
    except httpx.TimeoutException:
        yield "Error: Request timed out. Please try again."
    except httpx.RequestError as e:
        yield f"Error: Network error occurred: {str(e)}"
    except Exception as e:
        yield f"Error: Unexpected error occurred: {str(e)}"

@app.post("/fact-check")
async def fact_check(request: FactCheckRequest):
    """Fact-check a statement using Perplexity API"""
    
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Statement cannot be empty")
    
    if len(request.statement) > 500:
        raise HTTPException(status_code=400, detail="Statement too long (max 500 characters)")
    
    return StreamingResponse(
        stream_perplexity_response(request.statement),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)