# Telegram E-Commerce Platform

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)


[English](#english-version) <---> [Русский](#русская-версия)

## English Version

A production-ready, backend platform for managing a Telegram-based e-commerce store and survey. This system provides a secure backend for handling Telegram Webhooks, processing payments, executing asynchronous mass mailing, and designed for integration with a React frontend.

### Key Features
* **Secure Telegram Webhooks:** Implements the `X-Telegram-Bot-Api-Secret-Token` header validation to ensure incoming requests strictly originate from Telegram servers.
* **Native Payments Integration:** Full lifecycle management of the Telegram Payments API, including pre-checkout stock validation and automated database state updates.
* **Asynchronous Task Queue:** Utilizes Celery and Redis for handling mass messaging campaigns (text and media groups) without blocking the primary application thread. Implements retry mechanisms (`chord` structure) to comply with Telegram API rate limits.
* **Concurrency Control:** Utilizes database-level `F()` expressions to prevent race conditions during concurrent item purchases.
* **Infrastructure Security:** Nginx is configured with strict `limit_req_zone` directives to mitigate DDoS attacks and API flooding.

### Tech Stack
* **Backend:** Python 3.12, Django, Django REST Framework, Telebot (pyTelegramBotAPI).
* **Frontend:** React.js.
* **Database & Messaging:** PostgreSQL 15, Redis (Alpine).
* **Infrastructure & DevOps:** Docker, Docker Compose, Nginx, Gunicorn.

### Local Development Setup

1. **Clone the repository:**

git clone https://github.com/vdneech/telebot-ecommerce-platform.git
cd telebot-ecommerce-platform

2. **Environment Configuration:**
Copy the template environment file and populate it with specific keys:

cp .env.example .env

3. **Build and Run:**
Initialize the containerized infrastructure (Web Server, Database, Cache, Background Workers).

docker compose up --build -d

4. **Database Initialization:**

docker exec -it backend python manage.py migrate
docker exec -it backend python manage.py createsuperuser

The API will be available at `http://localhost/api/`

---

## Русская версия

Готовая к продакшену backend-платформа для управления интернет-анкетой с магазином на базе Telegram. Система предоставляет защищенный бэкенд для обработки вебхуков, проведения платежей, асинхронных массовых рассылок. Код рассчитан на билд фронтенда на React.

### Ключевые особенности
* **Защищенные вебхуки Telegram:** Реализована строгая валидация заголовка `X-Telegram-Bot-Api-Secret-Token` для предотвращения несанкционированного доступа к эндпоинтам бота.
* **Интеграция нативных платежей:** Полный цикл работы с Telegram Payments API, включая pre-checkout валидацию остатков товаров и автоматическое обновление состояния базы данных после успешной транзакции.
* **Асинхронные фоновые задачи:** Использование Celery и Redis для массовых рассылок (текст и медиагруппы) без блокировки основного потока WSGI-сервера. Реализованы механизмы повторных попыток для соблюдения лимитов Telegram API.
* **Контроль состояния гонки (Race Conditions):** Использование выражений `F()` на уровне базы данных для предотвращения ошибок при параллельной покупке товаров пользователями.
* **Безопасность инфраструктуры:** Nginx настроен с использованием директив `limit_req_zone` для защиты от DDoS-атак, ботов и ограничения частоты запросов к статике и API.

### Стек технологий
* **Бэкенд:** Python 3.12, Django, Django REST Framework, Telebot (pyTelegramBotAPI).
* **База данных и кэш:** PostgreSQL 15, Redis (Alpine).
* **Инфраструктура и DevOps:** Docker, Docker Compose, Nginx, Gunicorn.

### Локальный запуск

1. **Клонирование репозитория:**

git clone https://github.com/vdneech/telebot-ecommerce-platform.git
cd telebot-ecommerce-platform

2. **Настройка окружения:**
Скопируйте конфигурационный файл и заполните его данными:

cp .env.example .env

3. **Сборка и запуск:**
Запуск всей микросервисной архитектуры через Docker Compose.

docker compose up --build -d

4. **Инициализация базы данных:**

docker exec -it backend python manage.py migrate
docker exec -it backend python manage.py createsuperuser

API будет доступно по `http://localhost/api/`
