# Alembic migratsiyalari

Birinchi migratsiyani yaratish (modellar asosida avtomatik):

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

> Eslatma: Dev (SQLite) uchun `python -m app.seed` ham jadvallarni yaratadi.
> Prod (PostgreSQL) uchun Alembic migratsiyasidan foydalaning.
