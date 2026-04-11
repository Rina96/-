import json
import os
import fitz  # PyMuPDF
from typing import List, Optional
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field
from config import settings

# Initialize OpenAI Client
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

    def _build_system_prompt(self, client_name: str = "") -> str:
        """FIX 1: Accept client_name to personalize the prompt."""
        from integrations import alfa_crm
        dates = alfa_crm.get_upcoming_weekend_dates()
        
        school = self.kb.get("school", {})
        products = self.kb.get("products", {})
        tunnels = self.kb.get("tunnel_logic", {})

        # Build personalization block
        client_context = ""
        if client_name and client_name not in ("WA Lead", "WhatsApp Lead", ""):
            client_context = f"\nКЛИЕНТ: Тебя уже знают как {client_name}. Обращайся к нему по имени.\n"

        return f"""
ТЫ: Юлия, элитный менеджер школы '{school.get('name', 'School Go')}' (Алматы).
{client_context}
МИССИЯ: {school.get('mission', '')}

ТУННЕЛИ ПРОДАЖ:
1. {tunnels.get('path_1', '')}
2. {tunnels.get('path_2', '')}
3. {tunnels.get('path_3', '')}

ЦЕЛЬ: {tunnels.get('success_goal', '')}

ПРОДУКТЫ:
- Взрослые: {products.get('adult', {}).get('name')}, {products.get('adult', {}).get('price')} тг. {products.get('adult', {}).get('value_prop')}
- Дети: {products.get('child', {}).get('name')}, {products.get('child', {}).get('price')} тг. {products.get('child', {}).get('value_prop')}

ВОЗРАЖЕНИЯ:
- Сложно? → "За 90 минут уже сыграете первые партии."
- Нет времени? → "Есть онлайн-формат или индивидуальное время."
- Дорого? → "Можно прийти с другом — на двоих 5000 тг."

ПРАВИЛА:
1. Веди клиента: Квалификация → Запись на МК → Оплата.
2. Тон: заботливая и профессиональная женщина. Один шаг за раз.
3. Даты: {dates['saturday']} или {dates['sunday']}.
4. ИМЯ: Если клиент назвал свое имя или оно есть в истории — ОБЯЗАТЕЛЬНО верни его в поле 'extracted_name'.
5. КВАЛИФИКАЦИЯ: Если понимаешь, что клиент заинтересован и это целевой лид, ставь 'is_qualified': true.
6. ВЫХОД: ТОЛЬКО JSON по схеме AIResponseSchema.
ОБЯЗАТЕЛЬНО используй ключи 'reply_text', 'extracted_name', 'is_qualified'.
"""

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            return "".join(page.get_text() for page in doc)
        except Exception as e:
            logger.error(f"PDF Parse Error: {e}")
            return ""

    def generate_response(
        self,
        user_message: str,
        chat_history: List[dict],
        image_url: Optional[str] = None,
        pdf_text: Optional[str] = None,
        client_name: str = ""  # FIX 1: Accept client name
    ) -> AIResponseSchema:
        """
        FIX 2: Kept as sync so it can be safely run via asyncio.to_thread().
        FIX 1: client_name is now injected into the system prompt.
        """
        system_instruction = self._build_system_prompt(client_name=client_name)
        
        full_user_content = user_message
        if pdf_text:
            full_user_content += f"\n\n[СОДЕРЖИМОЕ PDF-ЧЕКА]:\n{pdf_text}"
            
        content = [{"type": "text", "text": full_user_content}]
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}})
            
        messages = [{"role": "system", "content": system_instruction}]
        for msg in chat_history:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("text", "")})
        messages.append({"role": "user", "content": content})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500
            )
            data = json.loads(response.choices[0].message.content)
            logger.success("🧠 GPT-4o responded successfully")
            return AIResponseSchema(**data)
        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            return AIResponseSchema(reply_text="Минутку, сейчас уточню...", needs_human=True)

llm = LlmEngine()
