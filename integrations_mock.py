import datetime
from loguru import logger

class AlphaCRMMock:
    def __init__(self):
        self.statuses = {
            "1": "Новый лид",
            "2": "В обработке",
            "3": "Записан на мастер-класс",
            "4": "Пришёл на мастер-класс",
            "9": "Уснул"
        }

    async def update_status(self, lead_id: str, status_id: str):
        status_name = self.statuses.get(status_id, "Неизвестный статус")
        logger.info(f"[ALPHA CRM] Лид {lead_id} -> {status_name}")
        return True

    async def create_lead(self, name: str, phone: str):
        logger.info(f"[ALPHA CRM] Создан лид: {name} ({phone})")
        return "alpha_lead_999"

class KaspiPayMock:
    async def create_invoice(self, phone: str, amount: int = 5000):
        logger.info(f"[MOCK Kaspi] Выставлен счет на {amount} тг для {phone}")
        return f"https://kaspi.kz/pay/mock_invoice_{datetime.datetime.now().timestamp()}"

def get_upcoming_weekend_dates():
    """
    Рассчитывает ближайшие Сб и Вс 13:00
    """
    today = datetime.datetime.now()
    # 5 - Saturday, 6 - Sunday
    days_until_sat = (5 - today.weekday()) % 7
    days_until_sun = (6 - today.weekday()) % 7
    
    # Если сегодня уже Сб или Вс, но время прошло 13:00, предлагаем следующий выходной
    if days_until_sat == 0 and today.hour >= 13:
        days_until_sat = 7
    if days_until_sun == 0 and today.hour >= 13:
        days_until_sun = 7

    sat_date = today + datetime.timedelta(days=days_until_sat)
    sun_date = today + datetime.timedelta(days=days_until_sun)

    return {
        "saturday": sat_date.strftime("%d.%m (суббота) в 13:00"),
        "sunday": sun_date.strftime("%d.%m (воскресенье) в 13:00")
    }

crm_mock = AlphaCRMMock()
kaspi_mock = KaspiPayMock()
