"""
Jarvis v2 - Update Candidate

Структурированное описание предлагаемого обновления.

LLM может ПРЕДЛОЖИТЬ UpdateCandidate.
Но сам объект ничего не записывает и ничего не выполняет.

Проверяются:
- допустимый путь;
- тип изменения;
- наличие объяснения;
- наличие ожидаемого эффекта;
- размер содержимого;
- запрещённые файлы.
"""

from __future__ import annotations

from dataclasses import dataclass


class CandidateError(Exception):
    pass


@dataclass(frozen=True)
class UpdateCandidate:
    relative_path: str
    new_content: str
    description: str
    expected_effect: str
    change_type: str = "fix"

    ALLOWED_CHANGE_TYPES = {
        "fix",
        "refactor",
        "feature",
        "optimization",
        "test",
    }

    ALLOWED_PREFIXES = (
        "core/",
        "tools/",
        "services/",
        "evals/",
        "updater/",
        "tests/",
    )

    BLOCKED_PATHS = {
        ".env",
        ".gitignore",
        "config.py",
        "main.py",
    }

    MAX_CONTENT_SIZE = 500_000

    def validate(self) -> None:
        path = self._normalize_path(
            self.relative_path
        )

        if not path:
            raise CandidateError(
                "Не указан файл обновления."
            )

        if path.startswith("/"):
            raise CandidateError(
                "Абсолютные пути запрещены."
            )

        if ":" in path:
            raise CandidateError(
                "Путь с указанием диска запрещён."
            )

        parts = path.split("/")

        if ".." in parts:
            raise CandidateError(
                "Выход за пределы проекта запрещён."
            )

        lower = path.lower()

        if lower in self.BLOCKED_PATHS:
            raise CandidateError(
                f"Автоматическое изменение "
                f"{path} запрещено."
            )

        if lower.startswith(".env"):
            raise CandidateError(
                "Доступ к .env запрещён."
            )

        if not lower.startswith(
            self.ALLOWED_PREFIXES
        ):
            raise CandidateError(
                "Автоматическое обновление "
                "разрешено только внутри "
                "контролируемых директорий v2."
            )

        if not lower.endswith(".py"):
            raise CandidateError(
                "На текущем этапе автоматически "
                "разрешены только Python-файлы."
            )

        if not isinstance(
            self.new_content,
            str,
        ):
            raise CandidateError(
                "new_content должен быть строкой."
            )

        if not self.new_content.strip():
            raise CandidateError(
                "Кандидат содержит пустой файл."
            )

        size = len(
            self.new_content.encode(
                "utf-8"
            )
        )

        if size > self.MAX_CONTENT_SIZE:
            raise CandidateError(
                "Кандидат слишком большой."
            )

        if not str(
            self.description
        ).strip():
            raise CandidateError(
                "Нет описания изменения."
            )

        if not str(
            self.expected_effect
        ).strip():
            raise CandidateError(
                "Не указан ожидаемый эффект."
            )

        if (
            self.change_type
            not in self.ALLOWED_CHANGE_TYPES
        ):
            raise CandidateError(
                "Неизвестный тип изменения: "
                + str(self.change_type)
            )

    def normalized_path(self) -> str:
        self.validate()

        return self._normalize_path(
            self.relative_path
        )

    @staticmethod
    def _normalize_path(
        path: str,
    ) -> str:

        if not isinstance(
            path,
            str,
        ):
            raise CandidateError(
                "Путь должен быть строкой."
            )

        return (
            path
            .strip()
            .replace("\\", "/")
        )