#pip install youtube-transcript-api

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from collections import defaultdict

end_time_seconds = 300  # укажите на какой секунде нажали кнопку
video_id = "8L51FUsjMxA"  # video_id, взять из ссылки после v....
PROXY_USERNAME = ""
PROXY_PASSWORD = ""


def format_time(sec: float):
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"


def get_segment_transcript(video_id: str, end_time: float, languages=('en', 'ru')):
    start_time = max(0, end_time - 120)
    ytt = YouTubeTranscriptApi(
        proxy_config=WebshareProxyConfig(
            proxy_username=PROXY_USERNAME,
            proxy_password=PROXY_PASSWORD
        )
    )
    transcript = ytt.get_transcript(video_id, languages=list(languages))

    grouped = defaultdict(list)
    full = []

    for item in transcript:
        st = item.start if hasattr(item, 'start') else item['start']
        if st < start_time:
            continue
        if st > end_time:
            break
        label = format_time(st - start_time)
        txt = item.text if hasattr(item, 'text') else item['text']
        grouped[label].append(txt)
        full.append(txt)

    return start_time, grouped, " ".join(full)


if __name__ == "__main__":
    st, grp, text = get_segment_transcript(video_id, end_time_seconds)
    print(f"Фрагмент с {format_time(st)} до {format_time(end_time_seconds)}:")
    print(text)
