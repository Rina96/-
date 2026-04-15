#!/bin/bash

###############################################################################
# 🚀 Julia AI - Automatic Production Deployment Script
# Запускает систему в production за 5 минут
###############################################################################

set -e  # Exit on error

echo "🚀 JULIA AI PRODUCTION DEPLOYMENT"
echo "=================================="
echo ""

# ============================================================================
# ШАГ 1: Проверка Docker
# ============================================================================

echo "📦 [1/5] Проверка Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "Установи Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose не установлен!"
    echo "Установи Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker установлен"
echo "   - Docker version: $(docker --version)"
echo "   - Docker Compose version: $(docker-compose --version)"
echo ""

# ============================================================================
# ШАГ 2: Подготовка окружения
# ============================================================================

echo "⚙️  [2/5] Подготовка окружения..."

if [ ! -f .env ]; then
    echo "📝 Создаю .env файл из примера..."
    cp .env.example .env
    echo "⚠️  ВНИМАНИЕ: Отредактируй .env файл перед запуском!"
    echo ""
    echo "Отредактируй эти переменные в .env:"
    echo "  - OPENAI_API_KEY"
    echo "  - GEMINI_API_KEY"
    echo "  - GREEN_API_ID_INSTANCE"
    echo "  - GREEN_API_API_TOKEN_INSTANCE"
    echo "  - DB_PASSWORD (опционально, default: julia_password)"
    echo ""
    read -p "Готово? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment отменён"
        exit 1
    fi
else
    echo "✅ .env файл найден"
fi

echo ""

# ============================================================================
# ШАГ 3: Сборка и запуск контейнеров
# ============================================================================

echo "🐳 [3/5] Запуск Docker контейнеров..."
echo "   (это может занять 2-3 минуты при первом запуске)"
echo ""

docker-compose down 2>/dev/null || true
docker-compose up -d

echo "✅ Контейнеры запущены!"
echo ""

# ============================================================================
# ШАГ 4: Ожидание готовности приложения
# ============================================================================

echo "⏳ [4/5] Ожидание готовности приложения..."

RETRIES=30
DELAY=2

for ((i=1; i<=RETRIES; i++)); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Приложение готово!"
        break
    fi

    if [ $i -lt $RETRIES ]; then
        echo "   Попытка $i/$RETRIES... (ждём $DELAY сек)"
        sleep $DELAY
    else
        echo "❌ Приложение не стартовало!"
        echo ""
        echo "Логи:"
        docker-compose logs app
        exit 1
    fi
done

echo ""

# ============================================================================
# ШАГ 5: Проверка и информация
# ============================================================================

echo "🧪 [5/5] Финальная проверка..."
echo ""

HEALTH=$(curl -s http://localhost:8000/health)
echo "✅ Health Check:"
echo "   $HEALTH" | python3 -m json.tool 2>/dev/null || echo "   OK"
echo ""

# ============================================================================
# ФИНИШ
# ============================================================================

echo "=================================="
echo "🎉 DEPLOYMENT УСПЕШЕН!"
echo "=================================="
echo ""

echo "📊 ИНФОРМАЦИЯ О СИСТЕМЕ:"
echo ""
echo "  🌐 API URL:        http://localhost:8000"
echo "  📋 API Docs:       http://localhost:8000/api/companies"
echo "  🏥 Health Check:   http://localhost:8000/health"
echo "  📊 Dashboard:      http://localhost (или https://your-domain.com)"
echo ""

echo "🚀 СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "  1️⃣  Добавить компании:"
echo "      docker exec -it julia_app python add_companies.py"
echo ""
echo "  2️⃣  Проверить компании:"
echo "      curl http://localhost:8000/api/companies"
echo ""
echo "  3️⃣  Просмотреть логи:"
echo "      docker-compose logs -f app"
echo ""
echo "  4️⃣  Остановить систему:"
echo "      docker-compose down"
echo ""

echo "📚 ДОКУМЕНТАЦИЯ:"
echo "   - Развертывание: PRODUCTION_DEPLOYMENT.md"
echo "   - API Docs: api_documentation.md"
echo "   - Клиентам: CLIENT_INTERFACE_GUIDE.md"
echo ""

echo "✨ Система готова к использованию! 🎊"
