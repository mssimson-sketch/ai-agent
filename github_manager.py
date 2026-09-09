"""
GitHub менеджер — надежная выгрузка и синхронизация всех файлов агента
"""
import os
from datetime import datetime
from config import Config

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False


class GitHubManager:
    def __init__(self):
        self.github = None
        self.repo = None
        self.user = None

        if GITHUB_AVAILABLE and Config.GITHUB_TOKEN:
            try:
                self.github = Github(Config.GITHUB_TOKEN.strip())
                self.user = self.github.get_user()
                print(f"🐙 GitHub подключён: {self.user.login}")
                self._ensure_repo()
            except Exception as e:
                print(f"⚠️ Ошибка инициализации GitHub: {e}")

    def _ensure_repo(self):
        """Подключение или создание репозитория"""
        if not self.user:
            return
        try:
            self.repo = self.user.get_repo(Config.GITHUB_REPO_NAME)
            print(f"📦 Репозиторий найден: {self.repo.full_name}")
        except Exception:
            try:
                self.repo = self.user.create_repo(
                    Config.GITHUB_REPO_NAME,
                    description=f"🤖 {Config.AGENT_NAME} — AI Desktop Agent",
                    private=True,
                    auto_init=True
                )
                print(f"📦 Репозиторий создан с автоинициализацией: {self.repo.full_name}")
            except Exception as e:
                print(f"⚠️ Статус репозитория: {e}")

    def backup_to_github(self) -> str:
        """Выгрузка файлов в репозиторий GitHub"""
        if not self.repo:
            return "GitHub репозиторий не подключен (проверьте токен)."

        files_to_backup = [
            'config.py', 'voice.py', 'brain.py', 'actions.py',
            'memory.py', 'system_monitor.py', 'github_manager.py',
            'self_upgrade.py', 'quality_control.py', 'plugin_manager.py',
            'main.py'
        ]

        uploaded = 0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for filename in files_to_backup:
            filepath = os.path.join(Config.BASE_DIR, filename)
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Проверяем, существует ли файл в репозитории
                try:
                    existing = self.repo.get_contents(filename, ref="main")
                    self.repo.update_file(
                        path=filename,
                        message=f"🤖 Обновление {filename} [{timestamp}]",
                        content=content,
                        sha=existing.sha,
                        branch="main"
                    )
                    uploaded += 1
                except Exception:
                    # Если файла нет — создаем
                    try:
                        self.repo.create_file(
                            path=filename,
                            message=f"🤖 Добавлен {filename} [{timestamp}]",
                            content=content,
                            branch="main"
                        )
                        uploaded += 1
                    except Exception as create_err:
                        # Если ветка называется master
                        self.repo.create_file(
                            path=filename,
                            message=f"🤖 Добавлен {filename}",
                            content=content
                        )
                        uploaded += 1

            except Exception as e:
                print(f"⚠️ Не удалось выгрузить {filename}: {e}")

        return f"Успешно выгружено {uploaded} файлов в репозиторий {self.repo.full_name}!"