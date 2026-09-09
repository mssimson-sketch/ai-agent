"""
Конфигурация агента
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    # ===== API КЛЮЧИ =====
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "")
    GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "ai-agent")

    # ===== АГЕНТ =====
    AGENT_NAME = os.getenv("AGENT_NAME", "Джарвис")
    VERSION = "1.0.0"
    WAKE_WORD = os.getenv("AGENT_NAME", "джарвис").lower()

    # ===== ГОЛОС =====
    VOICE_RATE = 170
    VOICE_VOLUME = 1.0
    VOICE_LANGUAGE = "ru"

    # ===== LLM (Groq / Llama 3.3 70B - Бесплатно) =====
    LLM_BASE_URL = "https://api.groq.com/openai/v1"
    LLM_MODEL = "openai/gpt-oss-20b"
    MAX_CONTEXT_MESSAGES = 20

    # ===== ПУТИ =====
    BASE_DIR = BASE_DIR
    MEMORY_FILE = os.path.join(BASE_DIR, "conversation_log.json")
    QUALITY_LOG = os.path.join(BASE_DIR, "quality_log.json")
    ERROR_LOG = os.path.join(BASE_DIR, "error_log.json")
    PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")
    BACKUPS_DIR = os.path.join(BASE_DIR, "backups")

    # ===== НАСТРОЙКИ =====
    AUTO_UPDATE_INTERVAL = 3600
    SELF_IMPROVE_ENABLED = True
    QUALITY_CHECK_INTERVAL = 1800

    @classmethod
    def validate(cls):
        errors = []
        if not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == "sk-ВАШ-КЛЮЧ-СЮДА":
            errors.append("❌ Не указан API_KEY в файле .env")
        if not cls.GITHUB_TOKEN:
            errors.append("⚠️ Не указан GITHUB_TOKEN (самообновление не будет работать)")

        os.makedirs(cls.PLUGINS_DIR, exist_ok=True)
        os.makedirs(cls.BACKUPS_DIR, exist_ok=True)
        return errors