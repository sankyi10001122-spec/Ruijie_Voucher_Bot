import asyncio
import html
import os
import time
from typing import List, Tuple

import aiohttp
from aiohttp import web
from aiohttp_socks import ProxyConnector
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "8099"))
MAX_PROXIES = int(os.environ.get("MAX_PROXIES", "300"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "25"))
CHECK_URL = os.environ.get("CHECK_URL", "https://api.ipify.org?format=json")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable မသတ်မှတ်ရသေးပါ။")

bot = AsyncTeleBot(BOT_TOKEN, parse_mode="HTML")

PROXY_SOURCES = {
    "HTTP": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "HTTPS": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=yes&anonymity=all",
    "SOCKS5": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all",
}


def main_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔎 HTTP စစ်ရန်", callback_data="check:HTTP"),
        InlineKeyboardButton("🔐 HTTPS စစ်ရန်", callback_data="check:HTTPS"),
        InlineKeyboardButton("🧦 SOCKS5 စစ်ရန်", callback_data="check:SOCKS5"),
        InlineKeyboardButton("📊 Status", callback_data="status"),
    )
    return keyboard


async def handle(request: web.Request) -> web.Response:
    return web.Response(text="Proxy Hunter Bot is running.")


async def web_server() -> None:
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()


@bot.message_handler(commands=["start", "help"])
async def start(message):
    await bot.reply_to(
        message,
        "<b>Proxy Hunter Bot</b>\n\n"
        "အောက်ပါခလုတ်ကိုနှိပ်ပြီး စစ်ဆေးလိုသော Proxy အမျိုးအစားကို ရွေးချယ်ပါ။\n"
        "အလုပ်လုပ်သော Proxy များကို တုံ့ပြန်ချိန် (ms) အလိုက် မြန်၊ အသင့်အတင့်၊ နှေးဟု ခွဲပြပေးပြီး "
        "တွေ့ရှိသမျှကို အားလုံးပို့ပေးပါမည်။\n\n"
        "⚠️ သတိပြုရန် — အများသုံး Proxy များသည် လုံခြုံမှုမရှိနိုင်ပါ။ လျှို့ဝှက်နံပါတ်နှင့် ကိုယ်ရေးအချက်အလက်များ မသုံးပါနှင့်။",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["status"])
async def status_cmd(message):
    await bot.reply_to(message, "📊 Bot အခြေအနေ — အသင့်ဖြစ်နေပါပြီ 🟢", reply_markup=main_keyboard())


@bot.callback_query_handler(func=lambda call: call.data == "status")
async def status_callback(call):
    await bot.answer_callback_query(call.id, "Bot အသင့်ဖြစ်နေပါပြီ 🟢")


@bot.callback_query_handler(func=lambda call: call.data.startswith("check:"))
async def proxy_button_callback(call):
    proxy_type = call.data.split(":", 1)[1].upper()
    if proxy_type not in PROXY_SOURCES:
        await bot.answer_callback_query(call.id, "မသိသော proxy အမျိုးအစားပါ။", show_alert=True)
        return
    await bot.answer_callback_query(call.id, f"{proxy_type} စစ်ဆေးနေပါသည်…")
    await hunt_proxy_process(call.message, proxy_type)


@bot.message_handler(commands=["http"])
async def cmd_http(message):
    await hunt_proxy_process(message, "HTTP")


@bot.message_handler(commands=["https"])
async def cmd_https(message):
    await hunt_proxy_process(message, "HTTPS")


@bot.message_handler(commands=["socks5"])
async def cmd_socks5(message):
    await hunt_proxy_process(message, "SOCKS5")


