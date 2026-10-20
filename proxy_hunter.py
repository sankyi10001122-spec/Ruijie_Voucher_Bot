import telebot, asyncio, aiohttp, os, time
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
from aiohttp_socks import ProxyConnector

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
bot = AsyncTeleBot(BOT_TOKEN)

async def handle(request):
    return web.Response(text="Proxy Hunter Bot with SOCKS5 & Progress Bar is awake and running 24/7!")

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
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🌐 HTTP ရှာရန်", callback_data="hunt_http"),
        InlineKeyboardButton("🔒 HTTPS ရှာရန်", callback_data="hunt_https")
    )
    markup.row(
        InlineKeyboardButton("⚡ SOCKS5 ရှာရန်", callback_data="hunt_socks5")
    )
    markup.row(
        InlineKeyboardButton("📊 Bot Status", callback_data="bot_status")
    )
    await bot.send_message(
        message.chat.id,
        "✨ <b>Proxy Hunter Bot</b> မှ ကြိုဆိုပါတယ် ဗျာ! ⚡\n\n"
        "အောက်ပါ လှပသော ခလုတ်များကို အသုံးပြု၍ လိုအပ်သော Proxy အမျိုးအစားကို ရွေးချယ်နိုင်ပါသည်:",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if data == "bot_status":
        await bot.answer_callback_query(call.id, "Bot သည် 24/7 ပုံမှန်အလုပ်လုပ်နေပါသည်။ 🟢")
        return

    if data in ["hunt_http", "hunt_https", "hunt_socks5"]:
        if data == "hunt_http":
            type_name = "HTTP"
            api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
            is_socks = False
        elif data == "hunt_https":
            type_name = "HTTPS"
            api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=yes&anonymity=all"
            is_socks = False
        else:
            type_name = "SOCKS5"
            api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
            is_socks = True

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"🔍 Public {type_name} Proxy များကို ဆွဲထုတ်နေပါပြီ ⏳...",
            parse_mode="HTML"
        )

        proxy_list = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    text = await resp.text()
                    proxy_list = [p.strip() for p in text.splitlines() if p.strip()]
        except Exception as e:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ Proxy ဆွဲထုတ်၍ မရပါ: {e}")
            return

        if not proxy_list:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ {type_name} Proxy စာရင်း မရရှိပါ။")
            return

        target_proxies = proxy_list[:100]
        total_count = len(target_proxies)

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
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
                        message_id=message_id,
                        text=f"🚀 <b>{type_name} Proxies များကို စစ်ဆေးနေပါပြီ...</b>\n\n[{bar}] {percent}%\n⚡ Checked: {checked_count}/{total_count}\n✅ Live Found: {len(working_proxies)}",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

        tasks = [test_and_update(p) for p in target_proxies]
        await asyncio.gather(*tasks)

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("⬅️ ပင်မမီနူးသို့ ပြန်ရန်", callback_data="back_home"))

        if working_proxies:
            result_text = f"🎉 <b>Live {type_name} Proxies Found ({len(working_proxies)}):</b>\n\n"
            result_text += "\n".join(f"<code>{p}</code>" for p in working_proxies[:25])
            if len(working_proxies) > 25:
                result_text += f"\n\n<i>(နှင့် အခြား {len(working_proxies) - 25} ခု...)</i>"
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=result_text, reply_markup=markup, parse_mode="HTML")
        else:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ လက်ရှိ စစ်ဆေးချက်အရ အလုပ်လုပ်သော {type_name} Proxy မတွေ့ပါ။ ထပ်မံကြိုးစားကြည့်ပါ။", reply_markup=markup, parse_mode="HTML")

    elif data == "back_home":
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🌐 HTTP ရှာရန်", callback_data="hunt_http"),
            InlineKeyboardButton("🔒 HTTPS ရှာရန်", callback_data="hunt_https")
        )
        markup.row(
            InlineKeyboardButton("⚡ SOCKS5 ရှာရန်", callback_data="hunt_socks5")
        )
        markup.row(
            InlineKeyboardButton("📊 Bot Status", callback_data="bot_status")
        )
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="✨ <b>Proxy Hunter Bot</b> မှ ကြိုဆိုပါတယ် ဗျာ! ⚡\n\nအောက်ပါ လှပသော ခလုတ်များကို အသုံးပြု၍ လိုအပ်သော Proxy အမျိုးအစားကို ရွေးချယ်နိုင်ပါသည်:",
            reply_markup=markup,
            parse_mode="HTML"
        )

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
