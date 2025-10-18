"""
Обновленная обработка видео на основе рабочего кода с Mac
"""

import os
import subprocess
import tempfile
from pathlib import Path
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from database.user import db
from keyboards.kb_user import video_effects_kb
import sys

# Добавляем путь к утилитам
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))

class VideoProcessor:
    """Класс для обработки видео на основе мак-кода"""
    
    @staticmethod
    async def normalize_video(input_path: str, output_path: str) -> bool:
        """Нормализация видео к 1080x1920"""
        try:
            from video_processing import process_video_advanced
            
            print(f"📐 Нормализация видео к 1080x1920")
            result = process_video_advanced(input_path, output_path)
            
            if result is True or (hasattr(result, 'returncode') and result.returncode == 0):
                print(f"✅ Нормализация завершена успешно")
                return True
            else:
                print(f"❌ Ошибка нормализации: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка нормализации: {e}")
            return False
    
    @staticmethod
    async def apply_ultra_unique(input_path: str, output_path: str) -> bool:
        """Применение эффекта Ultra Unique"""
        try:
            from video_processing import process_video_advanced
            
            print(f"🚀 Применяем Ultra Unique эффект")
            result = process_video_advanced(input_path, output_path, apply_ultra_unique=True)
            
            if result is True or (hasattr(result, 'returncode') and result.returncode == 0):
                print(f"✅ Ultra Unique применен успешно")
                return True
            else:
                print(f"❌ Ошибка Ultra Unique: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка Ultra Unique: {e}")
            return False
    
    @staticmethod
    async def apply_trending_frame(input_path: str, output_path: str) -> bool:
        """Применение эффекта Trending Frame"""
        try:
            from video_processing import process_video_advanced
            
            print(f"🔄 Применяем Trending Frame")
            result = process_video_advanced(input_path, output_path, apply_trending_frame=True)
            
            if result is True or (hasattr(result, 'returncode') and result.returncode == 0):
                print(f"✅ Trending Frame применен успешно")
                return True
            else:
                print(f"❌ Ошибка Trending Frame: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка Trending Frame: {e}")
            return False
    
    @staticmethod
    async def apply_subscribe_bait(input_path: str, output_path: str) -> bool:
        """Применение эффекта Subscribe Bait"""
        try:
            from video_processing import process_video_advanced
            
            print(f"🎣 Применяем Subscribe Bait")
            result = process_video_advanced(input_path, output_path, apply_subscribe_bait=True)
            
            if result is True or (hasattr(result, 'returncode') and result.returncode == 0):
                print(f"✅ Subscribe Bait применен успешно")
                return True
            else:
                print(f"❌ Ошибка Subscribe Bait: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка Subscribe Bait: {e}")
            return False
    
    @staticmethod
    async def apply_subtitles(input_path: str, output_path: str, text: str, font_path: str = None) -> bool:
        """Применение субтитров на основе мак-кода"""
        try:
            from simple_subtitles import apply_simple_subtitles
            
            print(f"🎬 Применяем субтитры с точной синхронизацией")
            print(f"📝 Текст: {text[:100]}...")
            
            # Применяем субтитры используя новую реализацию
            success = apply_simple_subtitles(
                input_path, 
                output_path, 
                text,
                timed_segments=None,  # Пока без временных меток
                theme="default",
                video_speed=1.0
            )
            
            if success:
                print("✅ Субтитры применены успешно")
                return True
            else:
                print("❌ Ошибка применения субтитров")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка обработки субтитров: {e}")
            return False
    
    @staticmethod
    async def apply_subtitles_with_timing(input_path: str, output_path: str, text: str, 
                                        timed_segments: list, font_path: str = None) -> bool:
        """Применение субтитров с временными метками"""
        try:
            from simple_subtitles import apply_simple_subtitles
            
            print(f"🎬 Применяем субтитры с точной синхронизацией")
            print(f"📝 Текст: {text[:100]}...")
            print(f"🎯 Сегментов: {len(timed_segments)}")
            
            # Применяем субтитры с временными метками
            success = apply_simple_subtitles(
                input_path, 
                output_path, 
                text,
                timed_segments=timed_segments,
                theme="default",
                video_speed=1.0
            )
            
            if success:
                print("✅ Субтитры применены успешно")
                return True
            else:
                print("❌ Ошибка применения субтитров")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка обработки субтитров: {e}")
            return False
    
    @staticmethod
    async def apply_music(input_path: str, output_path: str, music_path: str = None) -> bool:
        """Применение фоновой музыки"""
        try:
            print(f"🎵 Применяем фоновую музыку")
            
            # Простая реализация наложения музыки
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-i', music_path or 'default_music.mp3',
                '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2',
                '-c:v', 'copy',
                '-c:a', 'aac',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Музыка применена успешно")
                return True
            else:
                print(f"❌ Ошибка применения музыки: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка применения музыки: {e}")
            return False
    
    @staticmethod
    def extract_speech_with_timing(video_path: str, language: str = 'ru') -> list:
        """Извлечение речи с временными метками через Whisper"""
        try:
            import whisper
            
            print(f"🎤 Извлекаем речь из видео (язык: {language})...")
            
            # Загружаем модель Whisper
            model = whisper.load_model("base")
            
            # Извлекаем речь с временными метками
            result = model.transcribe(video_path, language=language)
            
            # Формируем сегменты
            segments = []
            for segment in result["segments"]:
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip()
                })
            
            if segments:
                print(f"✅ Извлечено {len(segments)} сегментов речи")
                return segments
            else:
                print(f"⚠️ В видео не найдена речь")
                return []
                
        except ImportError:
            print(f"❌ Whisper не установлен. Установите: pip install openai-whisper")
            return []
        except Exception as e:
            print(f"❌ Ошибка извлечения речи: {e}")
            return []
