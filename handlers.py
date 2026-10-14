import sqlite3
import asyncio
import os
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import Command
from aiocryptopay import AioCryptoPay, Networks
from config import ADMIN_ID, CRYPTO_PAY_TOKEN
from database import get_user, update_user_field, set_user_vip, is_user_vip
from parsers import scan_p2p_spreads
from math_utils import calculate_net_spread

router = Router()

crypto_pay = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
DB_PATH = "/data/database.db" if os.path.exists("/data") else "database.db"

def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    cfg = get_user(user_id)
    # Для админа и твоего ID мониторинг всегда визуально активен
    is_forced_active = cfg["is_active"] or (user_id == ADMIN_ID or user_id == 1433139527)
    toggle_text = "🔴 Остановить монитор" if is_forced_active else "🚀 Запустить авто-сканер"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data="toggle_monitor")],
            [
                InlineKeyboardButton(text="👤 Мой Профиль", callback_data="show_profile"),
                InlineKeyboardButton(text="⚙️ Фильтры & Лимиты", callback_data="change_limits")
            ],
            [
                InlineKeyboardButton(text="💎 Купить VIP (Crypto / Stars)", callback_data="buy_vip")
            ]
        ]
    )

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    cfg = get_user(user_id)
    has_vip = is_user_vip(user_id)
    curr_symbol = "₽" if cfg["currency"] == "RUB" else "₸"
    
    status_text = f"<code>{cfg['subscription_type']}</code> (до {cfg['expire_date']})" if has_vip else "❌ <code>Нет подписки</code>"

    text = (
        "🔥 <b>P2P ARBITRAGE TERMINAL v2.0</b>\n"
        "━━━━━━━★━━━━━━━\n\n"
        "Профессиональный сканер межбиржевых связок!\n\n"
        "📍 <b>Текущие настройки поиска:</b>\n"
        f"├ Валюта: <code>{cfg['currency']}</code>\n"
        f"├ Лимит ордера: <code>{int(cfg['amount']):,} {curr_symbol}</code>\n"
        f"├ Мин. спред: <code>≥ {cfg['min_net_spread']}%</code>\n"
        f"├ Способ оплаты: <code>{cfg['payment_method']}</code>\n"
        f"└ Мин. сделок продавца: <code>{cfg['min_orders']}</code>\n\n"
        f"🔑 <b>Статус доступа:</b> {status_text}\n\n"
        "<i>Для запуска мониторинга необходима активная VIP-подписка.</i>"
    ).replace(",", " ")
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(user_id))

@router.callback_query(F.data == "show_profile")
async def show_profile(call: CallbackQuery):
    user_id = call.from_user.id
    cfg = get_user(user_id)
    has_vip = is_user_vip(user_id)
    curr_symbol = "₽" if cfg["currency"] == "RUB" else "₸"

    status_str = f"✅ {cfg['subscription_type']}" if has_vip else "❌ Не активна"

    text = (
        "👤 <b>ЛИЧНЫЙ КАБИНЕТ ПОЛЬЗОВАТЕЛЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👑 VIP-Статус: <b>{status_str}</b>\n"
        f"⏳ Срок действия: <code>{cfg['expire_date']}</code>\n\n"
        "📊 <b>Рабочие фильтры:</b>\n"
        f"├ Валюта: <b>{cfg['currency']}</b>\n"
        f"├ Объём круга: <b>{int(cfg['amount']):,} {curr_symbol}</b>\n"
        f"├ Порог спреда: <b>≥ {cfg['min_net_spread']}%</b>\n"
        f"├ Способ оплаты: <b>{cfg['payment_method']}</b>\n"
        f"└ Мин. сделок мерчанта: <b>{cfg['min_orders']}</b>\n"
    ).replace(",", " ")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить / Продлить VIP", callback_data="buy_vip")],
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_main")]
        ]
    )
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass

