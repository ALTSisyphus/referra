# Карта соответствия ТЗ TB4

Этот документ помогает проверить проект перед защитой. Он показывает расположение реализации, **не подтверждая успешный запуск**, поскольку в среде подготовки не были доступны Django-зависимости.

| Пункт дипломного ТЗ | Где реализован / как проверить |
|---|---|
| Ввод телефона и получение четырёхзначного OTP | `accounts/services.py:request_phone_code`, `api/views.py:RequestCodeView`, `/` |
| Имитация SMS с задержкой 1–2 секунды | `send_simulated_sms`, настройка `SMS_SIMULATED_DELAY_SECONDS=1.5` |
| Ввод кода и авторизация | `verify_phone_code`, `POST /api/auth/verify-code/`, `/verify/` |
| Автоматическая регистрация нового пользователя | `User.objects.create_user` после правильного OTP |
| Случайный уникальный инвайт-код из 6 символов | `accounts/models.py:generate_invite_code`, `UserManager` |
| Активация чужого кода только один раз | `activate_invite_code`, транзакция, `POST /api/profile/activate-invite/` |
| В профиле отображается применённый код | `ProfileSerializer`, `/profile/` |
| Список номеров, применивших личный код | `ProfileSerializer.get_invited_phones`, шаблон профиля |
| API с примерами запросов/ответов | `README.md`, `api/views.py` |
| Коллекция Postman | `postman/TB4.postman_collection.json` |
| ReDoc | `/api/redoc/` (`drf-spectacular`) |
| Интерфейс Django Templates | `accounts/templates/accounts/*`, `accounts/views.py` |
| PostgreSQL | `config/settings.py`, `docker-compose.yml` |
| Docker | `Dockerfile`, `docker-compose.yml` |
| README и инструкции по запуску | `README.md` |
| Удалённый Git-репозиторий | Подключается владельцем проекта; GitHub Actions подготовлен в `.github/workflows/ci.yml` |
| Код PEP8 | `pyproject.toml`, `ruff check .` после установки зависимостей |
| Тесты / покрытие не меньше 75% | `tests/*`, `pytest.ini` (`--cov-fail-under=75`); фактический показатель требует запуска `pytest` |

## Чек-лист перед сдачей

- [ ] В Docker Compose успешно стартовали `db` и `web`, миграции применены.
- [ ] Пройдена авторизация по телефону из шаблона.
- [ ] Проведена авторизация по телефону из Postman, получен токен.
- [ ] Созданы два пользователя, активирован код первого пользователем второго.
- [ ] В профиле первого отображается номер второго.
- [ ] Повторная активация отклоняется и не изменяет данные.
- [ ] `python manage.py check` выполнен без ошибок.
- [ ] `python manage.py makemigrations --check --dry-run` не обнаруживает изменений.
- [ ] `ruff check .` завершён успешно.
- [ ] `pytest` завершён успешно с реальным покрытием **не менее 75%**.
- [ ] Репозиторий создан в GitHub и загружен (секреты и `.env` не опубликованы).
- [ ] Сделаны скриншоты ReDoc, Postman, страницы профиля и отчёта pytest для защиты.
