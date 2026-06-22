# PolyLife — هسته (Core)

پروژه درس مهندسی نرم‌افزار ۱ — سال ۱۴۰۴/۱۴۰۵.

این مخزن، **هسته (core)** پروژه‌ی PolyLife است: یک پروژه‌ی Django که زیرساخت مشترک (احراز هویت، صفحه‌ی فرود/هوم‌پیج، و دروازه‌ی احراز هویت برای میکروسرویس تیم‌ها) را فراهم می‌کند. هر تیم دانشجویی، سرویس خودش را با **پایگاه‌داده‌ی مجزا** و **gateway اختصاصی** پشت این هسته توسعه می‌دهد.

## معماری

```
 مرورگر ───────────────▶ هسته (Django)            http://localhost:8000
                          • صفحه‌ی فرود React (SPA)
                          • /api/register | login | user
                          • /api/verify  (forward-auth برای تیم‌ها)
                                  ▲
 مرورگر ─▶ gateway تیم (nginx) ───┘  http://localhost:910N
              │
              ▼
           backend تیم ──▶ دیتابیس مستقل تیم (با پسورد یکتا)
```

- **احراز هویت:** username + password ← JWT. هسته توکن را تأیید می‌کند؛ تیم‌ها JWT را decode نمی‌کنند — گیت‌وی‌شان `/api/verify` را صدا می‌زند و هدرهای `X-User-*` را به backend می‌دهد.
- **جداسازی:** هر تیم دیتابیس و یوزر/پسورد مخصوص خودش را دارد.

## ساختار

| مسیر | توضیح |
|------|-------|
| `polylife/` | پروژه‌ی Django (settings، urls، DB router تیم‌ها) |
| `core/` | اپ هسته: مدل User، JWT، API احراز هویت، middleware، `verify` |
| `frontend/` | صفحه‌ی فرود React/Vite (داخل Docker build می‌شود) |
| `teams/` | قالب ۸ تیم — راهنمای دانشجو: `teams/GETTING_STARTED.md` |
| `scripts/` | اسکریپت‌های کمکی (اجرای هسته/تیم‌ها، تولید تیم‌ها) |

## اجرا (با Docker — پیشنهادی)

```powershell
scripts\windows\start-core.ps1        # هسته  → http://localhost:8000
scripts\windows\start-team.ps1 1      # یک تیم → http://localhost:9101
scripts\windows\start-all-teams.ps1   # همه‌ی ۸ تیم (9101..9108)
```
توقف: `scripts\windows\stop-core.ps1` ، `scripts\windows\stop-team.ps1 1` ، `scripts\windows\stop-all.ps1` (همه‌چیز).
معادل bash در `scripts/bash/*.sh` هست.

یوزرهای آماده برای تست: `user1/user1pass` ، `user2/user2pass` ، `user3/user3pass`.

## اجرای هسته بدون Docker

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```
(صفحه‌ی React فقط وقتی داخل Docker build شود نمایش داده می‌شود؛ به‌صورت محلی یک صفحه‌ی fallback به‌علاوه‌ی API کامل می‌بینی.)

## تست‌ها

```powershell
.\.venv\Scripts\python.exe manage.py test core
```

## پیکربندی

برای تنظیمات محلی، `.env.example` را به `.env` کپی کن. هیچ secretـی commit نمی‌شود.
