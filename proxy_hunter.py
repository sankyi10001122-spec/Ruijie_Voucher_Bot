import telebot, asyncio, aiohttp, os
from telebot.async_telebot import AsyncTeleBot
from aiohttp import web
from aiohttp_socks import ProxyConnector

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
bot = AsyncTeleBot(BOT_TOKEN)

async def handle(request):
    return web.Response(text="Proxy Hunter Bot is awake and running 24/7!")

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
        "✨ <b>Proxy Hunter Bot</b> မှ ကြိုဆိုပါတယ် ဗျာ! ⚡\n\n"
        "📖 <b>Commands များ:</b>\n"
        "• <code>/hunt</code> - SOCKS5 Proxy အသစ်များကို ရှာဖွေပြီး အလုပ်လုပ်သည်များကို စစ်ဆေးရန်\n"
        "• <code>/status</code> - Bot အခြေအနေ ကြည့်ရန်",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['status'])
async def status_cmd(message):
    await bot.reply_to(message, "📊 <b>Bot Status:</b> အလုပ်လုပ်နေသည် 🟢", parse_mode="HTML")

async def test_proxy(proxy_str):
    connector = ProxyConnector.from_url(f"socks5://{proxy_str}")
    try:
        timeout = aiohttp.ClientTimeout(total=4)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get("https://httpbin.org/ip") as resp:
                if resp.status == 200:
                    return proxy_str
    except Exception:
        pass
    return None

@bot.message_handler(commands=['hunt'])
async def hunt_proxies(message):
    msg = await bot.reply_to(message, "🔍 Public SOCKS5 Proxy များကို စတင်ဆွဲထုတ်နေပါပြီ ⏳...")
    
    # ProxyScrape API မှ ဖရီး SOCKS5 များကို ဆွဲထုတ်ခြင်း
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
    proxy_list = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                text = await resp.text()
                proxy_list = [p.strip() for p in text.splitlines() if p.strip()]
    except Exception as e:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"❌ Proxy ဆွဲထုတ်၍ မရပါ: {e}")
        return

    if not proxy_list:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="❌ Proxy စာရင်း မရရှိပါ။")
        return

    await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"📦 စုစုပေါင်း Proxy {len(proxy_list)} ခု တွေ့ရှိပါသည်။ အလုပ်လုပ်သည်များကို စစ်ဆေးနေပါပြီ ⚡...")

    # Proxy များကို တစ်ပြိုင်နက် (Concurrent) အမြန်စစ်ဆေးခြင်း (အမြန်ဆုံးဖြစ်ရန် ၁၅၀ ခုကို စစ်မည်)
    tasks = [test_proxy(p) for p in proxy_list[:150]]
    results = await asyncio.gather(*tasks)
    working_proxies = [p for p in results if p]

    if working_proxies:
        result_text = f"🎉 <b>Live SOCKS5 Proxies Found ({len(working_proxies)}):</b>\n\n"
        result_text += "\n".join(f"<code>{p}</code>" for p in working_proxies[:30])
        if len(working_proxies) > 30:
            result_text += f"\n\n<i>(နှင့် အခြား {len(working_proxies) - 30} ခု...)</i>"
        await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=result_text, parse_mode="HTML")
    else:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="❌ လက်ရှိ စစ်ဆေးချက်အရ အလုပ်လုပ်သော Proxy မတွေ့ပါ။ ထပ်မံကြိုးစားကြည့်ပါ။")

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
