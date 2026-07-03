import asyncio
import json
import os
import random
from vkbottle.bot import Bot, Message

TOKEN = "vk1.a.2pOLRBpB9IS5rWeKcjgWwaGg_btNDHS7kdqShMxgX0iCkya38r7ONHi12aBMomYq8UabUhHaXSop2Qk5dd7GQ4Y8lj-kZGjfqzTBp3SDCorejXUBbJw4Eso0JCFYLkiYyiPcmgDPPC2fKpsniMyCDqHliGavCS3TAkCAVvuKljf14Yl22hiPLO-ikFZQlU3ttHQ_OCXa8W_3iBUI9dsDfA"
ADMIN_ID = 1038602002

DB_FILE = "chats_db.json"
BROADCAST_DELAY = 0  # Не задержка между сообщениями внутри одной итерации
RACILKA_INTERVAL = 70  # интервал между рассылками, сек

bot = Bot(token=TOKEN)
racilka_task = None  # глобальный таск рассылки
racilka_active = False

# ---- db helpers ----
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chats": [], "__welcome_sent": []}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def ensure_chat_saved(peer_id):
    db = load_db()
    if peer_id not in db["chats"]:
        db["chats"].append(peer_id)
        save_db(db)

def remove_chat(peer_id):
    db = load_db()
    if peer_id in db["chats"]:
        db["chats"].remove(peer_id)
        save_db(db)

def mark_welcome_sent(peer_id):
    db = load_db()
    if "__welcome_sent" not in db:
        db["__welcome_sent"] = []
    if peer_id not in db["__welcome_sent"]:
        db["__welcome_sent"].append(peer_id)
        save_db(db)

def is_chat(peer_id: int) -> bool:
    return peer_id >= 2000000000

# Функция фильтрации размеров изображений
def get_valid_photo_sizes(photo):
    allowed_types = {
        's', 'm', 'x', 'o', 'p', 'q', 'r', 'k', 'l', 'y', 'z', 'c', 'w', 'a', 'b', 'e', 'i', 'd', 'j', 'temp', 'h', 'g', 'n', 'f', 'max'
    }
    sizes = photo.get('sizes', [])
    valid_sizes = [size for size in sizes if size.get('type') in allowed_types]
    return valid_sizes

# ---- рассылка ----
async def racilka_loop(message_text: str):
    global racilka_active
    while racilka_active:
        db = load_db()
        chats = db.get("chats", [])
        for peer in chats:
            try:
                await bot.api.messages.send(peer_id=peer, message=message_text, random_id=random.randint(1, 2**31-1))
                await asyncio.sleep(BROADCAST_DELAY)
            except:
                remove_chat(peer)
        await asyncio.sleep(RACILKA_INTERVAL)

# ---- основной обработчик ----
@bot.on.message()
async def handler(message: Message):
    global racilka_task, racilka_active

    text = (message.text or "").strip()
    if not text:
        return
    command = text.split()[0].lower()
    peer_id = message.peer_id
    from_id = message.from_id

    # Обработка вложений (фото)
    if message.attachments:
        for attachment in message.attachments:
            if attachment.type == 'photo':
                # Получаем и фильтруем размеры фото
                valid_sizes = get_valid_photo_sizes(attachment.photo)
                # Можно далее использовать valid_sizes по необходимости
                # Например, выбрать самый большой или передать их куда нужно
                # В данном пример не используется, но фильтр есть
                pass

    # Личные сообщения от админа
    if not is_chat(peer_id) and from_id == ADMIN_ID:
        if command in ["/startracilka", "startracilka"]:
            if racilka_active:
                await message.answer("Рассылка уже активна!")
                return
            payload = text[len(command):].strip() or "🔥 Реклама 🔥"
            racilka_active = True
            racilka_task = asyncio.create_task(racilka_loop(payload))
            await message.answer(f"Рассылка запущена! Сообщение: {payload}")
            return
        if command in ["/stopracilka", "stopracilka"]:
            if not racilka_active:
                await message.answer("Рассилка уже остановлена!")
                return
            racilka_active = False
            if racilka_task:
                racilka_task.cancel()
                racilka_task = None
            await message.answer("Рассылка остановлена!")
            return

    # Беседы
    if is_chat(peer_id):
        db = load_db()
        if peer_id not in db.get("chats", []):
            if command in ["/подписаться", "subscribe", "подп"]:
                ensure_chat_saved(peer_id)
                await message.answer("Чат подписан на рассылку. Чтобы отписаться — напишите '/Отписаться'.")
                return
            if command in ["/отписаться", "unsubscribe", "отп"]:
                remove_chat(peer_id)
                await message.answer("Чат отписан от рассылки.")
                return
            if peer_id not in db.get("__welcome_sent", []):
                mark_welcome_sent(peer_id)
                await message.answer("Привет! Если хотите получать рассылку — напишите '/Подписаться'.")
            return
        else:
            if command in ["отписаться", "unsubscribe", "отп"]:
                remove_chat(peer_id)
                await message.answer("Чат отписан от рассылки.")
                return
            return

# ---- старт ----
if __name__ == "__main__":
    print("Bot запущен...")
    bot.run_forever()