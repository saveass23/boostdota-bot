#!/usr/bin/env python3
"""Автозаполнение лотов на FunPay через Playwright.

Скрипт:
1. Логинится на FunPay (можно использовать сохранённое состояние браузера).
2. Открывает страницу создания/редактирования лота.
3. Заполняет поля из CSV.
4. Опционально публикует/сохраняет лот.

⚠️ Используйте только в рамках правил площадки FunPay.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import pathlib
import time
from dataclasses import dataclass
from typing import Dict, List

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


LOGGER = logging.getLogger("funpay_bot")


@dataclass
class LotData:
    title: str
    description: str
    price: str
    amount: str

    @classmethod
    def from_dict(cls, row: Dict[str, str]) -> "LotData":
        required = ["title", "description", "price", "amount"]
        missing = [key for key in required if not row.get(key)]
        if missing:
            raise ValueError(f"В CSV отсутствуют обязательные поля: {', '.join(missing)}")
        return cls(
            title=row["title"].strip(),
            description=row["description"].strip(),
            price=row["price"].strip(),
            amount=row["amount"].strip(),
        )


def load_lots(csv_path: pathlib.Path) -> List[LotData]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = [LotData.from_dict(row) for row in reader]
    if not rows:
        raise ValueError("CSV-файл пустой")
    return rows


def wait_for_manual_login(page, login_url: str, timeout_seconds: int) -> None:
    LOGGER.info("Переход на страницу логина: %s", login_url)
    page.goto(login_url, wait_until="domcontentloaded")
    LOGGER.info("Выполните вход вручную в браузере. Ожидание до %s сек.", timeout_seconds)
    start = time.time()
    while time.time() - start < timeout_seconds:
        if "login" not in page.url:
            LOGGER.info("Похоже, вход выполнен. Текущий URL: %s", page.url)
            return
        time.sleep(1)
    raise TimeoutError("Время ожидания ручного входа истекло")


def fill_lot_form(page, lot: LotData, selectors: Dict[str, str]) -> None:
    page.fill(selectors["title"], lot.title)
    page.fill(selectors["description"], lot.description)
    page.fill(selectors["price"], lot.price)
    page.fill(selectors["amount"], lot.amount)


def submit_form_if_needed(page, selectors: Dict[str, str], dry_run: bool) -> None:
    if dry_run:
        LOGGER.info("DRY RUN: отправка формы пропущена")
        return

    submit_selector = selectors.get("submit")
    if not submit_selector:
        raise ValueError("В selectors отсутствует ключ submit, но dry-run отключен")

    page.click(submit_selector)
    LOGGER.info("Форма отправлена")


def run_bot(
    lots_csv: pathlib.Path,
    lot_url: str,
    selectors_json: pathlib.Path,
    storage_state: pathlib.Path,
    headless: bool,
    dry_run: bool,
    login_timeout: int,
) -> None:
    lots = load_lots(lots_csv)
    selectors = json.loads(selectors_json.read_text(encoding="utf-8"))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=str(storage_state) if storage_state.exists() else None
        )
        page = context.new_page()

        page.goto(lot_url, wait_until="domcontentloaded")

        if "login" in page.url:
            wait_for_manual_login(page, "https://funpay.com/account/login", login_timeout)

        # Сохраняем авторизационное состояние после логина
        context.storage_state(path=str(storage_state))

        for index, lot in enumerate(lots, start=1):
            LOGGER.info("Обрабатываю лот #%s: %s", index, lot.title)
            page.goto(lot_url, wait_until="domcontentloaded")
            try:
                page.wait_for_selector(selectors["title"], timeout=10_000)
                fill_lot_form(page, lot, selectors)
                submit_form_if_needed(page, selectors, dry_run)
            except PlaywrightTimeoutError as exc:
                LOGGER.error("Не найден элемент формы: %s", exc)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Ошибка при обработке лота #%s: %s", index, exc)

        context.close()
        browser.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Автозаполнение лотов FunPay")
    parser.add_argument("--lots", required=True, type=pathlib.Path, help="Путь к CSV с лотами")
    parser.add_argument("--lot-url", required=True, help="URL страницы создания/редактирования лота")
    parser.add_argument(
        "--selectors",
        required=True,
        type=pathlib.Path,
        help="JSON с CSS-селекторами полей формы",
    )
    parser.add_argument(
        "--storage-state",
        default=pathlib.Path("auth_state.json"),
        type=pathlib.Path,
        help="Файл сохранения сессии Playwright",
    )
    parser.add_argument("--headless", action="store_true", help="Запуск браузера в headless")
    parser.add_argument("--dry-run", action="store_true", help="Только заполнение без отправки")
    parser.add_argument(
        "--login-timeout",
        type=int,
        default=180,
        help="Таймаут ручного входа в секундах",
    )
    parser.add_argument("--log-level", default="INFO", help="Уровень логирования")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    run_bot(
        lots_csv=args.lots,
        lot_url=args.lot_url,
        selectors_json=args.selectors,
        storage_state=args.storage_state,
        headless=args.headless,
        dry_run=args.dry_run,
        login_timeout=args.login_timeout,
    )


if __name__ == "__main__":
    main()
