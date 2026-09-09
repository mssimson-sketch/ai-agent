"""
Jarvis v2 - Planner

Задачи модуля:
1. Понять естественный запрос пользователя.
2. Разделить составной запрос на отдельные шаги.
3. Извлечь параметры действий.
4. Проверить план до передачи Executor.
5. НИЧЕГО самостоятельно не выполнять на компьютере.

Planner intentionally has no access to ComputerActions.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from core.llm import LLMClient, LLMError


# ============================================================
# РАЗРЕШЕННЫЕ ДЕЙСТВИЯ
# ============================================================

ALLOWED_ACTIONS = {
    # Диалог
    "answer",

    # Самодиагностика
    "self_diagnose",
    "propose_improvement",
    "backup_github",
    "quality_report",

    # Компьютер
    "open_application",
    "close_application",
    "get_system_info",
    "get_datetime",
    "screenshot",
    "set_volume",

    # Интернет
    "open_website",
    "search_web",
    "search_youtube",

    # Информация
    "get_weather",
    "get_news",
    "translate_text",

    # Органайзер
    "set_reminder",
}


# ============================================================
# ОБЯЗАТЕЛЬНЫЕ ПАРАМЕТРЫ
# ============================================================

REQUIRED_PARAMETERS = {
    "open_application": ["app_name"],
    "close_application": ["app_name"],
    "open_website": ["url"],
    "search_web": ["query"],
    "search_youtube": ["query"],
    "set_volume": ["level"],
    "get_weather": ["city"],
    "translate_text": ["text", "target_lang"],
    "set_reminder": ["seconds", "text"],
}


# ============================================================
# МОДЕЛИ ДАННЫХ
# ============================================================

@dataclass
class PlanStep:
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class Plan:
    user_goal: str
    steps: list[PlanStep]
    final_response: bool = True


# ============================================================
# ОШИБКИ
# ============================================================

class PlannerError(Exception):
    """Ошибка создания или проверки плана."""
    pass


# ============================================================
# PLANNER
# ============================================================

class Planner:
    """
    Планировщик Jarvis v2.

    ВАЖНО:
    Planner понимает запрос и составляет план,
    но не имеет права выполнять его.
    """

    MAX_STEPS = 10

    def __init__(self, llm: LLMClient):
        self.llm = llm

    # --------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------

    def create_plan(self, user_text: str) -> Plan:
        """
        Создать и проверить план для пользовательского запроса.
        """

        if not isinstance(user_text, str):
            raise PlannerError(
                "Запрос пользователя должен быть строкой."
            )

        user_text = user_text.strip()

        if not user_text:
            raise PlannerError(
                "Получен пустой запрос пользователя."
            )

        prompt = self._build_prompt(user_text)

        try:
            result = self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты Planner персонального компьютерного "
                            "ассистента Jarvis. "
                            "Твоя задача только понять запрос пользователя "
                            "и составить точный JSON-план. "
                            "Ты ничего самостоятельно не выполняешь."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0,
                max_tokens=800,
            )

        except LLMError as exc:
            raise PlannerError(
                f"Ошибка LLM при создании плана: {exc}"
            ) from exc

        try:
            response = result["response"]
            text = response.choices[0].message.content or ""

        except Exception as exc:
            raise PlannerError(
                "LLM вернула ответ неизвестного формата."
            ) from exc

        data = self._extract_json(text)

        return self._validate_plan(
            data=data,
            original_request=user_text,
        )

    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    def _build_prompt(self, user_text: str) -> str:
        """
        Формирование промпта.

        Здесь специально НЕ используется f-string для большого
        шаблона, поскольку JSON содержит фигурные скобки.
        """

        actions = ", ".join(
            sorted(ALLOWED_ACTIONS)
        )

        template = """
ЗАПРОС ПОЛЬЗОВАТЕЛЯ:

__USER_TEXT__


ТВОЯ ЗАДАЧА:

Преобразуй запрос пользователя в точный последовательный план.


ДОСТУПНЫЕ ДЕЙСТВИЯ:

__ACTIONS__


==================================================
ОПИСАНИЕ ВАЖНЫХ ДЕЙСТВИЙ
==================================================

answer

Используется, когда пользователю нужен обычный ответ,
объяснение или разговор и не требуется действие на компьютере.


self_diagnose

Проверить:
- состояние агента;
- ошибки;
- метрики;
- стабильность компонентов.

Это действие НЕ изменяет код.


propose_improvement

Подготовить предложение по улучшению агента.

Это действие:
- анализирует возможное улучшение;
- может подготовить проект изменений;
- НЕ означает, что изменение уже применено.


backup_github

Создать резервную копию текущего проверенного состояния
проекта в GitHub.


quality_report

Получить показатели качества работы агента.


==================================================
ГЛАВНЫЕ ПРАВИЛА
==================================================

1.

НЕ ТЕРЯЙ ЧАСТИ СОСТАВНОГО ЗАПРОСА.

Если пользователь просит несколько вещей,
создай несколько отдельных шагов.


Пример:

Пользователь:

проверь себя и сделай бэкап

План:

self_diagnose
backup_github


