# 🎨 Руководство по интерфейсу клиента

## 📱 Dashboard для управления компаниями

### Файлы:
- **`client_dashboard.html`** — веб-интерфейс (открыть в браузере)
- **`api_routes.py`** — API endpoints для работы с интерфейсом
- **`api_documentation.md`** — полная API документация

---

## 🚀 БЫСТРЫЙ СТАРТ

### 1. Интеграция API в main.py

```python
# В главном файле main.py добавьте:

from api_routes import router as api_router

app = FastAPI()

# ... ваш существующий код ...

# Подключите API маршруты
app.include_router(api_router)
```

### 2. Запустите сервер

```bash
python main.py
```

### 3. Откройте dashboard

```bash
# В браузере откройте:
file:///path/to/client_dashboard.html

# Или если сервер на другом хосте:
# http://your-server:8000
# (добавьте CORS настройки в main.py)
```

---

## 🎯 ГЛАВНЫЕ РАЗДЕЛЫ ИНТЕРФЕЙСА

### 1️⃣ **Панель управления компаниями**
```
┌─────────────────────────────────────────┐
│  🏢 ВАШ КОМПАНИИ                        │
├─────────────────────────────────────────┤
│                                         │
│  ShoolaGo          🟢 AlfaCRM  ✅ Active│
│  Created: 2024-01-15                    │
│  [🧪 Тест] [✏️ Edit] [🗑️ Delete]        │
│                                         │
│  CompanyA          🟡 AmoCRM   ✅ Active│
│  Created: 2024-02-20                    │
│  [🧪 Тест] [✏️ Edit] [🗑️ Delete]        │
│                                         │
│  CompanyB          🔵 Bitrix24 ✅ Active│
│  Created: 2024-03-15                    │
│  [🧪 Тест] [✏️ Edit] [🗑️ Delete]        │
└─────────────────────────────────────────┘
```

**Возможности:**
- ✅ Просмотр всех компаний
- ✅ Статус активации (✅ Active / ❌ Inactive)
- ✅ Тип CRM с цветной иконкой
- ✅ Дата создания
- ✅ Быстрые действия (Тест, Изменить, Удалить)

---

### 2️⃣ **Статистика**
```
┌──────────────┬──────────────┐
│   📊 Статис  │   📊ика      │
├──────────────┼──────────────┤
│  Компаний: 3 │  Активных: 3 │
├──────────────┼──────────────┤
│Сообщений:5234│   Лидов: 234 │
└──────────────┴──────────────┘
```

**Показывает:**
- Общее количество компаний
- Активные компании
- Всего сообщений (WhatsApp)
- Всего лидов (из всех CRM)

---

### 3️⃣ **По типам CRM**
```
┌─────────────┐   ┌──────────┐   ┌──────────┐
│ 🟡 AmoCRM   │   │ 🔵 Bitrix│   │ 🟢 Alfa  │
├─────────────┤   ├──────────┤   ├──────────┤
│Компаний: 1  │   │ Компаний:│   │Компаний:1│
└─────────────┘   │    1     │   └──────────┘
                  └──────────┘
```

**Информация:**
- Количество компаний по каждому CRM
- Краткое описание каждой CRM
- Визуальное распределение

---

### 4️⃣ **Таблица со всеми компаниями**

| ID | Компания | CRM | Статус | Создана | Действия |
|---|--|--|--|--|--|
| 1 | ShoolaGo | ALFARC | ✅ | 2024-01-15 | [Тест] |
| 2 | CompanyA | AMOCRM | ✅ | 2024-02-20 | [Тест] |
| 3 | CompanyB | BITRIX24 | ✅ | 2024-03-15 | [Тест] |

**Функции:**
- Полный список всех компаний
- Сортировка (ID, имя, CRM, статус)
- Быстрая проверка соединения

---

### 5️⃣ **Модальное окно "Добавить компанию"**

