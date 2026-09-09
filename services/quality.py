"""
Jarvis v2 - Quality Service

Адаптер над существующим QualityControl.

Задачи:
- безопасно получать текущие метрики;
- не позволять ошибке старого модуля обрушить v2;
- подготовить единый интерфейс для будущей системы Evals.
"""

from quality_control import QualityControl


class QualityService:
    def __init__(self):
        self._legacy = QualityControl()

    def get_quality_report(self) -> dict:
        try:
            report = (
                self._legacy
                .get_quality_report()
            )

            if not isinstance(
                report,
                dict,
            ):
                return {
                    "status": "error",
                    "error": (
                        "QualityControl вернул "
                        "неизвестный формат."
                    ),
                }

            return report

        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }

    def get_report_text(self) -> str:
        try:
            return str(
                self._legacy
                .get_report_text()
            )

        except Exception as exc:
            return (
                "Не удалось получить "
                "отчёт качества: "
                + str(exc)
            )