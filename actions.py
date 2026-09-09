"""
Расширенные действия компьютера: Система, Программы, Погода, Новости, Переводчик, Таймеры, Установка библиотек и написание кода
"""
import subprocess
import os
import sys
import webbrowser
import pyautogui
import psutil
import pyperclip
import time
import threading
import json
import urllib.request
import urllib.parse
from datetime import datetime
from config import Config


class ComputerActions:
    def __init__(self):
        pyautogui.FAILSAFE = True

    # ==================== СИСТЕМА И ПРИЛОЖЕНИЯ ====================

    def open_application(self, app_name: str) -> str:
        apps = {
            "блокнот": "notepad.exe",
            "калькулятор": "calc.exe",
            "проводник": "explorer.exe",
            "терминал": "cmd.exe",
            "cmd": "cmd.exe",
            "диспетчер задач": "taskmgr.exe",
            "paint": "mspaint.exe",
            "паинт": "mspaint.exe",
            "настройки": "ms-settings:",
            "word": "winword.exe",
            "excel": "excel.exe",
            "vscode": "code",
            "код": "code",
            "хром": "chrome",
            "chrome": "chrome",
            "браузер": "start https://google.com",
            "телеграм": "telegram",
            "discord": "discord",
        }
        key = app_name.lower().strip()
        target = apps.get(key, key)
        try:
            if target.startswith("ms-") or target.startswith("start "):
                os.system(f"start {target}")
            else:
                subprocess.Popen(target, shell=True)
            return f"Открываю {app_name}"
        except Exception as e:
            return f"Не удалось открыть {app_name}: {e}"

    def close_application(self, app_name: str) -> str:
        try:
            name = app_name.lower().strip()
            if not name.endswith('.exe'):
                name += '.exe'
            os.system(f'taskkill /f /im {name} 2>nul')
            return f"Закрываю {app_name}"
        except Exception as e:
            return f"Ошибка закрытия: {e}"

    def open_website(self, url: str) -> str:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        webbrowser.open(url)
        return f"Открываю сайт {url}"

    def search_google(self, query: str) -> str:
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
        return f"Ищу в Google: {query}"

    def search_youtube(self, query: str) -> str:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"Ищу на YouTube: {query}"

    def get_system_info(self) -> str:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:' if os.name == 'nt' else '/')
        info = (
            f"Процессор загружен на {cpu}%. "
            f"Оперативная память: {mem.percent}% ({mem.used // (1024**3)} из {mem.total // (1024**3)} ГБ). "
            f"Основной диск заполнен на {disk.percent}%."
        )
        battery = psutil.sensors_battery()
        if battery:
            info += f" Батарея: {battery.percent}%"
        return info

    def get_datetime(self) -> str:
        now = datetime.now()
        days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        return f"Сегодня {days[now.weekday()]}, {now.day} {months[now.month - 1]} {now.year} года. Время: {now.strftime('%H:%M')}."

    def screenshot(self) -> str:
        path = os.path.join(os.path.expanduser("~"), "Desktop", f"screen_{int(time.time())}.png")
        pyautogui.screenshot().save(path)
        return "Скриншот сохранён на рабочий стол"

    def set_volume(self, level: int) -> str:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            vol_range = volume.GetVolumeRange()
            target = vol_range[0] + (vol_range[1] - vol_range[0]) * (int(level) / 100)
            volume.SetMasterVolumeLevel(target, None)
            return f"Громкость установлена на {level}%"
        except Exception as e:
            return f"Ошибка управления громкостью: {e}"

    def lock_screen(self) -> str:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Экран заблокирован"

    # ==================== НОВЫЕ МОДУЛИ ====================

    def get_weather(self, city: str = "Москва") -> str:
        """Получить погоду без API ключей через сервис wttr.in"""
        try:
            city_clean = city.strip()
            url = f"https://wttr.in/{urllib.parse.quote(city_clean)}?format=%C,+%t,+ветер+%w,+влажность+%h&lang=ru"
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                result = response.read().decode('utf-8').strip()
            return f"Погода в городе {city_clean}: {result}"
        except Exception as e:
            return f"Не удалось получить погоду для {city}: {e}"

    def get_news(self, category: str = "главное") -> str:
        """Получить актуальные новости через RSS"""
        try:
            import feedparser
            feeds = {
                "технологии": "https://habr.com/ru/rss/news/",
                "главное": "https://lenta.ru/rss/news",
                "игры": "https://dtf.ru/rss/all",
            }
            feed_url = feeds.get(category.lower(), feeds["главное"])
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                return "Не удалось загрузить новости на данный момент."

            titles = [f"{i+1}. {entry.title}" for i, entry in enumerate(feed.entries[:4])]
            return f"Свежие новости ({category}): " + " | ".join(titles)
        except Exception as e:
            return f"Ошибка при получении новостей: {e}"

    def translate_text(self, text: str, target_lang: str = "en") -> str:
        """Перевод текста на любой язык"""
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            return f"Перевод: {translated}"
        except Exception:
            # Резервный метод через веб-запрос
            try:
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as res:
                    data = json.loads(res.read().decode('utf-8'))
                    return f"Перевод: {data[0][0][0]}"
            except Exception as e:
                return f"Ошибка перевода: {e}"

    def set_reminder(self, seconds: int, text: str, voice_callback=None) -> str:
        """Установить таймер / напоминание в фоновом потоке"""
        try:
            sec = int(seconds)
            def _timer_worker():
                time.sleep(sec)
                print(f"\n⏰ НАПОМИНАНИЕ: {text}")
                try:
                    # Озвучивание через глобальный движок если передан
                    from voice import VoiceEngine
                    v = VoiceEngine()
                    v.speak(f"Внимание! Напоминание: {text}")
                except:
                    pass

            t = threading.Thread(target=_timer_worker, daemon=True)
            t.start()
            mins = sec // 60
            time_str = f"{mins} минут" if mins > 0 else f"{sec} секунд"
            return f"Напоминание установлено на через {time_str}: '{text}'"
        except Exception as e:
            return f"Ошибка таймера: {e}"

    # ==================== АВТОНОМНОЕ ПРОГРАММИРОВАНИЕ ====================

    def install_package(self, package_name: str) -> str:
        """Самостоятельная установка любой Python библиотеки"""
        try:
            print(f"📦 Устанавливаю библиотеку: {package_name}...")
            res = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                check=False
            )
            if res.returncode == 0:
                return f"Библиотека {package_name} успешно установлена в систему!"
            return f"Ошибка установки: {res.stderr[:200]}"
        except Exception as e:
            return f"Ошибка pip: {e}"

    def write_plugin(self, filename: str, code: str) -> str:
        """Создать или обновить плагин в папке plugins/"""
        try:
            if not filename.endswith('.py'):
                filename += '.py'
            path = os.path.join(Config.PLUGINS_DIR, filename)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(code)
            return f"Плагин {filename} успешно написан и сохранен в {path}!"
        except Exception as e:
            return f"Ошибка записи плагина: {e}"

    def run_python_code(self, code: str) -> str:
        """Выполнить Python код для решения задачи"""
        try:
            temp_script = os.path.join(Config.BASE_DIR, "_temp_run.py")
            with open(temp_script, 'w', encoding='utf-8') as f:
                f.write(code)
            res = subprocess.run(
                [sys.executable, temp_script],
                capture_output=True,
                text=True,
                timeout=15
            )
            if os.path.exists(temp_script):
                os.remove(temp_script)
            output = res.stdout.strip() or res.stderr.strip()
            return f"Результат выполнения: {output[:300]}"
        except Exception as e:
            return f"Ошибка выполнения кода: {e}"

    def get_available_actions(self) -> dict:
        return {
            "open_application": "Открыть программу (app_name)",
            "close_application": "Закрыть программу (app_name)",
            "open_website": "Открыть сайт (url)",
            "search_google": "Поиск в Google (query)",
            "search_youtube": "Поиск на YouTube (query)",
            "get_system_info": "Состояние ПК ()",
            "get_datetime": "Дата и время ()",
            "screenshot": "Сделать скриншот ()",
            "set_volume": "Громкость 0-100 (level)",
            "get_weather": "Погода в городе (city)",
            "get_news": "Новости категории главное/технологии/игры (category)",
            "translate_text": "Перевести текст (text, target_lang='en'|'ru'|'de'|...)",
            "set_reminder": "Напоминание (seconds, text)",
            "install_package": "Установить pip пакет (package_name)",
            "write_plugin": "Написать новый плагин (filename, code)",
            "run_python_code": "Запустить Python код (code)",
            "lock_screen": "Заблокировать экран ()",
        }