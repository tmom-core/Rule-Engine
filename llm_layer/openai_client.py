from llm_client import LLMClient
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv("../.env")
class OpenAILLMClient(LLMClient):
    def __init__(self, model: str = "gpt-4.1"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        return response.choices[0].message.content
