import telebot
import requests
import json
import time
import html
from telebot import types

TOKEN = '8596007073:AAFNvB6Zcl76uQGCkFGmU-n20euQeMXscgc'
bot = telebot.TeleBot(TOKEN)

user_emails = {}
user_last_message_id = {}

def get_temp_email():
    url = 'https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1'
    response = requests.get(url)
    if response.status_code == 200:
        email = json.loads(response.text)[0]
        return email
    return None

def check_email_inbox(email):
    login, domain = email.split('@')
    url = f'https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}'
    response = requests.get(url)
    if response.status_code == 200:
        messages = json.loads(response.text)
        return messages
    return []

def get_message_content(email, message_id):
    login, domain = email.split('@')
    url = f'https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={message_id}'
    response = requests.get(url)
    if response.status_code == 200:
        message = json.loads(response.text)
        return message
    return None

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_sticker(message.chat.id, 'CAACAgEAAxkBAAEpLcxm2dW5AS4WVB8PTRVshB2g1KNC5QACLQEAAjgOghHg_AlwrsI5zzYE')

    welcome_text = (
        "🙋 <b>Добро пожаловать!</b>\n"
        "❓ <i>Это бот для временных почт что бы привязать свой аккаунт на Arizona RP и не париться</i>.\n"
    )

    email = get_temp_email()
    if email:
        user_emails[message.chat.id] = email
        user_last_message_id[message.chat.id] = None

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_change = types.KeyboardButton("✉️Сменить почту✉️")
        btn_info = types.KeyboardButton("❓Информация❓")
        markup.add(btn_change, btn_info)

        bot.send_message(
            message.chat.id,
            welcome_text,
            parse_mode='HTML',
            reply_markup=markup
        )

        email_message = f"⚠️ <b>Ваша временная почта:</b> <code>{email}</code>⚠️"
        bot.send_message(message.chat.id, email_message, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "⚠️ <b>Ошибка при получении почты</b>⚠️", parse_mode='HTML')

@bot.message_handler(content_types=['text'])
def func(message):
    if message.text == "✉️Сменить почту✉️":
        new_email = get_temp_email()
        if new_email:
            user_emails[message.chat.id] = new_email
            user_last_message_id[message.chat.id] = None
            bot.send_message(message.chat.id, f"⚠️ <b>Ваша новая временная почта:</b> <code>{new_email}</code> ⚠️", parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, "⚠️ <b>Ошибка при смене почты</b> ⚠️", parse_mode='HTML')
    elif message.text == "❓Информация❓":
        bot.send_message(message.chat.id, "Это бот для временных почт что бы привязать свой аккаунт на Arizona RP и не париться. Он удобнее чем любая другая почта так как он прямо у вас в Telegram! Данный бот полностью бесплатный и создал его crio samp legend, хочешь так же? Тогда иди нахуй мелкий ты уебан!")

def check_for_new_emails():
    while True:
        for chat_id, email in user_emails.items():
            messages = check_email_inbox(email)
            if messages:
                last_message = messages[0]
                last_message_id = last_message['id']

                if user_last_message_id.get(chat_id) != last_message_id:
                    user_last_message_id[chat_id] = last_message_id
                    message_content = get_message_content(email, last_message_id)

                    email_from = html.escape(message_content['from'])
                    email_subject = html.escape(message_content['subject'])
                    email_body = html.escape(message_content['textBody'])

                    notification = (
                        f"📨 <b>Новое письмо на почту:</b> <code>{email}</code>\n"
                        f"👤 <b>От кого:</b> {email_from}\n"
                        f"📋 <b>Тема:</b> {email_subject}\n\n"
                        f"💬 <b>Содержание:</b>\n{email_body}"
                    )

                    bot.send_message(chat_id, notification, parse_mode='HTML')

        time.sleep(5) # Проверка почты (минимум 5 сек)

import threading
email_check_thread = threading.Thread(target=check_for_new_emails)
email_check_thread.start()

bot.polling(none_stop=True)
