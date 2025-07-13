from langchain.llms import Ollama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from openai import OpenAI
import os

class LastFactFilter:
    def __init__(self, model_name: str = "qwen2.5:14b-instruct"):
        self.model_name = model_name
        self.prompt_template = """
        Вот транскрипт видео:
        {transcript}

        Твоя задача — внимательно проанализировать весь транскрипт и определить **только один последний факт**, который был озвучен в конце этого текста. Под фактом понимается конкретное, чётко выраженное утверждение, событие, результат или ключевая информация, которая завершает обсуждение в видео.

        Обрати внимание:
        - Игнорируй вводные, приветствия, прощания и общие рассуждения, если они не содержат важного факта.
        - Если в конце транскрипта есть несколько предложений, выбери именно тот факт, который логически завершает повествование.
        - Сделай краткое и ёмкое резюме этого последнего факта, используя простой и понятный русский язык.
        - Не добавляй ничего лишнего, ответ должен быть максимально сжатым и по существу.

        Пожалуйста, ответь только сжато на русском языке.

        """
        self.prompt = PromptTemplate(
            input_variables=["transcript"], template=self.prompt_template
        )
        self.llm = Ollama(model=self.model_name, base_url="http://84.201.132.151:11450")
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def summarize_last_fact(self, transcript: str) -> str:
        result = self.chain.run(transcript=transcript)
        return result.strip()
    

class LastFactOpenAI:
    def __init__(self, model_name: str = "google/gemini-2.0-flash-exp:free"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model_name = model_name

    def summarize_last_fact(self, transcript: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": f"""
        Вот транскрипт видео:
        {transcript}

        Твоя задача — внимательно проанализировать весь транскрипт и определить **только один последний факт**, который был озвучен в конце этого текста. Под фактом понимается конкретное, чётко выраженное утверждение, событие, результат или ключевая информация, которая завершает обсуждение в видео.

        Обрати внимание:
        - Игнорируй вводные, приветствия, прощания и общие рассуждения, если они не содержат важного факта.
        - Если в конце транскрипта есть несколько предложений, выбери именно тот факт, который логически завершает повествование.
        - Сделай краткое и ёмкое резюме этого последнего факта, используя простой и понятный русский язык.
        - Не добавляй ничего лишнего, ответ должен быть максимально сжатым и по существу.

        Пожалуйста, ответь только сжато на русском языке.

        """,
                },
            ],
        )
        return response.choices[0].message.content.strip()
