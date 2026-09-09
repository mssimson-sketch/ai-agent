"""
Jarvis v2 - Speech Formatter

Преобразует фактический ExecutionReport в естественный
разговорный ответ пользователю.

ВАЖНО:
- Ничего не выполняет на компьютере.
- Не изменяет результаты Executor.
- Не имеет права выдумывать выполненные действия.
- При сбое LLM использует локальный fallback.
"""

import re

from core.llm import LLMClient, LLMError
from core.executor import ExecutionReport, StepResult


class SpeechFormatterError(Exception):
    pass


class SpeechFormatter:
    """
    Формирует два представления результата:

    1. display_text — текст для консоли/интерфейса.
    2. speech_text — короткая версия для озвучивания.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    # ========================================================
    # PUBLIC API
    # ========================================================

    def format(
        self,
        report: ExecutionReport,
        original_request: str,
    ) -> dict:
        """
        Создать естественный ответ на основе реальных результатов.
        """

        if not isinstance(report, ExecutionReport):
            raise SpeechFormatterError(
                "SpeechFormatter получил неверный ExecutionReport."
            )

        facts = self._build_facts(report)

        # Сначала пытаемся получить естественную формулировку через LLM.
        try:
            text = self._format_with_llm(
                report=report,
                original_request=original_request,
                facts=facts,
            )

        except Exception as exc:
            print(
                f"[SpeechFormatter] LLM fallback: {exc}"
            )

            text = self._format_locally(
                report
            )

        text = self._clean_text(text)

        # Последняя гарантия:
        # пользователь никогда не получает пустой ответ.
        if not text:
            text = self._format_locally(
                report
            )

        display_text = text

        speech_text = self._prepare_for_speech(
            text
        )

        return {
            "display_text": display_text,
            "speech_text": speech_text,
            "success": report.success,
        }

    # ========================================================
    # FACTS
    # ========================================================

    def _build_facts(
        self,
        report: ExecutionReport,
    ) -> str:
        """
        Формируем факты, которые LLM разрешено использовать.
        """

        lines = []

        lines.append(
            f"Общий успех выполнения: {report.success}"
        )

        for result in report.results:

            lines.append("")
            lines.append(
                f"Шаг {result.step_number}"
            )
            lines.append(
                f"Действие: {result.action}"
            )
            lines.append(
                f"Успех: {result.success}"
            )
            lines.append(
                f"Краткий результат: {result.summary}"
            )

            if result.data is not None:
                lines.append(
                    f"Данные: {result.data}"
                )

            if result.error:
                lines.append(
                    f"Ошибка: {result.error}"
                )

        return "\n".join(lines)

    # ========================================================
    # LLM FORMATTER
    # ========================================================

    def _format_with_llm(
        self,
        report: ExecutionReport,
        original_request: str,
        facts: str,
    ) -> str:

        system_prompt = """
Ты — речевой слой голосового ассистента Джарвис.

Твоя задача — кратко и естественно рассказать пользователю,
что РЕАЛЬНО произошло после выполнения его команды.

СТРОГИЕ ПРАВИЛА:

1. Используй только предоставленные факты.

2. Никогда не придумывай выполненные действия.

3. Если действие завершилось ошибкой — прямо, но кратко скажи об этом.

4. Если было только предложение улучшения и код НЕ применялся,
так и скажи:
"Я подготовил предложение по улучшению, но код пока не менял."

5. Не говори "обновление выполнено", если среди фактов
нет подтверждения реального применения обновления.

6. Не произноси:
- имена Python-функций;
- JSON;
- названия внутренних классов;
- технические логи;
- traceback;
- markdown.

7. Не используй списки для голосового ответа.

8. Обычно отвечай 1-3 короткими предложениями.

9. Если пользователь запросил данные, сообщи сами полезные данные,
а не только "данные получены".

Плохо:
"Я выполнил get_datetime и get_system_info."

Хорошо:
"Сейчас 15:28. Процессор загружен примерно на 30 процентов,
оперативная память — на 53 процента."

10. Если обнаружено важное состояние системы,
можно кратко обратить на него внимание.

Например, если диск заполнен более чем на 90 процентов:
"Обрати внимание: на диске осталось мало свободного места."

11. Не добавляй стандартное
"Чем ещё помочь?"
к каждому ответу.

