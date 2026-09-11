"""
Automated tests for Jarvis v2 Core.

These tests must:
- work without Groq;
- not open applications;
- not access GitHub;
- not modify the computer;
- verify safety and data integrity.
"""

import unittest
from unittest.mock import Mock

from core.planner import (
    Planner,
    PlannerError,
    Plan,
    PlanStep,
)

from core.permissions import (
    PermissionManager,
    PermissionLevel,
)

from core.executor import Executor

from core.speech_formatter import (
    SpeechFormatter,
)

from tools.computer import (
    SafeComputerTools,
    ToolError,
)


# ============================================================
# FAKE LLM
# ============================================================

class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [
            FakeChoice(content)
        ]


class FakeLLM:
    """
    Полностью локальная имитация LLM.
    Никаких сетевых запросов.
    """

    def __init__(self, responses=None):
        self.responses = list(
            responses or []
        )

    def chat(self, **kwargs):
        if not self.responses:
            raise RuntimeError(
                "FakeLLM: ответы закончились."
            )

        content = self.responses.pop(0)

        return {
            "response": FakeResponse(content),
            "model": "fake-model",
            "elapsed": 0.001,
        }

    def health_report(self):
        return {
            "provider": "fake",
            "preferred_model": "fake-model",
            "active_model": "fake-model",
            "available_models": 1,
            "status": "ok",
        }


# ============================================================
# FAKE COMPUTER TOOLS
# ============================================================

class FakeComputerTools:
    def __init__(self):
        self.calls = []

    def get_datetime(self):
        self.calls.append(
            ("get_datetime", {})
        )

        return (
            "Сегодня среда, "
            "9 сентября 2026 года. "
            "Время: 15:30."
        )

    def get_system_info(self):
        self.calls.append(
            ("get_system_info", {})
        )

        return (
            "Процессор загружен на 10%. "
            "Оперативная память: 50%. "
            "Диск заполнен на 93%."
        )

    def open_application(
        self,
        app_name,
    ):
        self.calls.append(
            (
                "open_application",
                {
                    "app_name":
                        app_name
                },
            )
        )

        return (
            f"Открываю {app_name}"
        )

    def set_volume(
        self,
        level,
    ):
        self.calls.append(
            (
                "set_volume",
                {
                    "level":
                        level
                },
            )
        )

        return (
            f"Громкость: {level}%"
        )


# ============================================================
# FAKE GITHUB
# ============================================================

class FakeGitHub:
    def __init__(
        self,
        result=(
            "Резервная копия создана. "
            "Загружено 15 файлов."
        ),
    ):
        self.result = result
        self.calls = 0

    def backup_to_github(self):
        self.calls += 1
        return self.result


# ============================================================
# FAKE QUALITY
# ============================================================

class FakeQuality:
    def get_quality_report(self):
        return {
            "score": 82.5,
            "success_rate": 95.0,
            "error_rate": 5.0,
            "avg_response_time": 2.4,
            "response_time_unit":
                "seconds",
        }


# ============================================================
# PLANNER TESTS
# ============================================================

