"""
Bitrix24 integration adapter.
Reference: https://dev.bitrix24.com/rest-api/
"""
import httpx
from typing import Optional, Dict, Any, List
from loguru import logger
from crm_base import BaseCRMAdapter, CRMLead, CRMResponse


class Bitrix24Adapter(BaseCRMAdapter):
    """Bitrix24 CRM integration adapter."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Bitrix24 adapter.

        Config structure:
        {
            "webhook_url": "https://mycompany.bitrix24.com/rest/1/abc123def456/"
            # or use user credentials:
            "domain": "mycompany.bitrix24.com",
            "client_id": "xxx",
            "client_secret": "xxx",
            "access_token": "xxx"
        }
        """
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
        self.domain = config.get("domain", "")
        self.access_token = config.get("access_token", "")
        self.base_url = self.webhook_url if self.webhook_url else f"https://{self.domain}/rest/1/"
        self.is_authenticated = bool(self.webhook_url or self.access_token)

    async def authenticate(self) -> bool:
        """Bitrix24 uses webhook or OAuth token - no login needed if already configured."""
        try:
            # Test connection
            params = {"access_token": self.access_token} if self.access_token else {}
            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(
                    f"{self.base_url}batch",
                    json={"halt": 0, "cmd": {}},
                    params=params,
                    timeout=10.0
                )
                if r.status_code == 200:
                    self.is_authenticated = True
                    logger.success("✅ Bitrix24 authenticated")
                    return True
                else:
                    logger.error(f"❌ Bitrix24 auth failed: {r.text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Bitrix24 auth error: {e}")
            return False

    async def get_lead_by_phone(self, phone: str) -> Optional[CRMLead]:
        """Fetch contact/lead by phone number."""
        try:
            # Normalize phone
            clean_phone = phone.replace(" ", "").replace("-", "").replace("+", "")

            params = {"access_token": self.access_token} if self.access_token else {}

            # Search in contacts
            payload = {
                "halt": 0,
                "cmd": {
                    "get_contacts": "crm.contact.list?filter[PHONE]=" + clean_phone + "&select=ID,NAME,PHONE,EMAIL"
                }
            }

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(
                    f"{self.base_url}batch",
                    json=payload,
                    params=params,
                    timeout=10.0
                )

                if r.status_code == 200:
                    data = r.json()
                    contacts = data.get("result", {}).get("get_contacts", {}).get("result", [])

                    if contacts:
                        contact = contacts[0]
                        phones = contact.get("PHONE", [])
                        phone_value = phones[0]["VALUE"] if phones else ""

                        return CRMLead(
                            id=str(contact["ID"]),
                            phone=phone_value,
                            name=contact.get("NAME", ""),
                            email=self._extract_email(contact)
                        )
                return None
        except Exception as e:
            logger.error(f"❌ Bitrix24 get_lead_by_phone error: {e}")
            return None

    async def create_lead(self, name: str, phone: str, email: Optional[str] = None) -> Optional[str]:
        """Create new contact in Bitrix24."""
        try:
            params = {"access_token": self.access_token} if self.access_token else {}

            phone_data = [{"VALUE": phone, "VALUE_TYPE": "MOBILE"}]
            email_data = [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else []

            payload = {
                "halt": 0,
                "cmd": {
                    "create_contact": "crm.contact.add?fields[NAME]=" + name +
                                     "&fields[PHONE]=" + str(phone_data) +
                                     ("&fields[EMAIL]=" + str(email_data) if email else "")
                }
            }

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(
                    f"{self.base_url}batch",
                    json=payload,
                    params=params,
                    timeout=10.0
                )

                if r.status_code == 200:
                    data = r.json()
                    result = data.get("result", {}).get("create_contact", {}).get("result")
                    if result:
                        logger.success(f"✅ Bitrix24 contact created: {result}")
                        return str(result)
                return None
        except Exception as e:
            logger.error(f"❌ Bitrix24 create_lead error: {e}")
            return None

    async def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> bool:
        """Update contact in Bitrix24."""
        try:
            params = {"access_token": self.access_token} if self.access_token else {}

            # Build field updates
            field_updates = f"ID={lead_id}"
            if "name" in updates:
                field_updates += f"&fields[NAME]={updates['name']}"
            if "phone" in updates:
                field_updates += f"&fields[PHONE]={{VALUE:{updates['phone']},VALUE_TYPE:MOBILE}}"

            payload = {
                "halt": 0,
                "cmd": {
                    "update_contact": f"crm.contact.update?{field_updates}"
                }
            }

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(
                    f"{self.base_url}batch",
                    json=payload,
                    params=params,
                    timeout=10.0
                )
                success = r.status_code == 200
                if success:
                    logger.success(f"✅ Bitrix24 contact {lead_id} updated")
                return success
        except Exception as e:
            logger.error(f"❌ Bitrix24 update_lead error: {e}")
            return False

    async def get_lead_status(self, lead_id: str) -> Optional[str]:
        """Get deal status associated with the contact."""
        try:
            params = {"access_token": self.access_token} if self.access_token else {}

            payload = {
                "halt": 0,
                "cmd": {
                    "get_deal": f"crm.deal.list?filter[CONTACT_ID]={lead_id}&select=ID,STAGE_ID"
                }
            }

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(
                    f"{self.base_url}batch",
                    json=payload,
                    params=params,
                    timeout=10.0
                )

                if r.status_code == 200:
                    data = r.json()
                    deals = data.get("result", {}).get("get_deal", {}).get("result", [])
                    if deals:
                        return deals[0].get("STAGE_ID")
            return None
        except Exception as e:
            logger.error(f"❌ Bitrix24 get_lead_status error: {e}")
            return None

    async def set_lead_status(self, lead_id: str, status: str) -> bool:
        """Update deal status."""
        try:
            params = {"access_token": self.access_token} if self.access_token else {}

            payload = {
                "halt": 0,
                "cmd": {
                    "update_deal": f"crm.deal.update?ID={lead_id}&fields[STAGE_ID]={status}"
                }
            }

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(
                    f"{self.base_url}batch",
                    json=payload,
                    params=params,
                    timeout=10.0
                )
                return r.status_code == 200
        except Exception as e:
            logger.error(f"❌ Bitrix24 set_lead_status error: {e}")
            return False

    async def get_next_available_slots(self, service_type: str = None) -> Dict[str, str]:
        """Get available booking slots from Bitrix24 calendar."""
        # Custom implementation needed based on Bitrix24 calendar setup
        return {
            "saturday": "Available Saturday slots",
            "sunday": "Available Sunday slots"
        }

    def _extract_email(self, contact: Dict[str, Any]) -> Optional[str]:
        """Extract email from contact data."""
        try:
            emails = contact.get("EMAIL", [])
            if emails:
                return emails[0]["VALUE"]
        except:
            pass
        return None
