import time
from openai import OpenAI
from config import Config


class LLMError(Exception):
    pass


class LLMClient:
    """
    Единая точка доступа Джарвиса к LLM.

    Остальные компоненты не должны самостоятельно
    создавать OpenAI/Groq клиентов.
    """

    def __init__(self):
        self.base_url = Config.LLM_BASE_URL
        self.api_key = Config.OPENAI_API_KEY
        self.preferred_model = Config.LLM_MODEL

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=30.0,
            max_retries=1
        )

        self.active_model = None
        self.available_models = []

    def refresh_models(self):
        """Получить реальные модели непосредственно от провайдера."""
        try:
            response = self.client.models.list()
            self.available_models = sorted(
                m.id for m in response.data
            )
            return self.available_models

        except Exception as e:
            raise LLMError(
                f"Не удалось получить список моделей: {e}"
            ) from e

    def select_model(self):
        """
        Используем модель из config.py, только если
        сервер подтверждает её наличие.
        """
        models = self.refresh_models()

        if self.preferred_model in models:
            self.active_model = self.preferred_model
            return self.active_model

        # Не выбираем случайные TTS/Whisper/Guard модели.
        excluded = (
            "whisper",
            "tts",
            "orpheus",
            "guard",
            "safeguard",
            "embed"
        )

        candidates = [
            m for m in models
            if not any(word in m.lower() for word in excluded)
        ]

        if not candidates:
            raise LLMError(
                "Провайдер не предоставил подходящих текстовых моделей."
            )

        # Это только кандидат.
        # Реально проверим его перед использованием.
        for model in candidates:
            if self._health_check_model(model):
                self.active_model = model
                return model

        raise LLMError(
            "Ни одна доступная текстовая модель не прошла проверку."
        )

    def _health_check_model(self, model):
        """Минимальный реальный запрос модели."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": "Ответь одним словом: OK"
                    }
                ],
                temperature=0,
                max_tokens=10
            )

            text = response.choices[0].message.content
            return bool(text and text.strip())

        except Exception:
            return False

    def ensure_ready(self):
        if self.active_model is None:
            self.select_model()

        return self.active_model

    def chat(
        self,
        messages,
        temperature=0.3,
        max_tokens=600,
        tools=None,
        tool_choice=None
    ):
        """Единый метод для всех запросов Джарвиса."""

        model = self.ensure_ready()

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Важный момент:
        # не отправляем tools/tool_choice вообще,
        # если инструменты не нужны.
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        try:
            started = time.monotonic()

            response = self.client.chat.completions.create(**kwargs)

            elapsed = time.monotonic() - started

            return {
                "response": response,
                "model": model,
                "elapsed": elapsed
            }

        except Exception as e:
            raise LLMError(
                f"Ошибка модели {model}: {e}"
            ) from e

    def health_report(self):
        model = self.ensure_ready()

        return {
            "provider": self.base_url,
            "preferred_model": self.preferred_model,
            "active_model": model,
            "available_models": len(self.available_models),
            "status": "ok"
        }