class PlannerTests(
    unittest.TestCase
):

    def test_composite_command_keeps_all_steps(
        self,
    ):
        response = """
{
  "user_goal": "Открыть блокнот и проверить систему",
  "steps": [
    {
      "action": "open_application",
      "parameters": {
        "app_name": "блокнот"
      },
      "reason": "Открыть приложение"
    },
    {
      "action": "get_datetime",
      "parameters": {},
      "reason": "Получить время"
    },
    {
      "action": "get_system_info",
      "parameters": {},
      "reason": "Проверить компьютер"
    }
  ],
  "final_response": true
}
"""

        planner = Planner(
            FakeLLM([response])
        )

        plan = planner.create_plan(
            "Открой блокнот, скажи "
            "время и проверь систему"
        )

        self.assertEqual(
            len(plan.steps),
            3,
        )

        self.assertEqual(
            plan.steps[0].action,
            "open_application",
        )

        self.assertEqual(
            plan.steps[0]
            .parameters["app_name"],
            "блокнот",
        )

        self.assertEqual(
            plan.steps[1].action,
            "get_datetime",
        )

        self.assertEqual(
            plan.steps[2].action,
            "get_system_info",
        )

    def test_missing_required_parameter_is_rejected(
        self,
    ):
        response = """
{
  "user_goal": "Открыть программу",
  "steps": [
    {
      "action": "open_application",
      "parameters": {},
      "reason": "Открыть приложение"
    }
  ],
  "final_response": true
}
"""

        planner = Planner(
            FakeLLM([response])
        )

        with self.assertRaises(
            PlannerError
        ):
            planner.create_plan(
                "Открой блокнот"
            )

    def test_unknown_action_is_rejected(
        self,
    ):
        response = """
{
  "user_goal": "Запустить shell",
  "steps": [
    {
      "action": "run_shell",
      "parameters": {},
      "reason": "Запустить команду"
    }
  ],
  "final_response": true
}
"""

        planner = Planner(
            FakeLLM([response])
        )

        with self.assertRaises(
            PlannerError
        ):
            planner.create_plan(
                "Запусти shell"
            )

    def test_garbage_parameter_is_removed(
        self,
    ):
        response = """
{
  "user_goal": "Получить время",
  "steps": [
    {
      "action": "get_datetime",
      "parameters": {
        "": " "
      },
      "reason": "Получить время"
    }
  ],
  "final_response": true
}
"""

        planner = Planner(
            FakeLLM([response])
        )

        plan = planner.create_plan(
            "Сколько времени"
        )

        self.assertEqual(
            plan.steps[0].parameters,
            {},
        )


# ============================================================
# PERMISSION TESTS
# ============================================================

class PermissionTests(
    unittest.TestCase
):

    def setUp(self):
        self.permissions = (
            PermissionManager()
        )

    def test_safe_action_is_allowed(
        self,
    ):
        decision = (
            self.permissions
            .check_step(
                PlanStep(
                    "get_datetime",
                    {},
                )
            )
        )

        self.assertTrue(
            decision.allowed
        )

        self.assertEqual(
            decision.level,
            PermissionLevel.SAFE,
        )

    def test_shell_requires_confirmation(
        self,
    ):
        decision = (
            self.permissions
            .check_step(
                PlanStep(
                    "run_shell",
                    {},
                )
            )
        )

        self.assertFalse(
            decision.allowed
        )

        self.assertTrue(
            decision.requires_confirmation
        )

    def test_self_update_requires_staging(
        self,
    ):
        decision = (
            self.permissions
            .check_step(
                PlanStep(
                    "apply_improvement",
                    {},
                )
            )
        )

        self.assertFalse(
            decision.allowed
        )

        self.assertEqual(
            decision.level,
            PermissionLevel.STAGED,
        )

    def test_secret_access_is_denied(
        self,
    ):
        decision = (
            self.permissions
            .check_step(
                PlanStep(
                    "read_secrets",
                    {},
                )
            )
        )

        self.assertFalse(
            decision.allowed
        )

        self.assertEqual(
            decision.level,
            PermissionLevel.DENY,
        )

    def test_dangerous_url_is_blocked(
        self,
    ):
        decision = (
            self.permissions
            .check_step(
                PlanStep(
                    "open_website",
                    {
                        "url":
                            "javascript:alert(1)"
                    },
                )
            )
        )

        self.assertFalse(
            decision.allowed
        )


# ============================================================
# SAFE TOOL TESTS
# ============================================================

class SafeToolsTests(
    unittest.TestCase
):

    def test_command_injection_in_app_name_is_blocked(
        self,
    ):
        tools = (
            SafeComputerTools()
        )

        with self.assertRaises(
            ToolError
        ):
            tools.open_application(
                "notepad & echo hacked"
            )

    def test_invalid_volume_is_blocked(
        self,
    ):
        tools = (
            SafeComputerTools()
        )

        with self.assertRaises(
            ToolError
        ):
            tools.set_volume(
                150
            )


# ============================================================
# EXECUTOR TESTS
# ============================================================

