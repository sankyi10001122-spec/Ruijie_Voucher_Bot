import asyncio
import html
import os
import time
from typing import List, Tuple

import aiohttp
from aiohttp import web
from aiohttp_socks import ProxyConnector
from telebot.async_telebot import AsyncTeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "8099"))
MAX_PROXIES = int(os.environ.get("MAX_PROXIES", "250"))
CONCURRENCY = max(1, int(os.environ.get("CONCURRENCY", "40")))

CHECK_URLS = [
    "https://api.ipify.org",
    "https://icanhazip.com",
    "https://checkip.amazonaws.com"
]

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable မသတ်မှတ်ရသေးပါ။")

bot = AsyncTeleBot(BOT_TOKEN, parse_mode="HTML")

# Multiple Free Proxy APIs
PROXY_SOURCES = {
    "HTTP": [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://www.proxyscan.io/download?type=http",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ],
    "HTTPS": [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=yes&anonymity=all",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ],
    "SOCKS5": [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "https://www.proxyscan.io/download?type=socks5"
    ],
}

# Visitor Statistics Tracker
stats = {
    "total_visits": 0,
    "active_visitors": set()
}

def main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(KeyboardButton("/http"), KeyboardButton("/https"))
    keyboard.row(KeyboardButton("/socks5"), KeyboardButton("/status"))
    return keyboard

async def handle(request: web.Request) -> web.Response:
    # Track visitor
    stats["total_visits"] += 1
    peername = request.transport.get_extra_info("peername")
    if peername:
        stats["active_visitors"].add(peername[0])

    html_content = f"""
    <!DOCTYPE html>
    <html lang="my">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Proxy Hunter Bot Dashboard</title>
        <style>
            body {{ font-family: monospace; background: #0f172a; color: #38bdf8; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; border: 1px solid #334155; width: 350px; }}
            h2 {{ color: #f8fafc; margin-bottom: 10px; }}
            p {{ color: #94a3b8; font-size: 14px; }}
            .status {{ display: inline-block; width: 12px; height: 12px; background: #22c55e; border-radius: 50%; margin-right: 6px; box-shadow: 0 0 8px #22c55e; }}
            .badge {{ margin-top: 15px; font-size: 14px; color: #4ade80; }}
            .stats-box {{ margin-top: 20px; background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #1e293b; text-align: left; }}
            .stats-item {{ color: #cbd5e1; font-size: 13px; margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Proxy Hunter Bot</h2>
            <p>Render Web Service & Telegram Bot Active.</p>
            <div class="badge"><span class="status"></span>Status: Online 🟢</div>
            <div class="stats-box">
                <div class="stats-item">📊 စုစုပေါင်း ဝင်ရောက်မှု: <b>{stats['total_visits']}</b> ကြိမ်</div>
                <div class="stats-item">🌐 ဝင်ရောက်သုံးစွဲသူ IP: <b>{len(stats['active_visitors'])}</b> ဦး</div>
            </div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type="text/html")

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
        "<b>Proxy Hunter Bot (Multi-API Version)</b>\n\n"
        "အောက်ပါ Commands များကို အသုံးပြု၍ Proxy ရှာဖွေနိုင်ပါသည်:\n"
        "• <code>/http</code> - HTTP Proxies ရှာရန်\n"
        "• <code>/https</code> - HTTPS Proxies ရှာရန်\n"
        "• <code>/socks5</code> - SOCKS5 Proxies ရှာရန်\n"
        "• <code>/status</code> - Bot အခြေအနေ",
        reply_markup=main_keyboard(),
    )

@bot.message_handler(commands=["status"])
async def status_cmd(message):
    await bot.reply_to(
        message,
        f"📊 <b>Bot အခြေအနေ</b>\n\n"
        f"🟢 အလုပ်လုပ်နေပါပြီ။\n"
        f"🌐 Web Dashboard ဝင်ရောက်မှု: {stats['total_visits']} ကြိမ်\n"
        f"👥 သုံးစွဲသူ IP အရေအတွက်: {len(stats['active_visitors'])} ဦး",
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=["http"])
async def cmd_http(message):
    await hunt_proxy_process(message, "HTTP")

@bot.message_handler(commands=["https"])
async def cmd_https(message):
    await hunt_proxy_process(message, "HTTPS")

@bot.message_handler(commands=["socks5"])
async def cmd_socks5(message):
    await hunt_proxy_process(message, "SOCKS5")

async def fetch_proxy_list(proxy_type: str) -> List[str]:
    timeout = aiohttp.ClientTimeout(total=20, connect=10)
    headers = {"User-Agent": "ProxyHunterBot/1.0"}
    proxies = []
    seen = set()

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        for url in PROXY_SOURCES[proxy_type]:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        continue
                    body = await response.text()
                    for line in body.splitlines():
                        proxy = line.strip()
                        if not proxy:
                            continue
                        for prefix in ["http://", "https://", "socks5://", "socks4://"]:
                            if proxy.lower().startswith(prefix):
                                proxy = proxy[len(prefix):]
                        if ":" not in proxy:
                            continue
                        host, port_text = proxy.rsplit(":", 1)
                        if not host or not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
                            continue
                        clean_proxy = f"{host}:{port_text}"
                        if clean_proxy not in seen:
                            seen.add(clean_proxy)
                            proxies.append(clean_proxy)
            except Exception:
                continue

    return proxies[:MAX_PROXIES]

async def check_one_proxy(proxy: str, proxy_type: str, semaphore: asyncio.Semaphore) -> Tuple[str, float | None, str | None]:
    async with semaphore:
        timeout = aiohttp.ClientTimeout(total=6, connect=3, sock_read=3)
        started = time.perf_counter()
        ip_address = None
        
        for prefix in ["http://", "https://", "socks5://", "socks4://"]:
            if proxy.lower().startswith(prefix):
                proxy = proxy[len(prefix):]

        for url in CHECK_URLS:
            try:
                if proxy_type == "SOCKS5":
                    connector = ProxyConnector.from_url(f"socks5://{proxy}")
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        async with session.get(url) as response:
                            if response.status == 200:
                                ip_address = (await response.text()).strip()
                                if ip_address and len(ip_address) < 45:
                                    break
                else:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url, proxy=f"http://{proxy}") as response:
                            if response.status == 200:
                                ip_address = (await response.text()).strip()
                                if ip_address and len(ip_address) < 45:
                                    break
            except Exception:
                continue

        if ip_address:
            duration = (time.perf_counter() - started) * 1000
            return proxy, duration, ip_address
            
        return proxy, None, None

def speed_label(milliseconds: float) -> str:
    if milliseconds < 1000:
        return "မြန် ⚡"
    if milliseconds < 3000:
        return "အလယ် 🟡"
    return "နှေး 🐢"

def progress_bar(completed: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(completed * width / total))
    return "█" * filled + "░" * (width - filled)

async def send_results(chat_id: int, title: str, results: List[Tuple[str, float, str]]) -> None:
    batches = [results[i:i + 15] for i in range(0, len(results), 15)]
    for part, batch in enumerate(batches, 1):
        text_lines = [f"<b>{html.escape(title)} — ပိုင်း {part}/{len(batches)}</b>\n"]
        for proxy, milliseconds, ip in batch:
            safe_proxy = html.escape(proxy)
            safe_ip = html.escape(ip or "N/A")
            text_lines.append(f"• <code>{safe_proxy}</code> | IP: <code>{safe_ip}</code> | {speed_label(milliseconds)} ({milliseconds:.0f} ms)")
        
        await bot.send_message(
            chat_id,
            "\n".join(text_lines),
            disable_web_page_preview=True
        )
    await bot.send_message(chat_id, "စစ်ဆေးမှု ပြီးဆုံးပါပြီ။", reply_markup=main_keyboard())

async def hunt_proxy_process(message, proxy_type: str) -> None:
    chat_id = message.chat.id
    status_message = await bot.send_message(chat_id, f"🔍 API များမှ {proxy_type} proxy စာရင်းများကို စုဆောင်းနေပါသည်…")
    try:
        proxies = await fetch_proxy_list(proxy_type)
    except Exception as exc:
        await bot.edit_message_text(
            f"❌ Proxy စာရင်းရယူမရပါ။\n<code>{html.escape(str(exc)[:500])}</code>",
            chat_id,
            status_message.message_id,
        )
        return

    if not proxies:
        await bot.edit_message_text(
            f"❌ {proxy_type} proxy စာရင်း မရရှိပါ။",
            chat_id,
            status_message.message_id,
        )
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

    try:
        for completed, future in enumerate(asyncio.as_completed(tasks), 1):
            result = await future
            if result[1] is not None:
                results.append(result)
            if completed % 15 == 0 or completed == len(tasks):
                try:
                    await bot.edit_message_text(
                        f"🧪 <b>{proxy_type} Proxy များကို စမ်းသပ်နေပါသည်…</b>\n\n"
                        f"[{progress_bar(completed, len(proxies))}] {completed * 100 // len(tasks)}%\n"
                        f"စစ်ဆေးပြီး — {completed}/{len(proxies)} ခု\n"
                        f"အသုံးပြုနိုင် — {len(results)} ခု",
                        chat_id,
                        status_message.message_id,
                    )
                except Exception:
                    pass
    except Exception:
        pass

    if not results:
        await bot.edit_message_text(
            f"❌ {proxy_type} proxy {len(proxies)} ခုကို စစ်ပြီးပါပြီ။ အသုံးပြုနိုင်တာ မတွေ့ပါ။",
            chat_id,
            status_message.message_id,
        )
        return

    results.sort(key=lambda item: item[1])
    fast = sum(ms < 1000 for _, ms, _ in results)
    medium = sum(1000 <= ms < 3000 for _, ms, _ in results)
    slow = sum(ms >= 3000 for _, ms, _ in results)
    summary = (
        f"✅ စစ်ဆေးပြီး — {len(proxies)} ခု | အလုပ်လုပ် — {len(results)} ခု\n"
        f"⚡ မြန်: {fast} | 🟡 အသင့်အတင့်: {medium} | 🐢 နှေး: {slow}"
    )
    await bot.edit_message_text(
        f"🎉 <b>{proxy_type} ရလဒ်</b>\n{summary}\n\n"
        f"📋 အလုပ်လုပ်သော proxy များကို ပို့ပေးနေပါပြီ...",
        chat_id,
        status_message.message_id,
    )

    await send_results(chat_id, f"{proxy_type} အသုံးပြုနိုင်သော Proxy ({len(results)} ခု)", results)

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

    keyboard.row(KeyboardButton("/http"), KeyboardButton("/https"))
    keyboard.row(KeyboardButton("/socks5"), KeyboardButton("/status"))
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
        "<b>Proxy Hunter Bot (Command Version)</b>\n\n"
        "အောက်ပါ Commands များကို အသုံးပြု၍ Proxy ရှာဖွေနိုင်ပါသည်:\n"
        "• <code>/http</code> - HTTP Proxies ရှာရန်\n"
        "• <code>/https</code> - HTTPS Proxies ရှာရန်\n"
        "• <code>/socks5</code> - SOCKS5 Proxies ရှာရန်\n"
        "• <code>/status</code> - Bot အခြေအနေ",
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
        timeout = aiohttp.ClientTimeout(total=6, connect=3, sock_read=3)
        started = time.perf_counter()
        ip_address = None
        
        for url in CHECK_URLS:
            try:
                if proxy_type == "SOCKS5":
                    connector = ProxyConnector.from_url(f"socks5://{proxy}")
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        async with session.get(url) as response:
                            if response.status == 200:
                                ip_address = (await response.text()).strip()
                                if ip_address and len(ip_address) < 45:
                                    break
                else:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url, proxy=f"http://{proxy}") as response:
                            if response.status == 200:
                                ip_address = (await response.text()).strip()
                                if ip_address and len(ip_address) < 45:
                                    break
            except Exception:
                continue

        if ip_address:
            duration = (time.perf_counter() - started) * 1000
            return proxy, duration, ip_address
            
        return proxy, None, None

def speed_label(milliseconds: float) -> str:
    if milliseconds < 1000:
        return "မြန် ⚡"
    if milliseconds < 3000:
        return "အလယ် 🟡"
    return "နှေး 🐢"

def progress_bar(completed: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(completed * width / total))
    return "█" * filled + "░" * (width - filled)

async def send_results(chat_id: int, title: str, results: List[Tuple[str, float, str]]) -> None:
    batches = [results[i:i + 15] for i in range(0, len(results), 15)]
    for part, batch in enumerate(batches, 1):
        text_lines = [f"<b>{html.escape(title)} — ပိုင်း {part}/{len(batches)}</b>\n"]
        for proxy, milliseconds, ip in batch:
            safe_proxy = html.escape(proxy)
            safe_ip = html.escape(ip or "N/A")
            text_lines.append(f"• <code>{safe_proxy}</code> | IP: <code>{safe_ip}</code> | {speed_label(milliseconds)} ({milliseconds:.0f} ms)")
        
        await bot.send_message(
            chat_id,
            "\n".join(text_lines),
            disable_web_page_preview=True
        )
    await bot.send_message(chat_id, "စစ်ဆေးမှု ပြီးဆုံးပါပြီ။", reply_markup=main_keyboard())

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
        return

    if not proxies:
        await bot.edit_message_text(
            f"❌ {proxy_type} proxy စာရင်း မရရှိပါ။",
            chat_id,
            status_message.message_id,
        )
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

    try:
        for completed, future in enumerate(asyncio.as_completed(tasks), 1):
            result = await future
            if result[1] is not None:
                results.append(result)
            if completed % 15 == 0 or completed == len(tasks):
                try:
                    await bot.edit_message_text(
                        f"🧪 <b>{proxy_type} Proxy များကို စမ်းသပ်နေပါသည်…</b>\n\n"
                        f"[{progress_bar(completed, len(tasks))}] {completed * 100 // len(tasks)}%\n"
                        f"စစ်ဆေးပြီး — {completed}/{len(tasks)} ခု\n"
                        f"အသုံးပြုနိုင် — {len(results)} ခု",
                        chat_id,
                        status_message.message_id,
                    )
                except Exception:
                    pass
    except Exception:
        pass

    if not results:
        await bot.edit_message_text(
            f"❌ {proxy_type} proxy {len(proxies)} ခုကို စစ်ပြီးပါပြီ။ အသုံးပြုနိုင်တာ မတွေ့ပါ။",
            chat_id,
            status_message.message_id,
        )
        return

    results.sort(key=lambda item: item[1])
    fast = sum(ms < 1000 for _, ms, _ in results)
    medium = sum(1000 <= ms < 3000 for _, ms, _ in results)
    slow = sum(ms >= 3000 for _, ms, _ in results)
    summary = (
        f"✅ စစ်ဆေးပြီး — {len(proxies)} ခု | အလုပ်လုပ် — {len(results)} ခု\n"
        f"⚡ မြန်: {fast} | 🟡 အသင့်အတင့်: {medium} | 🐢 နှေး: {slow}"
    )
    await bot.edit_message_text(
        f"🎉 <b>{proxy_type} ရလဒ်</b>\n{summary}\n\n"
        f"📋 အလုပ်လုပ်သော proxy များကို ပို့ပေးနေပါပြီ...",
        chat_id,
        status_message.message_id,
    )

    await send_results(chat_id, f"{proxy_type} အသုံးပြုနိုင်သော Proxy ({len(results)} ခု)", results)

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
