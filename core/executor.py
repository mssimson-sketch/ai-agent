"""
Jarvis v2 - Executor

Executor получает УЖЕ ПРОВЕРЕННЫЙ Plan от Planner.

Его задачи:
1. Выполнять шаги строго по порядку.
2. Фиксировать реальный результат каждого шага.
3. Не придумывать успешность.
4. Изолировать ошибку одного шага от остальных.
5. Возвращать структурированный ExecutionReport.

Executor НЕ отвечает пользователю голосом.
Executor НЕ изменяет собственный код агента.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from core.llm import LLMClient
from core.planner import Plan, PlanStep


# ============================================================
# RESULT MODELS
# ============================================================

@dataclass
class StepResult:
    step_number: int
    action: str
    success: bool

    summary: str = ""
    data: Any = None
    error: str | None = None

    started_at: float = 0.0
    finished_at: float = 0.0
    duration: float = 0.0


@dataclass
class ExecutionReport:
    user_goal: str
    success: bool

    results: list[StepResult] = field(
        default_factory=list
    )

    started_at: float = 0.0
    finished_at: float = 0.0
    duration: float = 0.0


# ============================================================
# EXECUTOR ERROR
# ============================================================

class ExecutorError(Exception):
    pass


# ============================================================
# EXECUTOR
# ============================================================

class Executor:
    """
    Центральный исполнитель Jarvis v2.
    """

    def __init__(
        self,
        actions,
        llm: LLMClient,
        github_manager=None,
        quality_control=None,
    ):
        self.actions = actions
        self.llm = llm

        self.github = github_manager
        self.quality = quality_control

    # --------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------

    def execute(
        self,
        plan: Plan,
    ) -> ExecutionReport:
        """
        Выполнить весь план по порядку.
        """

        if not isinstance(plan, Plan):
            raise ExecutorError(
                "Executor получил объект, "
                "который не является Plan."
            )

        report_started = time.monotonic()

        results: list[StepResult] = []

        for number, step in enumerate(
            plan.steps,
            start=1,
        ):
            result = self._execute_step(
                step_number=number,
                step=step,
            )

            results.append(result)

        report_finished = time.monotonic()

        # План успешен только если успешны ВСЕ
        # реальные шаги.
        overall_success = all(
            result.success
            for result in results
        )

        return ExecutionReport(
            user_goal=plan.user_goal,
            success=overall_success,
            results=results,
            started_at=report_started,
            finished_at=report_finished,
            duration=(
                report_finished
                - report_started
            ),
        )

    # --------------------------------------------------------
    # STEP EXECUTION
    # --------------------------------------------------------

    def _execute_step(
        self,
        step_number: int,
        step: PlanStep,
    ) -> StepResult:

        started = time.monotonic()

        try:
            handler = self._get_handler(
                step.action
            )

            if handler is None:
                raise ExecutorError(
                    f"Нет обработчика действия "
                    f"{step.action}"
                )

            result = handler(
                step.parameters
            )

            finished = time.monotonic()

            return StepResult(
                step_number=step_number,
                action=step.action,
                success=True,
                summary=result.get(
                    "summary",
                    "Выполнено.",
                ),
                data=result.get("data"),
                error=None,
                started_at=started,
                finished_at=finished,
                duration=finished - started,
            )

        except Exception as exc:
            finished = time.monotonic()

            return StepResult(
                step_number=step_number,
                action=step.action,
                success=False,
                summary=(
                    f"Не удалось выполнить "
                    f"{step.action}."
                ),
                data=None,
                error=str(exc),
                started_at=started,
                finished_at=finished,
                duration=finished - started,
            )

    # --------------------------------------------------------
    # ROUTER
    # --------------------------------------------------------

    def _get_handler(
        self,
        action: str,
    ):

        handlers = {
            # Диалог
            "answer":
                self._handle_answer,

            # Агент
            "self_diagnose":
                self._handle_self_diagnose,

            "propose_improvement":
                self._handle_propose_improvement,

            "quality_report":
                self._handle_quality_report,

            "backup_github":
                self._handle_backup_github,

            # Компьютер
            "open_application":
                self._handle_open_application,

            "close_application":
                self._handle_close_application,

            "get_system_info":
                self._handle_get_system_info,

            "get_datetime":
                self._handle_get_datetime,

            "screenshot":
                self._handle_screenshot,

            "set_volume":
                self._handle_set_volume,

            # Интернет
            "open_website":
                self._handle_open_website,

            "search_web":
                self._handle_search_web,

            "search_youtube":
                self._handle_search_youtube,

            # Информация
            "get_weather":
                self._handle_get_weather,

            "get_news":
                self._handle_get_news,

            "translate_text":
                self._handle_translate_text,

            # Органайзер
            "set_reminder":
                self._handle_set_reminder,
        }

        return handlers.get(action)

    # ========================================================
    # DIALOG
    # ========================================================

    def _handle_answer(
        self,
        params: dict,
    ) -> dict:
        """
        На этом этапе answer означает:
        финальный SpeechFormatter должен сформировать
        ответ на исходный запрос.

        Executor не должен самостоятельно вести диалог.
        """

        return {
            "summary":
                "Требуется обычный ответ пользователю.",
            "data": {
                "type": "answer_required"
            },
        }

    # ========================================================
    # SELF DIAGNOSTICS
    # ========================================================

    def _handle_self_diagnose(
        self,
        params: dict,
    ) -> dict:

        diagnostic = {
            "llm": None,
            "quality": None,
        }

        # Проверка LLM.
        diagnostic["llm"] = (
            self.llm.health_report()
        )

        # Метрики качества.
        if self.quality is not None:
            try:
                diagnostic["quality"] = (
                    self.quality.get_quality_report()
                )
            except Exception as exc:
                diagnostic["quality"] = {
                    "error": str(exc)
                }

        return {
            "summary":
                "Самодиагностика агента завершена.",
            "data": diagnostic,
        }

    # ========================================================
    # IMPROVEMENT PROPOSAL
    # ========================================================

    def _handle_propose_improvement(
        self,
        params: dict,
    ) -> dict:
        """
        ВАЖНО:
        этот метод НЕ меняет код.

        Он только формирует предложение.
        """

        diagnostic_context = ""

        if self.quality is not None:
            try:
                diagnostic_context = str(
                    self.quality.get_quality_report()
                )
            except Exception:
                diagnostic_context = (
                    "Метрики качества недоступны."
                )

        messages = [
            {
                "role": "system",
                "content": (
                    "Ты инженер Jarvis v2. "
                    "Предлагай только конкретные и "
                    "проверяемые улучшения. "
                    "Не утверждай, что изменение уже "
                    "применено. "
                    "Ответ должен быть кратким."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Подготовь предложение по улучшению "
                    "агента на основе этих метрик:\n"
                    + diagnostic_context
                ),
            },
        ]

        llm_result = self.llm.chat(
            messages=messages,
            temperature=0.2,
            max_tokens=350,
        )

        text = (
            llm_result["response"]
            .choices[0]
            .message
            .content
            or ""
        ).strip()

        if not text:
            raise ExecutorError(
                "LLM не сформировала предложение "
                "по улучшению."
            )

        return {
            "summary":
                "Подготовлено предложение "
                "по улучшению агента.",
            "data": {
                "proposal": text,
                "applied": False,
            },
        }

    # ========================================================
    # QUALITY
    # ========================================================

    def _handle_quality_report(
        self,
        params: dict,
    ) -> dict:

        if self.quality is None:
            raise ExecutorError(
                "QualityControl не подключён."
            )

        report = (
            self.quality.get_quality_report()
        )

        return {
            "summary":
                "Отчёт о качестве получен.",
            "data": report,
        }

    # ========================================================
    # GITHUB
    # ========================================================

    def _handle_backup_github(
        self,
        params: dict,
    ) -> dict:

        if self.github is None:
            raise ExecutorError(
                "GitHubManager не подключён."
            )

        result = (
            self.github.backup_to_github()
        )

        # Старый GitHubManager пока возвращает строку.
        text = str(result)

        # Не считаем ошибку успехом только потому,
        # что функция не выбросила exception.
        bad_markers = (
            "ошибка",
            "forbidden",
            "failed",
            "0 файлов",
            "не удалось",
            "не подключ",
        )

        if any(
            marker in text.lower()
            for marker in bad_markers
        ):
            raise ExecutorError(text)

        return {
            "summary":
                "Резервная копия GitHub создана.",
            "data": {
                "raw_result": text,
            },
        }

    # ========================================================
    # COMPUTER
    # ========================================================

    def _handle_open_application(
        self,
        params: dict,
    ) -> dict:

        app_name = params["app_name"]

        result = self.actions.open_application(
            app_name
        )

        return {
            "summary":
                f"Приложение «{app_name}» открыто.",
            "data": {
                "application": app_name,
                "raw_result": str(result),
            },
        }

    def _handle_close_application(
        self,
        params: dict,
    ) -> dict:

        app_name = params["app_name"]

        result = self.actions.close_application(
            app_name
        )

        return {
            "summary":
                f"Приложение «{app_name}» закрыто.",
            "data": {
                "application": app_name,
                "raw_result": str(result),
            },
        }

    def _handle_get_system_info(
        self,
        params: dict,
    ) -> dict:

        result = (
            self.actions.get_system_info()
        )

        return {
            "summary":
                "Информация о состоянии компьютера получена.",
            "data": {
                "system_info": str(result),
            },
        }

    def _handle_get_datetime(
        self,
        params: dict,
    ) -> dict:

        result = (
            self.actions.get_datetime()
        )

        return {
            "summary":
                "Текущие дата и время получены.",
            "data": {
                "datetime": str(result),
            },
        }

    def _handle_screenshot(
        self,
        params: dict,
    ) -> dict:

        result = (
            self.actions.screenshot()
        )

        return {
            "summary":
                "Снимок экрана создан.",
            "data": {
                "raw_result": str(result),
            },
        }

    def _handle_set_volume(
        self,
        params: dict,
    ) -> dict:

        level = int(
            params["level"]
        )

        result = (
            self.actions.set_volume(level)
        )

        return {
            "summary":
                f"Громкость установлена на {level} процентов.",
            "data": {
                "level": level,
                "raw_result": str(result),
            },
        }

    # ========================================================
    # INTERNET
    # ========================================================

    def _handle_open_website(
        self,
        params: dict,
    ) -> dict:

        url = params["url"]

        result = (
            self.actions.open_website(url)
        )

        return {
            "summary":
                "Сайт открыт в браузере.",
            "data": {
                "url": url,
                "raw_result": str(result),
            },
        }

    def _handle_search_web(
        self,
        params: dict,
    ) -> dict:

        query = params["query"]

        # В старом actions.py функция называется
        # search_google.
        if hasattr(
            self.actions,
            "search_google",
        ):
            result = (
                self.actions.search_google(query)
            )

        else:
            raise ExecutorError(
                "Инструмент веб-поиска "
                "не реализован."
            )

        return {
            "summary":
                "Поиск в интернете открыт.",
            "data": {
                "query": query,
                "raw_result": str(result),
            },
        }

    def _handle_search_youtube(
        self,
        params: dict,
    ) -> dict:

        query = params["query"]

        result = (
            self.actions.search_youtube(query)
        )

        return {
            "summary":
                "Поиск на YouTube открыт.",
            "data": {
                "query": query,
                "raw_result": str(result),
            },
        }

    # ========================================================
    # INFORMATION
    # ========================================================

    def _handle_get_weather(
        self,
        params: dict,
    ) -> dict:

        city = params["city"]

        result = (
            self.actions.get_weather(city)
        )

        return {
            "summary":
                f"Погода для города {city} получена.",
            "data": {
                "city": city,
                "weather": str(result),
            },
        }

    def _handle_get_news(
        self,
        params: dict,
    ) -> dict:

        category = params.get(
            "category",
            "главное",
        )

        result = (
            self.actions.get_news(category)
        )

        return {
            "summary":
                "Свежие новости получены.",
            "data": {
                "category": category,
                "news": str(result),
            },
        }

    def _handle_translate_text(
        self,
        params: dict,
    ) -> dict:

        text = params["text"]
        target_lang = params["target_lang"]

        result = (
            self.actions.translate_text(
                text,
                target_lang,
            )
        )

        return {
            "summary":
                "Перевод выполнен.",
            "data": {
                "source_text": text,
                "target_lang": target_lang,
                "translation": str(result),
            },
        }

    # ========================================================
    # REMINDERS
    # ========================================================

    def _handle_set_reminder(
        self,
        params: dict,
    ) -> dict:

        seconds = int(
            params["seconds"]
        )

        text = params["text"]

        result = (
            self.actions.set_reminder(
                seconds,
                text,
            )
        )

        return {
            "summary":
                "Напоминание установлено.",
            "data": {
                "seconds": seconds,
                "text": text,
                "raw_result": str(result),
            },
        }