```
┌─────────────────────────────────────┐
│ ➕ Добавить новую компанию          │
├─────────────────────────────────────┤
│                                     │
│ Название компании:                  │
│ [________________________]           │
│ Уникальное название вашей компании │
│                                     │
│ Тип CRM:                            │
│ [▼ Выберите CRM                     │
│   🟡 AmoCRM (Sales CRM)             │
│   🔵 Bitrix24 (All-in-One)          │
│   🟢 AlfaCRM (Education)            │
│                                     │
│ CRM-специфичные поля:               │
│ (динамически меняются)              │
│                                     │
│ ┌──────────────┐ ┌──────────────┐  │
│ │   Отмена     │ │  Сохранить   │  │
│ └──────────────┘ └──────────────┘  │
└─────────────────────────────────────┘
```

**Особенности:**
- Динамические поля в зависимости от CRM
- Валидация перед сохранением
- Наглядная помощь при каждом поле

---

## 🔑 **ДИНАМИЧЕСКИЕ ПОЛЯ ДЛЯ КАЖДОГО CRM**

### AmoCRM
```
Domain: company.amocrm.ru
Client ID: xxxxxxxx
Client Secret: xxxxxxxx
Redirect URI: https://example.com/callback
Refresh Token: xxxxxxxx
```

### Bitrix24
```
Webhook URL: https://company.bitrix24.com/rest/1/webhookid/
```

### AlfaCRM
```
Base URL: https://company.s20.online
Email: user@example.com
API Key: xxxxxxxx-xxxx-xxxx-xxxx
App Key: xxxxxxxx
```

---

## 🌐 **API ENDPOINTS ДЛЯ ИНТЕГРАЦИИ**

### Получить компании
```bash
GET /api/companies
```

**Ответ:**
```json
{
  "companies": [
    {
      "id": 1,
      "name": "ShoolaGo",
      "crm_type": "alfarc",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "total": 3
}
```

---

### Создать компанию
```bash
POST /api/companies
Content-Type: application/json

{
  "name": "NewCompany",
  "crm_type": "bitrix24",
  "crm_config": {
    "webhook_url": "https://company.bitrix24.com/rest/1/webhookid/"
  }
}
```

---

### Тестировать соединение
```bash
POST /api/companies/1/test-connection
```

**Ответ (успех):**
```json
{
  "status": "connected",
  "crm_type": "alfarc",
  "company_name": "ShoolaGo",
  "message": "✅ AlfaCRM connection successful"
}
```

**Ответ (ошибка):**
```json
{
  "status": "failed",
  "crm_type": "bitrix24",
  "error": "Failed to authenticate with Bitrix24"
}
```

---

### Получить статистику
```bash
GET /api/statistics
```

**Ответ:**
```json
{
  "timestamp": "2024-03-15T10:30:45",
  "companies": {
    "total": 3,
    "active": 3,
    "by_crm_type": {
      "alfarc": 1,
      "amocrm": 1,
      "bitrix24": 1
    }
  },
  "chat_sessions": {
    "total": 145,
    "booked": 45,
    "paid": 23,
    "total_messages": 5234
  }
}
```

---

### Получить чат сессии
```bash
GET /api/companies/1/chat-sessions?limit=10&status=booked
```

