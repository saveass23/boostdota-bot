# FunPay Lot Autofill Bot

Скрипт на Python + Playwright для полуавтоматического заполнения лотов на FunPay.

## Что умеет

- читает лоты из `CSV`;
- заполняет форму по CSS-селекторам из JSON;
- сохраняет авторизационную сессию (`storage_state`);
- поддерживает `--dry-run` без отправки формы.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Подготовка

1. Создайте CSV по примеру `lots.example.csv`.
2. Создайте JSON селекторов по примеру `selectors.example.json`.
   - Селекторы зависят от текущей вёрстки FunPay, проверьте их в DevTools.

## Запуск

```bash
python funpay_lot_autofill_bot.py \
  --lots lots.example.csv \
  --selectors selectors.example.json \
  --lot-url "https://funpay.com/lots/offerEdit?node=XXXX" \
  --dry-run
```

Если запуск без `--dry-run`, бот будет нажимать кнопку отправки формы.

## Важно

- Используйте инструмент только в рамках правил FunPay и закона.
- Перед массовым использованием прогоняйте в `--dry-run`.
- Для безопасной работы храните аккаунт с 2FA и отдельным браузерным профилем.