@bot.message_handler(func=lambda message: bool(message.text))
async def legacy_keyboard_handler(message):
    """Accept text sent by older Telegram Reply Keyboard buttons as well."""
    text = message.text.strip().lower()
    if "status" in text or "အခြေအနေ" in text:
        await bot.reply_to(message, "📊 Bot အခြေအနေ — အသင့်ဖြစ်နေပါပြီ 🟢", reply_markup=main_keyboard())
    elif "socks5" in text:
        await hunt_proxy_process(message, "SOCKS5")
    elif "https" in text:
        await hunt_proxy_process(message, "HTTPS")
    elif "http" in text:
        await hunt_proxy_process(message, "HTTP")


async def fetch_proxy_list(proxy_type: str) -> List[str]:
    timeout = aiohttp.ClientTimeout(total=20, connect=10)
    headers = {"User-Agent": "ProxyHunterBot/1.0"}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(PROXY_SOURCES[proxy_type]) as response:
            response.raise_for_status()
            body = await response.text()
    # Duplicate/invalid lines are removed. MAX_PROXIES prevents excessive checks.
    proxies = []
    seen = set()
    for line in body.splitlines():
        proxy = line.strip()
        if ":" not in proxy:
            continue
        host, port_text = proxy.rsplit(":", 1)
        if not host or not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
            continue
        if proxy not in seen:
            seen.add(proxy)
            proxies.append(proxy)
    return proxies[:MAX_PROXIES]


async def check_one_proxy(proxy: str, proxy_type: str, semaphore: asyncio.Semaphore) -> Tuple[str, float | None]:
    async with semaphore:
        timeout = aiohttp.ClientTimeout(total=8, connect=5, sock_read=5)
        started = time.perf_counter()
        try:
            if proxy_type == "SOCKS5":
                connector = ProxyConnector.from_url(f"socks5://{proxy}")
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.get(CHECK_URL) as response:
                        if response.status == 200:
                            await response.read()
                            return proxy, (time.perf_counter() - started) * 1000
            else:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(CHECK_URL, proxy=f"http://{proxy}") as response:
                        if response.status == 200:
                            await response.read()
                            return proxy, (time.perf_counter() - started) * 1000
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, OSError):
            pass
        except Exception:
            # A public proxy may fail for many implementation-specific reasons.
            pass
        return proxy, None


def speed_label(milliseconds: float) -> str:
    if milliseconds < 1000:
        return "မြန်"
    if milliseconds < 3000:
        return "အလယ်"
    return "နှေး"


async def send_results_in_chunks(chat_id: int, title: str, lines: List[str]) -> None:
    # Telegram messages have a 4096-character limit; keep a safe margin.
    prefix = f"<b>{html.escape(title)}</b>\n"
    chunks = []
    current = prefix
    for line in lines:
        safe_line = html.escape(line)
        addition = f"\n<code>{safe_line}</code>"
        if len(current) + len(addition) > 3800:
            chunks.append(current)
            current = prefix + addition
        else:
            current += addition
    if current != prefix or not chunks:
        chunks.append(current)
    total_parts = len(chunks)
    for index, chunk in enumerate(chunks, 1):
        if total_parts > 1:
            chunk = f"{chunk}\n\n<i>အပိုင်း {index}/{total_parts}</i>"
        await bot.send_message(chat_id, chunk, disable_web_page_preview=True)


