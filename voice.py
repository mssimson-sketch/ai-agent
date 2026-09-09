"""
Голосовой модуль с поддержкой живого нейросетевого голоса Microsoft (Edge-TTS)
"""
import os
import asyncio
import threading
import edge_tts
import pygame
import speech_recognition as sr
from config import Config

# Голос: "ru-RU-DmitryNeural" (мужской) или "ru-RU-SvetlanaNeural" (женский)
VOICE_NAME = "ru-RU-DmitryNeural"


class VoiceEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_speaking = False
        
        # Инициализация звукового плеера
        try:
            pygame.mixer.init()
        except:
            pass

        print("🎤 Калибровка микрофона (2 сек)...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ Микрофон откалиброван!")
        except Exception as e:
            print(f"⚠️ Микрофон: {e}")

    def speak(self, text: str):
        """Озвучить текст живым нейросетевым голосом"""
        if not text or not text.strip():
            return

        print(f"\n🤖 {Config.AGENT_NAME}: {text}")
        self.is_speaking = True

        try:
            # Генерация аудио через Microsoft Edge TTS
            temp_file = os.path.join(Config.BASE_DIR, "temp_voice.mp3")
            
            async def _generate():
                tts = edge_tts.Communicate(text[:600], VOICE_NAME, rate="+5%")
                await tts.save(temp_file)

            asyncio.run(_generate())

            # Воспроизведение
            if os.path.exists(temp_file):
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.music.unload()
                try:
                    os.remove(temp_file)
                except:
                    pass

        except Exception as e:
            print(f"❌ Ошибка синтеза речи: {e}")
        finally:
            self.is_speaking = False

    def listen(self, timeout=7, phrase_limit=15) -> str:
        """Слушать микрофон"""
        try:
            with self.microphone as source:
                print("👂 Слушаю...")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )

            print("🔄 Распознаю...")
            text = self.recognizer.recognize_google(
                audio,
                language=Config.VOICE_LANGUAGE
            )
            print(f"👤 Вы: {text}")
            return text.lower().strip()

        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except Exception as e:
            print(f"❌ Ошибка микрофона: {e}")
            return ""