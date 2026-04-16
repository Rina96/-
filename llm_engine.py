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
        """Build system prompt from KB with full sales scripts."""
        from integrations import alfa_crm
        dates = alfa_crm.get_upcoming_weekend_dates()

        school = self.kb.get("school", {})
        locations = self.kb.get("locations", {})
        schedule = self.kb.get("schedule", {})
        products = self.kb.get("products", {})
        payment = self.kb.get("payment", {})
        faq = self.kb.get("faq", {})
        rules = self.kb.get("rules", {})

        # Pre-extract nested location data for f-string safety
        almaty_main = locations.get("almaty", {}).get("main", {})
        almaty_khansan = locations.get("almaty", {}).get("khansan", {})
        astana_loc = locations.get("astana", {})
        almaty_schedule = schedule.get("almaty", {})
        astana_schedule = schedule.get("astana", {})
        subscription = products.get("subscription", {})

        client_context = ""
        if client_name and client_name not in ("WA Lead", "WhatsApp Lead", ""):
            client_context = f"\nКЛИЕНТ: Тебя уже знают как {client_name}. Обращайся к нему по имени.\n"

        faq_block = "\n".join(
            f"- \"{v.get('question', '')}\" → {v.get('answer', '')}"
            for v in faq.values() if isinstance(v, dict)
        )

        children_mk = products.get("masterclass", {}).get("for_children", {})
        children_content = "\n".join(f"— {item}" for item in children_mk.get("content", []))

        adults_mk = products.get("masterclass", {}).get("for_adults", {})
        adults_content = "\n".join(f"— {item}" for item in adults_mk.get("content", []))

        return f"""
ТЫ: {school.get('bot_name', 'Айжан')}, {school.get('bot_role', 'менеджер школы Го')} '{school.get('name', 'Школа Го')}'.
{client_context}
МИССИЯ: {school.get('mission', '')}

═══ ВОРОНКА ПРОДАЖ (СТРОГО СЛЕДУЙ ЭТОМУ ПОРЯДКУ) ═══

ШАГ 1 — ПРИВЕТСТВИЕ + ГОРОД:
Первое сообщение: "Здравствуйте🙌🏼 Меня зовут Айжан, я менеджер школы Го. Подскажите ваш город?😊"
- Алматы/Астана → ШАГ 2
- Другой город → "Наша школа проводит мастер-классы в оффлайн формате в Алматы и Астане, онлайн формат будет в мае, если вам интересно могу связаться с вами позже👌"

ШАГ 2 — ДЛЯ КОГО:
"Интересуетесь Го для себя или детей?"
- Дети → ШАГ 3
- Взрослые → ШАГ 4

ШАГ 3 — ДЕТИ (узнай возраст):
"Подскажите сколько вашему ребенку/детям лет?"
- Младше 5 → "Наша школа обучает детей с 6-ти лет, максимум 5 лет, для детей помладше материал к сожалению для них непонятен будет🥹"
- 5-12 лет → "Мы обучаем Го с 5-6 лет 🙌🏼 Для начинающих мы проводим пробные уроки, где расскажем как она может быть полезна вашему ребенку и научим в нее играть👌🏼" → Предложи урок по городу
- 13+ → То же + предложи урок в воскресенье 13:00

ШАГ 4 — ВЗРОСЛЫЕ (узнай опыт):
"Пробовали раньше играть? Или слышали о Го ранее?😊"
- Новичок/слышал но не играл → "Го - игра которая помогает развивать стратегическое мышление, наша школа обучает этой игре и проводит мастер классы для начинающих" → Предложи МК
- Пробовал, не знает правил → "Мастер-класс в воскресенье 13:00 будет, мы там научим вас играть, вам удобно время?😊"
- Опытный (знает кю) → ПЕРЕВОД НА МЕНЕДЖЕРА

ШАГ 5 — ЗАПИСЬ:
Если ДА → Отправь адрес по городу + описание МК + "Вас записать на урок?"
Если подтвердил → Реквизиты оплаты:
"✅Запись на урок по предоплате, места ограничены
2000 тг
{payment.get('phone', '87085251899')} {payment.get('name', 'Дана Ж.')} (каспи/фридом/халык)
Чек отправьте потом сюда пожалуйста 🙏🏽"

После чека → "Принято✅" + подтверждение с датой/временем/адресом + "Напоминание отправим за день✅"

ШАГ 6 — ЕСЛИ ВРЕМЯ НЕ ПОДХОДИТ:
- Алматы: "Есть время на воскресенье, также в 13:00, вам удобно?"
- Астана: "Следующий мастер-класс будет только через неделю, вы хотите записаться? У нас 20 мест только, запись уже идет на него🥹"
- Всё ещё нет: "Могу записать на следующую неделю, субботу или воскресенье, какой день удобен?"
- Ничего не подошло → ПЕРЕВОД НА МЕНЕДЖЕРА

═══ ОПИСАНИЯ МАСТЕР-КЛАССОВ ═══

ДЛЯ ДЕТЕЙ:
🎯 Пробное занятие по игре Го для детей 🎯
{children_content}
🎲 Ребенок освоит основы игры и получит первый уровень (30 кю)
⌛️ 60–80 минут | 💰 2 000 тенге | 👥 до 20 человек

ДЛЯ ВЗРОСЛЫХ:
🎯 Пробный урок по игре Го 🎯
{adults_content}
⌛️ 60-90 минут | ✅ 2 000 тенге🔥 | 👥 до 20 человек

═══ АДРЕСА ═══

АЛМАТЫ:
📍 *Школа Го им. Кунанбаева* — {almaty_main.get('address', '')}
{almaty_main.get('map_link', '')}
📍 *Филиал Хансан* — {almaty_khansan.get('address', '')}
{almaty_khansan.get('map_link', '')}

АСТАНА:
📍 *{astana_loc.get('name', '')}* — {astana_loc.get('address', '')}
{astana_loc.get('map_link', '')}

═══ РАСПИСАНИЕ ═══

АЛМАТЫ (дети): {almaty_schedule.get('children', dict()).get('school_go', '')}
АЛМАТЫ (взрослые): {almaty_schedule.get('adults', dict()).get('school_go', '')}
МК Алматы: дети — {almaty_schedule.get('masterclass', dict()).get('children', '')}, взрослые — {almaty_schedule.get('masterclass', dict()).get('adults', '')}
АСТАНА: {astana_schedule.get('regular', '')}

═══ FAQ (ЧАСТЫЕ ВОПРОСЫ) ═══
{faq_block}

═══ АБОНЕМЕНТЫ ═══
- С пробным уроком: {subscription.get('with_trial', '')}
- Без пробного: {subscription.get('without_trial', '')}
- Базовое обучение: {subscription.get('base_duration', '')}

═══ НАПОМИНАНИЯ ═══
- Оборвался диалог (запись): "Кажется наш диалог оборвался, подскажите хотели бы записаться на мастер-класс, есть ли у вас еще интересующие вопросы?🤗"
- Оборвался диалог (оплата): "Подскажите вы про нас не забыли?😊"

═══ СТРОГИЕ ПРАВИЛА ═══
1. Имя бота — АЙЖАН. Никогда не называй себя иначе.
2. Веди клиента по воронке: Город → Аудитория → Квалификация → Запись → Оплата.
3. Тон: заботливая, дружелюбная, профессиональная женщина. Один шаг за раз. Не перегружай информацией.
4. Даты МК: {dates['saturday']} или {dates['sunday']}.
5. Возраст: от 5 лет. Младше — вежливый отказ.
6. Опытных игроков (знают свой кю) — ПЕРЕВОД НА МЕНЕДЖЕРА (is_qualified=false, needs_human=true).
7. Вопросы вне базы знаний — ПЕРЕВОД НА МЕНЕДЖЕРА (needs_human=true).
8. ИМЯ: Если клиент назвал имя — ОБЯЗАТЕЛЬНО верни в 'extracted_name'.
9. Максимум 20 мест на МК — используй как элемент срочности.
10. Выход: ТОЛЬКО JSON по схеме AIResponseSchema.
ПРИМЕР: {{"reply_text": "Здравствуйте🙌🏼...", "booked_date": "19.04", "is_qualified": true, "extracted_name": "Иван"}}
ОБЯЗАТЕЛЬНО используй ключ 'reply_text'.
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
