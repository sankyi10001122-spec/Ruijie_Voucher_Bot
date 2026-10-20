import asyncio
import html
import os
import time
from typing import List, Tuple

import aiohttp
from aiohttp import web
from aiohttp_socks import ProxyConnector
from telebot.async_telebot import AsyncTeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "8099"))
MAX_PROXIES = int(os.environ.get("MAX_PROXIES", "300"))
CONCURRENCY = max(1, int(os.environ.get("CONCURRENCY", "40")))
CHECK_URL = os.environ.get("CHECK_URL", "https://api.ipify.org?format=json")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable မသတ်မှတ်ရသေးပါ။")

bot = AsyncTeleBot(BOT_TOKEN, parse_mode="HTML")

PROXY_SOURCES = {
    "HTTP": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "HTTPS": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=yes&anonymity=all",
    "SOCKS5": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all",
}


def main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(KeyboardButton("🔎 HTTP ရှာရန်"), KeyboardButton("🔐 HTTPS ရှာရန်"))
    keyboard.row(KeyboardButton("🧦 SOCKS5 ရှာရန်"), KeyboardButton("📊 Status"))
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
        "အလုပ်လုပ်သော Proxy များကို IP လိပ်စာ၊ တုံ့ပြန်ချိန် (ms) တို့နှင့်တကွ ဖော်ပြပေးပါမည်။",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["status"])
async def status_cmd(message):
    await bot.reply_to(message, "📊 Bot အခြေအနေ — အသင့်ဖြစ်နေပါပြီ 🟢", reply_markup=main_keyboard())


@bot.message_handler(commands=["http"])
async def cmd_http(message):
    await hunt_proxy_process(message, "HTTP")


@bot.message_handler(commands=["https"])
async def cmd_https(message):
    await hunt_proxy_process(message, "HTTPS")


@bot.message_handler(commands=["socks5"])
async def cmd_socks5(message):
    await hunt_proxy_process(message, "SOCKS5")


@bot.callback_query_handler(func=lambda call: call.data.startswith("copy|"))
async def copy_proxy_button(call):
    proxy = call.data.split("|", 1)[1]
    await bot.answer_callback_query(call.id, "Proxy ကို သီးခြားစာအဖြစ် ပို့လိုက်ပါပြီ။")
    await bot.send_message(call.message.chat.id, f"<code>{html.escape(proxy)}</code>")


@bot.message_handler(func=lambda message: bool(message.text))
async def legacy_keyboard_handler(message):
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


async def check_one_proxy(proxy: str, proxy_type: str, semaphore: asyncio.Semaphore) -> Tuple[str, float | None, str | None]:
    async with semaphore:
        timeout = aiohttp.ClientTimeout(total=8, connect=5, sock_read=5)
        started = time.perf_counter()
        try:
            ip_address = None
            if proxy_type == "SOCKS5":
                connector = ProxyConnector.from_url(f"socks5://{proxy}")
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.get(CHECK_URL) as response:
                        if response.status == 200:
                            data = await response.json(content_type=None)
                            ip_address = data.get("ip")
                            duration = (time.perf_counter() - started) * 1000
                            return proxy, duration, ip_address
            else:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(CHECK_URL, proxy=f"http://{proxy}") as response:
                        if response.status == 200:
                            data = await response.json(content_type=None)
                            ip_address = data.get("ip")
                            duration = (time.perf_counter() - started) * 1000
                            return proxy, duration, ip_address
        except Exception:
            pass
        return proxy, None, None


def speed_label(milliseconds: float) -> str:
    if milliseconds < 1000:
        return "မြန်"
    if milliseconds < 3000:
        return "အလယ်"
    return "နှေး"


def progress_bar(completed: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(completed * width / total))
    return "█" * filled + "░" * (width - filled)


