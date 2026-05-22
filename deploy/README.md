# Deployment Guide — Oracle Cloud

## Стек
- **Сервер:** Oracle Cloud Always Free ARM (Ubuntu 22.04, 4 OCPU, 24 GB RAM)
- **Домен:** [DuckDNS](https://www.duckdns.org) — безкоштовний субдомен
- **SSL:** Let's Encrypt (автооновлення через certbot)
- **Proxy:** Nginx (термінує SSL, проксує до бота на 127.0.0.1:8000)
- **Runtime:** Docker Compose (PostgreSQL + Redis + Bot)

---

## Крок 1 — Oracle Cloud VM

1. Зайди на [cloud.oracle.com](https://cloud.oracle.com) → Create Instance
2. Параметри:
   - **Image:** Ubuntu 22.04
   - **Shape:** VM.Standard.A1.Flex (ARM, Always Free) — 4 OCPU, 24 GB RAM
   - **Boot volume:** 47 GB (безкоштовний ліміт)
3. Завантаж або згенеруй SSH-ключ
4. Збережи публічний IP інстансу

**Важливо — Security List (VCN → Security Lists → Default):**
Додай Ingress Rules:
| Protocol | Port | Source    |
|----------|------|-----------|
| TCP      | 22   | 0.0.0.0/0 |
| TCP      | 80   | 0.0.0.0/0 |
| TCP      | 443  | 0.0.0.0/0 |

---

## Крок 2 — Безкоштовний домен (DuckDNS)

1. Зайди на [duckdns.org](https://www.duckdns.org) → Sign in
2. Створи субдомен, наприклад: `my-rpg-bot`
3. Вкажи публічний IP Oracle VM
4. Запиши токен зі сторінки

---

## Крок 3 — Налаштування сервера

```bash
# Підключитись до VM
ssh ubuntu@<ORACLE_VM_IP>

# Встановити netfilter-persistent (для iptables правил)
sudo apt-get install -y iptables-persistent

# Запустити setup-скрипт
curl -O https://raw.githubusercontent.com/.../deploy/setup.sh
# або скопіювати файл через scp:
# scp deploy/setup.sh ubuntu@<IP>:~/

bash setup.sh my-rpg-bot.duckdns.org <DUCKDNS_TOKEN>
```

Скрипт автоматично:
- Встановлює Docker, Nginx, Certbot
- Налаштовує firewall
- Реєструє DuckDNS cron-оновлення
- Отримує Let's Encrypt сертифікат
- Конфігурує Nginx як reverse proxy

---

## Крок 4 — Деплой бота

```bash
# На сервері
git clone https://github.com/YOUR_USERNAME/R-D-telegram-game.git ~/r-d-telegram-game
cd ~/r-d-telegram-game

# Створити .env з прикладу
cp .env.production.example .env
nano .env  # заповнити всі змінні

# Запустити
docker compose -f docker-compose.prod.yml up -d --build

# Міграції БД (перший раз)
docker compose -f docker-compose.prod.yml exec bot python -m alembic upgrade head

# Логи
docker compose -f docker-compose.prod.yml logs -f bot
```

---

## Оновлення бота

```bash
cd ~/r-d-telegram-game
git pull
docker compose -f docker-compose.prod.yml up -d --build bot
```

---

## Корисні команди

```bash
# Статус
docker compose -f docker-compose.prod.yml ps

# Рестарт бота
docker compose -f docker-compose.prod.yml restart bot

# Логи nginx
sudo tail -f /var/log/nginx/error.log

# Перевірити сертифікат
sudo certbot certificates

# Ручне оновлення сертифікату
sudo certbot renew --dry-run
```

---

## .env на сервері — що змінити

| Змінна | Локальне значення | Продакшн значення |
|--------|-------------------|-------------------|
| `NGROK_URL` | `https://...ngrok.io` | `https://my-rpg-bot.duckdns.org` |
| `WEBHOOK_SECRET` | `secret` | випадковий рядок 32+ символи |
| `POSTGRES_PASSWORD` | `telegram_password` | сильний пароль |
| `DATABASE_URL` | `localhost:5432` | `postgres:5432` (docker network) |
| `REDIS_URL` | `localhost:6379` | `redis:6379` (docker network) |