--------------------------------------------------

2.

Если пользователь говорит:

улучши себя

это НЕ означает немедленное изменение исходного кода.

План должен включать:

self_diagnose
propose_improvement


--------------------------------------------------

3.

Если пользователь говорит:

улучши себя и сделай бэкап

план должен включать:

self_diagnose
propose_improvement
backup_github


--------------------------------------------------

4.

ОБЯЗАТЕЛЬНО извлекай параметры непосредственно
из текста пользователя.


Пример:

Пользователь:

открой блокнот

Шаг:

{
  "action": "open_application",
  "parameters": {
    "app_name": "блокнот"
  },
  "reason": "Открыть запрошенное приложение"
}


--------------------------------------------------

Пример:

Пользователь:

закрой калькулятор

Шаг:

{
  "action": "close_application",
  "parameters": {
    "app_name": "калькулятор"
  },
  "reason": "Закрыть запрошенное приложение"
}


--------------------------------------------------

Пример:

Пользователь:

покажи погоду в Варшаве

Шаг:

{
  "action": "get_weather",
  "parameters": {
    "city": "Варшава"
  },
  "reason": "Получить текущую погоду"
}


--------------------------------------------------

Пример:

Пользователь:

поставь громкость на 35 процентов

Шаг:

{
  "action": "set_volume",
  "parameters": {
    "level": 35
  },
  "reason": "Изменить громкость компьютера"
}


--------------------------------------------------

Пример:

Пользователь:

найди в интернете официальный сайт Python

Шаг:

{
  "action": "search_web",
  "parameters": {
    "query": "официальный сайт Python"
  },
  "reason": "Найти запрошенную информацию"
}


--------------------------------------------------

Пример:

Пользователь:

открой калькулятор и потом блокнот

План должен содержать ДВА действия:

{
  "action": "open_application",
  "parameters": {
    "app_name": "калькулятор"
  },
  "reason": "Открыть калькулятор"
}

{
  "action": "open_application",
  "parameters": {
    "app_name": "блокнот"
  },
  "reason": "Затем открыть блокнот"
}


--------------------------------------------------

5.

НЕ оставляй обязательный параметр пустым,
если его значение присутствует в запросе пользователя.


--------------------------------------------------

6.

parameters ВСЕГДА должен быть JSON-объектом.

Правильно:

"parameters": {}

Неправильно:

"parameters": null


--------------------------------------------------

7.

Не создавай действий, которых нет в списке
ДОСТУПНЫЕ ДЕЙСТВИЯ.


--------------------------------------------------

8.

Не утверждай, что улучшение было применено,
если выполнялось только:

propose_improvement


--------------------------------------------------

9.

Каждое независимое действие пользователя должно
стать отдельным элементом массива steps.


--------------------------------------------------

10.

Сохраняй естественный порядок действий пользователя.

Например:

открой блокнот, потом скажи время

означает:

1. open_application
2. get_datetime


--------------------------------------------------

11.

Если пользователь просто задаёт вопрос:

объясни как работает процессор

используй:

answer


--------------------------------------------------

12.

final_response должен быть true,
если после выполнения пользователю необходимо сообщить результат.

По умолчанию используй true.


==================================================
ФОРМАТ ОТВЕТА
==================================================

Верни ТОЛЬКО один JSON-объект.

НЕ используй Markdown.

