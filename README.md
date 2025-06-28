# ILS - Интеллектуальная система обучения

## О проекте

Проект представляет собой интеллектуальную систему обучения, реализующую адаптивное тестирование с использованием нейронных сетей и модели Mistral (LLaMA). Система предназначена для автоматической генерации тестовых вопросов, проведения адаптивных тестов и психологических исследований.

## Авторы

* [Заволженский В.В.](https://github.com/vladdarkstalker)
* [Пивень Н.В.](https://github.com/Reveim)

## Требования к системе

* Операционная система: **Arch Linux / CachyOS Linux** (6.14.5-2-cachyos-deckify)
* Python 3.11+
* Git
* GCC, G++, CMake, Make
* Ngrok (для удалённого доступа)

## Быстрый старт

### Установка системных зависимостей

```bash
sudo pacman -Syu
sudo pacman -S git python python-pip python-virtualenv gcc make cmake
```

### Клонирование репозитория

```bash
git clone https://github.com/vladdarkstalker/ILS
cd ILS
```

### Настройка виртуального окружения

```bash
python -m venv venv
source venv/bin/activate
```

### Установка Python-зависимостей

```bash
pip install -r requirements.txt
```

## Установка и запуск LLaMA.cpp

### Клонирование и сборка llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake ..
make
```

### Подготовка модели

Скачайте модель и разместите её в папке:

```bash
~/ILS/models/
```

Пример файла: `mistral-7b-instruct-v0.2.Q4_K_M.gguf`

### Запуск llama-server

```bash
cd ~/ILS/llama.cpp/build
./bin/llama-server --model ~/ILS/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf --host 0.0.0.0 --port 8080
```

## Запуск Django-приложения

```bash
cd ~/ILS
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
```

### Запуск с использованием ngrok

Убедитесь, что `ngrok` установлен и настроен.

Запустите сервер через скрипт:

```bash
chmod +x start_ngrok_server.sh
./start_ngrok_server.sh
```

## Проверка работы

Перейдите по ссылке, предоставленной ngrok (например, `https://<random>.ngrok-free.app`).

## Структура проекта

* `learnsys/` — Django-приложение системы
* `llama.cpp/` — сервер и исходники модели LLaMA/Mistral
* `models/` — модели нейронных сетей
* `templates/` — HTML-шаблоны
* `media/` — медиафайлы
* `venv/` — виртуальное окружение Python
* `doc/` — документы ВКР о работе

## Основные возможности

* Генерация вопросов и ответов на основе заданного контента
* Адаптивное тестирование с применением модели IRT
* Проведение психологических тестов и их автоматическая интерпретация

## Важные файлы и скрипты

* `manage.py` — управление Django-приложением
* `requirements.txt` — зависимости Python
* `start_ngrok_server.sh` — запуск сервера через ngrok

## Полезные команды

* Остановка Django-сервера: `Ctrl+C`
* Деактивация виртуального окружения: `deactivate`
