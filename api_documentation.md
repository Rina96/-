# 🔌 API Документация - Julia AI Platform

## Базовый URL
```
http://localhost:8000
```

---

## 📋 Endpoints

### 1. **Получить все компании**

```http
GET /api/companies
```

**Ответ (200):**
```json
{
  "companies": [
    {
      "id": 1,
      "name": "ShoolaGo",
      "crm_type": "alfarc",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00"
    },
    {
      "id": 2,
      "name": "CompanyA",
      "crm_type": "amocrm",
      "is_active": true,
      "created_at": "2024-02-20T14:20:00"
    }
  ],
  "total": 2
}
```

---

### 2. **Получить компанию по ID**

```http
GET /api/companies/{id}
```

**Пример:**
```
GET /api/companies/1
```

**Ответ (200):**
```json
{
  "id": 1,
  "name": "ShoolaGo",
  "crm_type": "alfarc",
  "crm_config": {
    "base_url": "https://shkolago.s20.online",
    "email": "user@example.com"
  },
  "is_active": true,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

---

### 3. **Создать компанию**

```http
POST /api/companies
Content-Type: application/json
```

**Payload:**
```json
{
  "name": "NewCompany",
  "crm_type": "bitrix24",
  "crm_config": {
    "webhook_url": "https://company.bitrix24.com/rest/1/webhookid/"
  }
}
```

**Ответ (201):**
```json
{
  "id": 3,
  "name": "NewCompany",
  "crm_type": "bitrix24",
  "is_active": true,
  "created_at": "2024-03-15T10:30:00"
}
```

---

### 4. **Обновить компанию**

```http
PUT /api/companies/{id}
Content-Type: application/json
```

**Payload:**
```json
{
  "name": "UpdatedName",
  "is_active": false
}
```

**Ответ (200):**
```json
{
  "id": 1,
  "name": "UpdatedName",
  "is_active": false
}
```

---

### 5. **Удалить компанию**

```http
DELETE /api/companies/{id}
```

**Ответ (200):**
```json
{
  "message": "Company deleted successfully"
}
```

---

### 6. **Тестировать CRM соединение**

```http
POST /api/companies/{id}/test-connection
```

**Ответ (200):**
```json
{
  "status": "connected",
  "crm_type": "alfarc",
  "message": "✅ AlfaCRM connection successful"
}
```

**Ответ (400):**
```json
{
  "status": "failed",
  "error": "❌ AlfaCRM authentication failed - check credentials"
}
```

---

### 7. **Получить статистику**

```http
GET /api/statistics
```

**Ответ (200):**
```json
{
  "total_companies": 3,
  "active_companies": 2,
  "crm_distribution": {
    "alfarc": 1,
    "amocrm": 1,
    "bitrix24": 1
  },
  "total_messages": 5234,
  "total_leads": 234,
  "total_chat_sessions": 145
}
```

---

### 8. **Получить чат сессии компании**

```http
GET /api/companies/{id}/chat-sessions
```

**Query параметры:**
- `limit` (default: 20) — количество записей
- `offset` (default: 0) — смещение
- `status` — фильтр по статусу (new, qualified, booked, paid)

**Пример:**
```
GET /api/companies/1/chat-sessions?limit=10&status=booked
```

**Ответ (200):**
```json
{
  "company_id": 1,
  "chat_sessions": [
    {
      "id": 101,
      "whatsapp_chat_id": "1234567890@c.us",
      "client_name": "Иван Петров",
      "is_qualified": true,
      "booked_date": "2024-03-20",
      "is_paid": false,
      "created_at": "2024-03-10T15:30:00",
      "last_interaction": "2024-03-15T10:20:00"
    },
    {
      "id": 102,
      "whatsapp_chat_id": "9876543210@c.us",
      "client_name": "Мария Сидорова",
      "is_qualified": true,
      "booked_date": "2024-03-22",
      "is_paid": true,
      "created_at": "2024-03-05T12:15:00",
      "last_interaction": "2024-03-14T18:45:00"
    }
  ],
  "total": 45,
  "limit": 10,
  "offset": 0
}
```

---

### 9. **Получить лидов из CRM**

```http
GET /api/companies/{id}/leads
```

**Query параметры:**
- `status` — статус лида (new, qualified, booked, paid)
- `limit` — количество результатов
- `search` — поиск по имени/телефону

**Пример:**
```
GET /api/companies/1/leads?status=qualified&limit=20
```

**Ответ (200):**
```json
{
  "company_id": 1,
  "crm_type": "alfarc",
  "leads": [
    {
      "crm_lead_id": "12345",
      "name": "Иван Петров",
      "phone": "+77011234567",
      "email": "ivan@example.com",
      "status": "qualified",
      "created_at": "2024-03-10T15:30:00"
    }
  ],
  "total": 234
}
```

---

### 10. **Отправить сообщение в WhatsApp**

```http
POST /webhook/whatsapp
Content-Type: application/json
```

**Payload:**
```json
{
  "chatId": "1234567890@c.us",
  "textMessage": "Привет! Это сообщение от Юлии.",
  "timestamp": 1710675000,
  "companyId": 1,
  "imageUrl": "https://example.com/image.jpg"  // опционально
}
```

**Ответ (200):**
```json
{
  "status": "processing",
  "companyId": 1,
  "message": "Message queued for processing"
}
```

---

### 11. **Получить историю сообщений**

```http
GET /api/companies/{id}/messages/{chat_id}
```

**Параметры:**
- `id` — ID компании
- `chat_id` — WhatsApp chat ID
- `limit` — кол-во сообщений (default: 50)

**Ответ (200):**
```json
{
  "chat_id": "1234567890@c.us",
  "company_id": 1,
  "messages": [
    {
      "role": "user",
      "text": "Привет!",
      "timestamp": "2024-03-15T10:20:00"
    },
    {
      "role": "assistant",
      "text": "Привет! Как я могу вам помочь?",
      "timestamp": "2024-03-15T10:20:15"
    }
  ]
}
```

---

### 12. **Получить статус здоровья**

```http
GET /health
```

**Ответ (200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-15T10:30:45",
  "companies": [
    {
      "id": 1,
      "name": "ShoolaGo",
      "crm_type": "alfarc",
      "active": true,
      "crm_connected": true
    },
    {
      "id": 2,
      "name": "CompanyA",
      "crm_type": "amocrm",
      "active": true,
      "crm_connected": false
    }
  ]
}
```

