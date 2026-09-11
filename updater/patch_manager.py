"""
Jarvis v2 - Patch Manager

Работает ТОЛЬКО с файлами внутри staging.

Функции:
- проверка пути;
- запрет секретов и служебных директорий;
- изменение только разрешённых исходников;
- SHA-256 до/после;
- unified diff;
- ограничение размера патча.

Рабочий проект этот модуль не изменяет.
"""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from pathlib import Path


class PatchError(Exception):
    pass


@dataclass
class PatchResult:
    success: bool
    relative_path: str
    old_sha256: str
    new_sha256: str
    changed_lines: int
    diff: str


class PatchManager:
    """
    Контролируемое изменение staging-кандидата.
    """

    MAX_FILE_SIZE = 500_000
    MAX_DIFF_CHARS = 40_000

    ALLOWED_SUFFIXES = {
        ".py",
        ".json",
        ".txt",
        ".md",
    }

    BLOCKED_NAMES = {
        ".env",
        ".gitignore",
    }

    BLOCKED_PARTS = {
        ".git",
        "venv",
        "__pycache__",
        "backups",
    }

    def __init__(
        self,
        staging_root: Path,
    ):
        self.staging_root = Path(
            staging_root
        ).resolve()

        if not self.staging_root.is_dir():
            raise PatchError(
                "Staging-каталог не существует."
            )

    # ========================================================
    # PUBLIC
    # ========================================================

    def replace_file(
        self,
        relative_path: str,
        new_content: str,
    ) -> PatchResult:
        """
        Полностью заменить содержимое разрешённого
        файла внутри staging.
        """

        target = self._resolve_target(
            relative_path
        )

        if not target.is_file():
            raise PatchError(
                "Изменяемый файл не существует: "
                + relative_path
            )

        if not isinstance(
            new_content,
            str,
        ):
            raise PatchError(
                "Новое содержимое должно "
                "быть текстом."
            )

        encoded = new_content.encode(
            "utf-8"
        )

        if len(encoded) > self.MAX_FILE_SIZE:
            raise PatchError(
                "Новый файл превышает "
                "допустимый размер."
            )

        old_content = target.read_text(
            encoding="utf-8"
        )

        old_hash = self._sha256(
            old_content
        )

        new_hash = self._sha256(
            new_content
        )

        diff = self._make_diff(
            relative_path,
            old_content,
            new_content,
        )

        if len(diff) > self.MAX_DIFF_CHARS:
            raise PatchError(
                "Патч слишком большой."
            )

        changed_lines = self._count_changes(
            diff
        )

        # Если содержимое идентично,
        # не переписываем файл.
        if old_hash == new_hash:
            return PatchResult(
                success=True,
                relative_path=relative_path,
                old_sha256=old_hash,
                new_sha256=new_hash,
                changed_lines=0,
                diff="",
            )

        target.write_text(
            new_content,
            encoding="utf-8",
        )

        # Проверяем, что реально записалось именно
        # то содержимое, которое ожидалось.
        written = target.read_text(
            encoding="utf-8"
        )

        written_hash = self._sha256(
            written
        )

        if written_hash != new_hash:
            raise PatchError(
                "Контрольная сумма записанного "
                "файла не совпадает."
            )

        return PatchResult(
            success=True,
            relative_path=relative_path,
            old_sha256=old_hash,
            new_sha256=new_hash,
            changed_lines=changed_lines,
            diff=diff,
        )

    def read_file(
        self,
        relative_path: str,
    ) -> str:
        """
        Прочитать разрешённый файл staging.
        """

        target = self._resolve_target(
            relative_path
        )

        if not target.is_file():
            raise PatchError(
                "Файл не существует."
            )

        if target.stat().st_size > self.MAX_FILE_SIZE:
            raise PatchError(
                "Файл слишком большой."
            )

        return target.read_text(
            encoding="utf-8"
        )

    # ========================================================
    # PATH SECURITY
    # ========================================================

    def _resolve_target(
        self,
        relative_path: str,
    ) -> Path:

        if not isinstance(
            relative_path,
            str,
        ):
            raise PatchError(
                "Путь должен быть строкой."
            )

        relative_path = (
            relative_path
            .strip()
            .replace("\\", "/")
        )

        if not relative_path:
            raise PatchError(
                "Получен пустой путь."
            )

        relative = Path(
            relative_path
        )

        # Абсолютные пути запрещены.
        if relative.is_absolute():
            raise PatchError(
                "Абсолютный путь запрещён."
            )

        # Windows drive-like paths.
        if ":" in relative_path:
            raise PatchError(
                "Пути с указанием диска запрещены."
            )

        parts_lower = {
            part.lower()
            for part in relative.parts
        }

        if parts_lower & self.BLOCKED_PARTS:
            raise PatchError(
                "Доступ к служебной директории "
                "запрещён."
            )

        if relative.name.lower() in self.BLOCKED_NAMES:
            raise PatchError(
                "Изменение защищённого файла "
                "запрещено."
            )

        # Любой .env-вариант запрещён.
        if relative.name.lower().startswith(
            ".env"
        ):
            raise PatchError(
                "Доступ к секретам запрещён."
            )

        suffix = relative.suffix.lower()

        if suffix not in self.ALLOWED_SUFFIXES:
            raise PatchError(
                f"Тип файла {suffix or '<none>'} "
                "не разрешён для PatchManager."
            )

        target = (
            self.staging_root
            / relative
        ).resolve()

        # Главная защита от ../../
        if (
            target != self.staging_root
            and self.staging_root
            not in target.parents
        ):
            raise PatchError(
                "Попытка выхода за пределы "
                "staging заблокирована."
            )

        return target

    # ========================================================
    # HASH / DIFF
    # ========================================================

    def _sha256(
        self,
        text: str,
    ) -> str:

        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

    def _make_diff(
        self,
        relative_path: str,
        old: str,
        new: str,
    ) -> str:

        old_lines = old.splitlines(
            keepends=True
        )

        new_lines = new.splitlines(
            keepends=True
        )

        return "".join(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=(
                    "before/"
                    + relative_path
                ),
                tofile=(
                    "after/"
                    + relative_path
                ),
            )
        )

    def _count_changes(
        self,
        diff: str,
    ) -> int:

        count = 0

        for line in diff.splitlines():

            if line.startswith(
                ("+++", "---", "@@")
            ):
                continue

            if (
                line.startswith("+")
                or line.startswith("-")
            ):
                count += 1

        return count