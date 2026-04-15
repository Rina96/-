#!/bin/bash

###############################################################################
# 🤖 ПОЛНОСТЬЮ АВТОМАТИЧЕСКИЙ DEPLOYMENT
# Просто запусти: bash auto-deploy.sh
###############################################################################

set -e

PROJECT_DIR=$(pwd)
REPO_URL="https://github.com/Rina96/-.git"
BRANCH="main"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         🚀 JULIA AI - АВТОМАТИЧЕСКИЙ DEPLOYMENT           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# ЭТАП 1: ПОДГОТОВКА
# ============================================================================

echo "📋 ЭТАП 1: Подготовка системы..."
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ ОШИБКА: Docker не установлен"
    echo "   Установи: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ ОШИБКА: docker-compose не установлен"
    echo "   Установи: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker готов"
echo ""

# ============================================================================
# ЭТАП 2: ОКРУЖЕНИЕ
# ============================================================================

echo "📝 ЭТАП 2: Подготовка .env файла..."
echo ""

if [ ! -f .env ]; then
    echo "Создаю .env из шаблона..."
    cp .env.example .env

    # Автозаполнение значений (если нужны)
    if [ ! -z "$OPENAI_API_KEY" ]; then
        sed -i '' "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$OPENAI_API_KEY|g" .env
    fi

    if [ ! -z "$GEMINI_API_KEY" ]; then
        sed -i '' "s|GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_API_KEY|g" .env
    fi

    echo "✅ .env создан"
    echo ""
    echo "⚠️  ТРЕБУЕТСЯ НАСТРОЙКА!"
    echo "Отредактируй .env файл и добавь:"
    echo "  - OPENAI_API_KEY (обязательно)"
    echo "  - GEMINI_API_KEY (обязательно)"
    echo "  - GREEN_API_ID_INSTANCE (обязательно)"
    echo "  - GREEN_API_API_TOKEN_INSTANCE (обязательно)"
    echo ""
    echo "После редактирования запусти: bash auto-deploy.sh"
    exit 1
else
    echo "✅ .env файл готов"
    echo ""
fi

# ============================================================================
# ЭТАП 3: DOCKER
# ============================================================================

echo "🐳 ЭТАП 3: Запуск контейнеров Docker..."
echo ""

# Остановка старых контейнеров
echo "Останавливаю старые контейнеры..."
docker-compose down 2>/dev/null || true
sleep 2

# Сборка и запуск
echo "Собираю образы и запускаю контейнеры..."
docker-compose up -d

echo "✅ Контейнеры запущены"
echo ""

# ============================================================================
# ЭТАП 4: ОЖИДАНИЕ
# ============================================================================

echo "⏳ ЭТАП 4: Ожидание инициализации..."
echo ""

MAX_RETRIES=60
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Приложение готово!"
        break
    fi

    RETRY=$((RETRY + 1))

    if [ $((RETRY % 10)) -eq 0 ]; then
        echo "   Попытка $RETRY/$MAX_RETRIES..."
    fi

    sleep 1
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "❌ ОШИБКА: Приложение не стартовало"
    echo ""
    echo "Логи:"
    docker-compose logs app
    exit 1
fi

echo ""

# ============================================================================
# ЭТАП 5: ПРОВЕРКА
# ============================================================================

echo "🧪 ЭТАП 5: Проверка системы..."
echo ""

HEALTH=$(curl -s http://localhost:8000/health)
COMPANIES=$(curl -s http://localhost:8000/api/companies)

echo "✅ Health Check: OK"
echo "✅ API Response: OK"
echo ""

# ============================================================================
# ЭТАП 6: ИНСТРУКЦИИ
# ============================================================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✨ DEPLOYMENT УСПЕШЕН! ✨                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "🎯 СИСТЕМА ГОТОВА К ИСПОЛЬЗОВАНИЮ"
echo ""

echo "📍 ДОСТУПНЫЕ ЭНДПОИНТЫ:"
echo "   API:           http://localhost:8000/api"
echo "   Health:        http://localhost:8000/health"
echo "   Dashboard:     http://localhost"
echo ""

echo "🚀 БЫСТРЫЕ КОМАНДЫ:"
echo ""
echo "   Добавить компании:"
echo "   $ docker exec -it julia_app python add_companies.py"
echo ""
echo "   Просмотреть компании:"
echo "   $ curl http://localhost:8000/api/companies"
echo ""
echo "   Проверить здоровье системы:"
echo "   $ curl http://localhost:8000/health"
echo ""
echo "   Просмотреть логи:"
echo "   $ docker-compose logs -f app"
echo ""
echo "   Остановить систему:"
echo "   $ docker-compose down"
echo ""

echo "📚 ДОКУМЕНТАЦИЯ:"
echo "   Основное:        README.md"
echo "   Deployment:      PRODUCTION_DEPLOYMENT.md"
echo "   API:             api_documentation.md"
echo "   Dashboard:       CLIENT_INTERFACE_GUIDE.md"
echo ""

echo "💡 СЛЕДУЮЩИЕ ШАГИ:"
echo "   1. Добавь компании (запусти команду выше)"
echo "   2. Настрой Green API webhooks"
echo "   3. Тестируй API endpoints"
echo "   4. Готово к production!"
echo ""

echo "🎊 Enjoy! 🎉"
