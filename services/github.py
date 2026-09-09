"""
Jarvis v2 - GitHub Service

Безопасный адаптер над существующим GitHubManager.

Этот сервис:
- использует только backup;
- не предоставляет LLM прямой доступ к токену;
- не позволяет агенту менять произвольные репозитории;
- проверяет результат старого GitHubManager.
"""

from github_manager import GitHubManager


class GitHubServiceError(Exception):
    pass


class GitHubService:
    def __init__(self):
        self._legacy = GitHubManager()

    def backup_to_github(self) -> str:
        """
        Создать резервную копию текущего проекта.
        """

        try:
            result = (
                self._legacy
                .backup_to_github()
            )

        except Exception as exc:
            raise GitHubServiceError(
                f"Ошибка GitHub backup: {exc}"
            ) from exc

        text = str(result).strip()

        if not text:
            raise GitHubServiceError(
                "GitHubManager вернул "
                "пустой результат."
            )

        lower = text.lower()

        bad_markers = (
            "403",
            "401",
            "forbidden",
            "failed",
            "ошибка",
            "не удалось",
            "не подключ",
            "0 файлов",
        )

        if any(
            marker in lower
            for marker in bad_markers
        ):
            raise GitHubServiceError(
                text
            )

        return text