@router.callback_query(F.data == "back_main")
async def back_to_main(call: CallbackQuery):
    user_id = call.from_user.id
    cfg = get_user(user_id)
    has_vip = is_user_vip(user_id)
    curr_symbol = "₽" if cfg["currency"] == "RUB" else "₸"

    status_text = f"<code>{cfg['subscription_type']}</code> (до {cfg['expire_date']})" if has_vip else "❌ <code>Нет подписки</code>"

    text = (
        "🔥 <b>P2P ARBITRAGE TERMINAL v2.0</b>\n"
        "━━━━━━━★━━━━━━━\n\n"
        "Профессиональный сканер межбиржевых связок!\n\n"
        "📍 <b>Текущие настройки поиска:</b>\n"
        f"├ Валюта: <code>{cfg['currency']}</code>\n"
        f"├ Лимит ордера: <code>{int(cfg['amount']):,} {curr_symbol}</code>\n"
        f"├ Мин. спред: <code>≥ {cfg['min_net_spread']}%</code>\n"
        f"├ Способ оплаты: <code>{cfg['payment_method']}</code>\n"
        f"└ Мин. сделок продавца: <code>{cfg['min_orders']}</code>\n\n"
        f"🔑 <b>Статус доступа:</b> {status_text}\n\n"
        "<i>Для запуска мониторинга необходима активная VIP-подписка.</i>"
    ).replace(",", " ")
    
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
    except Exception:
        pass

@router.callback_query(F.data == "toggle_monitor")
async def toggle_monitor(call: CallbackQuery):
    user_id = call.from_user.id
    
    if not is_user_vip(user_id):
        await call.answer("❌ Доступ ограничен! Приобретите VIP-подписку.", show_alert=True)
        return

    cfg = get_user(user_id)
    # Принудительно держим активность включенной для админа/твоего ID
    if user_id == ADMIN_ID or user_id == 1433139527:
        new_status = True
    else:
        new_status = not cfg["is_active"]
        
    update_user_field(user_id, "is_active", 1 if new_status else 0)
    
    status_str = "запущен 🟢" if new_status else "остановлен 🔴"
    await call.answer(f"Авто-сканер {status_str}", show_alert=True)
    try:
        await call.message.edit_reply_markup(reply_markup=get_main_keyboard(user_id))
    except Exception:
        pass

@router.callback_query(F.data == "change_limits")
async def show_limit_options(call: CallbackQuery):
    cfg = get_user(call.from_user.id)
    curr = cfg["currency"]
    curr_symbol = "₽" if curr == "RUB" else "₸"

    bank_buttons = [
        InlineKeyboardButton(text="🏦 Сбербанк", callback_data="set_bank_Sberbank"),
        InlineKeyboardButton(text="🏦 Т-Банк (Tinkoff)", callback_data="set_bank_Tinkoff")
    ] if curr == "RUB" else [
        InlineKeyboardButton(text="🏦 Kaspi Bank", callback_data="set_bank_Kaspi"),
        InlineKeyboardButton(text="🏦 Halyk Bank", callback_data="set_bank_Halyk")
    ]

    amount_buttons_row1 = [
        InlineKeyboardButton(text="💰 500 ₽", callback_data="set_amount_500"),
        InlineKeyboardButton(text="💰 5k ₽", callback_data="set_amount_5000"),
        InlineKeyboardButton(text="💰 15k ₽", callback_data="set_amount_15000")
    ] if curr == "RUB" else [
        InlineKeyboardButton(text="💰 900 ₸", callback_data="set_amount_900"),
        InlineKeyboardButton(text="💰 10k ₸", callback_data="set_amount_10000"),
        InlineKeyboardButton(text="💰 50k ₸", callback_data="set_amount_50000")
    ]

    amount_buttons_row2 = [
        InlineKeyboardButton(text="💰 50k ₽", callback_data="set_amount_50000"),
        InlineKeyboardButton(text="💰 100k ₽", callback_data="set_amount_100000")
    ] if curr == "RUB" else [
        InlineKeyboardButton(text="💰 250k ₸", callback_data="set_amount_250000"),
        InlineKeyboardButton(text="💰 500k ₸", callback_data="set_amount_500000")
    ]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 RUB (Рубли)", callback_data="set_curr_RUB"),
                InlineKeyboardButton(text="🇰🇿 KZT (Тенге)", callback_data="set_curr_KZT")
            ],
            amount_buttons_row1,
            amount_buttons_row2,
            bank_buttons,
            [
                InlineKeyboardButton(text="🌐 Все банки (ALL)", callback_data="set_bank_ALL")
            ],
            [
                InlineKeyboardButton(text="🎯 Спред 0.1%", callback_data="set_spread_0.1"),
                InlineKeyboardButton(text="🎯 Спред 0.3%", callback_data="set_spread_0.3"),
                InlineKeyboardButton(text="🎯 Спред 0.5%", callback_data="set_spread_0.5")
            ],
            [
                InlineKeyboardButton(text="📊 От 5 ордеров", callback_data="set_orders_5"),
                InlineKeyboardButton(text="📊 От 20 ордеров", callback_data="set_orders_20")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
        ]
    )

    text = (
        "⚙️ <b>НАСТРОЙКА ФИЛЬТРОВ И ЛИМИТОВ:</b>\n\n"
        f"Валюта: <b>{cfg['currency']}</b>\n"
        f"Лимит ордера: <b>{int(cfg['amount']):,} {curr_symbol}</b>\n"
        f"Текущий банк: <b>{cfg['payment_method']}</b>\n"
        f"Мин. спред: <b>≥ {cfg['min_net_spread']}%</b>\n"
        f"Мин. ордеров продавца: <b>{cfg['min_orders']}</b>"
    ).replace(",", " ")

    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass

@router.callback_query(F.data.startswith("set_curr_"))
async def set_currency(call: CallbackQuery):
    curr = call.data.split("_")[2]
    user_id = call.from_user.id
    update_user_field(user_id, "currency", curr)
    
    default_amount = 500.0 if curr == "RUB" else 900.0
    update_user_field(user_id, "amount", default_amount)

    await call.answer(f"Валюта изменена на {curr}", show_alert=True)
    await show_limit_options(call)

@router.callback_query(F.data.startswith("set_amount_"))
async def set_amount(call: CallbackQuery):
    amt = float(call.data.split("_")[2])
    user_id = call.from_user.id
    update_user_field(user_id, "amount", amt)
    
    cfg = get_user(user_id)
    curr_symbol = "₽" if cfg["currency"] == "RUB" else "₸"
    await call.answer(f"Лимит ордера установлен: {int(amt):,} {curr_symbol}".replace(",", " "), show_alert=True)
    await show_limit_options(call)

@router.callback_query(F.data.startswith("set_bank_"))
async def set_bank(call: CallbackQuery):
    bank = call.data.split("_")[2]
    user_id = call.from_user.id
    update_user_field(user_id, "payment_method", bank)
    await call.answer(f"Способ оплаты: {bank}", show_alert=True)
    await show_limit_options(call)

@router.callback_query(F.data.startswith("set_spread_"))
async def set_spread(call: CallbackQuery):
    val = float(call.data.split("_")[2])
    user_id = call.from_user.id
    update_user_field(user_id, "min_net_spread", val)
    await call.answer(f"Мин. спред: {val}%", show_alert=True)
    await show_limit_options(call)

@router.callback_query(F.data.startswith("set_orders_"))
async def set_orders(call: CallbackQuery):
    num = int(call.data.split("_")[2])
    user_id = call.from_user.id
    update_user_field(user_id, "min_orders", num)
    await call.answer(f"Минимум сделок продавца: {num}", show_alert=True)
    await show_limit_options(call)

@router.callback_query(F.data == "buy_vip")
async def buy_vip_menu(call: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 VIP 30 дней — 10 USDT (Crypto Bot)", callback_data="pay_crypto_30")],
            [InlineKeyboardButton(text="👑 VIP Навсегда — 50 USDT (Crypto Bot)", callback_data="pay_crypto_forever")],
            [InlineKeyboardButton(text="⭐ VIP 30 дней — 500 Stars", callback_data="pay_stars_30")],
            [InlineKeyboardButton(text="⭐ VIP Навсегда — 2000 Stars", callback_data="pay_stars_forever")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
        ]
    )
    
    text = (
        "💎 <b>ОФОРМЛЕНИЕ VIP-ПОДПИСКИ</b>\n\n"
        "🤖 <b>Оплата криптовалютой (@CryptoBot):</b>\n"
        "└ 1 месяц (30 дней) — <b>10 USDT</b>\n"
        "└ Навсегда — <b>50 USDT</b>\n"
        "<i>Моментальная авто-выдача подписки сразу после оплаты!</i>\n\n"
        "⭐ <b>Оплата через Telegram Stars:</b>\n"
        "└ 1 месяц (30 дней) — <b>500 ⭐ Stars</b>\n"
        "└ Навсегда — <b>2000 ⭐ Stars</b>"
    )
    
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass

