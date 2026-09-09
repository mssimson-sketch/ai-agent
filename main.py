#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║   🤖 AI Desktop Agent v1.0                  ║
║   Самообучающийся голосовой ассистент        ║
║   с поддержкой GitHub и самоулучшения       ║
╚══════════════════════════════════════════════╝
"""

import sys
import os
import time
import threading

# Добавляем текущую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from voice import VoiceEngine
from brain import AgentBrain
from system_monitor import SystemMonitor
from github_manager import GitHubManager
from self_upgrade import SelfUpgrade
from quality_control import QualityControl
from plugin_manager import PluginManager


class AIAgent:
    """Главный класс ИИ-агента"""

    def __init__(self):
        self._print_banner()

        # Проверка конфигурации
        errors = Config.validate()
        for e in errors:
            print(e)

        if any("OPENAI_API_KEY" in e for e in errors):
            print("\n⛔ Без API ключа OpenAI агент не будет работать!")
            print("Добавьте ключ в файл .env")
            sys.exit(1)

        # Инициализация модулей
        print("\n🧠 Загрузка мозга...")
        self.brain = AgentBrain()

        print("🎤 Загрузка голоса...")
        self.voice = VoiceEngine()

        print("📊 Загрузка мониторинга...")
        self.monitor = SystemMonitor(alert_callback=self._on_alert)

        print("🐙 Подключение GitHub...")
        self.github = GitHubManager()

        print("🔧 Загрузка системы самоулучшения...")
        self.quality = self.brain.quality
        self.self_upgrade = SelfUpgrade(
            brain=self.brain,
            github_manager=self.github,
            quality_control=self.quality
        )

        print("🔌 Загрузка плагинов...")
        self.plugins = PluginManager()

        # Связываем модули с мозгом
        self.brain.github = self.github
        self.brain.self_upgrade = self.self_upgrade
        self.brain.plugins = self.plugins

        self.running = False

        print(f"\n✅ {Config.AGENT_NAME} v{Config.VERSION} готов!")
        print(f"{'=' * 50}\n")

    def _print_banner(self):
        print("""
    ╔══════════════════════════════════════════════════╗
    ║                                                  ║
    ║   🤖  AI DESKTOP AGENT  v1.0                    ║
    ║                                                  ║
    ║   Голосовой ассистент с самоулучшением           ║
    ║   и интеграцией GitHub                          ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝
        """)

    def _on_alert(self, message: str):
        """Системное уведомление"""
        self.voice.speak(message)

    def process(self, text: str) -> bool:
        """Обработать команду. Возвращает False если нужно выйти"""
        if not text:
            return True

        # Команды выхода
        if text in ["стоп", "выход", "пока", "до свидания", "выключись"]:
            self.voice.speak("До свидания! Буду рад помочь снова.")
            return False

        if text in ["помощь", "что ты умеешь", "помоги"]:
            self.voice.speak(self._get_help())
            return True

        # Обработка через мозг
        result = self.brain.think(text)

        if result.get("speech"):
            self.voice.speak(result["speech"])

        return True

    def _get_help(self) -> str:
        return (
            f"Я {Config.AGENT_NAME}, ваш ИИ-ассистент. Вот что я умею: "
            "Открывать и закрывать приложения. "
            "Искать в Google и YouTube. "
            "Показывать состояние системы. "
            "Делать скриншоты. "
            "Управлять громкостью. "
            "Работать с файлами и папками. "
            "Искать на GitHub. "
            "Оценивать своё качество. "
            "Сам себя улучшать. "
            "Сохранять бэкапы на GitHub. "
            "Отвечать на любые вопросы. "
            "Скажите 'проверь себя' для отчёта о качестве, "
            "или 'улучши себя' для запуска самоулучшения."
        )

    # ========== РЕЖИМЫ РАБОТЫ ==========

    def run_voice(self):
        """Голосовой режим"""
        self.running = True
        self.monitor.start()

        self.voice.speak(
            f"Привет! Я {Config.AGENT_NAME}. "
            f"Я готов помогать. Говорите, я слушаю!"
        )

        print("🎤 ГОЛОСОВОЙ РЕЖИМ")
        print("Говорите команды или вопросы")
        print("Скажите 'выход' для завершения\n")

        while self.running:
            try:
                text = self.voice.listen(timeout=10, phrase_limit=15)
                if text:
                    self.running = self.process(text)
            except KeyboardInterrupt:
                print("\n⌨️ Прервано")
                break

        self._shutdown()

    def run_text(self):
        """Текстовый режим"""
        self.running = True

        print("⌨️  ТЕКСТОВЫЙ РЕЖИМ")
        print("Введите команду или вопрос")
        print("Введите 'выход' для завершения")
        print("Введите 'голос' для голосового режима\n")

        while self.running:
            try:
                text = input("👤 Вы: ").strip()

                if not text:
                    continue

                if text.lower() == "голос":
                    self.run_voice()
                    return

                self.running = self.process(text)

            except KeyboardInterrupt:
                print("\n⌨️ Прервано")
                break
            except EOFError:
                break

        self._shutdown()

    def run_hybrid(self):
        """Гибридный режим: текст + горячая клавиша F5 для голоса"""
        self.running = True
        self.monitor.start()

        try:
            import keyboard as kb

            def on_f5():
                print("\n🎤 Говорите...")
                text = self.voice.listen(timeout=7)
                if text:
                    result = self.brain.think(text)
                    speech = result.get("speech", "")
                    if speech:
                        print(f"[🔊 Вызов голоса...]")
                        self.voice.speak(speech)

            kb.add_hotkey('F5', on_f5)
            print("🔀 ГИБРИДНЫЙ РЕЖИМ")
            print("Вводите текст или нажмите F5 для голоса\n")

            while self.running:
                try:
                    text = input("👤 Вы (или F5): ").strip()
                    if not text:
                        continue
                    result = self.brain.think(text)
                    speech = result.get("speech", "")
                    if speech:
                        print(f"[🔊 Вызов голоса...]")
                        self.voice.speak(speech)
                    self.running = self.process(text) if False else True # process уже вызван через think
                except KeyboardInterrupt:
                    break

            kb.remove_all_hotkeys()

        except ImportError:
            print("⚠️ Модуль keyboard не установлен, запускаю текстовый режим")
            self.run_text()
            return

        self._shutdown()

    def _shutdown(self):
        """Корректное завершение"""
        self.running = False
        self.monitor.stop()

        # Финальный бэкап
        if self.github and self.github.repo:
            try:
                print("💾 Финальный бэкап...")
                self.github.backup_to_github()
            except:
                pass

        print(f"\n🤖 {Config.AGENT_NAME} выключен. До встречи! 👋")


def main():
    """Точка входа"""
    print("\nВыберите режим работы:\n")
    print("  1. 🎤  Голосовой режим")
    print("  2. ⌨️   Текстовый режим")
    print("  3. 🔀  Гибридный (текст + F5 для голоса)")
    print("  4. 🔧  Проверка установки")
    print()

    choice = input("Ваш выбор (1/2/3/4): ").strip()

    if choice == "4":
        check_installation()
        return

    agent = AIAgent()

    if choice == "1":
        agent.run_voice()
    elif choice == "3":
        agent.run_hybrid()
    else:
        agent.run_text()


def check_installation():
    """Проверка что всё установлено"""
    print("\n🔧 Проверка установки...\n")

    modules = {
        "openai": "pip install openai",
        "speech_recognition": "pip install SpeechRecognition",
        "pyttsx3": "pip install pyttsx3",
        "pyautogui": "pip install pyautogui",
        "psutil": "pip install psutil",
        "keyboard": "pip install keyboard",
        "pyperclip": "pip install pyperclip",
        "dotenv": "pip install python-dotenv",
        "github": "pip install PyGithub",
        "git": "pip install gitpython",
        "PIL": "pip install pillow",
    }

    all_ok = True
    for module, install in modules.items():
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} — установите: {install}")
            all_ok = False

    # Проверка PyAudio отдельно (часто проблемы)
    try:
        import pyaudio
        print(f"  ✅ pyaudio")
    except ImportError:
        print(f"  ❌ pyaudio — установите: pip install pyaudio")
        print(f"     Если ошибка: pip install pipwin && pipwin install pyaudio")
        all_ok = False

    # Проверка .env
    print()
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        print("  ✅ Файл .env найден")
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("OPENAI_API_KEY", "")
        if key and key != "sk-ВАШ-КЛЮЧ-СЮДА":
            print("  ✅ OPENAI_API_KEY установлен")
        else:
            print("  ❌ OPENAI_API_KEY не заполнен в .env")
            all_ok = False

        token = os.getenv("GITHUB_TOKEN", "")
        if token and token != "ghp_ВАШ-ТОКЕН-СЮДА":
            print("  ✅ GITHUB_TOKEN установлен")
        else:
            print("  ⚠️ GITHUB_TOKEN не заполнен (самообновление не будет работать)")
    else:
        print("  ❌ Файл .env не найден!")
        all_ok = False

    print()
    if all_ok:
        print("🎉 Всё установлено! Запускайте: python main.py")
    else:
        print("⚠️ Есть проблемы. Исправьте их и запустите проверку снова.")

    print()


if __name__ == "__main__":
    main()