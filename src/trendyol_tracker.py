"""Trendyol Rakip Fiyat Radarı.

Kullanım:
    set TELEGRAM_BOT_TOKEN=...
    set TELEGRAM_CHAT_ID=...
    python -m src.trendyol_tracker --query "iphone 15" --interval 600

Notlar:
- Scraper normal Playwright Chromium kullanır; CAPTCHA/403/429 gibi korumaları
  aşmaya çalışmaz. Böyle bir yanıt alınırsa döngüde hata olarak kaydedilir.
- İlk tarama yalnızca başlangıç değerlerini oluşturur; alarm sonraki taramalarda
  tespit edilen fiyat düşüşlerinde veya açıkça doğrulanan stok tükenmesinde gider.
- Karşılaştırma geçmişi işlem belleğindedir; program yeniden başlatılırsa sıfırlanır.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin

from playwright.async_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)
from telegram import Bot
from telegram.error import TelegramError

LOGGER = logging.getLogger("trendyol_tracker")
BASE_URL = "https://www.trendyol.com"
SEARCH_URL = BASE_URL + "/sr?q={query}"
MAX_PRODUCTS = 10
NAVIGATION_TIMEOUT_MS = 30_000
BETWEEN_PRODUCT_SECONDS = 1.5


@dataclass
class ProductSnapshot:
    product_id: str
    name: str
    url: str
    price: float | None
    seller: str | None
    in_stock: bool | None


def parse_price(raw: str | None) -> float | None:
    """Türkçe fiyat gösterimini (örn. 34.999,90 TL) float'a çevirir."""
    if not raw:
        return None
    match = re.search(r"(\d[\d.\s]*(?:,\d{1,2})?|\d+(?:\.\d{1,2})?)", raw)
    if not match:
        return None
    value = match.group(1).replace(" ", "")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif value.count(".") > 1:
        value = value.replace(".", "")
    try:
        price = float(value)
    except ValueError:
        return None
    return price if price > 0 else None