async def hunt_proxy_process(message, proxy_type: str) -> None:
    chat_id = message.chat.id
    status_message = await bot.send_message(chat_id, f"🔍 {proxy_type} proxy စာရင်းကို ရယူနေပါသည်…")
    try:
        proxies = await fetch_proxy_list(proxy_type)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        await bot.edit_message_text(
            f"❌ Proxy စာရင်းရယူမရပါ။ ခဏကြာပြီး ပြန်စမ်းပါ။\n<code>{html.escape(str(exc)[:500])}</code>",
            chat_id,
            status_message.message_id,
            reply_markup=main_keyboard(),
        )
        return

    if not proxies:
        await bot.edit_message_text(
            f"❌ {proxy_type} proxy စာရင်း မရရှိပါ။",
            chat_id,
            status_message.message_id,
            reply_markup=main_keyboard(),
        )
        return

    await bot.edit_message_text(
        f"🧪 <b>{proxy_type} Proxy များကို စမ်းသပ်နေပါသည်…</b>\n"
        f"စာရင်းရရှိမှု — {len(proxies)} ခု | တစ်ပြိုင်နက် စစ်ဆေးမှု — {CONCURRENCY} ခု",
        chat_id,
        status_message.message_id,
    )

    semaphore = asyncio.Semaphore(max(1, CONCURRENCY))
    tasks = [check_one_proxy(proxy, proxy_type, semaphore) for proxy in proxies]
    results = []

    async def typing_animation() -> None:
        # Telegram app displays an animated typing indicator during the check.
        while True:
            try:
                await bot.send_chat_action(chat_id, "typing")
            except Exception:
                pass
            await asyncio.sleep(4)

    animation_task = asyncio.create_task(typing_animation())
    try:
        for completed, future in enumerate(asyncio.as_completed(tasks), 1):
            result = await future
            if result[1] is not None:
                results.append(result)
            if completed % 10 == 0 or completed == len(tasks):
                try:
                    await bot.edit_message_text(
                        f"🧪 <b>{proxy_type} Proxy များကို စမ်းသပ်နေပါသည်…</b>\n"
                        f"စစ်ဆေးပြီး — {completed}/{len(tasks)} ခု\n"
                        f"အသုံးပြုနိုင် — {len(results)} ခု",
                        chat_id,
                        status_message.message_id,
                    )
                except Exception:
                    # Avoid aborting checks if Telegram rate-limits a progress update.
                    pass
    finally:
        animation_task.cancel()
        try:
            await animation_task
        except asyncio.CancelledError:
            pass

    if not results:
        await bot.edit_message_text(
            f"❌ {proxy_type} proxy {len(proxies)} ခုကို စစ်ပြီးပါပြီ။ အသုံးပြုနိုင်တာ မတွေ့ပါ။",
            chat_id,
            status_message.message_id,
            reply_markup=main_keyboard(),
        )
        return

    results.sort(key=lambda item: item[1])
    fast = sum(ms < 1000 for _, ms in results)
    medium = sum(1000 <= ms < 3000 for _, ms in results)
    slow = sum(ms >= 3000 for _, ms in results)
    summary = (
        f"✅ စစ်ဆေးပြီး — {len(proxies)} ခု | အလုပ်လုပ် — {len(results)} ခု\n"
        f"⚡ မြန် (<1 စက္ကန့်): {fast} | 🟡 အသင့်အတင့် (1–3 စက္ကန့်): {medium} | 🐢 နှေး (≥3 စက္ကန့်): {slow}\n"
        f"⏱ တုံ့ပြန်ချိန်သည် စစ်ဆေးသည့်အချိန်အတွက်သာဖြစ်ပြီး နောက်ပိုင်းတွင် ပြောင်းလဲနိုင်ပါသည်။"
    )
    await bot.edit_message_text(
        f"🎉 <b>{proxy_type} ရလဒ်</b>\n{summary}\n\n"
        f"📋 အလုပ်လုပ်သော proxy အားလုံး ({len(results)} ခု) ကို အောက်တွင် ပို့နေပါသည်။",
        chat_id,
        status_message.message_id,
        reply_markup=main_keyboard(),
    )

    proxy_lines = [f"{proxy} — {speed_label(ms)} — {ms:.0f} ms" for proxy, ms in results]
    await send_results_in_chunks(chat_id, f"{proxy_type} အသုံးပြုနိုင်သော proxy များ ({len(results)} ခု)", proxy_lines)


async def start_polling() -> None:
    while True:
        try:
            await bot.infinity_polling(timeout=20, request_timeout=35, skip_pending=True)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(5)


async def main() -> None:
    await asyncio.gather(web_server(), start_polling())


if __name__ == "__main__":
    asyncio.run(main())
