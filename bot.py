import telebot
import requests
import json
import time
import html
import hashlib
from telebot import types

TOKEN = '8596007073:AAFNvB6Zcl76uQGCkFGmU-n20euQeMXscgc'
bot = telebot.TeleBot(TOKEN)

user_emails = {}
user_last_message_id = {}
user_sid = {}  # Сессия для каждого пользователя

def get_temp_email(chat_id):
    """Создание временной почты через Guerrilla Mail"""
    try:
        # Получаем новый email
        response = requests.get('https://api.guerrillamail.com/ajax.php?f=get_email_address&ip=127.0.0.1&agent=TelegramBot')
        if response.status_code == 200:
            data = response.json()
            email = data.get('email_addr')
            sid = data.get('sid')
            
            if email and sid:
                user_sid[chat_id] = sid
                return email
    except Exception as e:
        print(f"Ошибка создания почты: {e}")
    return None

def check_email_inbox(chat_id):
    """Проверка входящих писем через Guerrilla Mail"""
    try:
        sid = user_sid.get(chat_id)
        if not sid:
            return []
        
        response = requests.get(f'https://api.guerrillamail.com/ajax.php?f=get_email_list&sid={sid}&offset=0')
        if response.status_code == 200:
            data = response.json()
            return data.get('list', [])
    except Exception as e:
        print(f"Ошибка проверки почты: {e}")
    return []

def get_message_content(chat_id, message_id):
    """Получение содержимого письма"""
    try:
        sid = user_sid.get(chat_id)
        if not sid:
            return None
        
        response = requests.get(f'https://api.guerrillamail.com/ajax.php?f=fetch_email&sid={sid}&email_id={message_id}')
        if response.status_code == 200:
            data = response.json()
            return data
    except Exception as e:
        print(f"Ошибка получения письма: {e}")
    return None

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_sticker(message.chat.id, 'CAACAgEAAxkBAAEpLcxm2dW5AS4WVB8PTRVshB2g1KNC5QACLQEAAjgOghHg_AlwrsI5zzYE')

    welcome_text = (
        "🙋 <b>Добро пожаловать!</b>\n"
        "❓ <i>Это бот для временных почт чтобы привязать свой аккаунт на Arizona RP и не париться</i>.\n"
    )

    email = get_temp_email(message.chat.id)
    if email:
        user_emails[message.chat.id] = email
        user_last_message_id[message.chat.id] = None

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_change = types.KeyboardButton("✉️ Сменить почту ✉️")
        btn_info = types.KeyboardButton("❓ Информация ❓")
        btn_check = types.KeyboardButton("📬 Проверить письма 📬")
        markup.add(btn_change, btn_info, btn_check)

        bot.send_message(
            message.chat.id,
            welcome_text,
            parse_mode='HTML',
            reply_markup=markup
        )

        email_message = f"⚠️ <b>Ваша временная почта:</b>\n<code>{email}</code> ⚠️"
        bot.send_message(message.chat.id, email_message, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "⚠️ <b>Ошибка при получении почты</b> ⚠️", parse_mode='HTML')

@bot.message_handler(content_types=['text'])
def func(message):
    if message.text == "✉️ Сменить почту ✉️":
        new_email = get_temp_email(message.chat.id)
        if new_email:
            user_emails[message.chat.id] = new_email
            user_last_message_id[message.chat.id] = None
            bot.send_message(message.chat.id, f"⚠️ <b>Ваша новая временная почта:</b>\n<code>{new_email}</code> ⚠️", parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, "⚠️ <b>Ошибка при смене почты</b> ⚠️", parse_mode='HTML')
    
    elif message.text == "❓ Информация ❓":
        info_text = (
            "📧 <b>О боте:</b>\n"
            "Этот бот создаёт временные email адреса для регистрации на Arizona RP.\n\n"
            "✨ <b>Особенности:</b>\n"
            "• Бесплатно и без ограничений\n"
            "• Автоматическое уведомление о новых письмах\n"
            "• Можно вручную проверить почту\n"
            "• Письма хранятся до 1 часа\n\n"
            "👨‍💻 <b>Создатель:</b> @crio_samp_legend"
        )
        bot.send_message(message.chat.id, info_text, parse_mode='HTML')
    
    elif message.text == "📬 Проверить письма 📬":
        check_and_send_emails(message.chat.id, manual=True)

def check_and_send_emails(chat_id, manual=False):
    """Проверка и отправка писем пользователю"""
    email = user_emails.get(chat_id)
    if not email:
        if manual:
            bot.send_message(chat_id, "⚠️ <b>Сначала создайте почту командой /start</b> ⚠️", parse_mode='HTML')
        return
    
    messages = check_email_inbox(chat_id)
    
    if not messages:
        if manual:
            bot.send_message(chat_id, "📭 <b>Новых писем нет</b> 📭", parse_mode='HTML')
        return
    
    new_messages = []
    for msg in messages:
        msg_id = msg.get('mail_id')
        if user_last_message_id.get(chat_id) != msg_id:
            new_messages.append(msg)
    
    if not new_messages:
        if manual:
            bot.send_message(chat_id, "📭 <b>Новых писем нет</b> 📭", parse_mode='HTML')
        return
    
    for msg in new_messages:
        msg_id = msg.get('mail_id')
        user_last_message_id[chat_id] = msg_id
        
        msg_content = get_message_content(chat_id, msg_id)
        if msg_content:
            email_from = html.escape(msg_content.get('mail_from', 'Неизвестно'))
            email_subject = html.escape(msg_content.get('mail_subject', 'Без темы'))
            email_body = html.escape(msg_content.get('mail_text_only', 'Текст письма отсутствует')[:500])
            
            notification = (
                f"📨 <b>Новое письмо!</b>\n"
                f"📧 <b>Почта:</b> <code>{email}</code>\n"
                f"👤 <b>От кого:</b> {email_from}\n"
                f"📋 <b>Тема:</b> {email_subject}\n\n"
                f"💬 <b>Содержание:</b>\n{email_body}"
            )
            
            bot.send_message(chat_id, notification, parse_mode='HTML')

def check_for_new_emails():
    """Фоновая проверка писем для всех пользователей"""
    while True:
        try:
            for chat_id in list(user_emails.keys()):
                check_and_send_emails(chat_id, manual=False)
        except Exception as e:
            print(f"Ошибка в фоновой проверке: {e}")
        time.sleep(15)  # Проверка каждые 15 секунд

# Запуск фонового потока
import threading
email_check_thread = threading.Thread(target=check_for_new_emails, daemon=True)
email_check_thread.start()

if __name__ == '__main__':
    print("Бот запущен и готов к работе!")
    bot.polling(none_stop=True, interval=0)
