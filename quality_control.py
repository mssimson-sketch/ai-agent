"""
Контроль качества — агент оценивает сам себя
"""
import json
import os
import time
import threading
from datetime import datetime
from config import Config


class QualityControl:
    """Система самооценки и контроля качества"""

    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "errors": [],
            "response_times": [],
            "user_satisfaction": [],  # 1-5 если пользователь оценивает
            "improvements_applied": 0,
            "last_check": None
        }
        self.load_metrics()

    def load_metrics(self):
        if os.path.exists(Config.QUALITY_LOG):
            try:
                with open(Config.QUALITY_LOG, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                self.metrics.update(saved)
            except:
                pass

    def save_metrics(self):
        try:
            with open(Config.QUALITY_LOG, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, ensure_ascii=False, indent=2)
        except:
            pass

    def log_request(self, user_input: str, response: str,
                    success: bool, response_time: float, error: str = ""):
        """Записать результат запроса"""
        self.metrics["total_requests"] += 1

        if success:
            self.metrics["successful_actions"] += 1
        else:
            self.metrics["failed_actions"] += 1

        self.metrics["response_times"].append(response_time)
        # Ограничиваем историю
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-500:]

        if error:
            self.metrics["errors"].append({
                "time": datetime.now().isoformat(),
                "input": user_input[:200],
                "error": str(error)[:500],
                "module": "brain"
            })
            # Ограничиваем историю ошибок
            if len(self.metrics["errors"]) > 100:
                self.metrics["errors"] = self.metrics["errors"][-50:]

        self.save_metrics()

    def get_quality_report(self) -> dict:
        """Полный отчёт о качестве"""
        total = self.metrics["total_requests"]
        if total == 0:
            return {
                "score": 0,
                "report": "Недостаточно данных для оценки. Ещё не было запросов."
            }

        success_rate = (self.metrics["successful_actions"] / total) * 100

        avg_time = 0
        if self.metrics["response_times"]:
            avg_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])

        error_rate = (self.metrics["failed_actions"] / total) * 100

        # Оценка по 100-балльной шкале
        score = max(0, min(100,
            success_rate * 0.5 +                        # 50% за успешность
            max(0, (5 - avg_time) / 5 * 30) +          # 30% за скорость
            max(0, (100 - error_rate) / 100 * 20)       # 20% за отсутствие ошибок
        ))

        # Определяем уровень
        if score >= 90:
            level = "🟢 Отлично"
        elif score >= 70:
            level = "🟡 Хорошо"
        elif score >= 50:
            level = "🟠 Удовлетворительно"
        else:
            level = "🔴 Требует улучшения"

        # Частые ошибки
        frequent_errors = {}
        for err in self.metrics["errors"][-50:]:
            key = err.get("error", "unknown")[:100]
            frequent_errors[key] = frequent_errors.get(key, 0) + 1

        top_errors = sorted(frequent_errors.items(), key=lambda x: x[1], reverse=True)[:5]

        report = {
            "score": round(score, 1),
            "level": level,
            "total_requests": total,
            "success_rate": round(success_rate, 1),
            "error_rate": round(error_rate, 1),
            "avg_response_time": round(avg_time, 2),
            "top_errors": top_errors,
            "improvements_applied": self.metrics["improvements_applied"],
        }

        return report

    def get_report_text(self) -> str:
        """Текстовый отчёт для голосового ответа"""
        r = self.get_quality_report()
        if r["score"] == 0:
            return "Пока недостаточно данных для оценки качества."

        text = (
            f"Отчёт о качестве работы. "
            f"Оценка: {r['score']} из 100, уровень: {r['level']}. "
            f"Всего обработано {r['total_requests']} запросов. "
            f"Успешных: {r['success_rate']} процентов. "
            f"Среднее время ответа: {r['avg_response_time']} секунд. "
        )

        if r["top_errors"]:
            text += f"Найдено {len(r['top_errors'])} типов повторяющихся ошибок. "

        if r["score"] < 70:
            text += "Рекомендую запустить самоулучшение для повышения качества."

        return text

    def suggest_improvements(self) -> list:
        """Предложить улучшения на основе анализа"""
        suggestions = []
        report = self.get_quality_report()

        if report["score"] == 0:
            return ["Начните использовать агента для сбора статистики"]

        if report["error_rate"] > 20:
            suggestions.append({
                "area": "Обработка ошибок",
                "priority": "high",
                "suggestion": "Много ошибок. Нужно улучшить обработку исключений и валидацию ввода."
            })

        if report["avg_response_time"] > 5:
            suggestions.append({
                "area": "Скорость",
                "priority": "medium",
                "suggestion": "Медленные ответы. Стоит добавить кэширование и быстрые команды."
            })

        if report["success_rate"] < 80:
            suggestions.append({
                "area": "Распознавание команд",
                "priority": "high",
                "suggestion": "Низкая точность. Нужно улучшить системный промпт и добавить больше быстрых команд."
            })

        for error, count in report.get("top_errors", []):
            if count >= 3:
                suggestions.append({
                    "area": "Повторяющаяся ошибка",
                    "priority": "high",
                    "suggestion": f"Ошибка встречается {count} раз: {error[:100]}"
                })

        return suggestions