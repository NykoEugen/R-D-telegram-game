# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Мова проєкту

Спілкування — українською. Коментарі у коді — англійською.

---

## Команди

```bash
# Запуск (Docker — основний спосіб)
docker compose up -d          # старт PostgreSQL + Redis + бот
docker compose logs -f bot    # логи бота

# БД
make db-migrate MSG="опис змін"   # нова міграція
make db-upgrade                    # застосувати міграції
make db-downgrade                  # відкотити на один крок
make db-reset                      # повний reset

# Якість коду
make fix      # ruff + black + isort (авто-виправлення)
make check    # перевірка без змін (CI)
make lint     # тільки ruff
make typecheck  # mypy
```

---

## Сховище Obsidian

Звертайся до цього сховища, тут є вся інформація у тому числі знаходження Chroma
~/Documents/Claude/Obsidian/RD Telegram Game