# 🚀 Railway.app Cloud Deployment Guide

## ⚡ Quick Overview

Railway.app - самое простое облачное решение для развертывания Julia AI. **Без Docker локально!** Всё работает в облаке.

**⏱️ Время развертывания: 5-10 минут**

---

## 📋 Требования

- ✅ GitHub аккаунт
- ✅ Railway.app аккаунт (бесплатный)
- ✅ API ключи (уже есть в .env)

---

## 🎯 Шаги развертывания

### Шаг 1: Подготовка GitHub репозитория

```bash
# Убедись, что все изменения закоммичены
cd "/Users/rinatamangeldi/Downloads/whatsapp-agent 2/.claude/worktrees/tender-ptolemy"
git status  # должно быть "nothing to commit, working tree clean"

# Убедись что .env в .gitignore (ключи не попадут в GitHub)
grep .env .gitignore

# Убедись что docker-compose.yml правильный
cat docker-compose.yml | head -30
```

### Шаг 2: Создать проект на Railway.app

1. **Перейди на** https://railway.app
2. **Нажми** "Create New Project"
3. **Выбери** "Deploy from GitHub"
4. **Авторизуйся** в GitHub
5. **Выбери репо:** `Rina96/-`

### Шаг 3: Настроить переменные окружения

На странице проекта Railway:

**Нажми** "Variables" или "Add Variable"

**Добавь все из твоего .env файла:**

```
OPENAI_API_KEY=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

GEMINI_API_KEY=AIzaSyCBBUh04vUK19uW3oSRgFOaDRfD40eZpPg

GREEN_API_ID_INSTANCE=7107559743

GREEN_API_API_TOKEN_INSTANCE=8c0a74e817974b0a92ccab37818a7810d71331a8012c4b1e95

ALFA_EMAIL=schoolgoalmaty@gmail.com

ALFA_API_KEY=95a954c1-33e5-11f1-a996-3cecefbdd1ae

ALFA_APP_KEY=325702e0f2a21a95b6df99e47dc82d02

ALFA_BASE_URL=https://shkolago.s20.online

ALFA_SUBDOMAIN=shkolago

DB_PASSWORD=julia_password

DEBUG=False
```

### Шаг 4: Railway создаст PostgreSQL автоматически

Railway автоматически:
- ✅ Создаст PostgreSQL базу данных
- ✅ Добавит переменные окружения для БД
- ✅ Настроит сетевое соединение

**Добавь эту переменную:**
```
DATABASE_URL=postgresql+asyncpg://postgres:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}
```

(Railway предоставит значения для PGPASSWORD, PGHOST, PGPORT, PGDATABASE автоматически)

### Шаг 5: Deploy

1. **Нажми** "Deploy" в интерфейсе Railway
2. **Дождись** 3-5 минут (логи будут показывать прогресс)
3. **Railway скажет** успешно ✅ или ошибка ❌

### Шаг 6: Проверить развертывание

Railway предоставит URL твоего приложения:

```
https://your-project-name.railway.app
```

**Проверь здоровье:**
```
https://your-project-name.railway.app/health
```

**Должна вернуть JSON:**
```json
{
  "status": "ok",
  "database": "connected",
  "crm": "configured"
}
```

**Открой Dashboard:**
```
https://your-project-name.railway.app
```

---

## 🔧 Railway Environment Variables

Railway автоматически создаст эти переменные из PostgreSQL:
- `PGDATABASE` - имя БД
- `PGHOST` - хост БД
- `PGPORT` - порт БД  
- `PGUSER` - пользователь БД
- `PGPASSWORD` - пароль БД

**Используй их в DATABASE_URL:**
```
postgresql+asyncpg://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}
```

---

## 📊 Мониторинг после развертывания

### Логи в Railway:
```
Нажми "Logs" в интерфейсе Railway
```

### API статус:
```bash
curl https://your-project.railway.app/health
```

### Тестирование компании:
```bash
curl -X GET https://your-project.railway.app/api/companies
```

---

## 🚨 Решение проблем

### "Build failed"
- ❌ Проверь что requirements.txt существует
- ❌ Проверь что main.py есть в корне репо
- ❌ Проверь логи Railway (Logs tab)

### "Cannot connect to database"
- ❌ Проверь что DATABASE_URL правильный
- ❌ Дождись 2-3 мин чтобы PostgreSQL стартировал
- ❌ Проверь что PGPASSWORD установлена

### "API недоступен"
- ❌ Дождись 5 минут после deploy
- ❌ Проверь logи: `https://your-project.railway.app/health`
- ❌ Обнови страницу (браузер может кешировать)

---

## 💡 Best Practices

✅ **Сделай:**
- Используй Railway.app (простейший способ)
- Храни .env локально (не коммитай в git)
- Проверяй логи Railway при ошибках
- Добавь компании через API после развертывания

❌ **НЕ делай:**
- Не ставь Docker Desktop на macOS 13
- Не коммитай .env файл в GitHub  
- Не раскрывай API ключи в чате
- Не используй localhost URLs в production

---

## 🎉 Готово!

После успешного развертывания:

1. **Система работает в облаке** 24/7
2. **Все компании** автоматически синхронизируются
3. **API доступен** для интеграций
4. **Dashboard работает** в браузере

**URL твоей системы:**
```
https://your-project-name.railway.app
```

---

## 📚 Дополнительные ресурсы

- [Railway.app документация](https://docs.railway.app)
- [PostgreSQL на Railway](https://docs.railway.app/databases/postgresql)
- [Переменные окружения Railway](https://docs.railway.app/develop/variables)
- [Логирование на Railway](https://docs.railway.app/observe/logs)
