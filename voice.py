"""
Голосовой модуль: Edge-TTS (основной) + pyttsx3 (авто-фолбэк)
"""
import os
import re
import asyncio
import pygame
import edge_tts
import pyttsx3
import speech_recognition as sr
from config import Config

VOICE_NAME = "ru-RU-DmitryNeural"  # или "ru-RU-SvetlanaNeural"


class VoiceEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_speaking = False
        
        # Локальный голос-резерв
        self.fallback_engine = pyttsx3.init()
        self._setup_fallback()

        # Аудиоплеер
        try:
            pygame.mixer.init()
        except Exception:
            pass

        print("🎤 Калибровка микрофона (2 сек)...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ Микрофон готов!")
        except Exception as e:
            print(f"⚠️ Микрофон: {e}")

    def _setup_fallback(self):
        """Настройка офлайн-голоса"""
        self.fallback_engine.setProperty('rate', 170)
        self.fallback_engine.setProperty('volume', 1.0)
        voices = self.fallback_engine.getProperty('voices')
        for v in voices:
            if any(tag in v.name.lower() for tag in ['russian', 'ru', 'irina', 'milena', 'pavel']):
                self.fallback_engine.setProperty('voice', v.id)
                break

    def _clean_for_speech(self, text: str) -> str:
        """Очистка текста перед озвучкой"""
        if not text:
            return ""
        # Удаляем код, markdown, ссылки, технические символы
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]*`', '', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'[#*_~>|{}\[\]]', '', text)
        text = re.sub(r'\n+', '. ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Если после очистки пусто или только цифры/знаки
        if not re.search(r'[а-яА-ЯёЁa-zA-Z]', text):
            return "Готово."
            
        # Ограничиваем длину для комфортной речи
        if len(text) > 400:
            text = text[:397] + "..."
        return text

    def speak(self, text: str):
        """Озвучка с автоматическим переключением на офлайн при ошибке"""
        clean_text = self._clean_for_speech(text)
        if not clean_text:
            return

        print(f"\n🤖 {Config.AGENT_NAME}: {clean_text}")
        self.is_speaking = True

        try:
            self._speak_edge(clean_text)
        except Exception as e:
            print(f"⚠️ Edge-TTS недоступен: {e}")
            print("🔄 Переключаюсь на локальный голос...")
            self._speak_fallback(clean_text)
        finally:
            self.is_speaking = False

    def _speak_edge(self, text: str):
        """Основной нейросетевой голос"""
        temp_file = os.path.join(Config.BASE_DIR, "temp_voice.mp3")
        
        async def _generate():
            # Убран параметр rate для стабильности в новых версиях edge_tts
            tts = edge_tts.Communicate(text, VOICE_NAME)
            await tts.save(temp_file)

        asyncio.run(_generate())

        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 1024:
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            try: os.remove(temp_file)
            except: pass
        else:
            raise RuntimeError("Пустой аудиофайл")

    def _speak_fallback(self, text: str):
        """Резервный офлайн-голос"""
        self.fallback_engine.say(text)
        self.fallback_engine.runAndWait()

    def listen(self, timeout=7, phrase_limit=15) -> str:
        """Распознавание речи"""
        try:
            with self.microphone as source:
                print("👂 Слушаю...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            print("🔄 Распознаю...")
            text = self.recognizer.recognize_google(audio, language=Config.VOICE_LANGUAGE)
            print(f"👤 Вы: {text}")
            return text.lower().strip()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except Exception as e:
            print(f"❌ Ошибка микрофона: {e}")
            return ""