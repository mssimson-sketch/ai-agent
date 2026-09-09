"""
Jarvis v2 - Permission Manager

Отвечает за безопасность действий ДО их выполнения.

Уровни:
SAFE
    Можно выполнять автоматически.

CONTROLLED
    Можно выполнять автоматически только после
    программных проверок.

CONFIRM
    Нужно явное подтверждение пользователя.

STAGED
    Изменения разрешены только через staging/tests/rollback.

DENY
    Автономное выполнение запрещено.
"""

from dataclasses import dataclass
from enum import Enum

from core.planner import Plan, PlanStep


# ============================================================
# PERMISSION LEVEL
# ============================================================

class PermissionLevel(str, Enum):
    SAFE = "safe"
    CONTROLLED = "controlled"
    CONFIRM = "confirm"
    STAGED = "staged"
    DENY = "deny"


# ============================================================
# DECISION
# ============================================================

@dataclass
class PermissionDecision:
    allowed: bool
    level: PermissionLevel
    action: str
    reason: str
    requires_confirmation: bool = False


# ============================================================
# ACTION POLICY
# ============================================================

ACTION_POLICIES = {

    # ---------------- DIALOG ----------------

    "answer":
        PermissionLevel.SAFE,

    # ---------------- INFORMATION ----------------

    "get_datetime":
        PermissionLevel.SAFE,

    "get_system_info":
        PermissionLevel.SAFE,

    "get_weather":
        PermissionLevel.SAFE,

    "get_news":
        PermissionLevel.SAFE,

    "translate_text":
        PermissionLevel.SAFE,

    "quality_report":
        PermissionLevel.SAFE,

    "self_diagnose":
        PermissionLevel.SAFE,

    "propose_improvement":
        PermissionLevel.SAFE,

    # ---------------- BROWSER ----------------

    "search_web":
        PermissionLevel.SAFE,

    "search_youtube":
        PermissionLevel.SAFE,

    "open_website":
        PermissionLevel.CONTROLLED,

    # ---------------- COMPUTER ----------------

    "open_application":
        PermissionLevel.CONTROLLED,

    "close_application":
        PermissionLevel.CONTROLLED,

    "set_volume":
        PermissionLevel.CONTROLLED,

    "screenshot":
        PermissionLevel.CONTROLLED,

    "set_reminder":
        PermissionLevel.CONTROLLED,

    # ---------------- CLOUD ----------------

    "backup_github":
        PermissionLevel.CONTROLLED,

    # ---------------- FUTURE SELF UPDATE ----------------

    "apply_improvement":
        PermissionLevel.STAGED,

    "install_package":
        PermissionLevel.CONFIRM,

    "write_file":
        PermissionLevel.CONFIRM,

    "delete_file":
        PermissionLevel.CONFIRM,

    "run_shell":
        PermissionLevel.CONFIRM,

    "shutdown":
        PermissionLevel.CONFIRM,

    "restart":
        PermissionLevel.CONFIRM,

    # Никогда не даём LLM прямой доступ
    # к секретам.
    "read_secrets":
        PermissionLevel.DENY,

    "export_secrets":
        PermissionLevel.DENY,
}


# ============================================================
# MANAGER
# ============================================================