12. Отвечай на русском языке.
"""

        user_prompt = (
            "ИСХОДНЫЙ ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n"
            + original_request
            + "\n\n"
            + "ПОДТВЕРЖДЁННЫЕ РЕЗУЛЬТАТЫ EXECUTOR:\n"
            + facts
            + "\n\n"
            + "Сформулируй естественный ответ для пользователя."
        )

        result = self.llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.2,
            max_tokens=250,
        )

        response = result["response"]

        text = (
            response
            .choices[0]
            .message
            .content
            or ""
        ).strip()

        if not text:
            raise SpeechFormatterError(
                "LLM вернула пустой текст."
            )

        return text

    # ========================================================
    # LOCAL FALLBACK
    # ========================================================

    def _format_locally(
        self,
        report: ExecutionReport,
    ) -> str:
        """
        Формирование ответа без LLM.

        Даже если Groq недоступен после выполнения команды,
        Джарвис всё равно сможет рассказать результат.
        """

        successful = [
            r for r in report.results
            if r.success
        ]

        failed = [
            r for r in report.results
            if not r.success
        ]

        parts = []

        # Сначала извлекаем полезные результаты.
        for result in successful:

            phrase = self._local_phrase(
                result
            )

            if phrase:
                parts.append(phrase)

        # Потом ошибки.
        for result in failed:

            if result.error:
                parts.append(
                    "Не удалось выполнить одну из задач: "
                    + self._safe_error(result.error)
                )
            else:
                parts.append(
                    "Одну из задач выполнить не удалось."
                )

        if not parts:

            if report.success:
                return "Готово. Задача выполнена."

            return (
                "Задачу выполнить полностью не удалось."
            )

        return " ".join(parts)

    # ========================================================
    # LOCAL STEP → HUMAN PHRASE
    # ========================================================

    def _local_phrase(
        self,
        result: StepResult,
    ) -> str:

        data = (
            result.data
            if isinstance(result.data, dict)
            else {}
        )

        action = result.action

        if action == "get_datetime":
            return str(
                data.get(
                    "datetime",
                    result.summary,
                )
            )

        if action == "get_system_info":

            info = str(
                data.get(
                    "system_info",
                    result.summary,
                )
            )

            return info

        if action == "open_application":

            app = data.get(
                "application",
                "",
            )

            if app:
                return (
                    f"Я открыл {app}."
                )

            return result.summary

        if action == "close_application":

            app = data.get(
                "application",
                "",
            )

            if app:
                return (
                    f"Я закрыл {app}."
                )

            return result.summary

        if action == "get_weather":

            weather = data.get(
                "weather"
            )

            if weather:
                return str(weather)

            return result.summary

        if action == "get_news":

            news = data.get(
                "news"
            )

            if news:
                return str(news)

            return result.summary

        if action == "translate_text":

            translation = data.get(
                "translation"
            )

            if translation:
                return str(translation)

            return result.summary

        if action == "set_volume":

            level = data.get(
                "level"
            )

            if level is not None:
                return (
                    f"Громкость установлена "
                    f"на {level} процентов."
                )

            return result.summary

        if action == "set_reminder":

            seconds = data.get(
                "seconds"
            )

            text = data.get(
                "text"
            )

            if seconds and text:
                return (
                    f"Напоминание установлено "
                    f"через {seconds} секунд: {text}."
                )

            return result.summary

        if action == "screenshot":
            return (
                "Я сделал снимок экрана."
            )

        if action == "backup_github":

            raw = str(
                data.get(
                    "raw_result",
                    "",
                )
            )

            count_match = re.search(
                r"(\d+)\s+файл",
                raw,
                flags=re.IGNORECASE,
            )

            if count_match:

                count = count_match.group(1)

                return (
                    f"Я сохранил резервную копию "
                    f"на GitHub. Загружено файлов: {count}."
                )

            return (
                "Резервная копия на GitHub создана."
            )

        if action == "self_diagnose":
            return (
                "Я провёл самодиагностику."
            )

        if action == "quality_report":

            score = None

            if isinstance(
                result.data,
                dict,
            ):
                score = result.data.get(
                    "score"
                )

            if score is not None:
                return (
                    f"Текущая оценка качества: "
                    f"{score} из 100."
                )

            return result.summary

        if action == "propose_improvement":

            proposal = data.get(
                "proposal"
            )

            applied = data.get(
                "applied",
                False,
            )

            if proposal and not applied:

                clean = self._clean_text(
                    str(proposal)
                )

                return (
                    "Я подготовил предложение "
                    "по улучшению, но код пока не менял. "
                    + clean
                )

            return result.summary

        if action == "answer":
            return ""

        return result.summary

    # ========================================================
    # CLEANUP
    # ========================================================

    def _clean_text(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        # Блоки кода.
        text = re.sub(
            r"```.*?```",
            "",
            text,
            flags=re.DOTALL,
        )

        # Inline code.
        text = re.sub(
            r"`([^`]*)`",
            r"\1",
            text,
        )

        # Markdown-разметка.
        text = re.sub(
            r"[*#_~>]+",
            "",
            text,
        )

        # Лишние пробелы.
        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        text = re.sub(
            r"\n{2,}",
            "\n",
            text,
        )

        return text.strip()

    # ========================================================
    # SPEECH VERSION
    # ========================================================

    def _prepare_for_speech(
        self,
        text: str,
    ) -> str:
        """
        Финальная версия непосредственно для TTS.
        """

        text = self._clean_text(
            text
        )

        # Не заставляем голос читать URL.
        text = re.sub(
            r"https?://\S+",
            "ссылка",
            text,
        )

        # Переносы строк превращаем в паузы.
        text = re.sub(
            r"\s*\n\s*",
            ". ",
            text,
        )

        # Убираем повторные точки.
        text = re.sub(
            r"\.{2,}",
            ".",
            text,
        )

        # Лишние пробелы.
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        text = text.strip()

        # Для первого этапа ограничим монолог.
        # Полный текст всё равно останется в display_text.
        if len(text) > 650:
            cut = text[:650]

            last_period = cut.rfind(".")

            if last_period > 300:
                cut = cut[:last_period + 1]

            text = cut

        return text