НЕ используй ```.

НЕ добавляй текст до JSON или после JSON.


Формат:

{
  "user_goal": "краткое описание цели пользователя",
  "steps": [
    {
      "action": "имя_действия",
      "parameters": {},
      "reason": "краткая причина"
    }
  ],
  "final_response": true
}
"""

        return (
            template
            .replace("__USER_TEXT__", user_text)
            .replace("__ACTIONS__", actions)
        )

    # --------------------------------------------------------
    # JSON PARSER
    # --------------------------------------------------------

    def _extract_json(self, text: str) -> dict:
        """
        Безопасно извлечь JSON из ответа LLM.
        """

        if not isinstance(text, str):
            raise PlannerError(
                "Planner получил не текстовый ответ."
            )

        text = text.strip()

        if not text:
            raise PlannerError(
                "Planner вернул пустой ответ."
            )

        # На случай если модель всё-таки использовала Markdown.
        if text.startswith("```"):
            text = re.sub(
                r"^```(?:json)?\s*",
                "",
                text,
                flags=re.IGNORECASE,
            )

            text = re.sub(
                r"\s*```$",
                "",
                text,
            )

            text = text.strip()

        # Сначала пробуем разобрать весь ответ.
        try:
            data = json.loads(text)

            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            pass

        # Резервный вариант:
        # ищем внешний JSON-объект.
        start = text.find("{")
        end = text.rfind("}")

        if (
            start == -1
            or end == -1
            or end <= start
        ):
            raise PlannerError(
                "Planner не вернул JSON. "
                f"Начало ответа: {text[:300]}"
            )

        json_text = text[start:end + 1]

        try:
            data = json.loads(json_text)

        except json.JSONDecodeError as exc:
            raise PlannerError(
                f"Некорректный JSON Planner: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise PlannerError(
                "Корневой JSON Planner должен быть объектом."
            )

        return data

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def _validate_plan(
        self,
        data: dict,
        original_request: str,
    ) -> Plan:
        """
        Программная проверка плана.

        Даже если LLM ошиблась, некорректный план не должен
        попасть в Executor.
        """

        if not isinstance(data, dict):
            raise PlannerError(
                "План должен быть JSON-объектом."
            )

        raw_steps = data.get("steps")

        if not isinstance(raw_steps, list):
            raise PlannerError(
                "В плане отсутствует корректный список steps."
            )

        # Пустой план заменяем безопасным обычным ответом.
        if len(raw_steps) == 0:
            raw_steps = [
                {
                    "action": "answer",
                    "parameters": {},
                    "reason": "Ответить пользователю",
                }
            ]

        if len(raw_steps) > self.MAX_STEPS:
            raise PlannerError(
                "Planner создал слишком много шагов: "
                f"{len(raw_steps)}."
            )

        steps: list[PlanStep] = []

        for number, raw in enumerate(
            raw_steps,
            start=1,
        ):

            if not isinstance(raw, dict):
                raise PlannerError(
                    f"Шаг {number} имеет неверный формат."
                )

            # ---------------- ACTION ----------------

            action = str(
                raw.get("action", "")
            ).strip()

            if not action:
                raise PlannerError(
                    f"В шаге {number} отсутствует action."
                )

            if action not in ALLOWED_ACTIONS:
                raise PlannerError(
                    f"Planner предложил запрещённое действие: "
                    f"{action}"
                )

            # ---------------- PARAMETERS ----------------

            parameters = raw.get(
                "parameters",
                {},
            )

            if parameters is None:
                parameters = {}

            if not isinstance(parameters, dict):
                raise PlannerError(
                    f"parameters шага {number} "
                    "должен быть JSON-объектом."
                )

            # Удаляем мусор вроде:
            # {"": ""}
            # {"": " "}
            cleaned_parameters = {}

            for key, value in parameters.items():

                clean_key = str(key).strip()

                if not clean_key:
                    continue

                if value is None:
                    continue

                if (
                    isinstance(value, str)
                    and not value.strip()
                ):
                    continue

                cleaned_parameters[
                    clean_key
                ] = value

            parameters = cleaned_parameters

            # ---------------- REQUIRED PARAMETERS ----------------

            required = REQUIRED_PARAMETERS.get(
                action,
                [],
            )

            missing = []

            for name in required:

                if name not in parameters:
                    missing.append(name)
                    continue

                value = parameters[name]

                if value is None:
                    missing.append(name)
                    continue

                if (
                    isinstance(value, str)
                    and not value.strip()
                ):
                    missing.append(name)

            if missing:
                raise PlannerError(
                    f"Шаг {number} ({action}) потерял "
                    "обязательные параметры: "
                    f"{', '.join(missing)}"
                )

            # ---------------- NORMALIZATION ----------------

            parameters = self._normalize_parameters(
                action=action,
                parameters=parameters,
                step_number=number,
            )

            # ---------------- REASON ----------------

            reason = str(
                raw.get("reason", "")
            ).strip()

            # ---------------- CREATE STEP ----------------

            steps.append(
                PlanStep(
                    action=action,
                    parameters=parameters,
                    reason=reason,
                )
            )

        # ---------------- GOAL ----------------

        goal = str(
            data.get("user_goal")
            or original_request
        ).strip()

        # ---------------- FINAL RESPONSE ----------------

        final_response = data.get(
            "final_response",
            True,
        )

        if not isinstance(
            final_response,
            bool,
        ):
            final_response = True

        return Plan(
            user_goal=goal,
            steps=steps,
            final_response=final_response,
        )

    # --------------------------------------------------------
    # PARAMETER NORMALIZATION
    # --------------------------------------------------------

    def _normalize_parameters(
        self,
        action: str,
        parameters: dict[str, Any],
        step_number: int,
    ) -> dict[str, Any]:
        """
        Приводит параметры к ожидаемым типам.
        """

        result = dict(parameters)

        # Громкость должна быть целым числом 0..100.
        if action == "set_volume":

            try:
                level = int(
                    result["level"]
                )

            except (
                TypeError,
                ValueError,
                KeyError,
            ) as exc:
                raise PlannerError(
                    f"Шаг {step_number}: "
                    "громкость должна быть числом."
                ) from exc

            if not 0 <= level <= 100:
                raise PlannerError(
                    f"Шаг {step_number}: "
                    "громкость должна быть от 0 до 100."
                )

            result["level"] = level

        # Таймер должен быть положительным.
        if action == "set_reminder":

            try:
                seconds = int(
                    result["seconds"]
                )

            except (
                TypeError,
                ValueError,
                KeyError,
            ) as exc:
                raise PlannerError(
                    f"Шаг {step_number}: "
                    "seconds должен быть числом."
                ) from exc

            if seconds <= 0:
                raise PlannerError(
                    f"Шаг {step_number}: "
                    "таймер должен быть больше нуля."
                )

            result["seconds"] = seconds

        return result