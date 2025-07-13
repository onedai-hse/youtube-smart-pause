from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import os
from typing import List
from dotenv import load_dotenv
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from collections import defaultdict
from filter import LastFactFilter

load_dotenv()
app = FastAPI(title="YouTube Pause Assistant API")

last_fact_filter = LastFactFilter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FactCheckRequest(BaseModel):
    statement: str


class VideoAnalysisRequest(BaseModel):
    video_id: str
    current_time: float
    context_seconds: int = 30  # По умолчанию 30 секунд


class FactCheckResponse(BaseModel):
    final_decision: str  # "true", "false", or "unknown"
    short_explanation: str
    sources: List[str]


class VideoAnalysisResponse(BaseModel):
    video_id: str
    current_time: float
    segment_info: str
    analyzed_fact: str
    fact_check: FactCheckResponse


class FactCheckEndpointResponse(BaseModel):
    statement: str
    fact_check: FactCheckResponse


# Настройки прокси (если нужны)
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")


def format_time(sec: float):
    """Форматирует время в MM:SS"""
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"


def get_segment_transcript(
    video_id: str, end_time: float, context_seconds: int = 30, languages=("ru", "en")
):
    """Получает транскрипт сегмента"""
    try:
        start_time = max(0, end_time - context_seconds)

        # Настройка прокси если есть учетные данные
        if PROXY_USERNAME and PROXY_PASSWORD:
            ytt = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=PROXY_USERNAME, proxy_password=PROXY_PASSWORD
                )
            )
        else:
            ytt = YouTubeTranscriptApi()

        # Получаем транскрипт
        transcript = ytt.get_transcript(video_id, languages=list(languages))

        # Группируем по времени
        grouped = defaultdict(list)
        full_text = []

        for item in transcript:
            item_start = item.get("start", 0)

            if item_start < start_time:
                continue
            if item_start > end_time:
                break

            label = format_time(item_start - start_time)
            text = item.get("text", "")
            grouped[label].append(text)
            full_text.append(text)

        combined_text = " ".join(full_text)

        return {
            "start_time": start_time,
            "end_time": end_time,
            "grouped": dict(grouped),
            "full_text": combined_text,
            "segment_info": f"Сегмент с {format_time(start_time)} до {format_time(end_time)}",
        }

    except Exception as e:
        raise Exception(f"Ошибка получения транскрипта: {str(e)}")


PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


async def get_perplexity_fact_check(
    statement: str, context_info: str = ""
) -> FactCheckResponse:
    """Get structured fact-check response from Perplexity API"""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="PERPLEXITY_API_KEY environment variable not set")

    prompt = f"""
Here's a statement from the middle of a youtube video, please fact-check it: 

<statement>
{statement}
</statement>

Analyze the statement and provide a structured response with:
1. A final decision (true/false/unknown)
2. A short 2-3 sentence explanation based on reliable sources
3. Source links that were used for verification

Be precise and concise in your assessment.
"""

    # JSON Schema for structured output
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "fact_check_response",
            "schema": {
                "type": "object",
                "properties": {
                    "final_decision": {
                        "type": "string",
                        "enum": ["true", "false", "unknown"],
                        "description": "The final fact-checking decision"
                    },
                    "short_explanation": {
                        "type": "string",
                        "description": "A 2-3 sentence explanation of the fact-checking result based on sources"
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of source links used for verification"
                    }
                },
                "required": ["final_decision", "short_explanation", "sources"],
                "additionalProperties": False
            }
        }
    }

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant that helps to fact-check statements from youtube videos. Always provide structured responses with clear decisions and reliable sources.",
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": response_format,
        "max_tokens": 1500,
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                PERPLEXITY_API_URL, json=payload, headers=headers
            )
            
            if response.status_code != 200:
                error_text = response.text
                print(f"!!! Perplexity API Error: {response.status_code} - {error_text}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"API request failed with status {response.status_code}: {error_text}"
                )

            response_data = response.json()
            
            # Extract the structured content
            if "choices" in response_data and len(response_data["choices"]) > 0:
                content = response_data["choices"][0]["message"]["content"]
                
                try:
                    # Parse the JSON response
                    parsed_response = json.loads(content)
                    return FactCheckResponse(**parsed_response)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON response: {content}")
                    raise HTTPException(status_code=500, detail="Failed to parse API response")
            else:
                raise HTTPException(status_code=500, detail="No response from API")

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timed out. Please try again.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Network error occurred: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {str(e)}")


@app.post("/analyze", response_model=VideoAnalysisResponse)
async def analyze_video(request: VideoAnalysisRequest):
    """Анализ содержимого YouTube видео в определенный момент времени"""

    try:
        # 1. Получаем транскрипт сегмента
        transcript_data = get_segment_transcript(
            request.video_id, request.current_time, request.context_seconds
        )

        full_transcript = transcript_data["full_text"]
        if not full_transcript.strip():
            raise HTTPException(
                status_code=404, detail="Транскрипт для данного видео недоступен"
            )

        # 2. Выделяем последний факт с помощью фильтра
        last_fact = last_fact_filter.summarize_last_fact(full_transcript)

        # 3. Выводим информацию в консоль для отладки
        print("\n--- Original Transcript ---")
        print(f"Segment: {transcript_data['segment_info']}")
        print(f"Text: {full_transcript}")
        print("---------------------------\n")

        print("\n--- Filtered Fact for Perplexity ---")
        print(f"Fact: {last_fact}")
        print("------------------------------------\n")

        # 4. Анализируем отфильтрованный факт через Perplexity
        fact_check_result = await get_perplexity_fact_check(last_fact, transcript_data["segment_info"])
        
        return VideoAnalysisResponse(
            video_id=request.video_id,
            current_time=request.current_time,
            segment_info=transcript_data["segment_info"],
            analyzed_fact=last_fact,
            fact_check=fact_check_result
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/fact-check", response_model=FactCheckEndpointResponse)
async def fact_check(request: FactCheckRequest):
    """Проверка фактов для произвольного утверждения"""
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Утверждение не может быть пустым")

    if len(request.statement) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Утверждение слишком длинное (максимум 1000 символов)",
        )

    fact_check_result = await get_perplexity_fact_check(request.statement)
    return FactCheckEndpointResponse(
        statement=request.statement,
        fact_check=fact_check_result
    )


@app.get("/transcript/{video_id}")
async def get_transcript_preview(
    video_id: str, start_time: float = 0, duration: int = 60
):
    """Получить превью транскрипта для отладки"""
    try:
        transcript_data = get_segment_transcript(
            video_id, start_time + duration, duration
        )
        return {
            "video_id": video_id,
            "segment_info": transcript_data["segment_info"],
            "text_length": len(transcript_data["full_text"]),
            "preview": (
                transcript_data["full_text"][:500] + "..."
                if len(transcript_data["full_text"]) > 500
                else transcript_data["full_text"]
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "YouTube Pause Assistant API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