@router.callback_query(F.data.startswith("pay_crypto_"))
async def process_crypto_pay(call: CallbackQuery):
    plan = call.data.split("_")[2]
    amount = 10.0 if plan == "30" else 50.0
    days = 30 if plan == "30" else 3650
    user_id = call.from_user.id

    try:
        invoice = await crypto_pay.create_invoice(
            asset='USDT',
            amount=amount,
            description=f"VIP Доступ в P2P Сканер ({'30 дней' if plan == '30' else 'Навсегда'})",
            payload=f"{user_id}_{days}"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить в @CryptoBot", url=invoice.bot_invoice_url)],
                [InlineKeyboardButton(text="✅ Я оплатил (Проверить)", callback_data=f"check_crypto_{invoice.invoice_id}_{days}")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="buy_vip")]
            ]
        )

        await call.message.edit_text(
            f"🚀 <b>Счет на оплату создан!</b>\n\n"
            f"Сумма: <b>{amount} USDT</b>\n"
            f"Тариф: <b>{'30 дней' if plan == '30' else 'Навсегда'}</b>\n\n"
            f"Нажмите кнопку ниже для оплаты в Crypto Bot, затем нажмите «Проверить».",
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception:
        await call.answer("❌ Ошибка создания счета. Проверьте CRYPTO_PAY_TOKEN.", show_alert=True)

@router.callback_query(F.data.startswith("check_crypto_"))
async def check_crypto_pay(call: CallbackQuery):
    _, _, invoice_id, days = call.data.split("_")
    invoice_id = int(invoice_id)
    days = int(days)

    try:
        invoices = await crypto_pay.get_invoices(invoice_ids=invoice_id)
        if invoices and invoices.status == 'paid':
            set_user_vip(call.from_user.id, days)
            await call.message.edit_text(
                "🎉 <b>Оплата успешно подтверждена! VIP-статус активирован.</b>\n"
                "Теперь вы можете запустить авто-сканер в главном меню.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 В главное меню", callback_data="back_main")]])
            )
        else:
            await call.answer("❌ Оплата еще не поступила! Оплатите счет в @CryptoBot.", show_alert=True)
    except Exception:
        await call.answer("Ошибка проверки счета.", show_alert=True)

@router.callback_query(F.data.startswith("pay_stars_"))
async def process_stars_payment(call: CallbackQuery):
    plan = call.data.split("_")[2]
    title = "VIP Доступ на 30 дней" if plan == "30" else "VIP Доступ Навсегда"
    price = 500 if plan == "30" else 2000
    
    prices = [LabeledPrice(label=title, amount=price)]
    await call.message.answer_invoice(
        title=title,
        description="Полный доступ к сканеру и уведомлениям",
        payload=f"vip_{plan}",
        currency="XTR",
        prices=prices
    )
    await call.answer()

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    days = 30 if "30" in payload else 3650
    set_user_vip(message.from_user.id, days)
    await message.answer("🎉 <b>Оплата прошла успешно! VIP-статус активирован.</b>", parse_mode="HTML")

