import httpx
import asyncio
from typing import Optional, List, Dict, Any
import datetime
from loguru import logger
from config import settings

class AlfaCrmManager:
    """Enterprise-grade connector for AlfaCRM (s20.online) API v2."""
    
    BRANCH_ID = 1  # "Школа Го"
    STATUS_NEW = 1 # "Установлен контакт"
    STATUS_BOOKED = 2 # "Назначено пробное"
    STATUS_PAID = 4 # "Получена оплата"
    
    @staticmethod
    def get_upcoming_weekend_dates():
        """Рассчитывает ближайшие Сб и Вс 13:00"""
        today = datetime.datetime.now()
        days_until_sat = (5 - today.weekday()) % 7
        days_until_sun = (6 - today.weekday()) % 7
        
        if days_until_sat == 0 and today.hour >= 13: days_until_sat = 7
        if days_until_sun == 0 and today.hour >= 13: days_until_sun = 7

        sat_date = today + datetime.timedelta(days=days_until_sat)
        sun_date = today + datetime.timedelta(days=days_until_sun)

        return {
            "saturday": sat_date.strftime("%d.%m (суббота) в 13:00"),
            "sunday": sun_date.strftime("%d.%m (воскресенье) в 13:00")
        }
    
    def __init__(self):
        self.base_url = f"{settings.ALFA_BASE_URL}/v2api"
        self.email = settings.ALFA_EMAIL
        self.api_key = settings.ALFA_API_KEY
        self.app_key = settings.ALFA_APP_KEY
        self.token = None
        self._lock = asyncio.Lock()

    async def _login(self) -> bool:
        """Authenticate and retrieve JWT token."""
        url = f"{self.base_url}/auth/login"
        payload = {
            "email": self.email,
            "api_key": self.api_key
        }
        headers = {"X-App-Key": self.app_key}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("token")
                    logger.success("🔑 Successfully logged into AlfaCRM")
                    return True
                else:
                    logger.error(f"❌ AlfaCRM Login Failed: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"❌ AlfaCRM Auth Exception: {e}")
                return False

    async def get_headers(self) -> Dict[str, str]:
        """Ensure token is valid and return headers."""
        async with self._lock:
            if not self.token:
                await self._login()
        
        return {
            "X-ALFACRM-TOKEN": self.token,
            "X-App-Key": self.app_key,
            "Content-Type": "application/json"
        }

    async def sync_customer(self, phone: str, name: str = "New Lead"):
        """Find or create a lead in the CRM."""
        headers = await self.get_headers()
        search_url = f"{self.base_url}/{self.BRANCH_ID}/customer/index"
        
        # Clean phone to 10 digits
        clean_phone = "".join(filter(str.isdigit, phone))
        if len(clean_phone) > 10:
            clean_phone = clean_phone[-10:]
        
        async with httpx.AsyncClient() as client:
            # 1. Search
            search_payload = {"phone": clean_phone}
            response = await client.post(search_url, headers=headers, json=search_payload)
            
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    logger.info(f"👤 Lead found in CRM: {items[0].get('id')}")
                    return items[0].get("id")
            
            # 2. Create if not found
            create_url = f"{self.base_url}/{self.BRANCH_ID}/customer/create"
            create_payload = {
                "name": name,
                "is_lead": 1,
                "phone": [clean_phone],
                "lead_status_id": self.STATUS_NEW
            }
            create_resp = await client.post(create_url, headers=headers, json=create_payload)
            if create_resp.status_code == 200:
                new_id = create_resp.json().get("model", {}).get("id")
                logger.success(f"🆕 Created NEW Lead in CRM: {new_id}")
                return new_id
                
        return None

    async def set_status(self, customer_id: int, status_id: int):
        """Update lead funnel stage."""
        headers = await self.get_headers()
        url = f"{self.base_url}/{self.BRANCH_ID}/customer/update/{customer_id}"
        payload = {"lead_status_id": status_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                logger.success(f"📈 Lead {customer_id} moved to status {status_id}")
                return True
        return False

    async def add_comment(self, customer_id: int, text: str):
        """Add a log entry to customer's profile in CRM."""
        headers = await self.get_headers()
        url = f"{self.base_url}/{self.BRANCH_ID}/communication/create"
        payload = {
            "customer_id": customer_id,
            "type": 1, # "Comment"
            "text": f"🤖 Юлия (ИИ): {text}"
        }
        async with httpx.AsyncClient() as client:
            await client.post(url, headers=headers, json=payload)

alfa_crm = AlfaCrmManager()
