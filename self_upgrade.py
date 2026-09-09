"""
Самоулучшение агента — анализ качества и генерация улучшений через Groq LLM
"""
import os
import json
import shutil
from datetime import datetime
from openai import OpenAI
from config import Config


class SelfUpgrade:
    """Система самоулучшения агента"""

    def __init__(self, brain=None, github_manager=None, quality_control=None):
        self.brain = brain
        self.github = github_manager
        self.quality = quality_control
        self.upgrade_log = []
        self.load_log()

    def _get_client(self):
        """Клиент с поддержкой Groq"""
        return OpenAI(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.OPENAI_API_KEY
        )

    def load_log(self):
        log_path = os.path.join(Config.BASE_DIR, "upgrade_log.json")
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    self.upgrade_log = json.load(f)
            except:
                pass

    def save_log(self):
        log_path = os.path.join(Config.BASE_DIR, "upgrade_log.json")
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(self.upgrade_log[-100:], f, ensure_ascii=False, indent=2)
        except:
            pass

    def create_backup(self) -> str:
        """Создать локальный бэкап всех исходных файлов"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(Config.BACKUPS_DIR, f"backup_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)

        files = [f for f in os.listdir(Config.BASE_DIR) if f.endswith('.py') or f.endswith('.json')]
        for f in files:
            src = os.path.join(Config.BASE_DIR, f)
            dst = os.path.join(backup_dir, f)
            if os.path.isfile(src):
                shutil.copy2(src, dst)

        return backup_dir

    def analyze_and_improve(self) -> str:
        """Анализ качества работы и генерация рекомендаций через нейросеть"""
        if not self.quality:
            return "Модуль контроля качества не подключен."

        report = self.quality.get_quality_report()
        suggestions = self.quality.suggest_improvements()

        analysis_prompt = f"""
Ты — модуль самодиагностики и оптимизации ИИ-агента Джарвис.
Проанализируй текущие показатели и дай 1-2 кратких вывода по улучшению:

МЕТРИКИ РАБОТЫ:
- Общая оценка: {report.get('score', 0)}/100 ({report.get('level', 'N/A')})
- Всего запросов: {report.get('total_requests', 0)}
- Успешность: {report.get('success_rate', 0)}%
- Среднее время ответа: {report.get('avg_response_time', 0)} сек
- Предложения: {suggestions}

Напиши короткий оптимистичный отчет инженера (2-3 предложения) на русском языке.
"""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "Ты ведущий инженер оптимизации Python-систем."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            summary = response.choices[0].message.content.strip()

            self.upgrade_log.append({
                "time": datetime.now().isoformat(),
                "score": report.get('score', 0),
                "summary": summary
            })
            self.save_log()

            if self.quality:
                self.quality.metrics["improvements_applied"] = self.quality.metrics.get("improvements_applied", 0) + 1
                self.quality.save_metrics()

            return f"Анализ завершен. Оценка: {report.get('score', 0)}/100. Резюме: {summary}"

        except Exception as e:
            return f"Базовый анализ выполнен (оценка: {report.get('score', 0)}/100). Ошибка LLM: {e}"

    def auto_improve_cycle(self) -> str:
        """Полный цикл: Диагностика -> Локальный бэкап -> Синхронизация с GitHub"""
        results = []

        # 1. Диагностика
        analysis = self.analyze_and_improve()
        results.append(f"📊 Диагностика: {analysis}")

        # 2. Локальный бэкап
        backup_path = self.create_backup()
        results.append(f"💾 Локальный бэкап создан")

        # 3. GitHub бэкап
        if self.github:
            gh_res = self.github.backup_to_github()
            results.append(f"🐙 GitHub: {gh_res}")

        return " | ".join(results)