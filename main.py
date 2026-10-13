import asyncio
import logging
import os
import time
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TOKEN
from database import init_db, check_expiring_subscriptions, get_active_vip_users
from handlers import router
from parsers import scan_p2p_spreads, get_p2p_link
from math_utils import calculate_net_spread

sent_spreads_cache = {}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def handle_ping(request):
    return web.Response(text="Bot is live!")

async def start_fake_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_get('/health', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Fake Web Server started on port {port}")

async def subscription_checker(bot: Bot):
    while True:
        try:
            expiring_users = check_expiring_subscriptions()
            for u_id in expiring_users:
                try:
                    await bot.send_message(
                        u_id,
                        "🔔 <b>ВНИМАНИЕ! VIP-ПОДПИСКА ИСТЕКАЕТ!</b>\n\n"
                        "Ваша подписка завершится в течение 24 часов. Продлите доступ, чтобы не пропускать профитные связки!",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Ошибка проверки подписок: {e}")
        await asyncio.sleep(3600)

async def background_p2p_scanner(bot: Bot):
    global sent_spreads_cache
    logging.info("🔥 ФОНОВЫЙ СКАНЕР P2P УСПЕШНО ЗАПУЩЕН")
    
    while True:
        try:
            active_users = get_active_vip_users()
            logging.info(f"🔍 [SCANNER] Активных пользователей в мониторинге: {len(active_users)}")
            
            if not active_users:
                await asyncio.sleep(5)
                continue

            for user_cfg in active_users:
                curr = user_cfg["currency"]
                amt = user_cfg["amount"]
                user_id = user_cfg["user_id"]
                min_spread = user_cfg["min_net_spread"]
                
                data = await scan_p2p_spreads(token="USDT", currency=curr, amount=amt)
                buy_price = data.get("buy_price")
                buy_market = data.get("buy_market", "Bybit")
                
                if buy_price and buy_price > 0:
                    for sell_market, sell_price in data.get("sells", {}).items():
                        if not sell_price or sell_price <= 0:
                            continue

                        calc = calculate_net_spread(buy_price, sell_price, amt)
                        net_spread = calc["net_spread"]

                        logging.info(f"📊 [User {user_id}] {buy_market} -> {sell_market}: спред {net_spread}% (порог в настройках: {min_spread}%)")

                        if net_spread >= min_spread:
                            cache_key = f"{user_id}_{buy_market}_{sell_market}"
                            current_time = time.time()
                            
                            # Не отправляем одинаковый сигнал чаще чем раз в 30 секунд
                            if cache_key not in sent_spreads_cache or (current_time - sent_spreads_cache[cache_key] > 30):
                                sent_spreads_cache[cache_key] = current_time
                                curr_symbol = "₽" if curr == "RUB" else "₸"

                                alert_text = (
                                    "⚡ <b>P2P SIGNAL DETECTED</b>\n"
                                    "━━━━━━━━━━━━━━━━━━\n"
                                    f"💱 <b>Инструмент:</b> <code>USDT / {curr}</code>\n"
                                    f"🎯 <b>Лимит:</b> <code>{int(amt):,} {curr_symbol}</code>\n\n"
                                    f"🟢 <b>ПОКУПКА ({buy_market} P2P):</b>\n"
                                    f"└ Курс: <code>{buy_price:.2f} {curr_symbol}</code>\n\n"
                                    f"🔵 <b>ПРОДАЖА ({sell_market} P2P):</b>\n"
                                    f"└ Курс: <code>{sell_price:.2f} {curr_symbol}</code>\n"
                                    "━━━━━━━━━━━━━━━━━━\n"
                                    f"📈 <b>Чистый спред:</b> <code>+{calc['net_spread']}%</code>\n"
                                    f"💵 <b>Профит с круга:</b> <code>~{int(calc['net_profit']):,} {curr_symbol}</code>\n"
                                    "⚡ <i>Скорость обнаружения: 0.3s</i>"
                                ).replace(",", " ")

                                links_kb = InlineKeyboardMarkup(
                                    inline_keyboard=[
                                        [
                                            InlineKeyboardButton(text=f"🟢 {buy_market}", url=get_p2p_link(buy_market, "BUY", "USDT", curr, amt)),
                                            InlineKeyboardButton(text=f"🔵 {sell_market}", url=get_p2p_link(sell_market, "SELL", "USDT", curr, amt))
                                        ],
                                        [
                                            InlineKeyboardButton(text="🔄 Обновить стакан", callback_data=f"refresh_spread_{curr}_{amt}_{sell_market}")
                                        ]
                                    ]
                                )

                                try:
                                    await bot.send_message(user_id, alert_text, parse_mode="HTML", reply_markup=links_kb)
                                    logging.info(f"✅ Сигнал успешно отправлен юзеру {user_id} (спред: {net_spread}%)")
                                except Exception as send_err:
                                    logging.error(f"❌ Ошибка отправки сигнала юзеру {user_id}: {send_err}")

        except Exception as e:
            logging.error(f"❌ Ошибка цикла сканера: {e}")
            
        await asyncio.sleep(5)

async def main():
    init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await start_fake_web_server()
    
    asyncio.create_task(background_p2p_scanner(bot))
    asyncio.create_task(subscription_checker(bot))
    
    logging.info("🤖 Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
