import httpx
import os
from typing import List, Dict, Any
from loguru import logger
from config import settings

class GreenApiManager:
    """Enhanced WhatsApp gateway with cloud history retrieval."""
    
    def __init__(self):
        self.host = settings.GREEN_API_HOST
        self.id_instance = settings.GREEN_API_ID_INSTANCE
        self.api_token = settings.GREEN_API_API_TOKEN_INSTANCE
        
    def _get_url(self, action: str) -> str:
        return f"{self.host}/waInstance{self.id_instance}/{action}/{self.api_token}"

    async def send_message(self, chat_id: str, message: str) -> bool:
        url = self._get_url("sendMessage")
        payload = {"chatId": chat_id, "message": message}
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, timeout=10.0)
                return r.status_code == 200
            except Exception as e:
                logger.error(f"WA Error: {e}")
                return False

    async def get_chat_history(self, chat_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """Cloud memory: Fetches official chat history from Green API Cloud."""
        url = self._get_url("getChatHistory")
        payload = {"chatId": chat_id, "count": count}
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, timeout=10.0)
                if r.status_code == 200:
                    history = r.json()
                    ai_history = []
                    for msg in reversed(history):
                        role = "assistant" if msg.get("type") == "outgoing" else "user"
                        text = msg.get("textMessage", "")
                        if text:
                            ai_history.append({"role": role, "text": text})
                    return ai_history
                return []
            except Exception as e:
                logger.error(f"⚠️ WA History Fail: {e}")
                return []

    async def send_file(self, chat_id: str, file_path: str, caption: str = "") -> bool:
        url = self._get_url("sendFileByUpload")
        file_name = os.path.basename(file_path)
        async with httpx.AsyncClient() as client:
            try:
                files = {'file': (file_name, open(file_path, 'rb'), 'application/octet-stream')}
                data = {'chatId': chat_id, 'caption': caption}
                r = await client.post(url, data=data, files=files, timeout=30.0)
                return r.status_code == 200
            except Exception as e:
                logger.error(f"WA File Error: {e}")
                return False

    async def download_file(self, download_url: str) -> bytes:
        async with httpx.AsyncClient() as client:
            r = await client.get(download_url)
            return r.content

wa_client = GreenApiManager()
