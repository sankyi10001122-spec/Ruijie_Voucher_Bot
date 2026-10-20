import telebot, asyncio, aiohttp, os, time
from telebot.async_telebot import AsyncTeleBot
from aiohttp import web
from aiohttp_socks import ProxyConnector

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
bot = AsyncTeleBot(BOT_TOKEN)

async def handle(request):
    return web.Response(text="Proxy Hunter Bot (Text Version) is awake and running 24/7!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8099))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

@bot.message_handler(commands=['start', 'help'])
async def start(message):
    await bot.reply_to(
        message,
        "✨ <b>Proxy Hunter Bot (Text Version)</b> မှ ကြိုဆိုပါတယ် ဗျာ! ⚡\n\n"
        "📖 <b>အသုံးပြုနိုင်သော Commands များ:</b>\n"
        "• <code>/http</code> - HTTP Proxies ရှာရန်\n"
        "• <code>/https</code> - HTTPS Proxies ရှာရန်\n"
        "• <code>/socks5</code> - SOCKS5 Proxies ရှာရန်\n"
        "• <code>/status</code> - Bot အခြေအနေ ကြည့်ရန်",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['status'])
async def status_cmd(message):
    await bot.reply_to(message, "📊 <b>Bot Status:</b> အလုပ်လုပ်နေသည် 🟢", parse_mode="HTML")

async def hunt_proxy_process(message, proxy_type):
    chat_id = message.chat.id
    if proxy_type == "HTTP":
        type_name = "HTTP"
        api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
        is_socks = False
    elif proxy_type == "HTTPS":
        type_name = "HTTPS"
        api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=yes&anonymity=all"
        is_socks = False
    else:
        type_name = "SOCKS5"
        api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
        is_socks = True

    msg = await bot.reply_to(message, f"🔍 Public {type_name} Proxy များကို ဆွဲထုတ်နေပါပြီ ⏳...", parse_mode="HTML")

    proxy_list = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                text = await resp.text()
                proxy_list = [p.strip() for p in text.splitlines() if p.strip()]
    except Exception as e:
        await bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ Proxy ဆွဲထုတ်၍ မရပါ: {e}")
        return

    if not proxy_list:
        await bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ {type_name} Proxy စာရင်း မရရှိပါ။")
        return

    target_proxies = proxy_list[:100]
    total_count = len(target_proxies)

    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg.message_id,
        text=f"🚀 <b>{type_name} Proxies များကို စစ်ဆေးနေပါပြီ...</b>\n\n[▒▒▒▒▒▒▒▒▒▒] 0%\n⚡ Checked: 0/{total_count}",
        parse_mode="HTML"
    )

    working_proxies = []
    checked_count = 0

    async def test_and_update(proxy_str):
        nonlocal checked_count
        try:
            timeout = aiohttp.ClientTimeout(total=3)
            if is_socks:
                connector = ProxyConnector.from_url(f"socks5://{proxy_str}")
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.get("https://httpbin.org/ip") as resp:
                        if resp.status == 200:
                            working_proxies.append(proxy_str)
            else:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get("https://httpbin.org/ip", proxy=f"http://{proxy_str}") as resp:
                        if resp.status == 200:
                            working_proxies.append(proxy_str)
        except Exception:
            pass
        
        checked_count += 1
        percent = int((checked_count / total_count) * 100)
        filled = int(percent / 10)
        bar = ("█" * filled) + ("▒" * (10 - filled))

        if checked_count % 5 == 0 or checked_count == total_count:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg.message_id,
                    text=f"🚀 <b>{type_name} Proxies များကို စစ်ဆေးနေပါပြီ...</b>\n\n[{bar}] {percent}%\n⚡ Checked: {checked_count}/{total_count}\n✅ Live Found: {len(working_proxies)}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    tasks = [test_and_update(p) for p in target_proxies]
    await asyncio.gather(*tasks)

    if working_proxies:
        result_text = f"🎉 <b>Live {type_name} Proxies Found ({len(working_proxies)}):</b>\n\n"
        result_text += "\n".join(f"<code>{p}</code>" for p in working_proxies[:25])
        if len(working_proxies) > 25:
            result_text += f"\n\n<i>(နှင့် အခြား {len(working_proxies) - 25} ခု...)</i>"
        await bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=result_text, parse_mode="HTML")
    else:
        await bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ လက်ရှိ စစ်ဆေးချက်အရ အလုပ်လုပ်သော {type_name} Proxy မတွေ့ပါ။ ထပ်မံကြိုးစားကြည့်ပါ။", parse_mode="HTML")

@bot.message_handler(commands=['http'])
async def cmd_http(message):
    await hunt_proxy_process(message, "HTTP")

@bot.message_handler(commands=['https'])
async def cmd_https(message):
    await hunt_proxy_process(message, "HTTPS")

@bot.message_handler(commands=['socks5'])
async def cmd_socks5(message):
    await hunt_proxy_process(message, "SOCKS5")

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
