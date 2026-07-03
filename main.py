import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import threading
import time
import json
import random

class VKAutopiarBot:
    def __init__(self, token, admin_id):
        self.token = token
        self.admin_id = admin_id
        self.vk = vk_api.VkApi(token=token)
        self.vk_api = self.vk.get_api()
        
        # Используем обычный LongPoll вместо BotLongPoll
        self.longpoll = VkLongPoll(self.vk)
        
        # Настройки по умолчанию
        self.settings = {
            "text": "🔥 Автопиар! Подписывайтесь на наш паблик!",
            "interval": 3600,  # 1 час
            "groups": []
        }
        
        # Загрузка настроек
        self.load_settings()
        
        # Флаг для остановки автопиара
        self.running = True
        self.piar_thread = None
        
    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except:
            self.save_settings()
            
    def save_settings(self):
        """Сохранение настроек в файл"""
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)
            
    def start_autopiar(self):
        """Запуск автопиара в отдельном потоке"""
        if self.piar_thread and self.piar_thread.is_alive():
            return
            
        self.running = True
        self.piar_thread = threading.Thread(target=self.autopiar_loop)
        self.piar_thread.daemon = True
        self.piar_thread.start()
        
    def stop_autopiar(self):
        """Остановка автопиара"""
        self.running = False
        if self.piar_thread:
            self.piar_thread.join(timeout=1)
            
    def autopiar_loop(self):
        """Основной цикл автопиара"""
        while self.running:
            try:
                for group_id in self.settings["groups"]:
                    self.send_piar(group_id)
                    time.sleep(5)  # Пауза между постами
                time.sleep(self.settings["interval"])
            except Exception as e:
                print(f"Ошибка в автопиаре: {e}")
                time.sleep(10)
                
    def send_piar(self, group_id):
        """Отправка сообщения в группу"""
        try:
            # Проверяем, есть ли доступ к группе
            self.vk_api.wall.post(
                owner_id=-abs(group_id),
                message=self.settings["text"],
                from_group=1
            )
            print(f"✅ Автопиар отправлен в группу {group_id}")
        except Exception as e:
            print(f"❌ Ошибка отправки в группу {group_id}: {e}")
            
    def add_group(self, group_id):
        """Добавление группы в список"""
        group_id = abs(group_id)  # Приводим к положительному числу
        if group_id not in self.settings["groups"]:
            self.settings["groups"].append(group_id)
            self.save_settings()
            return True
        return False
        
    def remove_group(self, group_id):
        """Удаление группы из списка"""
        group_id = abs(group_id)
        if group_id in self.settings["groups"]:
            self.settings["groups"].remove(group_id)
            self.save_settings()
            return True
        return False
        
    def is_admin(self, user_id):
        """Проверка, является ли пользователь администратором"""
        return str(user_id) == str(self.admin_id)
        
    def handle_commands(self, message, user_id):
        """Обработка команд"""
        if not self.is_admin(user_id):
            self.send_message(user_id, "❌ У вас нет прав администратора!")
            return
            
        parts = message.split()
        command = parts[0].lower()
        
        if command == "/txt":
            if len(parts) < 2:
                self.send_message(user_id, "❌ Использование: /txt [текст рассылки]")
                return
            new_text = " ".join(parts[1:])
            self.settings["text"] = new_text
            self.save_settings()
            self.send_message(user_id, f"✅ Текст обновлен: {new_text}")
            
        elif command == "/interval":
            if len(parts) != 2:
                self.send_message(user_id, "❌ Использование: /interval [секунды]")
                return
            try:
                interval = int(parts[1])
                if interval < 10:
                    self.send_message(user_id, "❌ Интервал должен быть больше 10 секунд")
                    return
                self.settings["interval"] = interval
                self.save_settings()
                self.send_message(user_id, f"✅ Интервал обновлен: {interval} секунд")
                self.stop_autopiar()
                self.start_autopiar()
            except ValueError:
                self.send_message(user_id, "❌ Введите число!")
                
        elif command == "/infochat":
            count = len(self.settings["groups"])
            groups = "\n".join([f"  - {g}" for g in self.settings["groups"]]) if self.settings["groups"] else "  (пусто)"
            self.send_message(user_id, f"📊 Подключенные группы: {count}\n{groups}")
            
        elif command == "/help":
            help_text = """
🤖 **Команды бота:**
/txt [текст] — Изменить текст рассылки
/interval [сек] — Изменить интервал автопиара
/infochat — Показать количество групп
/help — Показать это сообщение
/add [id] — Добавить группу (по ID)
/remove [id] — Удалить группу (по ID)
/start — Запустить автопиар
/stop — Остановить автопиар
            """
            self.send_message(user_id, help_text)
            
        elif command == "/add":
            if len(parts) != 2:
                self.send_message(user_id, "❌ Использование: /add [id_группы]")
                return
            try:
                group_id = int(parts[1])
                if self.add_group(group_id):
                    self.send_message(user_id, f"✅ Группа {group_id} добавлена")
                    self.stop_autopiar()
                    self.start_autopiar()
                else:
                    self.send_message(user_id, f"⚠️ Группа {group_id} уже в списке")
            except ValueError:
                self.send_message(user_id, "❌ Введите число!")
                
        elif command == "/remove":
            if len(parts) != 2:
                self.send_message(user_id, "❌ Использование: /remove [id_группы]")
                return
            try:
                group_id = int(parts[1])
                if self.remove_group(group_id):
                    self.send_message(user_id, f"✅ Группа {group_id} удалена")
                    self.stop_autopiar()
                    if self.settings["groups"]:
                        self.start_autopiar()
                else:
                    self.send_message(user_id, f"⚠️ Группа {group_id} не найдена")
            except ValueError:
                self.send_message(user_id, "❌ Введите число!")
                
        elif command == "/start":
            if not self.settings["groups"]:
                self.send_message(user_id, "❌ Нет подключенных групп. Добавьте группы через /add")
                return
            self.start_autopiar()
            self.send_message(user_id, "✅ Автопиар запущен!")
            
        elif command == "/stop":
            self.stop_autopiar()
            self.send_message(user_id, "⏹️ Автопиар остановлен")
            
        else:
            self.send_message(user_id, "❌ Неизвестная команда. Используйте /help")
            
    def send_message(self, user_id, text):
        """Отправка сообщения пользователю"""
        try:
            self.vk_api.messages.send(
                user_id=user_id,
                message=text,
                random_id=random.randint(1, 999999999)
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            
    def run(self):
        """Основной цикл бота"""
        print("🤖 Бот автопиара запущен!")
        print(f"👤 Администратор: {self.admin_id}")
        print(f"📝 Текст: {self.settings['text']}")
        print(f"⏱️ Интервал: {self.settings['interval']} сек")
        print(f"📊 Групп: {len(self.settings['groups'])}")
        
        # Автозапуск, если есть группы
        if self.settings["groups"]:
            self.start_autopiar()
            
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW:
                        if event.message and event.message.get('text'):
                            message = event.message['text'].strip()
                            user_id = event.message['from_id']
                            
                            if message.startswith('/'):
                                self.handle_commands(message, user_id)
                            
            except Exception as e:
                print(f"Ошибка в основном цикле: {e}")
                time.sleep(5)

if __name__ == "__main__":
    TOKEN = "vk1.a.McsxY5CGtA6s9PtFItFhGXJ7-JFYd4wezGHSleFBB6ABfalcwzGRO3Hz0qVY15GgLw0T4FSFF8I-z6DrG7CfthYPAV3u7ftNDmQ9qkRGUGrypx5AB9v9s1t_KVcCwHt4z0yAqLZX-ErX2oefsWHpn79cqeYzIJfn7lD3mdsZV_ihPJ9VlGhqnbzDROujIil76-ZfRmXyp9DOUQTJsP65wg"
    ADMIN_ID = 823652026
    
    bot = VKAutopiarBot(TOKEN, ADMIN_ID)
    bot.run()