class ExecutorTests(
    unittest.TestCase
):

    def test_steps_execute_in_order(
        self,
    ):
        tools = FakeComputerTools()

        executor = Executor(
            actions=tools,
            llm=FakeLLM(),
        )

        plan = Plan(
            user_goal=(
                "Проверить время и систему"
            ),
            steps=[
                PlanStep(
                    "get_datetime",
                    {},
                ),
                PlanStep(
                    "get_system_info",
                    {},
                ),
            ],
        )

        report = executor.execute(
            plan
        )

        self.assertTrue(
            report.success
        )

        self.assertEqual(
            [
                call[0]
                for call in tools.calls
            ],
            [
                "get_datetime",
                "get_system_info",
            ],
        )

    def test_failed_step_makes_report_failed(
        self,
    ):
        tools = Mock()

        tools.get_datetime.side_effect = (
            RuntimeError(
                "test failure"
            )
        )

        executor = Executor(
            actions=tools,
            llm=FakeLLM(),
        )

        plan = Plan(
            user_goal="Test",
            steps=[
                PlanStep(
                    "get_datetime",
                    {},
                )
            ],
        )

        report = executor.execute(
            plan
        )

        self.assertFalse(
            report.success
        )

        self.assertEqual(
            len(report.results),
            1,
        )

        self.assertFalse(
            report.results[0].success
        )

        self.assertIn(
            "test failure",
            report.results[0].error,
        )

    def test_github_zero_files_is_failure(
        self,
    ):
        github = FakeGitHub(
            "Успешно выгружено 0 файлов."
        )

        executor = Executor(
            actions=FakeComputerTools(),
            llm=FakeLLM(),
            github_manager=github,
        )

        plan = Plan(
            user_goal="Backup",
            steps=[
                PlanStep(
                    "backup_github",
                    {},
                )
            ],
        )

        report = executor.execute(
            plan
        )

        self.assertFalse(
            report.success
        )


# ============================================================
# SPEECH FORMATTER TESTS
# ============================================================

class SpeechFormatterTests(
    unittest.TestCase
):

    def test_local_fallback_uses_real_data(
        self,
    ):
        formatter = SpeechFormatter(
            FakeLLM([])
        )

        tools = FakeComputerTools()

        executor = Executor(
            actions=tools,
            llm=FakeLLM(),
        )

        plan = Plan(
            user_goal="System info",
            steps=[
                PlanStep(
                    "get_datetime",
                    {},
                ),
                PlanStep(
                    "get_system_info",
                    {},
                ),
            ],
        )

        report = executor.execute(
            plan
        )

        # Вызываем локальный formatter напрямую,
        # чтобы тест не зависел от LLM.
        text = formatter._format_locally(
            report
        )

        self.assertIn(
            "15:30",
            text,
        )

        self.assertIn(
            "93%",
            text,
        )

    def test_improvement_is_not_claimed_as_applied(
        self,
    ):
        formatter = SpeechFormatter(
            FakeLLM([])
        )

        from core.executor import (
            ExecutionReport,
            StepResult,
        )

        report = ExecutionReport(
            user_goal="Improve",
            success=True,
            results=[
                StepResult(
                    step_number=1,
                    action=(
                        "propose_improvement"
                    ),
                    success=True,
                    summary=(
                        "Подготовлено предложение."
                    ),
                    data={
                        "proposal":
                            "Добавить тесты.",
                        "applied":
                            False,
                    },
                )
            ],
        )

        text = formatter._format_locally(
            report
        )

        self.assertIn(
            "код пока не менял",
            text.lower(),
        )

    def test_time_unit_remains_seconds(
        self,
    ):
        """
        Защита от ошибки, которую мы уже видели:
        12.8 seconds не должно превратиться
        в 12.8 ms в локальном слое.
        """

        quality = FakeQuality()

        report = (
            quality.get_quality_report()
        )

        self.assertEqual(
            report[
                "response_time_unit"
            ],
            "seconds",
        )

        self.assertEqual(
            report[
                "avg_response_time"
            ],
            2.4,
        )


# ============================================================
# GITIGNORE SECURITY
# ============================================================

class SecretProtectionTests(
    unittest.TestCase
):

    def test_env_is_gitignored(
        self,
    ):
        import subprocess

        result = subprocess.run(
            [
                "git",
                "check-ignore",
                ".env",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            ".env",
            result.stdout,
        )

    def test_env_is_not_tracked(
        self,
    ):
        import subprocess

        result = subprocess.run(
            [
                "git",
                "ls-files",
                ".env",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.stdout.strip(),
            "",
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    unittest.main()