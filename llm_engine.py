import json
import os
from typing import List, Optional
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field
from config import settings
from integrations_mock import get_upcoming_weekend_dates

# Initialize OpenAI Client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class AIResponseSchema(BaseModel):
    """
    Schema for forcing the LLM to output structured state along with the text reply.
    """
    reply_text: str = Field(description="Friendly response in Russian.")
    is_qualified: Optional[bool] = False
    needs_human: Optional[bool] = False
    extracted_name: Optional[str] = ""
    extracted_phone: Optional[str] = ""
    adult_count: Optional[int] = 1
    child_count: Optional[int] = 0
    audience: Optional[str] = "adult"
    booked_date: Optional[str] = ""

class LlmEngine:
    def __init__(self):
        self.model = "gpt-4o-mini" # Cheapest and high quality model as requested

    def _build_system_prompt(self) -> str:
        dates = get_upcoming_weekend_dates()
        base_prompt = f"""
ТЫ: Дружелюбная и уверенная девушка-ассистент Школы Го имени Кунабаева.
ТВОЙ ТОН: Теплый, спокойный, уважительный, немного экспертный. Минимум терминов, упор на развитие мышления.

ЦЕЛЬ: Провести клиента по 10 шагам воронки и записать на Мастер-класс (5000 тг).

АКТУАЛЬНЫЕ ДАТЫ (Предлагай их):
- {dates['saturday']}
- {dates['sunday']}

ПРАВИЛА:
1. ИМЯ: Обязательно спроси имя в первом или втором сообщении. ВСЕГДА обращайся к клиенту по имени, если оно известно.
2. ПЕРВЫЙ ВОПРОС: Уточни, для кого обучение (себя/ребенок).
3. ЦЕНООБРАЗОВАНИЕ (Строго): 
   - Взрослый: 5000 тг.
   - Ребенок: 2000 тг.
   - СЧИТАЙ ИТОГ: Если приходят несколько человек, назови итоговую сумму (например: "Для вас и двоих детей это будет 9000 тенге").
4. СТИЛЬ: Пиши короткими абзацами. Разделяй разные мысли двойным переносом строки (\\n\\n), чтобы я мог отправить их по отдельности.
5. АРГУМЕНТАЦИЯ: Разная для взрослых (бизнес/стратегия) и детей (логика/будущее).
6. ДАТЫ: Сб/Вс 13:00.
7. ОГРАНИЧЕНИЯ: 
   - Возраст детей строго от 7 лет. Если меньше — вежливо объясни, что игра требует концентрации.
   - Скидок на мастер-класс нет (цена и так минимальна для промо).
   - Если группа > 3 человек — скажи, что нужно уточнить у менеджера и передай диалог (needs_human = True).

КОНТЕКСТ ШКОЛЫ:
You must respond in JSON format with exactly these fields:
- reply_text (string): Ваша дружелюбная фраза
- is_qualified (boolean): готов ли клиент к оплате
- needs_human (boolean): нужен ли менеджер
- extracted_name (string): имя клиента
- extracted_phone (string): телефон
- adult_count (integer): кол-во взрослых
- child_count (integer): кол-во детей
- booked_date (string): выбранная дата (сб/вс)
"""
        # Load KB using robust path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(current_dir, "school_go_kb.json")
        
        with open(kb_path, "r", encoding="utf-8") as f:
            kb_data = f.read()
        base_prompt += kb_data
        return base_prompt

    def generate_response(self, user_message: str, chat_history: List[dict]) -> AIResponseSchema:
        """
        Calls OpenAI API with strict structured output.
        """
        system_instruction = self._build_system_prompt()
        
        # Prepare history for OpenAI
        messages = [{"role": "system", "content": system_instruction}]
        for msg in chat_history:
            messages.append({
                "role": "user" if msg["role"] == "user" else "assistant",
                "content": msg["text"]
            })
        messages.append({"role": "user", "content": user_message})

        logger.debug(f"Sending request to OpenAI ({self.model}), history length: {len(chat_history)}")
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={ "type": "json_object" },
                temperature=0.3
            )
            
            raw_json = response.choices[0].message.content
            logger.debug(f"OpenAI raw response: {raw_json}")
            data = json.loads(raw_json)
            
            # OpenAI sometimes needs a nudge for the JSON schema, so we validate/fallback
            result = AIResponseSchema(
                reply_text=data.get("reply_text", "Извините, сейчас уточню..."),
                is_qualified=data.get("is_qualified", False),
                needs_human=data.get("needs_human", False),
                extracted_name=data.get("extracted_name", ""),
                extracted_phone=data.get("extracted_phone", ""),
                adult_count=data.get("adult_count", 1),
                child_count=data.get("child_count", 0),
                audience=data.get("audience", "adult"),
                booked_date=data.get("booked_date", "")
            )
            
            logger.success(f"OpenAI successful. Qualified: {result.is_qualified}")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            # Fallback safe response
            return AIResponseSchema(
                reply_text="Извините, сейчас я уточню информацию. Минутку...",
                is_qualified=False,
                needs_human=True
            )

llm = LlmEngine()
