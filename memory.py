"""
Память агента — сохраняет разговоры и учится
"""
import json
import os
from datetime import datetime
from config import Config


class Memory:
    def __init__(self):
        self.conversation_history = []
        self.user_preferences = {}
        self.learned_commands = {}
        self.load()

    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Ограничение
        if len(self.conversation_history) > Config.MAX_CONTEXT_MESSAGES * 3:
            self.conversation_history = self.conversation_history[-Config.MAX_CONTEXT_MESSAGES:]

        self.save()

    def get_context(self) -> list:
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.conversation_history[-Config.MAX_CONTEXT_MESSAGES:]
        ]

    def learn_command(self, trigger: str, action: str):
        """Запомнить пользовательскую команду"""
        self.learned_commands[trigger.lower()] = action
        self.save()

    def get_learned_command(self, trigger: str) -> str:
        return self.learned_commands.get(trigger.lower(), "")

    def save(self):
        data = {
            "history": self.conversation_history[-100:],
            "preferences": self.user_preferences,
            "learned": self.learned_commands
        }
        try:
            with open(Config.MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения памяти: {e}")

    def load(self):
        if os.path.exists(Config.MEMORY_FILE):
            try:
                with open(Config.MEMORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.conversation_history = data.get("history", [])
                self.user_preferences = data.get("preferences", {})
                self.learned_commands = data.get("learned", {})
                print(f"💾 Загружено {len(self.conversation_history)} сообщений")
            except:
                pass

    def clear(self):
        self.conversation_history = []
        self.save()
        return "Память очищена"

    def get_stats(self) -> str:
        return (
            f"Сообщений в памяти: {len(self.conversation_history)}, "
            f"Выученных команд: {len(self.learned_commands)}, "
            f"Предпочтений: {len(self.user_preferences)}"
        )