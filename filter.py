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
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model_name = os.getenv("OPENROUTER_MODEL_NAME")

    def summarize_last_fact(self, transcript: str) -> str:
        print("transcript", transcript)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": f"""
Here is a video transcript:
<transcript>
{transcript}
</transcript>

Your task is to carefully read the piece of transcript that we sent and identify only one final fact that was stated at the end of this text. By fact, we mean a specific, clearly expressed statement, event, result, or key information that concludes the discussion in the video.
Pay attention:
- Ignore introductions, greetings, farewells, and general reasoning if they don't contain important facts.
- If there are several sentences at the end of the transcript, choose exactly that fact which logically concludes the narrative.
- Make a brief and concise summary of this final fact, using simple and clear English.
- Don't add anything unnecessary, the answer should be as compressed and to the point as possible.
        """,
                },
            ],
        )

        return_value = response.choices[0].message.content.strip()
        print("return_value", return_value)

        return return_value
