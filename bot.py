import asyncio
import logging
import sqlite3
import random
import string
from datetime import datetime
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8526013668:AAFRoaXtOlpfeXB5k3QPVVr_mw88dlGMc-8"  # Замени на свой токен
ADMIN_IDS = [7673683792]  # Замени на свой Telegram ID (целое число)

# Цены на подарки (стоимость покупки в Stars)
GIFT_PRICES = {
    "15": 5,   # подарок за 15⭐ продаём за 5⭐
    "25": 10,
    "50": 20,
    "100": 40
}

# Комментарий стоит дополнительно 10⭐
COMMENT_PRICE = 10

# Настройки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== БД ==========
def init_db():
    conn = sqlite3.connect("gift_bot.db")
    c = conn.cursor()
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
                  reg_date TEXT, total_stars_spent INTEGER DEFAULT 0)''')
    # Таблица покупок
    c.execute('''CREATE TABLE IF NOT EXISTS purchases
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, gift_value TEXT, gift_name TEXT, comment TEXT,
                  stars_paid INTEGER, purchase_date TEXT, is_active INTEGER DEFAULT 1)''')
    # Таблица активационных чеков
    c.execute('''CREATE TABLE IF NOT EXISTS activation_codes
                 (code TEXT PRIMARY KEY, gift_value TEXT, gift_name TEXT,
                  created_by INTEGER, created_at TEXT, used_by INTEGER DEFAULT NULL,
                  used_at TEXT DEFAULT NULL)''')
    conn.commit()
    conn.close()

init_db()

def add_user(user_id: int, username: str, first_name: str):
    conn = sqlite3.connect("gift_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, reg_date) VALUES (?, ?, ?, ?)",
              (user_id, username, first_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def add_purchase(user_id: int, gift_value: str, gift_name: str, comment: str, stars_paid: int):
    conn = sqlite3.connect("gift_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO purchases (user_id, gift_value, gift_name, comment, stars_paid, purchase_date) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, gift_value, gift_name, comment, stars_paid, datetime.now().isoformat()))
    c.execute("UPDATE users SET total_stars_spent = total_stars_spent + ? WHERE user_id = ?",
              (stars_paid, user_id))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect("gift_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM purchases")
    total_sales = c.fetchone()[0]
    c.execute("SELECT SUM(stars_paid) FROM purchases")
    total_stars = c.fetchone()[0] or 0
    conn.close()
    return users_count, total_sales, total_stars

# ========== FSM СОСТОЯНИЯ ==========
class BuyGiftState(StatesGroup):
    choosing_gift = State()
    entering_comment = State()
    confirm_payment = State()

class AdminState(StatesGroup):
    waiting_gift_user = State()
    waiting_gift_value = State()
    waiting_gift_name = State()
    waiting_code_activation = State()

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎁 Купить подарок", callback_data="buy_gift"))
    builder.row(InlineKeyboardButton(text="🎫 Активировать чек", callback_data="activate_code"))
    if user_id in ADMIN_IDS:
        builder.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))
    return builder.as_markup()

def get_gift_keyboard():
    builder = InlineKeyboardBuilder()
    for value, price in GIFT_PRICES.items():
        builder.add(InlineKeyboardButton(text=f"⭐{value} подарок — {price}⭐", callback_data=f"gift_{value}"))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    return builder.as_markup()

def get_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Оплатить Stars", callback_data="confirm_pay"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    return builder.as_markup()

def get_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎁 Подарить подарок", callback_data="admin_gift"))
    builder.row(InlineKeyboardButton(text="🧾 Создать чек", callback_data="admin_create_code"))
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    return builder.as_markup()

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    add_user(user.id, user.username or "", user.first_name)
    await message.answer(
        f"🎁 Привет, {user.first_name}!\n\n"
        "Я продаю Telegram Подарки за Telegram Stars!\n\n"
        "💰 Прайс:\n"
        "• Подарок за 15⭐ → 5⭐\n"
        "• Подарок за 25⭐ → 10⭐\n"
        "• Подарок за 50⭐ → 20⭐\n"
        "• Подарок за 100⭐ → 40⭐\n\n"
        "💬 Комментарий к подарку +10⭐\n\n"
        "Выбери действие:",
        reply_markup=get_main_keyboard(user.id)
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎁 Главное меню:",
        reply_markup=get_main_keyboard(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_gift")
async def buy_gift_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BuyGiftState.choosing_gift)
    await callback.message.edit_text(
        "🎁 Выбери подарок, который хочешь купить:",
        reply_markup=get_gift_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("gift_"))
async def gift_selected(callback: CallbackQuery, state: FSMContext):
    gift_value = callback.data.split("_")[1]  # 15, 25, 50, 100
    price = GIFT_PRICES[gift_value]
    
    await state.update_data(gift_value=gift_value, gift_price=price, comment_text="")
    await state.set_state(BuyGiftState.entering_comment)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➡️ Без комментария", callback_data="no_comment"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    
    await callback.message.edit_text(
        f"🎁 Ты выбрал подарок стоимостью {gift_value}⭐\n"
        f"💰 Цена: {price}⭐\n\n"
        f"💬 Хочешь добавить комментарий? (+{COMMENT_PRICE}⭐)\n"
        f"Напиши текст комментария (до 100 символов) или нажми «Без комментария»",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "no_comment", StateFilter(BuyGiftState.entering_comment))
async def no_comment(callback: CallbackQuery, state: FSMContext):
    await state.update_data(comment_text="", comment_price=0)
    await show_payment_confirmation(callback, state)

@dp.message(BuyGiftState.entering_comment)
async def got_comment(message: Message, state: FSMContext):
    if len(message.text) > 100:
        await message.answer("❌ Комментарий слишком длинный (максимум 100 символов). Попробуй ещё раз:")
        return
    
    await state.update_data(comment_text=message.text, comment_price=COMMENT_PRICE)
    
    # Создаём временную клавиатуру для перехода к оплате
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Далее", callback_data="proceed_to_pay"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    
    await message.answer(
        f"💬 Комментарий сохранён: \"{message.text}\"\n\n"
        f"Нажми «Далее», чтобы продолжить оплату.",
        reply_markup=builder.as_markup()
    )
    
    # Запоминаем, что нужно вызвать подтверждение
    await state.update_data(waiting_for_pay=True)

@dp.callback_query(F.data == "proceed_to_pay", StateFilter(BuyGiftState.entering_comment))
async def proceed_to_pay(callback: CallbackQuery, state: FSMContext):
    await show_payment_confirmation(callback, state)

async def show_payment_confirmation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    gift_value = data.get("gift_value")
    price = data.get("gift_price")
    comment_text = data.get("comment_text", "")
    comment_price = data.get("comment_price", 0)
    total_price = price + comment_price
    
    await state.update_data(total_price=total_price)
    await state.set_state(BuyGiftState.confirm_payment)
    
    text = f"🛒 Проверь заказ:\n\n"
    text += f"🎁 Подарок: {gift_value}⭐\n"
    text += f"💰 Цена: {price}⭐\n"
    if comment_text:
        text += f"💬 Комментарий: \"{comment_text}\" +{comment_price}⭐\n"
    text += f"\n⭐ Итого к оплате: {total_price} Telegram Stars\n\n"
    text += f"Нажми «Оплатить Stars», чтобы завершить покупку."
    
    await callback.message.edit_text(text, reply_markup=get_confirm_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "confirm_pay", StateFilter(BuyGiftState.confirm_payment))
async def confirm_payment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    total_price = data.get("total_price")
    gift_value = data.get("gift_value")
    comment_text = data.get("comment_text", "")
    
    # Создаём инвойс для Telegram Stars
    prices = [LabeledPrice(label="Подарок", amount=total_price)]
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="🎁 Покупка Telegram Подарка",
        description=f"Подарок за {gift_value}⭐" + (f" + комментарий" if comment_text else ""),
        payload=f"gift_{gift_value}_{int(datetime.now().timestamp())}",
        provider_token="",  # Для Stars не нужен
        currency="XTR",
        prices=prices,
        need_name=False,
        need_phone_number=False,
        need_email=False,
        is_flexible=False
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    data = await state.get_data()
    gift_value = data.get("gift_value")
    gift_price = data.get("gift_price")
    comment_text = data.get("comment_text", "")
    comment_price = data.get("comment_price", 0)
    total_price = data.get("total_price")
    
    # Регистрируем покупку в БД
    add_purchase(message.from_user.id, gift_value, f"Подарок {gift_value}⭐", comment_text, total_price)
    
    # Здесь ты должен отправить реальный подарок пользователю через API Telegram
    # (это требует бота-администратора с правом отправлять подарки)
    # В данном примере отправляем сообщение с инструкцией
    await message.answer(
        f"✅ Оплата прошла успешно!\n\n"
        f"Ты купил подарок за {gift_value}⭐\n"
        f"💰 Списано: {total_price} Telegram Stars\n"
        f"{'💬 Комментарий: \"' + comment_text + '\"' if comment_text else ''}\n\n"
        f"🎁 Сейчас администратор вручит тебе подарок вручную.\n"
        f"Пожалуйста, напиши @adminusername (замени на своего админа), чтобы получить подарок.\n"
        f"Пришли скриншот этого сообщения как подтверждение оплаты."
    )
    
    # Оповещаем админов о новой покупке
    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"🆕 Новая покупка!\n"
            f"👤 {message.from_user.first_name} (@{message.from_user.username or 'нет'})\n"
            f"🎁 Подарок за {gift_value}⭐\n"
            f"💰 Оплачено: {total_price}⭐\n"
            f"💬 Комментарий: {comment_text or 'нет'}\n\n"
            f"🔹 Используй /give_gift {message.from_user.id} {gift_value} чтобы подарить вручную."
        )
    
    await state.clear()
    
    # Показываем меню
    await message.answer("Вернуться в менто:", reply_markup=get_main_keyboard(message.from_user.id))

# ========== АКТИВАЦИЯ ЧЕКОВ ==========
@dp.callback_query(F.data == "activate_code")
async def activate_code_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_code_activation)
    await callback.message.edit_text(
        "🎫 Введи код активации чека (например, ABC123):\n\n"
        "Код можно получить у администратора.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]])
    )
    await callback.answer()

@dp.message(AdminState.waiting_code_activation)
async def process_code_activation(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    
    conn = sqlite3.connect("gift_bot.db")
    c = conn.cursor()
    c.execute("SELECT gift_value, gift_name, used_by FROM activation_codes WHERE code = ?", (code,))
    result = c.fetchone()
    
    if not result:
        await message.answer("❌ Неверный код активации. Попробуй ещё раз или введи /start для выхода.")
        return
    
    gift_value, gift_name, used_by = result
    if used_by:
        await message.answer("❌ Этот чек уже был активирован.")
        await state.clear()
        await message.answer("Вернуться в меню:", reply_markup=get_main_keyboard(message.from_user.id))
        return
    
    # Активируем чек
    c.execute("UPDATE activation_codes SET used_by = ?, used_at = ? WHERE code = ?",
              (message.from_user.id, datetime.now().isoformat(), code))
    conn.commit()
    conn.close()
    
    # Записываем покупку (как бесплатную активацию)
    add_purchase(message.from_user.id, gift_value, gift_name, f"Активация чека {code}", 0)
    
    # Здесь аналогично — нужно отправить подарок или уведомить админа
    await message.answer(
        f"✅ Чек успешно активирован!\n\n"
        f"Ты получил подарок: {gift_name}\n"
        f"Свяжись с администратором, чтобы получить подарок в Telegram."
    )
    await state.clear()
    await message.answer("Меню:", reply_markup=get_main_keyboard(message.from_user.id))

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("⚙️ Админ-панель:", reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return
    users, sales, stars = get_stats()
    text = f"📊 Статистика бота:\n\n👥 Пользователей: {users}\n💰 Продаж: {sales}\n⭐ Заработано Stars: {stars}"
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_create_code")
async def admin_create_code_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return
    await state.set_state(AdminState.waiting_gift_value)
    await callback.message.edit_text(
        "🧾 Создание чека.\n\nВведи номинал подарка (15, 25, 50 или 100):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_panel")]])
    )
    await callback.answer()

@dp.message(AdminState.waiting_gift_value)
async def admin_get_gift_value(message: Message, state: FSMContext):
    if message.text not in ["15", "25", "50", "100"]:
        await message.answer("❌ Номинал должен быть 15, 25, 50 или 100. Попробуй снова:")
        return
    await state.update_data(gift_value=message.text)
    await state.set_state(AdminState.waiting_gift_name)
    await message.answer("Введи название подарка (например, Мишка, Сердце):")

@dp.message(AdminState.waiting_gift_name)
async def admin_get_gift_name(message: Message, state: FSMContext):
    data = await state.get_data()
    gift_value = data.get("gift_value")
    gift_name = message.text.strip()
    
    # Генерируем уникальный код
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    conn = sqlite3.connect("gift_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO activation_codes (code, gift_value, gift_name, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
              (code, gift_value, gift_name, message.from_user.id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"✅ Чек создан!\n\n"
        f"Подарок: {gift_name} ({gift_value}⭐)\n"
        f"Код активации: `{code}`\n\n"
        f"Отправь этот код пользователю, чтобы он мог активировать подарок.",
        parse_mode="Markdown"
    )
    await state.clear()
    await message.answer("Админ-панель:", reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "admin_gift")
async def admin_gift_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return
    await state.set_state(AdminState.waiting_gift_user)
    await callback.message.edit_text(
        "🎁 Подарить подарок.\n\nВведи username пользователя (без @) или его ID:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_panel")]])
    )
    await callback.answer()

@dp.message(AdminState.waiting_gift_user)
async def admin_get_user(message: Message, state: FSMContext):
    user_input = message.text.strip()
    user_id = None
    if user_input.isdigit():
        user_id = int(user_input)
    else:
        user_input = user_input.lstrip('@')
        # Пытаемся найти пользователя по username в БД
        conn = sqlite3.connect("gift_bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username = ?", (user_input,))
        row = c.fetchone()
        conn.close()
        if row:
            user_id = row[0]
    
    if not user_id:
        await message.answer("❌ Пользователь не найден в базе. Попроси его написать /start боту.")
        return
    
    await state.update_data(gift_user_id=user_id)
    await state.set_state(AdminState.waiting_gift_value)
    await message.answer("Теперь введи номинал подарка (15, 25, 50, 100):")

@dp.message(AdminState.waiting_gift_value)
async def admin_gift_final(message: Message, state: FSMContext):
    if message.text not in ["15", "25", "50", "100"]:
        await message.answer("Номинал 15, 25, 50 или 100.")
        return
    data = await state.get_data()
    user_id = data.get("gift_user_id")
    gift_value = message.text
    
    # Отправляем подарок (тут должен быть реальный API вызов, но в демо — уведомление)
    await bot.send_message(
        user_id,
        f"🎁 Администратор подарил тебе подарок стоимостью {gift_value}⭐!\n"
        f"Свяжись с {message.from_user.first_name} чтобы получить его."
    )
    add_purchase(user_id, gift_value, f"Подарок от админа", "админский подарок", 0)
    await message.answer(f"✅ Подарок отправлен пользователю!")
    await state.clear()
    await message.answer("Админ-панель:", reply_markup=get_admin_keyboard())

# ========== ЗАПУСК ==========
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
