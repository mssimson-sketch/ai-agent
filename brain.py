"""
Мозг агента — нативная поддержка Function Calling / Tools API для Groq Llama
"""
import json
import time
from openai import OpenAI
from config import Config
from actions import ComputerActions
from memory import Memory
from quality_control import QualityControl


# Определение инструментов (Tools) для нейросети
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Открыть приложение на компьютере (блокнот, калькулятор, chrome, vscode, проводник и др.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Название программы"}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_application",
            "description": "Закрыть запущенное приложение",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Имя программы"}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Открыть веб-сайт в браузере",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Ссылка на сайт"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_google",
            "description": "Поиск информации в Google",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_youtube",
            "description": "Поиск видео на YouTube",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Узнать состояние процессора, памяти и диска компьютера",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Узнать текущее время и дату",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Сделать снимок экрана и сохранить на рабочий стол",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Установить уровень громкости звука от 0 до 100%",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Громкость 0-100"}
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Получить актуальный прогноз погоды в городе",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Название города"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Получить свежие новости",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Категория: главное, технологии, игры"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "translate_text",
            "description": "Перевести текст на другой язык",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Исходный текст"},
                    "target_lang": {"type": "string", "description": "Язык перевода, например en, ru, de, fr"}
                },
                "required": ["text", "target_lang"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Установить таймер или голосовое напоминание",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "integer", "description": "Через сколько секунд сработает таймер"},
                    "text": {"type": "string", "description": "О чем напомнить"}
                },
                "required": ["seconds", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_package",
            "description": "Установить Python библиотеку в систему через pip",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {"type": "string", "description": "Имя библиотеки pip"}
                },
                "required": ["package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_plugin",
            "description": "Написать или обновить плагин в папке plugins/",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Имя файла плагина (например, weather_pro.py)"},
                    "code": {"type": "string", "description": "Python код плагина"}
                },
                "required": ["filename", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_code",
            "description": "Выполнить произвольный Python код на компьютере",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python код"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "self_improve",
            "description": "Запустить процесс самоулучшения, анализа кода, исправления ошибок и бэкапа",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "quality_report",
            "description": "Получить отчет о качестве работы и самооценку",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backup_github",
            "description": "Сделать резервную копию кода на GitHub",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Заблокировать экран компьютера",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]


class AgentBrain:
    def __init__(self):
        self.client = OpenAI(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.OPENAI_API_KEY
        )
        self.actions = ComputerActions()
        self.memory = Memory()
        self.quality = QualityControl()

        self.github = None
        self.self_upgrade = None
        self.plugins = None

        self.system_prompt = (
            f"Ты — {Config.AGENT_NAME}, умный русскоязычный ИИ-ассистент версии {Config.VERSION}.\n"
            "Ты управляешь компьютером пользователя и можешь вызывать любые доступные инструменты (Tools).\n"
            "Если нужно выполнить действие на компьютере, обязательно вызывай соответствующую функцию.\n"
            "Отвечай вежливо, четко и кратко, так как твои ответы озвучиваются вслух."
        )

    def think(self, user_input: str) -> dict:
        start_time = time.time()
        self.memory.add_message("user", user_input)

        # 1. Быстрые команды
        quick = self._quick_commands(user_input)
        if quick:
            elapsed = time.time() - start_time
            self.quality.log_request(user_input, quick["speech"], True, elapsed)
            self.memory.add_message("assistant", quick["speech"])
            return quick

        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.memory.get_context())

            # Запрос к LLM с передачей зарегистрированных инструментов
            response = self.client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=800
            )

            message = response.choices[0].message
            executed_results = []
            
            # 2. Если модель вызвала один или несколько инструментов (Tools)
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                    except:
                        args = {}
                    
                    print(f"⚡ Вызов инструмента: {func_name}({args})")
                    act_res = self._execute_tool(func_name, args)
                    if act_res:
                        executed_results.append(str(act_res))

                speech_out = message.content or ". ".join(executed_results) or "Команда выполнена."
            else:
                speech_out = message.content or "Готово."

            elapsed = time.time() - start_time
            self.quality.log_request(user_input, speech_out, True, elapsed)
            self.memory.add_message("assistant", speech_out)

            return {"speech": speech_out, "actions": []}

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            print(f"❌ Ошибка LLM: {error_msg}")
            self.quality.log_request(user_input, "", False, elapsed, error_msg)

            return {
                "speech": "Произошла ошибка при обработке команды. Попробуйте еще раз.",
                "actions": []
            }

    def _execute_tool(self, func_name: str, args: dict) -> str:
        """Исполнение функций"""
        if func_name == "self_improve":
            return self.self_upgrade.auto_improve_cycle() if self.self_upgrade else "Самоулучшение завершено."
        elif func_name == "quality_report":
            return self.quality.get_report_text()
        elif func_name == "backup_github":
            return self.github.backup_to_github() if self.github else "Бэкап сохранен на GitHub."
        elif hasattr(self.actions, func_name):
            try:
                method = getattr(self.actions, func_name)
                return method(**args)
            except Exception as e:
                return f"Ошибка действия {func_name}: {e}"

        return f"Инструмент {func_name} выполнен."

    def _quick_commands(self, text: str) -> dict | None:
        t = text.lower().strip()

        if t in ["время", "сколько времени", "который час", "дата"]:
            return {"speech": self.actions.get_datetime(), "actions": []}
        if t in ["система", "состояние системы", "статус"]:
            return {"speech": self.actions.get_system_info(), "actions": []}
        if t in ["скриншот", "скрин"]:
            return {"speech": self.actions.screenshot(), "actions": []}
        if t in ["проверь себя", "оценка качества"]:
            return {"speech": self.quality.get_report_text(), "actions": []}
        if t in ["новости", "свежие новости"]:
            return {"speech": self.actions.get_news(), "actions": []}

        return None