**Ответ:**
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
      "created_at": "2024-03-10T15:30:00"
    }
  ],
  "total": 45
}
```

---

## 🎨 **ДИЗАЙН И UX**

### Цветовая схема
```
🟡 AmoCRM  → Красный/Розовый (#d65555)
🔵 Bitrix24 → Синий (#2196F3)
🟢 AlfaCRM → Зелёный (#4CAF50)
🟣 Главное → Фиолетовый (#667eea)
```

### Адаптивность
- ✅ Мобильные (375px)
- ✅ Планшеты (768px)
- ✅ Десктопы (1280px+)

### Анимации
- Плавные переходы (0.3s)
- Hover эффекты
- Pulse анимация для статус-индикаторов

---

## 🔌 **ИНТЕГРАЦИЯ С BACKEND**

### Шаг 1: Добавьте API маршруты в main.py

```python
from api_routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware

# Добавьте CORS (для работы dashboard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключите API маршруты
app.include_router(api_router)
```

### Шаг 2: Запустите сервер

```bash
python main.py
```

Сервер будет доступен на `http://localhost:8000`

### Шаг 3: Откройте dashboard

```bash
# Откройте в браузере:
file:///path/to/client_dashboard.html
```

---

## 📊 **ТИПИЧНЫЕ СЦЕНАРИИ ИСПОЛЬЗОВАНИЯ**

### Сценарий 1: Добавить новую компанию

1. Нажмите `➕ Добавить компанию`
2. Введите название: "MyCompany"
3. Выберите CRM: "Bitrix24"
4. Вставьте webhook URL
5. Нажмите "Сохранить"
6. Нажмите "🧪 Тест" для проверки соединения

### Сценарий 2: Проверить статус всех компаний

1. Откройте dashboard
2. Посмотрите раздел "Статистика"
3. Нажмите "🔄 Обновить" для свежих данных
4. Перейдите во вкладку "По типам CRM" для распределения

### Сценарий 3: Просмотреть лидов компании

1. В таблице найдите компанию
2. Откройте `/api/companies/1/leads` в браузере
3. Получите JSON список всех лидов

### Сценарий 4: Проверить сообщения пользователя

1. Выполните запрос к `/api/companies/1/messages/{chat_id}`
2. Получите полную историю сообщений

---

## 🧪 **ТЕСТИРОВАНИЕ ИНТЕРФЕЙСА**

### Локальное тестирование

```bash
# 1. Запустите сервер
python main.py

# 2. В другом терминале проверьте API
curl http://localhost:8000/api/companies

# 3. Откройте dashboard
open client_dashboard.html
```

### Тестирование CRM соединения

```bash
# Проверить все компании
curl http://localhost:8000/health

# Проверить одну компанию
curl -X POST http://localhost:8000/api/companies/1/test-connection
```

---

## 📚 **ДОКУМЕНТАЦИЯ**

- **API Docs:** `/api_documentation.md`
- **Multi-CRM Setup:** `/MULTI_CRM_SETUP.md`
- **Code Examples:** `/main_multi_company_example.py`
- **Verification:** `python verify_setup.py`

---

## 🚀 **РАЗВЕРТЫВАНИЕ НА ПРОДАКШЕНЕ**

### Использование Gunicorn + Nginx

```bash
# Установка
pip install gunicorn

# Запуск
gunicorn -w 4 -b 0.0.0.0:8000 main:app

# Nginx конфиг
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

### Docker контейнеризация

```dockerfile
FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🎓 **ОБУЧЕНИЕ КЛИЕНТОВ**

### Для ваших клиентов:

**Основные функции:**
1. ✅ Добавить компанию за 3 клика
2. ✅ Выбрать нужную CRM
3. ✅ Вставить учетные данные
4. ✅ Проверить соединение
5. ✅ Видеть статистику в реальном времени

**Что они видят:**
- Список всех своих компаний
- Статус каждой компании
- Какой CRM используется
- Когда была добавлена компания
- Статистику сообщений и лидов

---

## 🆘 **ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ**

**Q: Как добавить компанию?**
A: Нажмите `➕ Добавить компанию`, заполните форму, нажмите `Сохранить`

**Q: Как проверить соединение с CRM?**
A: Нажмите кнопку `🧪 Тест` рядом с компанией

**Q: Где видеть ошибки соединения?**
A: В alert уведомлении в правом верхнем углу

**Q: Как просмотреть детальную информацию о лидах?**
A: Используйте API endpoint `/api/companies/{id}/leads`

**Q: Можно ли отредактировать компанию?**
A: Да, нажмите `✏️ Изменить` (функция в разработке)

---

## 📞 **ПОДДЕРЖКА**

Если возникают проблемы:

1. Проверьте `/health` endpoint
2. Проверьте логи в консоли
3. Запустите `python verify_setup.py`
4. Проверьте файл `.env` с учетными данными

---

**Dashboard готов к использованию! 🎉**
