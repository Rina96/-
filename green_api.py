import httpx
from loguru import logger
from config import settings

class GreenApiManager:
    def __init__(self):
        self.host = "https://api.green-api.com"
        self.id_instance = settings.GREEN_API_ID_INSTANCE
        self.api_token = settings.GREEN_API_API_TOKEN_INSTANCE
        
        if not self.id_instance or not self.api_token:
            logger.warning("GREEN API Credentials not set! WhatsApp integration will fail.")

    def _get_url(self, action: str) -> str:
        return f"{self.host}/waInstance{self.id_instance}/{action}/{self.api_token}"

    async def send_message(self, chat_id: str, message: str) -> bool:
        """
        Sends a standard text message.
        chat_id: usually formatting '79991234567@c.us'
        """
        if not self.id_instance:
            logger.error("Cannot send WA message. Credentials missing.")
            return False

        url = self._get_url("sendMessage")
        payload = {
            "chatId": chat_id,
            "message": message
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Message sent to {chat_id}, receipt: {data.get('idMessage')}")
                return True
            except Exception as e:
                logger.error(f"Failed to send WA message: {e}")
                return False

wa_client = GreenApiManager()
