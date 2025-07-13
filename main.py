from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
import os
from typing import AsyncGenerator
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


async def stream_perplexity_response(
    statement: str, context_info: str = ""
) -> AsyncGenerator[str, None]:
    """Stream response from Perplexity API"""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        yield "Error: PERPLEXITY_API_KEY environment variable not set"
        return

    prompt = f"""Проанализируй содержимое YouTube видео на предмет фактической точности и объясни ключевые понятия:

{context_info}

Содержимое: "{statement}"

Пожалуйста:
1. Выдели ключевые фактические утверждения
2. Проверь их точность, используя надежные источники
3. Объясни технические термины или концепции простым языком
4. Предоставь дополнительный контекст и полезную информацию
5. Отвечай **кратко, ёмко** и на том же языке, что и содержимое"""

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "Ты полезный фактчекер и преподаватель. Анализируй контент на точность, объясняй концепции понятно и предоставляй образовательный контекст. Отвечай структурированно и подробно.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        "max_tokens": 1500,
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST", PERPLEXITY_API_URL, json=payload, headers=headers
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    # Оставляем только лог ошибки
                    print(
                        f"!!! Perplexity API Error: {response.status_code} - {error_text.decode()}"
                    )
                    yield f"Error: API request failed with status {response.status_code}: {error_text.decode()}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
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


@app.post("/analyze")
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
        return StreamingResponse(
            stream_perplexity_response(last_fact, transcript_data["segment_info"]),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/fact-check")
async def fact_check(request: FactCheckRequest):
    """Проверка фактов для произвольного утверждения"""
    if not request.statement.strip():
        raise HTTPException(status_code=400, detail="Утверждение не может быть пустым")

    if len(request.statement) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Утверждение слишком длинное (максимум 1000 символов)",
        )

    return StreamingResponse(
        stream_perplexity_response(request.statement),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
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
