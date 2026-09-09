"""
Менеджер плагинов — расширение возможностей агента
"""
import os
import importlib
import json
from config import Config


class PluginManager:
    """Загрузка и управление плагинами"""

    def __init__(self):
        self.plugins = {}
        self.load_plugins()

    def load_plugins(self):
        """Загрузить все плагины из папки plugins/"""
        plugin_dir = Config.PLUGINS_DIR
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir, exist_ok=True)
            return

        for filename in os.listdir(plugin_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                self._load_plugin(filename[:-3])

    def _load_plugin(self, name: str):
        """Загрузить один плагин"""
        try:
            import sys
            sys.path.insert(0, Config.PLUGINS_DIR)
            module = importlib.import_module(name)

            if hasattr(module, 'Plugin'):
                plugin = module.Plugin()
                self.plugins[name] = {
                    "module": module,
                    "instance": plugin,
                    "name": getattr(plugin, 'name', name),
                    "description": getattr(plugin, 'description', ''),
                    "commands": getattr(plugin, 'commands', {})
                }
                print(f"🔌 Плагин загружен: {name}")
            else:
                print(f"⚠️ Плагин {name} не содержит класс Plugin")

        except Exception as e:
            print(f"❌ Ошибка загрузки плагина {name}: {e}")

    def execute_plugin_command(self, plugin_name: str, command: str, **kwargs) -> str:
        """Выполнить команду плагина"""
        if plugin_name not in self.plugins:
            return f"Плагин {plugin_name} не найден"

        plugin = self.plugins[plugin_name]["instance"]

        if hasattr(plugin, command):
            try:
                method = getattr(plugin, command)
                return str(method(**kwargs))
            except Exception as e:
                return f"Ошибка плагина: {e}"

        return f"Команда {command} не найдена в плагине {plugin_name}"

    def list_plugins(self) -> str:
        """Список установленных плагинов"""
        if not self.plugins:
            return "Плагины не установлены"

        lines = []
        for name, info in self.plugins.items():
            lines.append(f"🔌 {info['name']}: {info['description']}")

        return "Установленные плагины: " + "; ".join(lines)

    def create_plugin_template(self, name: str, description: str) -> str:
        """Создать шаблон нового плагина"""
        template = f'''"""
Плагин: {name}
Описание: {description}
"""


class Plugin:
    name = "{name}"
    description = "{description}"
    commands = {{}}  # "команда": "описание"

    def __init__(self):
        print(f"🔌 Плагин {{self.name}} инициализирован")

    # Добавьте свои методы ниже
    def hello(self) -> str:
        return f"Привет от плагина {{self.name}}!"
'''

        filepath = os.path.join(Config.PLUGINS_DIR, f"{name}.py")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)

        return f"Шаблон плагина создан: {filepath}"