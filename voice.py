"""
Голосовой модуль: Edge-TTS + офлайн фолбэк + таймауты
"""
import os
import re
import asyncio
import pygame
import edge_tts
import pyttsx3
import speech_recognition as sr
from config import Config

VOICE_NAME = "ru-RU-DmitryNeural"

class VoiceEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_speaking = False
        
        self.fallback_engine = pyttsx3.init()
        self._setup_fallback()

        try:
            pygame.mixer.init()
        except Exception:
            pass

        print("🎤 Калибровка микрофона...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ Микрофон готов!")
        except Exception as e:
            print(f"⚠️ Микрофон: {e}")

    def _setup_fallback(self):
        self.fallback_engine.setProperty('rate', 170)
        self.fallback_engine.setProperty('volume', 1.0)
        voices = self.fallback_engine.getProperty('voices')
        for v in voices:
            if any(tag in v.name.lower() for tag in ['russian', 'ru', 'irina', 'milena', 'pavel']):
                self.fallback_engine.setProperty('voice', v.id)
                break

    def _clean_for_speech(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]*`', '', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'[#*_~>|{}\[\]]', '', text)
        text = re.sub(r'\n+', '. ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if not re.search(r'[а-яА-ЯёЁa-zA-Z]', text):
            return "Готово."
        return text[:400] + ("..." if len(text) > 400 else "")

    def speak(self, text: str):
        clean = self._clean_for_speech(text)
        if not clean: return
        print(f"\n🤖 {Config.AGENT_NAME}: {clean}")
        self.is_speaking = True
        try:
            asyncio.run(self._speak_edge_async(clean))
        except Exception as e:
            print(f"⚠️ Edge-TTS сбой: {e} → переключаюсь на офлайн")
            self._speak_fallback(clean)
        finally:
            self.is_speaking = False

    async def _speak_edge_async(self, text: str):
        temp_file = os.path.join(Config.BASE_DIR, "temp_voice.mp3")
        tts = edge_tts.Communicate(text, VOICE_NAME)
        await asyncio.wait_for(tts.save(temp_file), timeout=15.0)
        
        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 2048:
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            start = time.time()
            while pygame.mixer.music.get_busy() and (time.time() - start) < 30:
                await asyncio.sleep(0.1)
            pygame.mixer.music.unload()
            try: os.remove(temp_file)
            except: pass
        else:
            raise RuntimeError("Пустой или битый аудиофайл")

    def _speak_fallback(self, text: str):
        self.fallback_engine.say(text)
        self.fallback_engine.runAndWait()

    def listen(self, timeout=7, phrase_limit=15) -> str:
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
            print(f"❌ Микрофон: {e}")
            return ""

import time  # для таймаута в pygame