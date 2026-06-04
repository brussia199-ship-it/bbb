import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

BOT_TOKEN = "600000042001:_G5qCoOrda_VX4l7_atkEP53MbgwxRiRkIA"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

GIFT_ID = "5956217000635139069"
GIFT_NAME = "🧸 Плюшевый мишка"
DEFAULT_COMMENT = "@DuDRovEGift залетай в нашу банду"
PRICE = 100
GIFT_COUNT = 6

async def send_gift(user_id: int, gift_id: str, text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendGift"
    payload = {
        "user_id": user_id,
        "gift_id": gift_id,
        "text": text,
        "pay_for_upgrade": True
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()
            return result.get("ok", False), result

async def get_bot_stars_balance():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getStarBalance"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            result = await resp.json()
            if result.get("ok"):
                return result.get("result", {}).get("total_stars", 0)
            return 0

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 КУПИТЬ 6 МЕДВЕДЕЙ ЗА 100⭐", callback_data="buy")],
        [InlineKeyboardButton(text="💰 БАЛАНС БОТА", callback_data="balance")]
    ])
    return keyboard

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    text = (
        f"🧸 **ПОДАРКИ ЗА TELEGRAM STARS** 🧸\n\n"
        f"Привет! При нажатии на кнопку ниже ты получишь **{GIFT_COUNT}** плюшевых мишек!\n\n"
        f"🎁 **Подарок:** {GIFT_NAME}\n"
        f"💰 **Цена:** {PRICE} Stars за {GIFT_COUNT} шт.\n"
        f"💬 **Комментарий к подарку:**\n"
        f"`{DEFAULT_COMMENT}`\n\n"
        f"📌 Нажми на кнопку и оплати Stars"
    )
    
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "buy")
async def buy_callback(callback: types.CallbackQuery):
    prices = [LabeledPrice(label=f"{GIFT_NAME} x{GIFT_COUNT}", amount=PRICE)]
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"{GIFT_NAME} x{GIFT_COUNT}",
        description=f"Вы получите {GIFT_COUNT} плюшевых мишек с подписью: {DEFAULT_COMMENT}",
        payload="gift_purchase",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="gift_purchase"
    )
    await callback.answer()

@dp.callback_query(F.data == "balance")
async def balance_callback(callback: types.CallbackQuery):
    balance = await get_bot_stars_balance()
    text = f"💰 **БАЛАНС БОТА:** {balance} Stars\n\n💡 Эти Stars используются для отправки подарков."
    await callback.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    bot_balance = await get_bot_stars_balance()
    if bot_balance < PRICE:
        await query.answer(ok=False, error_message="У бота нет Stars для отправки подарков. Попробуйте позже.")
        return
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    user = message.from_user
    stars_spent = message.successful_payment.total_amount
    
    success_count = 0
    fail_count = 0
    
    await message.answer("🔄 Отправляю подарки... Подождите немного ⏳")
    
    for i in range(GIFT_COUNT):
        success, response = await send_gift(user.id, GIFT_ID, DEFAULT_COMMENT)
        if success:
            success_count += 1
        else:
            fail_count += 1
        await asyncio.sleep(0.5)
    
    if success_count > 0:
        text = (
            f"✅ **ГОТОВО!** 🎉\n\n"
            f"🧸 **Получено мишек:** {success_count} из {GIFT_COUNT}\n"
            f"💬 Комментарий: {DEFAULT_COMMENT}\n"
            f"⭐ Потрачено: {stars_spent} Stars\n\n"
            f"📱 Все подарки уже в вашем профиле!\n\n"
            f"🔗 **ПРИСОЕДИНЯЙСЯ К НАМ:**\n"
            f"https://t.me/durov_gifts"
        )
        
        if fail_count > 0:
            text += f"\n\n⚠️ {fail_count} подарков не отправились. Администратор уведомлён."
        
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(
            f"❌ **ОШИБКА!**\n\n"
            f"Не удалось отправить подарки. Администратор уведомлён.\n"
            f"Ваши Stars будут возвращены вручную.",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

async def main():
    balance = await get_bot_stars_balance()
    print("🚀 БОТ ЗАПУЩЕН!")
    print(f"💰 Баланс бота: {balance} Stars")
    print(f"🎁 При старте бот отправляет счёт на {PRICE}⭐ за {GIFT_COUNT} мишек")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
