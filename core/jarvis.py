"""
Jarvis v2 - Core Orchestrator

Единая точка обработки пользовательского запроса.

Pipeline:

User
 ↓
Planner
 ↓
Permissions
 ↓
Executor
 ↓
ExecutionReport
 ↓
SpeechFormatter
 ↓
display_text / speech_text

Этот модуль:
- не работает с микрофоном;
- не занимается TTS;
- не изменяет собственный код;
- не читает .env напрямую.
"""

from dataclasses import dataclass, field

from core.llm import LLMClient
from core.planner import Planner, Plan, PlanStep
from core.permissions import (
    PermissionManager,
    PermissionDecision,
)
from core.executor import (
    Executor,
    ExecutionReport,
    StepResult,
)
from core.speech_formatter import SpeechFormatter
from tools.computer import SafeComputerTools


# ============================================================
# RESULT
# ============================================================

@dataclass
class JarvisResponse:
    success: bool
    display_text: str
    speech_text: str

    plan: Plan | None = None
    report: ExecutionReport | None = None

    permission_decisions: list[
        PermissionDecision
    ] = field(default_factory=list)

    needs_confirmation: bool = False
    confirmation_actions: list[str] = field(
        default_factory=list
    )


# ============================================================
# CORE
# ============================================================

class JarvisCore:
    """
    Главный программный конвейер Jarvis v2.
    """

    def __init__(
        self,
        github_manager=None,
        quality_control=None,
    ):
        # Один LLMClient на всё ядро.
        self.llm = LLMClient()

        self.planner = Planner(
            self.llm
        )

        self.permissions = (
            PermissionManager()
        )

        self.tools = (
            SafeComputerTools()
        )

        self.executor = Executor(
            actions=self.tools,
            llm=self.llm,
            github_manager=github_manager,
            quality_control=quality_control,
        )

        self.speech_formatter = (
            SpeechFormatter(
                self.llm
            )
        )

    # ========================================================
    # MAIN API
    # ========================================================

    def process(
        self,
        user_text: str,
    ) -> JarvisResponse:
        """
        Полностью обработать запрос пользователя.
        """

        if not isinstance(
            user_text,
            str,
        ):
            return self._error_response(
                "Запрос должен быть текстом."
            )

        user_text = user_text.strip()

        if not user_text:
            return self._error_response(
                "Я не услышал команду."
            )

        # ----------------------------------------------------
        # 1. PLAN
        # ----------------------------------------------------

        try:
            plan = (
                self.planner.create_plan(
                    user_text
                )
            )

        except Exception as exc:
            return self._error_response(
                "Не удалось корректно "
                "понять запрос.",
                technical_error=str(exc),
            )

        # ----------------------------------------------------
        # 2. PERMISSIONS
        # ----------------------------------------------------

        decisions = (
            self.permissions.check_plan(
                plan
            )
        )

        confirmation = [
            d
            for d in decisions
            if d.requires_confirmation
        ]

        denied = [
            d
            for d in decisions
            if (
                not d.allowed
                and not d.requires_confirmation
            )
        ]

        # -----------------------------------------------
        # Требуется подтверждение.
        # Ничего пока не выполняем.
        # -----------------------------------------------

        if confirmation:

            names = [
                d.action
                for d in confirmation
            ]

            display = (
                "Для выполнения части запроса "
                "нужно ваше подтверждение: "
                + ", ".join(names)
                + "."
            )

            return JarvisResponse(
                success=False,
                display_text=display,
                speech_text=display,
                plan=plan,
                report=None,
                permission_decisions=decisions,
                needs_confirmation=True,
                confirmation_actions=names,
            )

        # -----------------------------------------------
        # Запрещённое действие.
        # -----------------------------------------------

        if denied:

            reasons = [
                d.reason
                for d in denied
            ]

            display = (
                "Я не стал выполнять часть запроса. "
                + " ".join(reasons)
            )

            return JarvisResponse(
                success=False,
                display_text=display,
                speech_text=display,
                plan=plan,
                report=None,
                permission_decisions=decisions,
            )

        # ----------------------------------------------------
        # 3. EXECUTION
        # ----------------------------------------------------

        try:
            report = (
                self.executor.execute(
                    plan
                )
            )

        except Exception as exc:
            return self._error_response(
                "Не удалось выполнить план.",
                technical_error=str(exc),
                plan=plan,
                decisions=decisions,
            )

        # ----------------------------------------------------
        # 4. NORMAL ANSWER
        # ----------------------------------------------------
        #
        # Если план содержит action=answer,
        # Executor намеренно ничего не придумывает.
        #
        # Здесь создаём содержательный ответ отдельно.
        # ----------------------------------------------------

        answer_text = self._generate_answer_if_needed(
            user_text=user_text,
            plan=plan,
            report=report,
        )

        # ----------------------------------------------------
        # 5. SPEECH FORMATTER
        # ----------------------------------------------------

        try:
            formatted = (
                self.speech_formatter.format(
                    report=report,
                    original_request=user_text,
                )
            )

            display_text = (
                formatted["display_text"]
            )

            speech_text = (
                formatted["speech_text"]
            )

        except Exception as exc:

            print(
                "[JarvisCore] SpeechFormatter "
                f"fallback: {exc}"
            )

            display_text = (
                self._local_report_text(
                    report
                )
            )

            speech_text = display_text

        # ----------------------------------------------------
        # 6. MERGE NORMAL ANSWER
        # ----------------------------------------------------

        if answer_text:

            # Если были только answer-шаги,
            # техническое "требуется ответ"
            # пользователю не показываем.

            real_actions = [
                step
                for step in plan.steps
                if step.action != "answer"
            ]

            if not real_actions:

                display_text = answer_text
                speech_text = answer_text

            else:

                if display_text:
                    display_text = (
                        display_text.rstrip()
                        + " "
                        + answer_text
                    )

                else:
                    display_text = answer_text

                if speech_text:
                    speech_text = (
                        speech_text.rstrip()
                        + " "
                        + answer_text
                    )

                else:
                    speech_text = answer_text

        # ----------------------------------------------------
        # 7. FINAL GUARANTEE
        # ----------------------------------------------------

        if not display_text.strip():
            display_text = (
                "Задача обработана."
            )

        if not speech_text.strip():
            speech_text = display_text

        return JarvisResponse(
            success=report.success,
            display_text=display_text,
            speech_text=speech_text,
            plan=plan,
            report=report,
            permission_decisions=decisions,
        )

    # ========================================================
    # NORMAL ANSWER
    # ========================================================

    def _generate_answer_if_needed(
        self,
        user_text: str,
        plan: Plan,
        report: ExecutionReport,
    ) -> str:
        """
        Генерирует обычный разговорный ответ,
        только если Planner действительно добавил answer.
        """

        answer_steps = [
            step
            for step in plan.steps
            if step.action == "answer"
        ]

        if not answer_steps:
            return ""

        facts = []

        for result in report.results:

            if (
                result.action != "answer"
                and result.success
            ):
                facts.append(
                    {
                        "action":
                            result.action,
                        "summary":
                            result.summary,
                        "data":
                            result.data,
                    }
                )

        prompt = """
Ты — Джарвис, персональный русскоязычный
голосовой ассистент.

Ответь на вопрос пользователя естественно
и по существу.

Если тебе переданы результаты уже выполненных
действий, учитывай их.

Не утверждай, что действие выполнено,
если этого нет среди подтверждённых результатов.

Не выдумывай факты о состоянии компьютера.

Не используй Markdown без необходимости.

Для голосового общения предпочитай короткий,
содержательный ответ.
"""

        content = (
            "Запрос пользователя:\n"
            + user_text
            + "\n\n"
            + "Подтверждённые результаты "
            + "выполненных действий:\n"
            + str(facts)
        )

        try:
            result = self.llm.chat(
                messages=[
                    {
                        "role":
                            "system",
                        "content":
                            prompt,
                    },
                    {
                        "role":
                            "user",
                        "content":
                            content,
                    },
                ],
                temperature=0.3,
                max_tokens=350,
            )

            text = (
                result["response"]
                .choices[0]
                .message
                .content
                or ""
            ).strip()

            return text

        except Exception as exc:

            print(
                "[JarvisCore] answer fallback: "
                f"{exc}"
            )

            return ""

    # ========================================================
    # LOCAL FALLBACK
    # ========================================================

    def _local_report_text(
        self,
        report: ExecutionReport,
    ) -> str:

        messages = []

        for result in report.results:

            if result.success:

                if (
                    result.action
                    != "answer"
                ):
                    messages.append(
                        result.summary
                    )

            else:

                messages.append(
                    result.summary
                )

        if not messages:

            if report.success:
                return (
                    "Задача выполнена."
                )

            return (
                "Задачу выполнить "
                "полностью не удалось."
            )

        return " ".join(messages)

    # ========================================================
    # ERROR
    # ========================================================

    def _error_response(
        self,
        user_message: str,
        technical_error: str | None = None,
        plan: Plan | None = None,
        decisions=None,
    ) -> JarvisResponse:

        if technical_error:
            print(
                "[JarvisCore ERROR] "
                + technical_error
            )

        return JarvisResponse(
            success=False,
            display_text=user_message,
            speech_text=user_message,
            plan=plan,
            report=None,
            permission_decisions=(
                decisions or []
            ),
        )