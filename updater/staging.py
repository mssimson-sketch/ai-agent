"""
Jarvis v2 - Staging Manager

Создаёт изолированную копию отслеживаемого проекта
для проверки обновлений.

Ни один кандидат на обновление не должен сначала
применяться к рабочей копии.

ВАЖНО:
- .env не копируется;
- venv не копируется;
- .git не копируется;
- staging создаётся внутри backups/staging;
- копируются только файлы, которые отслеживает Git.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from config import Config


class StagingError(Exception):
    pass


@dataclass
class ValidationResult:
    success: bool
    compile_success: bool
    tests_success: bool
    return_code: int
    output: str
    duration_seconds: float


class StagingManager:
    """
    Управление временной тестовой копией Jarvis.
    """

    def __init__(self):
        self.project_dir = Path(
            Config.BASE_DIR
        ).resolve()

        self.staging_root = (
            self.project_dir
            / "backups"
            / "staging"
        )

        self.staging_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ========================================================
    # CREATE
    # ========================================================

    def create(self) -> Path:
        """
        Создать новую staging-копию.

        Используем git ls-files, поэтому туда попадает
        только версионируемый исходный код.
        """

        stamp = time.strftime(
            "%Y%m%d_%H%M%S"
        )

        staging_dir = (
            self.staging_root
            / f"candidate_{stamp}"
        )

        suffix = 1

        while staging_dir.exists():
            staging_dir = (
                self.staging_root
                / f"candidate_{stamp}_{suffix}"
            )
            suffix += 1

        staging_dir.mkdir(
            parents=True
        )

        files = self._tracked_files()

        if not files:
            raise StagingError(
                "Git не вернул отслеживаемых файлов."
            )

        for relative in files:

            # Дополнительная защита.
            if self._is_secret(relative):
                continue

            source = (
                self.project_dir
                / relative
            )

            destination = (
                staging_dir
                / relative
            )

            if not source.is_file():
                continue

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source,
                destination,
            )

        return staging_dir

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(
        self,
        staging_dir: Path,
    ) -> ValidationResult:
        """
        1. Компилируем Python.
        2. Запускаем unittest.

        Используется текущий venv Python,
        но рабочая директория — staging.
        """

        staging_dir = Path(
            staging_dir
        ).resolve()

        self._assert_inside_staging(
            staging_dir
        )

        started = time.monotonic()

        # ----------------------------------------------------
        # COMPILE
        # ----------------------------------------------------

        compile_result = subprocess.run(
            [
                os.sys.executable,
                "-m",
                "compileall",
                "-q",
                ".",
            ],
            cwd=str(staging_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

        compile_success = (
            compile_result.returncode == 0
        )

        if not compile_success:

            duration = (
                time.monotonic()
                - started
            )

            output = (
                compile_result.stdout
                + "\n"
                + compile_result.stderr
            ).strip()

            return ValidationResult(
                success=False,
                compile_success=False,
                tests_success=False,
                return_code=(
                    compile_result.returncode
                ),
                output=output,
                duration_seconds=duration,
            )

        # ----------------------------------------------------
        # UNIT TESTS
        # ----------------------------------------------------

        tests_dir = (
            staging_dir
            / "tests"
        )

        if not tests_dir.is_dir():

            duration = (
                time.monotonic()
                - started
            )

            return ValidationResult(
                success=False,
                compile_success=True,
                tests_success=False,
                return_code=2,
                output=(
                    "Папка tests отсутствует "
                    "в staging."
                ),
                duration_seconds=duration,
            )

        test_result = subprocess.run(
            [
                os.sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ],
            cwd=str(staging_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        tests_success = (
            test_result.returncode == 0
        )

        duration = (
            time.monotonic()
            - started
        )

        output = (
            test_result.stdout
            + "\n"
            + test_result.stderr
        ).strip()

        return ValidationResult(
            success=(
                compile_success
                and tests_success
            ),
            compile_success=(
                compile_success
            ),
            tests_success=(
                tests_success
            ),
            return_code=(
                test_result.returncode
            ),
            output=output,
            duration_seconds=duration,
        )

    # ========================================================
    # TEST FAILURE INJECTION
    # ========================================================

    def inject_broken_python(
        self,
        staging_dir: Path,
    ) -> Path:
        """
        Только для проверки защиты updater.

        Создаёт синтаксически сломанный файл ИСКЛЮЧИТЕЛЬНО
        внутри staging.

        Рабочий проект не меняется.
        """

        staging_dir = Path(
            staging_dir
        ).resolve()

        self._assert_inside_staging(
            staging_dir
        )

        target = (
            staging_dir
            / "_intentional_broken_test.py"
        )

        target.write_text(
            "def broken(:\n"
            "    pass\n",
            encoding="utf-8",
        )

        return target

    # ========================================================
    # CLEANUP
    # ========================================================

    def remove(
        self,
        staging_dir: Path,
    ):
        staging_dir = Path(
            staging_dir
        ).resolve()

        self._assert_inside_staging(
            staging_dir
        )

        if staging_dir.exists():
            shutil.rmtree(
                staging_dir
            )

    # ========================================================
    # SECURITY
    # ========================================================

    def _tracked_files(
        self,
    ) -> list[Path]:

        result = subprocess.run(
            [
                "git",
                "ls-files",
            ],
            cwd=str(
                self.project_dir
            ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        if result.returncode != 0:
            raise StagingError(
                result.stderr.strip()
                or "git ls-files завершился ошибкой."
            )

        paths = []

        for line in result.stdout.splitlines():

            line = line.strip()

            if not line:
                continue

            paths.append(
                Path(line)
            )

        return paths

    def _is_secret(
        self,
        relative: Path,
    ) -> bool:

        text = (
            relative
            .as_posix()
            .lower()
        )

        name = (
            relative.name.lower()
        )

        if name == ".env":
            return True

        if name.startswith(
            ".env."
        ):
            return True

        if text.startswith(
            "venv/"
        ):
            return True

        if text.startswith(
            ".git/"
        ):
            return True

        return False

    def _assert_inside_staging(
        self,
        path: Path,
    ):
        root = (
            self.staging_root
            .resolve()
        )

        path = path.resolve()

        if path == root:
            raise StagingError(
                "Операция над корнем "
                "staging запрещена."
            )

        if root not in path.parents:
            raise StagingError(
                "Попытка операции вне "
                "staging заблокирована."
            )