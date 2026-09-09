"""
Голосовой модуль с очисткой текста и живым нейросетевым голосом (Edge-TTS)
"""
import os
import re
import asyncio
import pygame
import edge_tts
import speech_recognition as sr
from config import Config

VOICE_NAME = "ru-RU-DmitryNeural"  # или "ru-RU-SvetlanaNeural"


class VoiceEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_speaking = False
        
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

    def _clean_for_speech(self, text: str) -> str:
        """Очищает текст от технического мусора перед озвучкой"""
        if not text:
            return ""
        # Удаляем код, markdown, ссылки, спецсимволы
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]*`', '', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'[#*_~>|{}\[\]]', '', text)
        text = re.sub(r'\n+', '. ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Ограничиваем длину для комфортного прослушивания
        if len(text) > 450:
            text = text[:447] + "..."
        return text

    def speak(self, text: str):
        """Озвучить текст живым голосом"""
        clean_text = self._clean_for_speech(text)
        if not clean_text:
            return

        print(f"\n🤖 {Config.AGENT_NAME}: {clean_text}")
        self.is_speaking = True

        try:
            temp_file = os.path.join(Config.BASE_DIR, "temp_voice.mp3")
            
            async def _generate():
                tts = edge_tts.Communicate(clean_text, VOICE_NAME, rate="+5%")
                await tts.save(temp_file)

            asyncio.run(_generate())

            if os.path.exists(temp_file):
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.music.unload()
                try: os.remove(temp_file)
                except: pass
        except Exception as e:
            print(f"❌ Ошибка синтеза речи: {e}")
        finally:
            self.is_speaking = False

    def listen(self, timeout=7, phrase_limit=15) -> str:
        """Слушать микрофон"""
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