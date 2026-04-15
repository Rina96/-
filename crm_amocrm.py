"""
AmoCRM integration adapter.
Reference: https://www.amocrm.ru/developers/content/crm_platform/
"""
import httpx
import time
from typing import Optional, Dict, Any
from loguru import logger
from crm_base import BaseCRMAdapter, CRMLead, CRMResponse


class AmoCRMAdapter(BaseCRMAdapter):
    """AmoCRM CRM integration adapter."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AmoCRM adapter.

        Config structure:
        {
            "domain": "mycompany.amocrm.ru",  # Subdomain
            "client_id": "xxx",
            "client_secret": "xxx",
            "redirect_uri": "https://example.com/callback",
            "refresh_token": "xxx"  # OAuth refresh token
        }
        """
        super().__init__(config)
        self.domain = config.get("domain", "")
        self.base_url = f"https://{self.domain}/api/v4"
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.redirect_uri = config.get("redirect_uri", "")
        self.refresh_token = config.get("refresh_token", "")
        self._access_token = None
        self._token_expires_at = 0

    async def authenticate(self) -> bool:
        """Authenticate using OAuth refresh token."""
        try:
            url = f"https://{self.domain}/oauth2/token"
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "redirect_uri": self.redirect_uri
            }

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(url, data=payload, timeout=10.0)
                if r.status_code == 200:
                    data = r.json()
                    self._access_token = data.get("access_token")
                    self._token_expires_at = time.time() + data.get("expires_in", 3600)
                    self.is_authenticated = True
                    logger.success("✅ AmoCRM authenticated")
                    return True
                else:
                    logger.error(f"❌ AmoCRM auth failed: {r.text}")
                    return False
        except Exception as e:
            logger.error(f"❌ AmoCRM auth error: {e}")
            return False

    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with valid access token."""
        if not self._access_token or time.time() >= self._token_expires_at:
            await self.authenticate()

        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }

    async def get_lead_by_phone(self, phone: str) -> Optional[CRMLead]:
        """Fetch contact by phone number."""
        try:
            headers = await self._get_headers()
            # Normalize phone (remove spaces, dashes)
            clean_phone = phone.replace(" ", "").replace("-", "")

            # Search contacts by phone
            url = f"{self.base_url}/contacts"
            params = {"query": clean_phone}

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.get(url, headers=headers, params=params, timeout=10.0)
                if r.status_code == 200:
                    data = r.json()
                    contacts = data.get("_embedded", {}).get("contacts", [])

                    if contacts:
                        contact = contacts[0]
                        return CRMLead(
                            id=str(contact["id"]),
                            phone=phone,
                            name=contact.get("name", ""),
                            email=self._extract_email(contact),
                            custom_fields=contact.get("custom_fields_values", {})
                        )
                return None
        except Exception as e:
            logger.error(f"❌ AmoCRM get_lead_by_phone error: {e}")
            return None

    async def create_lead(self, name: str, phone: str, email: Optional[str] = None) -> Optional[str]:
        """Create new contact in AmoCRM."""
        try:
            headers = await self._get_headers()
            url = f"{self.base_url}/contacts"

            payload = {
                "name": name,
                "custom_fields_values": [
                    {
                        "field_id": 0,  # Phone field ID (customize for your setup)
                        "values": [{"value": phone, "enum_id": 0}]
                    }
                ]
            }

            if email:
                payload["custom_fields_values"].append({
                    "field_id": 1,  # Email field ID (customize)
                    "values": [{"value": email}]
                })

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.post(url, headers=headers, json=[payload], timeout=10.0)
                if r.status_code == 200:
                    data = r.json()
                    new_contacts = data.get("_embedded", {}).get("contacts", [])
                    if new_contacts:
                        logger.success(f"✅ AmoCRM contact created: {new_contacts[0]['id']}")
                        return str(new_contacts[0]["id"])
                return None
        except Exception as e:
            logger.error(f"❌ AmoCRM create_lead error: {e}")
            return None

    async def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> bool:
        """Update contact in AmoCRM."""
        try:
            headers = await self._get_headers()
            url = f"{self.base_url}/contacts/{lead_id}"

            payload = {"id": int(lead_id)}
            if "name" in updates:
                payload["name"] = updates["name"]
            if "custom_fields_values" in updates:
                payload["custom_fields_values"] = updates["custom_fields_values"]

            async with httpx.AsyncClient(verify=False) as client:
                r = await client.patch(url, headers=headers, json=payload, timeout=10.0)
                success = r.status_code in [200, 204]
                if success:
                    logger.success(f"✅ AmoCRM contact {lead_id} updated")
                return success
        except Exception as e:
            logger.error(f"❌ AmoCRM update_lead error: {e}")
            return False

    async def get_lead_status(self, lead_id: str) -> Optional[str]:
        """Get lead status (not directly available in contacts, use deals)."""
        # This would require querying deals linked to the contact
        return None

    async def set_lead_status(self, lead_id: str, status: str) -> bool:
        """Set lead status via deal status."""
        # This would create or update a deal with the new status
        return True

    async def get_next_available_slots(self, service_type: str = None) -> Dict[str, str]:
        """Get available booking slots (custom integration needed)."""
        return {
            "saturday": "Nearest Saturday at 13:00",
            "sunday": "Nearest Sunday at 13:00"
        }

    def _extract_email(self, contact: Dict[str, Any]) -> Optional[str]:
        """Extract email from contact custom fields."""
        try:
            custom_fields = contact.get("custom_fields_values", [])
            for field in custom_fields:
                # Assuming field_name contains "email"
                if "email" in field.get("field_name", "").lower():
                    values = field.get("values", [])
                    if values:
                        return values[0].get("value")
        except:
            pass
        return None
