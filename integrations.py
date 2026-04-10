import httpx
import asyncio
from typing import Optional, List, Dict, Any
import datetime
from loguru import logger
from config import settings

class AlfaCrmManager:
    """Enterprise-grade connector for AlfaCRM (s20.online) with Swiss reliability."""
    
    BRANCH_ID = 1
    STATUS_NEW = 1
    STATUS_BOOKED = 2
    STATUS_PAID = 4
    
    def __init__(self):
        self.base_url = f"{settings.ALFA_BASE_URL}/v2api"
        self.email = settings.ALFA_EMAIL
        self.api_key = settings.ALFA_API_KEY
        self.app_key = settings.ALFA_APP_KEY
        self.token = None
        self._lock = asyncio.Lock()

    async def _login(self) -> bool:
        url = f"{self.base_url}/auth/login"
        payload = {"email": self.email, "api_key": self.api_key}
        headers = {"X-App-Key": self.app_key}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=5.0)
                if response.status_code == 200:
                    self.token = response.json().get("token")
                    return True
                return False
            except Exception as e:
                logger.error(f"❌ CRM Auth Fail: {e}")
                return False

    async def get_headers(self) -> Dict[str, str]:
        async with self._lock:
            if not self.token: await self._login()
        return {
            "X-ALFACRM-TOKEN": self.token,
            "X-App-Key": self.app_key,
            "Content-Type": "application/json"
        }

    async def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Safe lookup with timeout."""
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/customer/index"
            clean_phone = "".join(filter(str.isdigit, phone))[-10:]
            async with httpx.AsyncClient() as client:
                r = await client.post(url, headers=headers, json={"phone": clean_phone}, timeout=5.0)
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    return items[0] if items else None
            return None
        except Exception as e:
            logger.error(f"⚠️ CRM Lookup Fail: {e}")
            return None
    async def sync_customer(self, phone: str, name: str = "WA Lead"):
        existing = await self.get_customer_by_phone(phone)
        if existing: return existing.get("id")
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/customer/create"
            # Format phone as 7XXXXXXXXXX
            clean_phone = "".join(filter(str.isdigit, phone))
            if len(clean_phone) == 10: clean_phone = "7" + clean_phone
            elif len(clean_phone) == 11 and clean_phone.startswith("8"): clean_phone = "7" + clean_phone[1:]
            
            payload = {
                "name": name, 
                "is_lead": 1, 
                "phone": [clean_phone], 
                "branch_ids": [self.BRANCH_ID],
                "lead_status_id": self.STATUS_NEW,
                "legal_type": 1, # Physical person
                "is_study": 0    # Not yet studying (Lead)
            }
            async with httpx.AsyncClient() as client:
                r = await client.post(url, headers=headers, json=payload, timeout=5.0)
                if r.status_code == 200:
                    return r.json().get("model", {}).get("id")
                else:
                    logger.error(f"❌ CRM Sync Error {r.status_code}: {r.text}")
        except Exception as e:
            logger.error(f"❌ CRM Sync Exception: {e}")
        return None


    async def set_status(self, customer_id: int, status_id: int):
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/customer/update/{customer_id}"
            async with httpx.AsyncClient() as client:
                await client.post(url, headers=headers, json={"lead_status_id": status_id}, timeout=5.0)
        except: pass

    async def add_comment(self, customer_id: int, text: str):
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/communication/create"
            payload = {"customer_id": customer_id, "type": 1, "text": f"🤖 Юлия (ИИ): {text}"}
            async with httpx.AsyncClient() as client:
                await client.post(url, headers=headers, json=payload, timeout=5.0)
        except: pass

    def get_upcoming_weekend_dates(self) -> Dict[str, str]:
        """Returns the dates of the next Saturday and Sunday."""
        today = datetime.date.today()
        saturday = today + datetime.timedelta((5 - today.weekday()) % 7)
        if saturday == today: saturday += datetime.timedelta(7)
        sunday = saturday + datetime.timedelta(1)
        return {
            "saturday": saturday.strftime("%d.%m"),
            "sunday": sunday.strftime("%d.%m")
        }

alfa_crm = AlfaCrmManager()