@router.callback_query(F.data.startswith("refresh_spread_"))
async def refresh_spread(call: CallbackQuery):
    _, _, curr, amt, sell_market = call.data.split("_")
    amt = float(amt)

    await call.answer("🔄 Проверяем актуальные стаканы...")
    
    data = await scan_p2p_spreads(token="USDT", currency=curr, amount=amt)
    buy_price = data.get("buy_price")
    sell_price = data.get("sells", {}).get(sell_market)

    if not buy_price or not sell_price:
        await call.answer("❌ Связка уже закрыта или стакан изменился!", show_alert=True)
        return

    calc = calculate_net_spread(buy_price, sell_price, amt)
    curr_symbol = "₽" if curr == "RUB" else "₸"

    alert_text = (
        "⚡ <b>P2P SIGNAL DETECTED (ОБНОВЛЕНО)</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💱 <b>Инструмент:</b> <code>USDT / {curr}</code>\n"
        f"🎯 <b>Лимит:</b> <code>{int(amt):,} {curr_symbol}</code>\n\n"
        f"🟢 <b>ПОКУПКА ({data.get('buy_market', 'P2P')}):</b>\n"
        f"└ Курс: <code>{buy_price:.2f} {curr_symbol}</code>\n\n"
        f"🔵 <b>ПРОДАЖА ({sell_market} P2P):</b>\n"
        f"└ Курс: <code>{sell_price:.2f} {curr_symbol}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>Актуальный спред:</b> <code>+{calc['net_spread']}%</code>\n"
        f"💵 <b>Профит с круга:</b> <code>~{int(calc['net_profit']):,} {curr_symbol}</code>"
    ).replace(",", " ")

    try:
        await call.message.edit_text(alert_text, parse_mode="HTML", reply_markup=call.message.reply_markup)
        await call.answer("✅ Данные обновлены!")
    except Exception:
        await call.answer("Курс не изменился.")

@router.message(Command("test_scan"))
async def cmd_test_scan(message: Message):
    msg = await message.answer(
        "🔎 <b>Запуск мгновенного сканирования...</b>\n"
        "Параллельно запрашиваю Bybit, HTX, BingX, MEXC, Bitget...",
        parse_mode="HTML"
    )

    try:
        cfg = get_user(message.from_user.id)
        curr = cfg["currency"]
        amt = cfg["amount"]

        data = await scan_p2p_spreads(token="USDT", currency=curr, amount=amt)
        buy_price = data.get("buy_price")
        buy_market = data.get("buy_market", "P2P")
        sells = data.get("sells", {})

        res_text = (
            f"📊 <b>РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ</b>\n"
            f"Валюта: <b>{curr}</b> | Сумма: <b>{int(amt)}</b>\n\n"
            f"🟢 <b>Закупка ({buy_market}):</b> {f'{buy_price:.2f}' if buy_price else '❌ Ошибка'}\n"
            "━━━━━━━━━━━━━━━━━━\n"
        )

        if buy_price:
            for market, sell_p in sells.items():
                if sell_p and sell_p > 0:
                    calc = calculate_net_spread(buy_price, sell_p, amt)
                    res_text += f"🔵 <b>{market} (Продажа):</b> {sell_p:.2f} | Спред: <b>{calc['net_spread']}%</b>\n"
                else:
                    res_text += f"🔵 <b>{market} (Продажа):</b> ❌ Нет ответа / 0.00\n"
        else:
            res_text += "⚠️ <i>Не удалось получить цену закупки ни с одной биржи.</i>"

        await msg.edit_text(res_text, parse_mode="HTML")
    except Exception as e:
        await msg.edit_text(f"❌ <b>Ошибка при парсинге:</b> <code>{e}</code>", parse_mode="HTML")

@router.message(Command("grant_vip"))
async def cmd_grant_vip(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        args = message.text.split()
        target_id = int(args[1])
        days = int(args[2])
        set_user_vip(target_id, days)
        await message.answer(f"✅ Пользователю <code>{target_id}</code> успешно выдан VIP на {days} дней!", parse_mode="HTML")
    except Exception:
        await message.answer("❌ Ошибка! Формат: <code>/grant_vip USER_ID DAYS</code>")

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot):
    if message.from_user.id != ADMIN_ID:
        return
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        await message.answer("Ошибка! Использование: <code>/broadcast Ваш текст</code>")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    count = 0
    for u in users:
        try:
            await bot.send_message(u[0], f"📢 <b>ОПОВЕЩЕНИЕ ОТ АДМИНИСТРАЦИИ:</b>\n\n{text_to_send}", parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(f"🚀 Сообщение доставлено {count} пользователям!")
