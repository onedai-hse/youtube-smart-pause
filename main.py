from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
import os
from typing import AsyncGenerator, List, Optional
import logging

from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class Source(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None

class FactCheckResult(BaseModel):
    verdict: str  # "true", "false", "unclear"
    status: dict  # {"type": "true/false/unclear", "icon": "✓/✗/?", "text": "Описание"}
    confidence: float
    explanation: str
    sources: List[Source]
    evidence_summary: str
    context: Optional[str] = None

class StructuredFactCheckResponse(BaseModel):
    result: FactCheckResult
    statement: str

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

async def get_structured_fact_check_fallback(statement: str) -> StructuredFactCheckResponse:
    """Fallback function using regular API call and parsing the response"""
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="PERPLEXITY_API_KEY environment variable not set")
    
    logger.info(f"Using fallback method for statement: {statement[:50]}...")
    
    prompt = f"""Проверьте это утверждение, используя надежные академические и новостные источники: "{statement}"

Проанализируйте утверждение и предоставьте ответ в следующем JSON формате:
{{
    "verdict": "true/false/unclear",
    "confidence": 0.85,
    "explanation": "Подробное объяснение",
    "evidence_summary": "Краткое резюме доказательств",
    "context": "Дополнительный контекст (если есть)",
    "sources": [
        {{
            "title": "Название источника",
            "url": "https://example.com",
            "snippet": "Релевантный отрывок"
        }}
    ]
}}

Вердикт должен быть одним из трех: "true", "false", "unclear".
Ответьте на том же языке, что и утверждение."""

    payload = {
        "model": "sonar-small",
        "messages": [
            {
                "role": "system", 
                "content": "Вы эксперт по проверке фактов. Всегда отвечайте в формате JSON с указанными полями."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2000
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        logger.info("Sending fallback request to Perplexity API...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                PERPLEXITY_API_URL,
                json=payload,
                headers=headers
            )
            
            logger.info(f"Fallback API response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Fallback API request failed: {error_text}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"API request failed: {error_text}"
                )
            
            response_data = response.json()
            content = response_data["choices"][0].get("message", {}).get("content", "")
            
            if not content:
                raise HTTPException(status_code=500, detail="No content in API response")
            
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result_data = json.loads(json_str)
            else:
                # If no JSON found, create a basic response
                result_data = {
                    "verdict": "unclear",
                    "confidence": 0.0,
                    "explanation": content,
                    "evidence_summary": "Не удалось структурировать ответ",
                    "sources": []
                }
            
            # Convert sources to Source objects
            sources = []
            for source_data in result_data.get("sources", []):
                sources.append(Source(
                    title=source_data.get("title", ""),
                    url=source_data.get("url", ""),
                    snippet=source_data.get("snippet")
                ))
            
            # Create status object for frontend
            verdict = result_data.get("verdict", "unclear")
            status_map = {
                "true": {"type": "true", "icon": "✓", "text": "Утверждение истинно"},
                "false": {"type": "false", "icon": "✗", "text": "Утверждение ложно"},
                "unclear": {"type": "unclear", "icon": "?", "text": "Неопределено"}
            }
            
            fact_check_result = FactCheckResult(
                verdict=verdict,
                status=status_map.get(verdict, {"type": "unclear", "icon": "?", "text": "Неопределено"}),
                confidence=result_data.get("confidence", 0.0),
                explanation=result_data.get("explanation", ""),
                evidence_summary=result_data.get("evidence_summary", ""),
                context=result_data.get("context"),
                sources=sources
            )
            
            return StructuredFactCheckResponse(
                result=fact_check_result,
                statement=statement
            )
                
    except Exception as e:
        logger.error(f"Fallback method failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fallback method failed: {str(e)}")

async def get_structured_fact_check(statement: str) -> StructuredFactCheckResponse:
    """Get structured fact check response from Perplexity API"""
    
    return await get_structured_fact_check_fallback(statement)

async def stream_perplexity_response(statement: str) -> AsyncGenerator[str, None]:
    """Stream response from Perplexity API (legacy function)"""
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        yield "Error: PERPLEXITY_API_KEY environment variable not set"
        return
    
    prompt = f"""Verify this claim using credible academic and news sources: "{statement}. If statement is true, return True. If statement is false, return False. If statement is unclear, return Unclear." 

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
    """Fact-check a statement using Perplexity API (streaming)"""
    
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

@app.post("/fact-check-structured", response_model=StructuredFactCheckResponse)
async def fact_check_structured(request: FactCheckRequest):
    """Fact-check a statement using Perplexity API with structured output and sources"""
    
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Statement cannot be empty")
    
    if len(request.statement) > 500:
        raise HTTPException(status_code=400, detail="Statement too long (max 500 characters)")
    
    return await get_structured_fact_check(request.statement)

@app.post("/fact-check-status")
async def fact_check_status(request: FactCheckRequest):
    """Get only the status verdict in a simple format for frontend"""
    
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Statement cannot be empty")
    
    if len(request.statement) > 500:
        raise HTTPException(status_code=400, detail="Statement too long (max 500 characters)")
    
    try:
        structured_response = await get_structured_fact_check(request.statement)
        return {
            "verdict": structured_response.result.status,
            "confidence": structured_response.result.confidence
        }
    except HTTPException:
        # Fallback to unclear if structured check fails
        return {
            "verdict": {"type": "unclear", "icon": "?", "text": "Неопределено"},
            "confidence": 0.0
        }
    
@app.post("/check-statement")
async def check_statement_endpoint(request: FactCheckRequest):
    """Check if statement is true, false, or unclear (legacy endpoint)"""
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Statement cannot be empty")
    
    if len(request.statement) > 500:
        raise HTTPException(status_code=400, detail="Statement too long (max 500 characters)")
    
    full_response = ""
    async for result in stream_perplexity_response(request.statement):
        full_response += result
    
    lower_response = full_response.lower()
    
    if "true" in lower_response and "false" not in lower_response:
        return {"verdict": {"type": "true", "icon": "✓", "text": "Утверждение истинно"}}
    elif "false" in lower_response and "true" not in lower_response:
        return {"verdict": {"type": "false", "icon": "✗", "text": "Утверждение ложно"}}
    elif "unclear" in lower_response or "uncertain" in lower_response:
        return {"verdict": {"type": "unclear", "icon": "?", "text": "Неопределено"}}
    else:
        true_count = len(lower_response.split("true")) - 1
        false_count = len(lower_response.split("false")) - 1
        
        if false_count > true_count:
            return {"verdict": {"type": "false", "icon": "✗", "text": "Утверждение ложно"}}
        elif true_count > false_count:
            return {"verdict": {"type": "true", "icon": "✓", "text": "Утверждение истинно"}}
        else:
            return {"verdict": {"type": "unclear", "icon": "?", "text": "Неопределено"}}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)