---

## 🔐 Коды ответов

| Код | Описание |
|-----|----------|
| 200 | OK — успешный запрос |
| 201 | Created — ресурс создан |
| 400 | Bad Request — ошибка в запросе |
| 404 | Not Found — ресурс не найден |
| 500 | Internal Server Error — ошибка сервера |

---

## 📝 Примеры использования

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8000"

# Получить все компании
response = requests.get(f"{BASE_URL}/api/companies")
companies = response.json()

# Создать компанию
payload = {
    "name": "MyCompany",
    "crm_type": "bitrix24",
    "crm_config": {
        "webhook_url": "https://..."
    }
}
response = requests.post(f"{BASE_URL}/api/companies", json=payload)
new_company = response.json()

# Тестировать соединение
response = requests.post(f"{BASE_URL}/api/companies/1/test-connection")
test_result = response.json()
```

### JavaScript (fetch)

```javascript
const BASE_URL = "http://localhost:8000";

// Получить компании
fetch(`${BASE_URL}/api/companies`)
  .then(r => r.json())
  .then(data => console.log(data.companies));

// Создать компанию
const payload = {
  name: "MyCompany",
  crm_type: "amocrm",
  crm_config: {
    domain: "company.amocrm.ru",
    client_id: "xxx"
  }
};

fetch(`${BASE_URL}/api/companies`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
})
.then(r => r.json())
.then(data => console.log(data));
```

### cURL

```bash
# Получить компании
curl http://localhost:8000/api/companies

# Создать компанию
curl -X POST http://localhost:8000/api/companies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyCompany",
    "crm_type": "bitrix24",
    "crm_config": {"webhook_url": "https://..."}
  }'

# Тестировать соединение
curl -X POST http://localhost:8000/api/companies/1/test-connection

# Получить статистику
curl http://localhost:8000/api/statistics
```

---

## 🚀 Развертывание

### Запуск сервера

```bash
python main.py
```

### Использование dashboard

1. Откройте `client_dashboard.html` в браузере
2. Dashboard подключится к API на `http://localhost:8000`
3. Добавьте компании через интерфейс

### Для продакшена

```bash
# Используйте Gunicorn/Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 📚 Дополнительные ресурсы

- **CRM Setup:** `MULTI_CRM_SETUP.md`
- **Dashboard:** `client_dashboard.html`
- **Добавление компаний:** `python add_companies.py`
- **Проверка:** `python verify_setup.py`
