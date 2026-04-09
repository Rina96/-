import json
import os
import base64
import httpx
import fitz  # PyMuPDF
from typing import List, Optional, Union
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field
from config import settings
from integrations_mock import get_upcoming_weekend_dates

# Initialize OpenAI Client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class AIResponseSchema(BaseModel):
    reply_text: str = Field(description="Friendly response in Russian.")
    is_qualified: Optional[bool] = False
    needs_human: Optional[bool] = False
    extracted_name: Optional[str] = ""
    extracted_phone: Optional[str] = ""
    adult_count: Optional[int] = 1
    child_count: Optional[int] = 0
    booked_date: Optional[str] = ""
    voice_response_needed: Optional[bool] = False
    is_paid_detected: Optional[bool] = False  # NEW: Did the AI see a valid payment?

class LlmEngine:
    def __init__(self):
        self.model = "gpt-4o"

    def _build_system_prompt(self) -> str:
        dates = get_upcoming_weekend_dates()
        return f"""
ТЫ: Юлия, элитный ассистент школы Го имени Кунабаева. 
ТЫ МОЖЕШЬ: Видеть скриншоты и PDF-чеки Каспи.

ЗАПОВЕДИ:
1. Краткость. Один шаг за раз. 
2. САМОАНАЛИЗ: Перед ответом проверь: на каком этапе воронки клиент? 
3. Если это ЧЕК КАСПИ (PDF или фото) и сумма совпадает с расчетом — установи is_paid_detected: true.
4. Если вопрос сложный — используй голос (voice_response_needed: true).

ЭТАПЫ:
1. "Вы для себя или ребенка?".
2. Квалификация (имя, возраст 7+).
3. Цена: 5000/2000 тг.
4. Запись: {dates['saturday']} или {dates['sunday']}.

ВЫХОД: ТОЛЬКО JSON.
"""

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extracts text from a Kaspi PDF check."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"PDF Parse Error: {e}")
            return ""

    async def transcribe_voice(self, audio_content: bytes) -> str:
        # ... (whisper logic) ...
        temp_path = "temp_voice.ogg"
        with open(temp_path, "wb") as f:
            f.write(audio_content)
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        os.remove(temp_path)
        return transcript.text

    async def generate_voice(self, text: str) -> bytes:
        response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
        return response.read()

    def generate_response(self, user_message: str, chat_history: List[dict], image_url: Optional[str] = None, pdf_text: Optional[str] = None) -> AIResponseSchema:
        system_instruction = self._build_system_prompt()
        
        full_user_content = user_message
        if pdf_text:
            full_user_content += f"\n\n[СОДЕРЖИМОЕ PDF-ЧЕКА]:\n{pdf_text}"
            
        content = [{"type": "text", "text": full_user_content}]
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}})
            
        messages = [{"role": "system", "content": system_instruction}]
        for msg in chat_history:
            messages.append({"role": "user" if msg["role"] == "user" else "assistant", "content": msg["text"]})
        
        messages.append({"role": "user", "content": content})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={ "type": "json_object" },
                temperature=0.2
            )
            data = json.loads(response.choices[0].message.content)
            return AIResponseSchema(**data)
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return AIResponseSchema(reply_text="Минутку, сейчас уточню...", needs_human=True)

llm = LlmEngine()