async def first_text(root: Any, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        try:
            locator = root.locator(selector).first
            if await locator.count():
                value = (await locator.inner_text(timeout=1_500)).strip()
                if value:
                    return re.sub(r"\s+", " ", value)
        except (PlaywrightError, PlaywrightTimeoutError):
            continue
    return None


async def first_attribute(root: Any, selectors: tuple[str, ...], attribute: str) -> str | None:
    for selector in selectors:
        try:
            locator = root.locator(selector).first
            if await locator.count():
                value = await locator.get_attribute(attribute, timeout=1_500)
                if value:
                    return value.strip()
        except (PlaywrightError, PlaywrightTimeoutError):
            continue
    return None


def extract_product_id(url: str) -> str:
    match = re.search(r"-p-(\d+)", url, flags=re.IGNORECASE)
    return match.group(1) if match else url.split("?")[0].rstrip("/")


async def detect_stock(page: Page) -> bool | None:
    """Yalnızca açık stok sinyali varsa True/False döndürür; aksi halde None."""
    text = await first_text(
        page,
        (
            "[data-testid='add-to-basket-button']",
            "button.add-to-basket",
            "button[class*='add-to-basket']",
            "button[class*='addBasket']",
            "[data-testid='sold-out']",
            "[class*='outOfStock']",
            "[class*='stock-warning']",
        ),
    )
    if text:
        normalized = text.casefold()
        if any(term in normalized for term in ("tükendi", "stokta yok", "satışta değil", "mevcut değil")):
            return False
        if any(term in normalized for term in ("sepete ekle", "hemen al", "satın al")):
            return True

    # Bazı ürün sayfalarında buton metni boş olup disabled işareti bulunabilir.
    for selector in (
        "[data-testid='add-to-basket-button']",
        "button.add-to-basket",
        "button[class*='add-to-basket']",
        "button[class*='addBasket']",
    ):
        try:
            button = page.locator(selector).first
            if await button.count():
                disabled = await button.get_attribute("disabled")
                aria_disabled = await button.get_attribute("aria-disabled")
                if disabled is not None or aria_disabled == "true":
                    return False
        except (PlaywrightError, PlaywrightTimeoutError):
            pass
    return None


async def scrape_search_results(page: Page, query: str, limit: int) -> list[dict[str, str | None]]:
    url = SEARCH_URL.format(query=quote(query))
    response = await page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
    if response and response.status in (401, 403, 429):
        raise RuntimeError(
            f"Trendyol HTTP {response.status} döndürdü. Koruma/erişim sınırı aşılmayacak; "
            "bir sonraki kontrol döngüsünde tekrar denenecek."
        )

    await page.wait_for_timeout(1_500)
    page_title = (await page.title()).casefold()
    body_text = ((await page.locator("body").inner_text())[:5_000]).casefold()
    if any(term in page_title or term in body_text for term in ("captcha", "robot olmadığınızı", "erişim engellendi")):
        raise RuntimeError("Trendyol doğrulama/erişim engeli gösterdi; otomatik aşma yapılmadı.")

    card_selector = ".p-card-wrppr, .product-card, [data-testid='product-card']"
    try:
        await page.locator(card_selector).first.wait_for(state="visible", timeout=12_000)
    except PlaywrightTimeoutError:
        raise RuntimeError("Arama sonuç kartları bulunamadı; sayfa yapısı değişmiş veya erişim kısıtlanmış olabilir.")

    cards = page.locator(card_selector)
    count = min(await cards.count(), limit)
    results: list[dict[str, str | None]] = []
    seen: set[str] = set()

    for index in range(count):
        card = cards.nth(index)
        href = await first_attribute(
            card,
            ("a.p-card-chldrn-cntnr", "a[href*='-p-']", "a"),
            "href",
        )
        if not href:
            continue
        product_url = urljoin(BASE_URL, href.split("?")[0])
        product_id = extract_product_id(product_url)
        if product_id in seen:
            continue
        seen.add(product_id)

        name = await first_text(
            card,
            (
                ".prdct-desc-cntnr-name",
                ".product-title",
                "[data-testid='product-name']",
                "img",
            ),
        )
        if not name:
            name = await first_attribute(card, ("img",), "alt")
        price_text = await first_text(
            card,
            (
                ".prc-box-dscntd",
                ".prc-box-sllng",
                "[data-testid='price-current-price']",
                "[class*='price']",
            ),
        )
        seller = await first_text(
            card,
            (
                ".merchant-name",
                ".prdct-desc-cntnr-merchant",
                "[data-testid='merchant-name']",
                "[class*='merchant']",
            ),
        )
        results.append(
            {
                "product_id": product_id,
                "name": name or f"Trendyol ürünü {product_id}",
                "url": product_url,
                "price": price_text,
                "seller": seller,
            }
        )
    return results


async def scrape_products(context: BrowserContext, query: str, limit: int) -> list[ProductSnapshot]:
    search_page = await context.new_page()
    try:
        raw_products = await scrape_search_results(search_page, query, limit)
    finally:
        await search_page.close()

    products: list[ProductSnapshot] = []
    for index, item in enumerate(raw_products):
        price = parse_price(item["price"])
        seller = item["seller"]
        in_stock: bool | None = None

        # Arama kartı fiyat/satıcı bilgisi eksikse, ürün sayfasında kontrollü şekilde tamamla.
        detail_page = await context.new_page()
        try:
            response = await detail_page.goto(
                str(item["url"]),
                wait_until="domcontentloaded",
                timeout=NAVIGATION_TIMEOUT_MS,
            )
            if response and response.status in (401, 403, 429):
                LOGGER.warning("Ürün sayfası HTTP %s: %s", response.status, item["url"])
            else:
                await detail_page.wait_for_timeout(800)
                detail_title = await first_text(
                    detail_page,
                    ("h1.pr-new-br", "h1", "[data-testid='product-name']"),
                )
                detail_price_text = await first_text(
                    detail_page,
                    (
                        ".prc-dsc",
                        ".prc-slg",
                        "[data-testid='price-current-price']",
                        "[class*='price-container'] [class*='price']",
                    ),
                )
                detail_seller = await first_text(
                    detail_page,
                    (
                        ".merchant-name",
                        "[data-testid='merchant-name']",
                        ".seller-name-text",
                        "[class*='merchant']",
                    ),
                )
                if detail_title:
                    item["name"] = detail_title
                if price is None:
                    price = parse_price(detail_price_text)
                if detail_seller:
                    seller = detail_seller
                in_stock = await detect_stock(detail_page)
        except (PlaywrightError, PlaywrightTimeoutError) as exc:
            LOGGER.warning("Ürün ayrıntısı okunamadı (%s): %s", item["url"], exc)
        finally:
            await detail_page.close()

        products.append(
            ProductSnapshot(
                product_id=str(item["product_id"]),
                name=str(item["name"]),
                url=str(item["url"]),
                price=price,
                seller=seller,
                in_stock=in_stock,
            )
        )
        if index + 1 < len(raw_products):
            await asyncio.sleep(BETWEEN_PRODUCT_SECONDS)
    return products


def format_price(value: float | None) -> str:
    if value is None:
        return "bilinmiyor"
    return f"{value:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


async def send_alert(bot: Bot, chat_id: str, message: str) -> None:
    try:
        await bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
    except TelegramError:
        LOGGER.exception("Telegram alarmı gönderilemedi.")


async def monitor(args: argparse.Namespace) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ortam değişkeni tanımlı değil.")
    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID tanımlı değil. Bot token'ı tek başına mesajın gönderileceği sohbeti belirleyemez."
        )

    previous: dict[str, ProductSnapshot] = {}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not args.headed)
        context = await browser.new_context(
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            viewport={"width": 1365, "height": 900},
        )
        async with Bot(token=token) as bot:
            try:
                while True:
                    LOGGER.info('"%s" araması kontrol ediliyor; en fazla %s ürün.', args.query, args.limit)
                    try:
                        current_products = await scrape_products(context, args.query, args.limit)
                        if not current_products:
                            LOGGER.warning("Bu döngüde ürün bulunamadı; mevcut karşılaştırma geçmişi korunuyor.")
                        else:
                            for current in current_products:
                                old = previous.get(current.product_id)
                                if old is not None:
                                    if old.price is not None and current.price is not None and current.price < old.price:
                                        await send_alert(
                                            bot,
                                            chat_id,
                                            (
                                                f"ALARM: {current.name} fiyatı {format_price(old.price)}'tan "
                                                f"{format_price(current.price)}'a düştü!\n"
                                                f"Satıcı: {current.seller or old.seller or 'Belirtilmemiş'}\n"
                                                f"{current.url}"
                                            ),
                                        )
                                    if old.in_stock is True and current.in_stock is False:
                                        await send_alert(
                                            bot,
                                            chat_id,
                                            (
                                                f"STOK ALARMI: {current.name} stoktan çıktı.\n"
                                                f"Son bilinen fiyat: {format_price(current.price or old.price)}\n"
                                                f"{current.url}"
                                            ),
                                        )
                                # Bilinmeyen fiyat/stok, bilinen geçmişi silmesin.
                                if old is not None:
                                    if current.price is None:
                                        current.price = old.price
                                    if current.seller is None:
                                        current.seller = old.seller
                                    if current.in_stock is None:
                                        current.in_stock = old.in_stock
                                previous[current.product_id] = current
                            LOGGER.info("%s ürün güncellendi; hafızada %s ürün var.", len(current_products), len(previous))
                    except (RuntimeError, PlaywrightError, PlaywrightTimeoutError):
                        LOGGER.exception("Bu kontrol başarısız oldu; program çalışmaya devam edecek.")
                    except Exception:
                        LOGGER.exception("Beklenmeyen tarama hatası; program çalışmaya devam edecek.")

                    if args.once:
                        break
                    LOGGER.info("%s saniye sonra yeniden kontrol edilecek.", args.interval)
                    await asyncio.sleep(args.interval)
            finally:
                await context.close()
                await browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trendyol arama sonuçlarında ilk ürünlerin fiyat ve stok değişimini Telegram'a bildirir."
    )
    parser.add_argument("--query", default="iphone 15", help="Trendyol arama sorgusu (varsayılan: iphone 15)")
    parser.add_argument("--interval", type=int, default=600, help="Kontrol aralığı, saniye (varsayılan: 600)")
    parser.add_argument("--limit", type=int, default=10, help="İzlenecek ürün sayısı (1-10, varsayılan: 10)")
    parser.add_argument("--headed", action="store_true", help="Tarayıcıyı görünür aç; varsayılan headless")
    parser.add_argument("--once", action="store_true", help="Tek tarama yapıp çık")
    args = parser.parse_args()
    if args.interval < 60:
        parser.error("--interval en az 60 saniye olmalı.")
    if not 1 <= args.limit <= MAX_PRODUCTS:
        parser.error("--limit 1 ile 10 arasında olmalı.")
    return args


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = parse_args()
    try:
        asyncio.run(monitor(args))
    except KeyboardInterrupt:
        LOGGER.info("Kullanıcı isteğiyle durduruldu.")
    except Exception as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
