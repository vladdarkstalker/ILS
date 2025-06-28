#!/bin/bash

PROJECT_DIR="/home/vladdarkstalker/Projects/ILS"
SETTINGS_FILE="$PROJECT_DIR/iis/settings.py"
VENV="$PROJECT_DIR/venv"

function cleanup {
  echo "[🧹] Завершение работы, остановка процессов и очистка..."
  pkill -f "ngrok http"
  sed -i '/# Django ngrok settings/,$d' "$SETTINGS_FILE"
  echo "[✔] ALLOWED_HOSTS и CSRF_TRUSTED_ORIGINS удалены из settings.py"
}
trap cleanup EXIT

echo "[1] Активация виртуального окружения..."
source "$VENV/bin/activate"

echo "[2] Запуск ngrok..."
ngrok http 8000 > /dev/null &
sleep 5

NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[0-9a-zA-Z\.-]*ngrok-free\.app' | head -n 1)
NGROK_HOST=$(echo "$NGROK_URL" | sed 's|https://||')

if [ -z "$NGROK_HOST" ]; then
  echo "❌ Не удалось получить ngrok URL. Убедись, что токен установлен и ngrok работает."
  exit 1
fi

echo "[3] Обновление settings.py с ALLOWED_HOSTS и CSRF_TRUSTED_ORIGINS..."
sed -i '/# Django ngrok settings/,$d' "$SETTINGS_FILE"
echo -e "\n# Django ngrok settings" >> "$SETTINGS_FILE"
echo "ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0', '$NGROK_HOST']" >> "$SETTINGS_FILE"
echo "CSRF_TRUSTED_ORIGINS = ['$NGROK_URL']" >> "$SETTINGS_FILE"

echo "[4] Запуск Django-сервера на 0.0.0.0:8000..."
cd "$PROJECT_DIR"
echo "✅ Сервер доступен по адресу: $NGROK_URL"
python manage.py runserver 0.0.0.0:8000