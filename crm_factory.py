"""
CRM Factory - creates appropriate CRM adapter based on CRM type.
"""
from typing import Dict, Any, Optional
from loguru import logger
from crm_base import BaseCRMAdapter
from crm_amocrm import AmoCRMAdapter
from crm_bitrix24 import Bitrix24Adapter
from integrations import AlfaCrmManager


class CRMFactory:
    """Factory for creating CRM adapters based on CRM type."""

    SUPPORTED_CRMS = {
        "amocrm": AmoCRMAdapter,
        "bitrix24": Bitrix24Adapter,
        "alfarc": AlfaCrmManager,
        "alfacrm": AlfaCrmManager,  # Alias
    }

    @staticmethod
    async def create_adapter(crm_type: str, config: Dict[str, Any]) -> Optional[BaseCRMAdapter]:
        """
        Create and authenticate CRM adapter.

        Args:
            crm_type: Type of CRM ("amocrm", "bitrix24", "alfarc")
            config: Configuration dictionary with credentials

        Returns:
            Authenticated CRM adapter or None if failed
        """
        crm_type = crm_type.lower().strip()

        if crm_type not in CRMFactory.SUPPORTED_CRMS:
            logger.error(f"❌ Unsupported CRM type: {crm_type}")
            logger.info(f"Supported CRMs: {', '.join(CRMFactory.SUPPORTED_CRMS.keys())}")
            return None

        try:
            adapter_class = CRMFactory.SUPPORTED_CRMS[crm_type]
            adapter = adapter_class(config)

            # Authenticate
            if not await adapter.authenticate():
                logger.error(f"❌ Failed to authenticate {crm_type}")
                return None

            logger.success(f"✅ {crm_type.upper()} adapter created and authenticated")
            return adapter

        except Exception as e:
            logger.error(f"❌ Error creating {crm_type} adapter: {e}")
            return None

    @staticmethod
    def get_supported_crms() -> Dict[str, str]:
        """Get list of supported CRMs."""
        return {
            "amocrm": "AmoCRM - Web-based CRM for sales teams",
            "bitrix24": "Bitrix24 - All-in-one CRM and collaboration platform",
            "alfarc": "AlfaCRM - Sales funnel management (s20.online)"
        }

    @staticmethod
    def validate_config(crm_type: str, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate CRM configuration has required fields.

        Args:
            crm_type: Type of CRM
            config: Configuration to validate

        Returns:
            (is_valid, error_message)
        """
        crm_type = crm_type.lower().strip()

        if crm_type == "amocrm":
            required_fields = ["domain", "client_id", "client_secret", "refresh_token"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                return False, f"AmoCRM: Missing fields {missing}"

        elif crm_type == "bitrix24":
            required_fields = ["webhook_url"] if config.get("webhook_url") else ["domain", "access_token"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                return False, f"Bitrix24: Missing fields {missing}"

        elif crm_type in ("alfarc", "alfacrm"):
            required_fields = ["base_url", "email", "api_key", "app_key"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                return False, f"AlfaCRM: Missing fields {missing}"

        return True, "Valid configuration"


# Example usage function
async def example_multi_crm_usage():
    """Example of how to use multiple CRMs with different companies."""

    # Company 1: Using AmoCRM
    amo_config = {
        "domain": "mycompany.amocrm.ru",
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "redirect_uri": "https://example.com/callback",
        "refresh_token": "your_refresh_token"
    }

    # Company 2: Using Bitrix24
    bitrix_config = {
        "webhook_url": "https://mycompany.bitrix24.com/rest/1/webhookid/"
    }

    # Create adapters
    amo_adapter = await CRMFactory.create_adapter("amocrm", amo_config)
    bitrix_adapter = await CRMFactory.create_adapter("bitrix24", bitrix_config)

    if amo_adapter:
        # Use AmoCRM
        lead = await amo_adapter.get_lead_by_phone("+1234567890")
        logger.info(f"Lead from AmoCRM: {lead}")

    if bitrix_adapter:
        # Use Bitrix24
        lead = await bitrix_adapter.get_lead_by_phone("+1234567890")
        logger.info(f"Lead from Bitrix24: {lead}")