async def send_results_in_chunks(chat_id: int, title: str, results: List[Tuple[str, float, str]]) -> None:
    batches = [results[i:i + 10] for i in range(0, len(results), 10)]
    for part, batch in enumerate(batches, 1):
        keyboard = InlineKeyboardMarkup(row_width=1)
        text_lines = [f"<b>{html.escape(title)} — {part}/{len(batches)}</b>"]
        for proxy, milliseconds, ip in batch:
            safe_proxy = html.escape(proxy)
            safe_ip = html.escape(ip or "N/A")
            text_lines.append(f"<code>{safe_proxy}</code> (IP: {safe_ip}) — {speed_label(milliseconds)} — {milliseconds:.0f} ms")
            keyboard.add(InlineKeyboardButton(f"📋 {proxy}", callback_data=f"copy|{proxy}"))
        await bot.send_message(
            chat_id,
            "\n".join(text_lines),
            disable_web_page_preview=True,
            reply_markup=keyboard,
        )
    await bot.send_message(chat_id, "အောက်ပါခလုတ်များမှ Proxy ကိုရွေးပါ။", reply_markup=main_keyboard())


async def hunt_proxy_process(message, proxy_type: str) -> None:
    chat_id = message.chat.id
    status_message = await bot.send_message(chat_id, f"🔍 {proxy_type} proxy စာရင်းကို ရယူနေပါသည်…")
    try:
        proxies = await fetch_proxy_list(proxy_type)
    except Exception as exc:
        await bot.edit_message_text(
            f"❌ Proxy စာရင်းရယူမရပါ။\n<code>{html.escape(str(exc)[:500])}</code>",
            chat_id,
            status_message.message_id,
        )
        await bot.send_message(chat_id, "အောက်ပါခလုတ်မှ ပြန်လည်ရွေးချယ်နိုင်ပါသည်။", reply_markup=main_keyboard())
        return

    if not proxies:
        await bot.edit_message_text(
            f"❌ {proxy_type} proxy စာရင်း မရရှိပါ။",
            chat_id,
            status_message.message_id,
        )
        await bot.send_message(chat_id, "Proxy စာရင်း မရရှိပါ။", reply_markup=main_keyboard())
        return

    await bot.edit_message_text(
        f"🧪 <b>{proxy_type} Proxy များကို စမ်းသပ်နေပါသည်…</b>\n\n"
        f"[{progress_bar(0, len(proxies))}] 0%\n"
        f"စစ်ဆေးပြီး — 0/{len(proxies)} ခု\n"
        f"တစ်ပြိုင်နက် စစ်ဆေးမှု — {CONCURRENCY} ခု",
        chat_id,
        status_message.message_id,
    )

    semaphore = asyncio.Semaphore(max(1, CONCURRENCY))
    tasks = [check_one_proxy(proxy, proxy_type, semaphore) for proxy in proxies]
    results = []

    async def typing_animation() -> None:
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
                        f"🧪 <b>{proxy_type} Proxy များကို စမ်းသပ်နေပါသည်…</b>\n\n"
                        f"[{progress_bar(completed, len(tasks))}] {completed * 100 // len(tasks)}%\n"
                        f"စစ်ဆေးပြီး — {completed}/{len(tasks)} ခု\n"
                        f"အသုံးပြုနိုင် — {len(results)} ခု | မြန်နှုန်း — {CONCURRENCY} ခု တစ်ပြိုင်နက်",
                        chat_id,
                        status_message.message_id,
                    )
                except Exception:
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
        )
        await bot.send_message(chat_id, "အခြား Proxy အမျိုးအစားကို ရွေးနိုင်ပါသည်။", reply_markup=main_keyboard())
        return

    results.sort(key=lambda item: item[1])
    fast = sum(ms < 1000 for _, ms, _ in results)
    medium = sum(1000 <= ms < 3000 for _, ms, _ in results)
    slow = sum(ms >= 3000 for _, ms, _ in results)
    summary = (
        f"✅ စစ်ဆေးပြီး — {len(proxies)} ခု | အလုပ်လုပ် — {len(results)} ခု\n"
        f"⚡ မြန် (<1 စက္ကန့်): {fast} | 🟡 အသင့်အတင့် (1–3 စက္ကန့်): {medium} | 🐢 နှေး (≥3 စက္ကန့်): {slow}"
    )
    await bot.edit_message_text(
        f"🎉 <b>{proxy_type} ရလဒ်</b>\n{summary}\n\n"
        f"📋 အလုပ်လုပ်သော proxy အားလုံး ({len(results)} ခု) ကို အောက်တွင် ပို့နေပါသည်။",
        chat_id,
        status_message.message_id,
    )

    await send_results_in_chunks(chat_id, f"{proxy_type} အသုံးပြုနိုင်သော Proxy ({len(results)} ခု)", results)


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
