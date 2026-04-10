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
        self.kb = self._load_kb()

    def _load_kb(self) -> dict:
        kb_path = os.path.join(os.path.dirname(__file__), "school_go_kb.json")
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading KB: {e}")
            return {}

    def _build_system_prompt(self) -> str:
        # Import dates dynamically
        from integrations import alfa_crm
        dates = alfa_crm.get_upcoming_weekend_dates()
        
        school = self.kb.get("school", {})
        products = self.kb.get("products", {})
        tunnels = self.kb.get("tunnel_logic", {})
        
        return f"""
ТЫ: Юлия, элитный менеджер школы '{school.get('name', 'School Go')}' (Алматы), глубоко интегрированная с AlfaCRM.

МИССИЯ: {school.get('mission', '')}

ТВОИ ТУННЕЛИ ПРОДАЖ (Success Path):
1. {tunnels.get('path_1', '')}
2. {tunnels.get('path_2', '')}
3. {tunnels.get('path_3', '')}

ЦЕЛЬ: {tunnels.get('success_goal', '')}

ТВОИ ПРОДУКТЫ:
- Взрослые: {products.get('adult', {}).get('name')}, {products.get('adult', {}).get('price')} тг. {products.get('adult', {}).get('value_prop')}
- Дети: {products.get('child', {}).get('name')}, {products.get('child', {}).get('price')} тг. {products.get('child', {}).get('value_prop')}

ПРАВИЛА:
1. Вести клиента по воронке продаж: Квалификация -> Запись -> Оплата.
2. Все твои действия (подтверждение даты `booked_date`, детекция оплаты `is_paid_detected`) автоматически синхронизируются с CRM.
3. Тон: Friendly Woman (заботливая, но профессиональная). Один шаг за раз.
4. Даты на выбор: {dates['saturday']} или {dates['sunday']}.
5. Выход: Только JSON соответствующий AIResponseSchema. 
ПРИМЕР: {{"reply_text": "Привет!...", "booked_date": "15.04", "is_qualified": true}}
ОБЯЗАТЕЛЬНО используй ключ 'reply_text' для ответа.
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