class PermissionManager:
    """
    Проверяет план до передачи Executor.
    """

    def __init__(self):
        pass

    # --------------------------------------------------------
    # SINGLE STEP
    # --------------------------------------------------------

    def check_step(
        self,
        step: PlanStep,
    ) -> PermissionDecision:

        action = step.action

        level = ACTION_POLICIES.get(
            action,
            PermissionLevel.DENY,
        )

        # ---------------- SAFE ----------------

        if level == PermissionLevel.SAFE:

            return PermissionDecision(
                allowed=True,
                level=level,
                action=action,
                reason=(
                    "Информационное или "
                    "неизменяющее действие."
                ),
                requires_confirmation=False,
            )

        # ---------------- CONTROLLED ----------------

        if level == PermissionLevel.CONTROLLED:

            result = self._check_controlled(
                step
            )

            return result

        # ---------------- CONFIRM ----------------

        if level == PermissionLevel.CONFIRM:

            return PermissionDecision(
                allowed=False,
                level=level,
                action=action,
                reason=(
                    "Действие может изменить состояние "
                    "компьютера и требует подтверждения."
                ),
                requires_confirmation=True,
            )

        # ---------------- STAGED ----------------

        if level == PermissionLevel.STAGED:

            return PermissionDecision(
                allowed=False,
                level=level,
                action=action,
                reason=(
                    "Изменение ядра агента разрешено "
                    "только через staging, тесты "
                    "и автоматический rollback."
                ),
                requires_confirmation=False,
            )

        # ---------------- DENY ----------------

        return PermissionDecision(
            allowed=False,
            level=PermissionLevel.DENY,
            action=action,
            reason=(
                "Автономное выполнение этого "
                "действия запрещено."
            ),
            requires_confirmation=False,
        )

    # --------------------------------------------------------
    # COMPLETE PLAN
    # --------------------------------------------------------

    def check_plan(
        self,
        plan: Plan,
    ) -> list[PermissionDecision]:

        decisions = []

        for step in plan.steps:

            decisions.append(
                self.check_step(step)
            )

        return decisions

    # --------------------------------------------------------
    # CONTROLLED ACTIONS
    # --------------------------------------------------------

    def _check_controlled(
        self,
        step: PlanStep,
    ) -> PermissionDecision:

        action = step.action

        params = step.parameters

        # ====================================================
        # OPEN APPLICATION
        # ====================================================

        if action == "open_application":

            app_name = str(
                params.get(
                    "app_name",
                    ""
                )
            ).strip()

            if not app_name:

                return PermissionDecision(
                    allowed=False,
                    level=PermissionLevel.CONTROLLED,
                    action=action,
                    reason=(
                        "Не указано приложение."
                    ),
                )

            return self._controlled_ok(
                action,
                "Приложение можно открыть.",
            )

        # ====================================================
        # CLOSE APPLICATION
        # ====================================================

        if action == "close_application":

            app_name = str(
                params.get(
                    "app_name",
                    ""
                )
            ).strip()

            if not app_name:

                return PermissionDecision(
                    allowed=False,
                    level=PermissionLevel.CONTROLLED,
                    action=action,
                    reason=(
                        "Не указано приложение."
                    ),
                )

            return self._controlled_ok(
                action,
                "Приложение можно закрыть.",
            )

        # ====================================================
        # VOLUME
        # ====================================================

        if action == "set_volume":

            try:
                level = int(
                    params.get(
                        "level"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                return PermissionDecision(
                    allowed=False,
                    level=PermissionLevel.CONTROLLED,
                    action=action,
                    reason=(
                        "Некорректный уровень громкости."
                    ),
                )

            if not 0 <= level <= 100:

                return PermissionDecision(
                    allowed=False,
                    level=PermissionLevel.CONTROLLED,
                    action=action,
                    reason=(
                        "Громкость должна быть "
                        "от 0 до 100."
                    ),
                )

            return self._controlled_ok(
                action,
                "Громкость прошла проверку.",
            )

        # ====================================================
        # WEBSITE
        # ====================================================

        if action == "open_website":

            url = str(
                params.get(
                    "url",
                    ""
                )
            ).strip().lower()

            if not url:

                return PermissionDecision(
                    allowed=False,
                    level=PermissionLevel.CONTROLLED,
                    action=action,
                    reason="URL отсутствует.",
                )

            # Не разрешаем опасные схемы.
            blocked_prefixes = (
                "file:",
                "javascript:",
                "data:",
                "powershell:",
                "cmd:",
            )

            if url.startswith(
                blocked_prefixes
            ):

                return PermissionDecision(
                    allowed=False,
                    level=PermissionLevel.CONTROLLED,
                    action=action,
                    reason=(
                        "Опасная схема URL заблокирована."
                    ),
                )

            return self._controlled_ok(
                action,
                "URL прошёл проверку.",
            )

        # ====================================================
        # REMINDER
        # ====================================================

        if action == "set_reminder":

            try:
                seconds = int(
                    params.get(
                        "seconds"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                return PermissionDecision(
                    allowed=False,
                    level=PermissionLevel.CONTROLLED,
                    action=action,
                    reason=(
                        "Некорректное время напоминания."
                    ),
                )

            if seconds <= 0:

                return PermissionDecision(
                    allowed=False,
                    level=PermissionLevel.CONTROLLED,
                    action=action,
                    reason=(
                        "Время напоминания должно "
                        "быть больше нуля."
                    ),
                )

            return self._controlled_ok(
                action,
                "Напоминание прошло проверку.",
            )

        # ====================================================
        # GITHUB BACKUP
        # ====================================================

        if action == "backup_github":

            return self._controlled_ok(
                action,
                (
                    "Резервное копирование "
                    "разрешено."
                ),
            )

        # ====================================================
        # SCREENSHOT
        # ====================================================

        if action == "screenshot":

            return self._controlled_ok(
                action,
                "Создание снимка экрана разрешено.",
            )

        # Нераспознанное controlled-действие
        # не выполняем автоматически.

        return PermissionDecision(
            allowed=False,
            level=PermissionLevel.CONTROLLED,
            action=action,
            reason=(
                "Для controlled-действия "
                "не определена проверка."
            ),
        )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def _controlled_ok(
        self,
        action: str,
        reason: str,
    ) -> PermissionDecision:

        return PermissionDecision(
            allowed=True,
            level=PermissionLevel.CONTROLLED,
            action=action,
            reason=reason,
            requires_confirmation=False,
        )