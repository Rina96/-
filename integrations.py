import httpx
import asyncio
import time
from typing import Optional, Dict, Any
import datetime
from loguru import logger
from config import settings
from crm_base import BaseCRMAdapter, CRMLead


class AlfaCrmManager(BaseCRMAdapter):
    """Enterprise-grade AlfaCRM connector with token caching and fail-safe."""

    BRANCH_ID = 1
    STATUS_NEW = 1
    STATUS_BOOKED = 2
    STATUS_PAID = 4

    # FIX 5: Token cache — avoid re-login on every request
    _token: Optional[str] = None
    _token_expires_at: float = 0.0
    TOKEN_TTL = 3600  # 1 hour

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize AlfaCRM adapter with config or use env variables."""
        if config is None:
            config = {
                "base_url": settings.ALFA_BASE_URL,
                "email": settings.ALFA_EMAIL,
                "api_key": settings.ALFA_API_KEY,
                "app_key": settings.ALFA_APP_KEY
            }

        super().__init__(config)
        self.base_url = f"{config.get('base_url', settings.ALFA_BASE_URL)}/v2api"
        self.email = config.get("email", settings.ALFA_EMAIL)
        self.api_key = config.get("api_key", settings.ALFA_API_KEY)
        self.app_key = config.get("app_key", settings.ALFA_APP_KEY)
        self._lock = asyncio.Lock()

    @staticmethod
    def get_upcoming_weekend_dates():
        """Calculates nearest Saturday and Sunday at 13:00 (Almaty UTC+5)."""
        from datetime import timezone, timedelta
        now = datetime.datetime.now(timezone(timedelta(hours=5)))
        days_until_sat = (5 - now.weekday()) % 7 or 7
        days_until_sun = (6 - now.weekday()) % 7 or 7

        sat = now + datetime.timedelta(days=days_until_sat)
        sun = now + datetime.timedelta(days=days_until_sun)

        return {
            "saturday": sat.strftime("%d.%m (суббота) в 13:00"),
            "sunday": sun.strftime("%d.%m (воскресенье) в 13:00")
        }

    async def _login(self) -> bool:
        url = f"{self.base_url}/auth/login"
        payload = {"email": self.email, "api_key": self.api_key}
        headers = {"X-App-Key": self.app_key}
        async with httpx.AsyncClient(verify=False) as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=5.0)
                if r.status_code == 200:
                    AlfaCrmManager._token = r.json().get("token")
                    # FIX 5: Cache token with TTL
                    AlfaCrmManager._token_expires_at = time.time() + self.TOKEN_TTL
                    logger.success("🔑 AlfaCRM login successful, token cached for 1h")
                    return True
                logger.error(f"❌ CRM Login failed: {r.status_code}")
                return False
            except Exception as e:
                logger.error(f"❌ CRM Auth Fail: {e}")
                return False

    async def get_headers(self) -> Dict[str, str]:
        """FIX 5: Only re-login when token is expired or missing."""
        async with self._lock:
            if not AlfaCrmManager._token or time.time() >= AlfaCrmManager._token_expires_at:
                await self._login()
        return {
            "X-ALFACRM-TOKEN": AlfaCrmManager._token or "",
            "X-App-Key": self.app_key,
            "Content-Type": "application/json"
        }

    async def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Safe lead lookup with 5s timeout."""
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/customer/index"
            clean_phone = "".join(filter(str.isdigit, phone))[-10:]
            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(
                    url, headers=headers, json={"phone": clean_phone}, timeout=5.0
                )
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    return items[0] if items else None
            return None
        except Exception as e:
            logger.error(f"⚠️ CRM Lookup Fail: {e}")
            return None

    async def sync_customer(self, phone: str, name: str = "WA Lead") -> Optional[int]:
        """Find or create lead, return CRM ID. Updates name if it was a placeholder."""
        existing = await self.get_customer_by_phone(phone)
        
        if existing:
            customer_id = existing.get("id")
            current_name = existing.get("name", "")
            
            # If current name is a placeholder and we have a real name, update it
            if name not in ("WA Lead", "WhatsApp Lead", "") and \
               current_name in ("WA Lead", "WhatsApp Lead", "", "Lead"):
                logger.info(f"🔄 Updating CRM lead {customer_id} name: {current_name} -> {name}")
                try:
                    headers = await self.get_headers()
                    url = f"{self.base_url}/{self.BRANCH_ID}/customer/update/{customer_id}"
                    async with httpx.AsyncClient(verify=False) as client:
                        await client.post(url, headers=headers, json={"name": name}, timeout=5.0)
                except Exception as e:
                    logger.error(f"⚠️ CRM Name Update Fail: {e}")
            return customer_id

        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/customer/create"
            clean_phone = "".join(filter(str.isdigit, phone))[-10:]
            payload = {
                "name": name,
                "is_lead": 1,
                "phone": [clean_phone],
                "lead_status_id": self.STATUS_NEW
            }
            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(url, headers=headers, json=payload, timeout=5.0)
                if r.status_code == 200:
                    new_id = r.json().get("model", {}).get("id")
                    logger.success(f"🆕 CRM lead created: {new_id}")
                    return new_id
        except Exception as e:
            logger.error(f"⚠️ CRM Create Fail: {e}")
        return None

    async def set_status(self, customer_id: int, status_id: int):
        """Update lead funnel stage."""
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/customer/update/{customer_id}"
            async with httpx.AsyncClient(verify=False) as client:
                await client.post(
                    url, headers=headers, json={"lead_status_id": status_id}, timeout=5.0
                )
                logger.info(f"📈 CRM lead {customer_id} → status {status_id}")
        except Exception as e:
            logger.error(f"⚠️ CRM Status Fail: {e}")

    async def add_comment(self, customer_id: int, text: str):
        """Add comment to lead profile."""
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/communication/create"
            payload = {"customer_id": customer_id, "type": 1, "text": f"🤖 Юлия: {text}"}
            async with httpx.AsyncClient(verify=False) as client:
                await client.post(url, headers=headers, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"⚠️ CRM Comment Fail: {e}")

    # Implementation of BaseCRMAdapter abstract methods
    async def authenticate(self) -> bool:
        """Authenticate with AlfaCRM. Alias for _login."""
        return await self._login()

    async def get_lead_by_phone(self, phone: str) -> Optional[CRMLead]:
        """Fetch lead by phone number (implements BaseCRMAdapter)."""
        customer = await self.get_customer_by_phone(phone)
        if customer:
            return CRMLead(
                id=str(customer.get("id")),
                phone=phone,
                name=customer.get("name", ""),
                email=customer.get("email"),
                custom_fields=customer
            )
        return None

    async def create_lead(self, name: str, phone: str, email: Optional[str] = None) -> Optional[str]:
        """Create new lead in AlfaCRM (implements BaseCRMAdapter)."""
        new_id = await self.sync_customer(phone, name)
        return str(new_id) if new_id else None

    async def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> bool:
        """Update lead in AlfaCRM (implements BaseCRMAdapter)."""
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/customer/update/{lead_id}"
            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(url, headers=headers, json=updates, timeout=5.0)
                return r.status_code == 200
        except Exception as e:
            logger.error(f"❌ AlfaCRM update_lead error: {e}")
            return False

    async def get_lead_status(self, lead_id: str) -> Optional[str]:
        """Get lead status from AlfaCRM."""
        try:
            headers = await self.get_headers()
            url = f"{self.base_url}/{self.BRANCH_ID}/customer/get/{lead_id}"
            async with httpx.AsyncClient(verify=False) as client:
                r = await client.get(url, headers=headers, timeout=5.0)
                if r.status_code == 200:
                    customer = r.json().get("model", {})
                    return str(customer.get("lead_status_id"))
            return None
        except Exception as e:
            logger.error(f"❌ AlfaCRM get_lead_status error: {e}")
            return None

    async def set_lead_status(self, lead_id: str, status: str) -> bool:
        """Set lead status in AlfaCRM."""
        try:
            status_id = int(status)
            await self.set_status(int(lead_id), status_id)
            return True
        except Exception as e:
            logger.error(f"❌ AlfaCRM set_lead_status error: {e}")
            return False

    async def get_next_available_slots(self, service_type: str = None) -> Dict[str, str]:
        """Get next available booking slots (AlfaCRM specific)."""
        return self.get_upcoming_weekend_dates()


alfa_crm = AlfaCrmManager()
