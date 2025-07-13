from langchain.llms import Ollama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class LastFactFilter:
    def __init__(self, model_name :str = "qwen2.5:14b-instruct", temperature = 0.5, max_tokens = 1000):
        self.model_name = model_name
        self.temperature = temperature
        self.prompt_template = """
        Вот транскрипт видео:
{transcript}

Твоя задача — внимательно проанализировать весь транскрипт и определить **только один последний факт**, который был озвучен в конце этого текста. Под фактом понимается конкретное, чётко выраженное утверждение, событие, результат или ключевая информация, которая завершает обсуждение в видео.

Обрати внимание:
- Текст может не заканчиваться ровно на этом факте. После последнего полного факта может идти обрывок следующего предложения, который не завершён и не несёт самостоятельного смысла.
- Игнорируй такие обрывки и оставляй только полный последний факт, который логически завершает повествование.
- Собери и включи в ответ весь релевантный контекст из транскрипта, который касается людей, событий и вещей, упомянутых в этом последнем факте. Этот контекст поможет лучше понять и объяснить факт.
- Игнорируй вводные, приветствия, прощания и общие рассуждения, если они не содержат важного факта.
- Сделай краткое и ёмкое резюме этого последнего факта, используя простой и понятный русский язык.
- Не добавляй ничего лишнего, ответ должен быть максимально сжатым и по существу.

        В ответе выведи только резюме последнего факта, который был озвучен в конце этого текста. Не добавляй ничего лишнего, ответ должен быть максимально сжатым и по существу.


        """
        self.prompt = PromptTemplate(
            input_variables=["transcript"],
            template=self.prompt_template
        )
        self.llm = Ollama(model=self.model_name, base_url='http://localhost:11450', temperature = self.temperature)
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def summarize_last_fact(self, transcript: str) -> str:
        result = self.chain.run(transcript=transcript)
        return result.strip()
