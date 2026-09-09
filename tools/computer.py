"""
Jarvis v2 - Safe Computer Tools

Безопасный адаптер над старым ComputerActions.

Только явно перечисленные методы становятся доступны
Executor v2.

Здесь НЕТ:
- run_python_code
- install_package
- write_plugin
- удаления файлов
- запуска shell
- чтения .env
- выключения компьютера
"""

from actions import ComputerActions


class ToolError(Exception):
    pass


class SafeComputerTools:
    """
    Белый список разрешённых инструментов Jarvis v2.
    """

    def __init__(self):
        self._legacy = ComputerActions()

    # ========================================================
    # APPLICATIONS
    # ========================================================

    def open_application(
        self,
        app_name: str,
    ) -> str:

        app_name = self._clean_text(
            app_name,
            "app_name",
        )

        # На v2 пока запрещаем передавать команды оболочки
        # под видом названия программы.
        blocked = (
            "&",
            "|",
            ">",
            "<",
            "\n",
            "\r",
        )

        if any(
            symbol in app_name
            for symbol in blocked
        ):
            raise ToolError(
                "Недопустимые символы "
                "в названии приложения."
            )

        return self._legacy.open_application(
            app_name
        )

    def close_application(
        self,
        app_name: str,
    ) -> str:

        app_name = self._clean_text(
            app_name,
            "app_name",
        )

        blocked = (
            "&",
            "|",
            ">",
            "<",
            "\n",
            "\r",
        )

        if any(
            symbol in app_name
            for symbol in blocked
        ):
            raise ToolError(
                "Недопустимые символы "
                "в названии приложения."
            )

        return self._legacy.close_application(
            app_name
        )

    # ========================================================
    # SYSTEM INFORMATION
    # ========================================================

    def get_system_info(
        self,
    ) -> str:

        return self._legacy.get_system_info()

    def get_datetime(
        self,
    ) -> str:

        return self._legacy.get_datetime()

    # ========================================================
    # SCREENSHOT
    # ========================================================

    def screenshot(
        self,
    ) -> str:

        return self._legacy.screenshot()

    # ========================================================
    # VOLUME
    # ========================================================

    def set_volume(
        self,
        level: int,
    ) -> str:

        try:
            level = int(level)

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ToolError(
                "Громкость должна быть числом."
            ) from exc

        if not 0 <= level <= 100:
            raise ToolError(
                "Громкость должна быть "
                "от 0 до 100."
            )

        return self._legacy.set_volume(
            level
        )

    # ========================================================
    # BROWSER
    # ========================================================

    def open_website(
        self,
        url: str,
    ) -> str:

        url = self._clean_text(
            url,
            "url",
        )

        lower = url.lower()

        blocked_schemes = (
            "file:",
            "javascript:",
            "data:",
            "cmd:",
            "powershell:",
        )

        if lower.startswith(
            blocked_schemes
        ):
            raise ToolError(
                "Опасная схема URL заблокирована."
            )

        return self._legacy.open_website(
            url
        )

    def search_google(
        self,
        query: str,
    ) -> str:

        query = self._clean_text(
            query,
            "query",
        )

        return self._legacy.search_google(
            query
        )

    def search_youtube(
        self,
        query: str,
    ) -> str:

        query = self._clean_text(
            query,
            "query",
        )

        return self._legacy.search_youtube(
            query
        )

    # ========================================================
    # WEATHER
    # ========================================================

    def get_weather(
        self,
        city: str,
    ) -> str:

        city = self._clean_text(
            city,
            "city",
        )

        return self._legacy.get_weather(
            city
        )

    # ========================================================
    # NEWS
    # ========================================================

    def get_news(
        self,
        category: str = "главное",
    ) -> str:

        category = (
            str(category).strip()
            if category is not None
            else "главное"
        )

        if not category:
            category = "главное"

        return self._legacy.get_news(
            category
        )

    # ========================================================
    # TRANSLATION
    # ========================================================

    def translate_text(
        self,
        text: str,
        target_lang: str,
    ) -> str:

        text = self._clean_text(
            text,
            "text",
        )

        target_lang = self._clean_text(
            target_lang,
            "target_lang",
        )

        # Ограничиваем код языка.
        if len(target_lang) > 10:
            raise ToolError(
                "Некорректный код языка."
            )

        return self._legacy.translate_text(
            text,
            target_lang,
        )

    # ========================================================
    # REMINDERS
    # ========================================================

    def set_reminder(
        self,
        seconds: int,
        text: str,
    ) -> str:

        try:
            seconds = int(seconds)

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ToolError(
                "Время напоминания должно "
                "быть числом."
            ) from exc

        if seconds <= 0:
            raise ToolError(
                "Время напоминания должно "
                "быть больше нуля."
            )

        # Защита от случайного абсурдного таймера.
        # 1 год — более чем достаточно для текущей версии.
        if seconds > 31_536_000:
            raise ToolError(
                "Слишком большой интервал "
                "напоминания."
            )

        text = self._clean_text(
            text,
            "text",
        )

        return self._legacy.set_reminder(
            seconds,
            text,
        )

    # ========================================================
    # INTERNAL VALIDATION
    # ========================================================

    def _clean_text(
        self,
        value,
        name: str,
    ) -> str:

        if value is None:
            raise ToolError(
                f"Параметр {name} отсутствует."
            )

        value = str(value).strip()

        if not value:
            raise ToolError(
                f"Параметр {name} пуст."
            )

        if len(value) > 4000:
            raise ToolError(
                f"Параметр {name} слишком длинный."
            )

        return value