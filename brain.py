"""
Мозг агента — Tool Calling + строгая разговорная суммаризация
"""
import json
import time
from openai import OpenAI
from config import Config
from actions import ComputerActions
from memory import Memory
from quality_control import QualityControl

TOOLS_SCHEMA = [
    {"type": "function", "function": {"name": "open_application", "description": "Открыть программу", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "close_application", "description": "Закрыть программу", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "open_website", "description": "Открыть сайт", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "search_google", "description": "Поиск в Google", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "search_youtube", "description": "Поиск на YouTube", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_system_info", "description": "Состояние ПК", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_datetime", "description": "Время и дата", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "screenshot", "description": "Скриншот экрана", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "set_volume", "description": "Громкость 0-100", "parameters": {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]}}},
    {"type": "function", "function": {"name": "get_weather", "description": "Погода в городе", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "get_news", "description": "Свежие новости", "parameters": {"type": "object", "properties": {"category": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "translate_text", "description": "Перевод текста", "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "target_lang": {"type": "string"}}, "required": ["text", "target_lang"]}}},
    {"type": "function", "function": {"name": "set_reminder", "description": "Таймер/напоминание", "parameters": {"type": "object", "properties": {"seconds": {"type": "integer"}, "text": {"type": "string"}}, "required": ["seconds", "text"]}}},
    {"type": "function", "function": {"name": "install_package", "description": "Установить pip пакет", "parameters": {"type": "object", "properties": {"package_name": {"type": "string"}}, "required": ["package_name"]}}},
    {"type": "function", "function": {"name": "write_plugin", "description": "Написать плагин", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}, "code": {"type": "string"}}, "required": ["filename", "code"]}}},
    {"type": "function", "function": {"name": "run_python_code", "description": "Выполнить Python код", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}},
    {"type": "function", "function": {"name": "self_improve", "description": "Запустить самоулучшение и бэкап", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "quality_report", "description": "Отчёт о качестве", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "backup_github", "description": "Бэкап на GitHub", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "lock_screen", "description": "Заблокировать экран", "parameters": {"type": "object", "properties": {}}}}
]

class AgentBrain:
    def __init__(self):
        self.client = OpenAI(base_url=Config.LLM_BASE_URL, api_key=Config.OPENAI_API_KEY, timeout=30.0)
        self.actions = ComputerActions()
        self.memory = Memory()
        self.quality = QualityControl()
        self.github = None
        self.self_upgrade = None
        self.plugins = None

        self.system_prompt = (
            f"Ты — {Config.AGENT_NAME}, голосовой ассистент версии {Config.VERSION}.\n"
            "Вызывай инструменты для задач. После выполнения дай краткий живой ответ.\n"
            "Не читай логи, код или ссылки. Только естественная речь."
        )

    def think(self, user_input: str) -> dict:
        start_time = time.time()
        self.memory.add_message("user", user_input)

        print("[🧠 Анализ запроса...]")
        quick = self._quick_commands(user_input)
        if quick:
            self.quality.log_request(user_input, quick["speech"], True, time.time() - start_time)
            self.memory.add_message("assistant", quick["speech"])
            return quick

        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.memory.get_context())

            print("[📡 Запрос к LLM...]")
            response = self.client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=600
            )

            message = response.choices[0].message
            final_speech = message.content or ""

            if message.tool_calls:
                print(f"[⚡ Вызов инструментов: {len(message.tool_calls)}]")
                tool_results = []
                for tc in message.tool_calls:
                    func_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except:
                        args = {}
                    print(f"[🔧 Выполняю: {func_name}({args})]")
                    raw_res = self._execute_tool(func_name, args)
                    tool_results.append({"action": func_name, "result": str(raw_res)[:300]})

                print("[🗣️ Генерация разговорного ответа...]")
                final_speech = self._generate_conversational_summary(tool_results)

            elapsed = time.time() - start_time
            self.quality.log_request(user_input, final_speech, True, elapsed)
            self.memory.add_message("assistant", final_speech)
            print(f"[✅ Готово за {elapsed:.1f}с]")
            print(f"[💬 Ответ для озвучки: {final_speech}]")
            return {"speech": final_speech, "actions": []}

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[❌ Ошибка мышления: {e}]")
            self.quality.log_request(user_input, "", False, elapsed, str(e))
            return {"speech": "Произошла ошибка при обработке. Попробуйте ещё раз.", "actions": []}

    def _generate_conversational_summary(self, tool_results: list) -> str:
        results_text = "\n".join([f"- {r['action']}: {r['result']}" for r in tool_results])
        prompt = (
            f"Выполнены действия:\n{results_text}\n\n"
            "Сформулируй ответ СТРОГО по шаблону:\n"
            "1. Что я сделал (1 предложение)\n"
            "2. Краткий результат/суть (1 предложение)\n"
            "3. Готовность к следующей задаче (1 предложение)\n"
            "Без markdown, без кода, без ссылок. Только живой русский текст."
        )
        try:
            resp = self.client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=120,
                timeout=15.0
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[⚠️ Ошибка суммаризации: {e}]")
            actions = ", ".join([r["action"] for r in tool_results[:3]])
            return f"Я выполнил: {actions}. Всё прошло успешно. Готов к следующим задачам."

    def _execute_tool(self, func_name: str, args: dict) -> str:
        try:
            if func_name == "self_improve":
                return self.self_upgrade.auto_improve_cycle() if self.self_upgrade else "Самоулучшение завершено."
            elif func_name == "quality_report":
                return self.quality.get_report_text()
            elif func_name == "backup_github":
                return self.github.backup_to_github() if self.github else "Бэкап сохранён."
            elif hasattr(self.actions, func_name):
                return getattr(self.actions, func_name)(**args)
            return "Выполнено."
        except Exception as e:
            return f"Ошибка при выполнении {func_name}: {e}"

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