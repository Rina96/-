import json
import os
import httpx
import fitz  # PyMuPDF
from typing import List, Optional
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field
from config import settings

# Initialize OpenAI Client (Master Brain)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class AIResponseSchema(BaseModel):
    reply_text: str = Field(description="Friendly response in Russian.")
    is_qualified: Optional[bool] = False
    needs_human: Optional[bool] = False
    extracted_name: Optional[str] = ""
    extracted_phone: Optional[str] = ""
    booked_date: Optional[str] = ""
    voice_response_needed: Optional[bool] = False
    is_paid_detected: Optional[bool] = False

class LlmEngine:
    """Unified AI Engine strictly using OpenAI GPT-4o."""
    
    def __init__(self):
        self.model = "gpt-4o"

    def _build_system_prompt(self) -> str:
        # Import dates dynamically
        from integrations import alfa_crm
        dates = alfa_crm.get_upcoming_weekend_dates()
        return f"""
ТЫ: Юлия, элитный менеджер школы 'School Go' (Алматы), интегрированная с AlphaCRM.

ТВОЯ РОЛЬ:
- Вести клиента по воронке продаж: Квалификация -> Запись -> Оплата.
- Все твои действия (подтверждение даты, детекция оплаты) автоматически синхронизируются с CRM.

ТВОИ ВОЗМОЖНОСТИ:
1. Видеть текстовое описание скриншотов и PDF-чеков Каспи. Сумма для проверки: 5000/2000 тг.
2. Делать выводы об оплате (is_paid_detected).

ПРАВИЛА:
1. Один шаг за раз. Тон: Friendly Woman (заботливая, но профессиональная).
2. Даты на выбор: {dates['saturday']} или {dates['sunday']}.
3. Выход: Только JSON соответствующий AIResponseSchema.
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

    async def generate_voice(self, text: str) -> bytes:
        """Converts text to speech using OpenAI TTS."""
        try:
            response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
            return response.read()
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return b""

    def generate_response(self, user_message: str, chat_history: List[dict], image_url: Optional[str] = None, pdf_text: Optional[str] = None) -> AIResponseSchema:
        """Generates a structured response using GPT-4o."""
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
            logger.success(f"🧠 GPT-4o responded for message")
            return AIResponseSchema(**data)
        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            return AIResponseSchema(reply_text="Минутку, сейчас уточню...", needs_human=True)

llm = LlmEngine()
