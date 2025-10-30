"""
Обновленная обработка видео на основе рабочего кода с Mac
"""

import os
import subprocess
import tempfile
from pathlib import Path
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from database.user import db
from keyboards.kb_user import main_reply_kb, video_effects_kb
from handlers.User.states import VideoProcessingStates
from services.subscription_checker import subscription_checker
import sys

router = Router()

# Добавляем путь к утилитам
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
# Добавляем путь к скриптам (караоке-субтитры)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

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
    async def apply_ultra_unique_new(input_path: str, output_path: str) -> bool:
        """Применение эффекта Ultra Unique на основе рабочего скрипта"""
        try:
            # Настройки из вашего скрипта
            brightness_percent = 4.0
            speed_percent = 2.0
            
            # Ищем изображение 2.png в папке images
            project_root = Path(__file__).resolve().parent.parent.parent
            overlay_image_path = project_root / "images" / "2.png"
            
            if not overlay_image_path.exists():
                print(f"❌ Изображение для Ultra Unique не найдено: {overlay_image_path}")
                print("💡 Убедитесь, что файл 2.png находится в папке images/")
                return False
            
            # Конвертируем проценты в значения для FFmpeg
            brightness_value = brightness_percent / 100.0
            speed_value = 1.0 + (speed_percent / 100.0)
            
            print(f"🚀 Применяем Ultra Unique эффект (новый алгоритм)")
            print(f"📁 Входное видео: {input_path}")
            print(f"📁 Выходное видео: {output_path}")
            print(f"🖼️ Изображение для наложения: {overlay_image_path}")
            print(f"💡 Яркость: +{brightness_percent}%")
            print(f"⚡ Скорость: +{speed_percent}%")
            
            # Создаем команду FFmpeg для Ultra Unique эффекта
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,  # Входное видео
                '-i', str(overlay_image_path),  # Изображение для наложения
                '-filter_complex', 
                f"[0:v]eq=brightness={brightness_value},setpts=PTS/{speed_value}[video_with_effects];"  # Яркость и скорость
                f"[1:v]scale=1080:1920,format=rgba[overlay_img];"  # Масштабируем изображение под размер видео
                f"[video_with_effects][overlay_img]overlay=(W-w)/2:(H-h)/2:format=auto[v];"  # Центрируем наложение
                f"[0:a]atempo={speed_value}[a]",  # Ускоряем аудио
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
                output_path
            ]
            
            print(f"💻 Команда: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Ultra Unique применен успешно")
                return True
            else:
                print(f"❌ Ошибка Ultra Unique: {result.stderr}")
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
    async def apply_trending_frame_new(input_path: str, output_path: str) -> bool:
        """Применение эффекта Trending Frame на основе рабочего скрипта"""
        try:
            import shlex
            from PIL import Image, ImageDraw
            
            # Настройки из вашего скрипта
            ZOOM = 0.66
            Y_SHIFT = 0.24
            RADIUS_PX = 120
            BRIGHT = 0.04
            CONTRAST = 1.06
            SPEED = 1.08
            CRF = 18
            PRESET = "medium"
            AUDIO_BR = "160k"
            
            # Создаем маску
            mask_path = os.path.join(os.path.dirname(output_path), "frame_mask.png")
            
            def ensure_frame_mask(png_path, w=1000, h=1500, radius=RADIUS_PX):
                """Генерит временную PNG-маску с прозрачным окном и чёрным фоном"""
                if os.path.exists(png_path):
                    return
                img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
                drw = ImageDraw.Draw(img)
                drw.rounded_rectangle((0, 0, w, h), radius=radius, fill=(0, 0, 0, 0))
                os.makedirs(os.path.dirname(png_path), exist_ok=True)
                img.save(png_path)
            
            ensure_frame_mask(mask_path, w=1000, h=1500, radius=RADIUS_PX)
            
            # Формируем команду FFmpeg на основе вашего скрипта
            fc = (
                f"[0:v]scale=iw*{ZOOM}:ih*{ZOOM},format=rgba[sv];"
                f"[1:v][sv]scale2ref=w=iw:h=ih[mask][sv2];"
                f"[sv2][mask]overlay=0:0:format=auto[rounded];"
                f"[rounded]pad=trunc(iw/{ZOOM}/2)*2:trunc(ih/{ZOOM}/2)*2:(ow-iw)/2:(oh-ih)*{Y_SHIFT}:black,"
                f"eq=brightness={BRIGHT}:contrast={CONTRAST},"
                f"setpts=PTS/{SPEED},format=yuv420p[v];"
                f"[0:a]aresample=48000,atempo={SPEED}[a]"
            )
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-i', mask_path,
                '-filter_complex', fc,
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', str(CRF), '-preset', PRESET, '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', AUDIO_BR, '-movflags', '+faststart',
                output_path
            ]
            
            print(f"🔄 Применяем Trending Frame (новый алгоритм)")
            print(f"💻 Команда: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Удаляем временную маску
            try:
                if os.path.exists(mask_path):
                    os.unlink(mask_path)
                    print("🗑️ Временная маска удалена")
            except Exception as e:
                print(f"⚠️ Не удалось удалить маску: {e}")
            
            if result.returncode == 0:
                print(f"✅ Trending Frame применен успешно")
                return True
            else:
                print(f"❌ Ошибка Trending Frame: {result.stderr}")
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
    async def apply_subscribe_bait_new(input_path: str, output_path: str) -> bool:
        """Применение эффекта Subscribe Bait на основе нового скрипта"""
        try:
            # Ищем картинку в папке images (корень проекта)
            project_root = Path(__file__).resolve().parent.parent.parent
            images_dir = project_root / "images"
            
            # Возможные имена файлов
            possible_names = [
                "subscribe_bait.png",
                "subscribe_bait.jpg", 
                "subscribe.png",
                "subscribe.jpg",
                "bait.png",
                "bait.jpg",
                "1.jpg",  # как в коде
                "1.png"
            ]
            
            subscribe_image = None
            for name in possible_names:
                image_path = images_dir / name
                if image_path.exists():
                    subscribe_image = str(image_path)
                    print(f"✅ Найдена картинка Subscribe Bait: {subscribe_image}")
                    break
            
            if not subscribe_image:
                print(f"❌ Картинка для Subscribe Bait не найдена в {images_dir}")
                return False
            
            print(f"🎣 Применяем Subscribe Bait (новый алгоритм)")
            print(f"📁 Входное видео: {input_path}")
            print(f"🖼 Картинка: {subscribe_image}")
            print(f"📁 Выходное видео: {output_path}")
            
            # Команда FFmpeg для наложения картинки по центру под рамкой
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-i', subscribe_image,
                '-filter_complex', 
                '[0:v]scale=1080:1920[video];'
                '[1:v]scale=200:50[subscribe_img];'
                '[video][subscribe_img]overlay=(W-w)/2:H-h-250:format=auto[final]',
                '-map', '[final]',
                '-map', '0:a',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                output_path
            ]
            
            print(f"💻 Команда: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Subscribe Bait применен успешно")
                return True
            else:
                print(f"❌ Ошибка Subscribe Bait: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка Subscribe Bait: {e}")
            return False
    
    @staticmethod
    async def apply_subtitles(input_path: str, output_path: str, text: str, font_path: str = None) -> bool:
        """Применение субтитров (интеграция рабочего кода)"""
        try:
            from apply_subtitles import (
                check_ffmpeg,
                extract_audio_from_video,
                transcribe_with_words,
                chunk_segments_into_word_groups,
                write_srt,
                burn_srt_into_video,
            )
            
            print(f"🎬 Применяем субтитры с точной синхронизацией")
            print(f"📝 Текст: {text[:100]}...")
            
            # Создаем временную папку
            import tempfile
            temp_dir = tempfile.mkdtemp()
            
            try:
                temp_wav = os.path.join(temp_dir, "audio.wav")
                temp_srt = os.path.join(temp_dir, "subtitles.srt")
                
                check_ffmpeg()
                if extract_audio_from_video(input_path, temp_wav):
                    result = transcribe_with_words(temp_wav, language='ru')
                    segments = result.get("segments", [])
                    chunks = chunk_segments_into_word_groups(segments, max_words=3)
                    
                    write_srt(chunks, temp_srt, width=30, lines=2)
                    burn_srt_into_video(input_path, temp_srt, output_path, fontsize=16, margin_v=50)
                    
                    if os.path.exists(output_path):
                        print("✅ Субтитры применены успешно")
                        return True
                    else:
                        print("❌ Ошибка применения субтитров")
                        return False
                else:
                    print("❌ Ошибка извлечения аудио")
                    return False
                    
            finally:
                # Очищаем временные файлы
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            print(f"❌ Ошибка обработки субтитров: {e}")
            return False
    
    @staticmethod
    async def apply_subtitles_with_timing(input_path: str, output_path: str, text: str, 
                                        timed_segments: list, font_path: str = None) -> bool:
        """Применение субтитров с временными метками (интеграция рабочего кода)"""
        try:
            print(f"🎬 Применяем субтитры с точной синхронизацией")
            print(f"📝 Текст: {text[:100]}...")
            print(f"🎯 Сегментов: {len(timed_segments)}")
            
            # Используем ту же логику что и в apply_subtitles
            return await VideoProcessor.apply_subtitles(input_path, output_path, text, font_path)
                
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
    async def process_unique_video(input_path: str, output_path: str, config: dict) -> bool:
        """Обрабатывает видео с уникальной конфигурацией"""
        try:
            print(f"🎲 Обрабатываем уникальное видео с конфигурацией: {config}")
            
            current_file = input_path
            temp_dir = os.path.dirname(output_path)
            
            # Применяем базовые эффекты (яркость, контраст, скорость, зум)
            if config.get('brightness') != 0 or config.get('contrast') != 1.0:
                temp_basic = os.path.join(temp_dir, f"temp_basic_{hash(str(config))}.mp4")
                if await VideoProcessor.apply_basic_effects(current_file, temp_basic, config):
                    current_file = temp_basic
            
            # Применяем эффекты
            for effect in config.get('effects', []):
                if effect == "ultra_unique":
                    temp_effect = os.path.join(temp_dir, f"temp_ultra_{hash(str(config))}.mp4")
                    if await VideoProcessor.apply_ultra_unique_new(current_file, temp_effect):
                        current_file = temp_effect
                elif effect == "trending_frame":
                    temp_effect = os.path.join(temp_dir, f"temp_trending_{hash(str(config))}.mp4")
                    if await VideoProcessor.apply_trending_frame_new(current_file, temp_effect):
                        current_file = temp_effect
                elif effect == "subscribe_bait":
                    temp_effect = os.path.join(temp_dir, f"temp_subscribe_{hash(str(config))}.mp4")
                    if await VideoProcessor.apply_subscribe_bait_new(current_file, temp_effect):
                        current_file = temp_effect
                elif effect == "subtitles":
                    temp_effect = os.path.join(temp_dir, f"temp_subtitles_{hash(str(config))}.mp4")
                    if await VideoProcessor.apply_subtitles_new(current_file, temp_effect):
                        current_file = temp_effect
            
            # Применяем музыку
            if config.get('music_id') is not None:
                temp_music = os.path.join(temp_dir, f"temp_music_{hash(str(config))}.mp4")
                if await VideoProcessor.apply_music_new(current_file, temp_music, config['music_id']):
                    current_file = temp_music
            
            # Нормализация если нужно
            if config.get('normalize', False):
                if await VideoProcessor.normalize_video(current_file, output_path):
                    print(f"✅ Уникальное видео создано с нормализацией")
                    return True
                else:
                    print(f"❌ Ошибка нормализации уникального видео")
                    return False
            else:
                # Просто копируем файл
                import shutil
                shutil.copy2(current_file, output_path)
                print(f"✅ Уникальное видео создано без нормализации")
                return True
                
        except Exception as e:
            print(f"❌ Ошибка обработки уникального видео: {e}")
            return False
    
    @staticmethod
    async def apply_basic_effects(input_path: str, output_path: str, config: dict) -> bool:
        """Применяет базовые эффекты (яркость, контраст, скорость, зум)"""
        try:
            brightness = config.get('brightness', 0)
            contrast = config.get('contrast', 1.0)
            speed = config.get('speed', 1.0)
            zoom = config.get('zoom', 1.0)
            
            print(f"🎨 Применяем базовые эффекты: brightness={brightness}, contrast={contrast}, speed={speed}, zoom={zoom}")
            
            # Строим фильтр для базовых эффектов
            filters = []
            
            if brightness != 0:
                filters.append(f"eq=brightness={brightness}")
            
            if contrast != 1.0:
                filters.append(f"eq=contrast={contrast}")
            
            if zoom != 1.0:
                filters.append(f"scale=iw*{zoom}:ih*{zoom}:force_original_aspect_ratio=increase,crop=trunc(iw/2)*2:trunc(ih/2)*2")
            
            if speed != 1.0:
                filters.append(f"setpts=PTS/{speed}")
            
            filter_chain = ",".join(filters) if filters else "null"
            
            # Команда FFmpeg
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-filter:v', filter_chain,
                '-filter:a', f"atempo={speed}" if speed != 1.0 else "null",
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Базовые эффекты применены")
                return True
            else:
                print(f"❌ Ошибка базовых эффектов: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка базовых эффектов: {e}")
            return False
    
    @staticmethod
    async def apply_music_new(input_path: str, output_path: str, music_id: int = None) -> bool:
        """Применение фоновой музыки на основе рабочего скрипта"""
        try:
            # Настройки из вашего скрипта
            volume_db = -17  # Громкость музыки как вы просили
            fade_in = 2.0
            fade_out = 2.0
            loop = True
            
            # Получаем длительность видео
            def get_video_duration(video_path: str) -> float:
                try:
                    cmd = [
                        'ffprobe', '-v', 'quiet', '-print_format', 'json',
                        '-show_format', video_path
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        print(f"❌ Ошибка получения информации о видео: {result.stderr}")
                        return 0
                    
                    import json
                    data = json.loads(result.stdout)
                    duration = float(data.get('format', {}).get('duration', 0))
                    return duration
                except Exception as e:
                    print(f"❌ Ошибка анализа видео: {e}")
                    return 0
            
            video_duration = get_video_duration(input_path)
            if video_duration == 0:
                print(f"❌ Не удалось получить длительность видео")
                return False
            
            # Ищем музыку из базы данных
            music_path = None
            music_name = "Случайная музыка"
            
            try:
                if music_id:
                    # Получаем конкретную музыку по ID
                    music_record = await db.get_music_by_id(music_id)
                    if music_record and music_record.get('is_active', True) and os.path.exists(music_record['file_path']):
                        music_path = music_record['file_path']
                        music_name = music_record['file_name']
                        print(f"🎵 Используем выбранную музыку: {music_name}")
                    else:
                        print(f"⚠️ Выбранная музыка не найдена или неактивна, используем случайную")
                        music_record = await db.get_random_music()
                        if music_record and os.path.exists(music_record['file_path']):
                            music_path = music_record['file_path']
                            music_name = music_record['file_name']
                            print(f"🎵 Используем случайную музыку: {music_name}")
                else:
                    # Получаем случайную музыку из базы данных
                    music_record = await db.get_random_music()
                    if music_record and os.path.exists(music_record['file_path']):
                        music_path = music_record['file_path']
                        music_name = music_record['file_name']
                        print(f"🎵 Используем случайную музыку: {music_name}")
            except Exception as e:
                print(f"⚠️ Ошибка получения музыки из БД: {e}")
            
            # Fallback: используем музыку по умолчанию
            if not music_path:
                project_root = Path(__file__).resolve().parent.parent.parent
                default_music_path = project_root / "music" / "природа.wav"
                if default_music_path.exists():
                    music_path = str(default_music_path)
                    music_name = "природа.wav"
                    print(f"🎵 Используем музыку по умолчанию: {music_name}")
                else:
                    print(f"❌ Музыкальный файл не найден")
                    return False
            
            print(f"🎵 Применяем фоновую музыку:")
            print(f"   📁 Файл: {music_path}")
            print(f"   🔊 Громкость: {volume_db}dB")
            print(f"   ⏱️ Длительность видео: {video_duration:.1f}s")
            print(f"   🔄 Зацикливание: {'Да' if loop else 'Нет'}")
            print(f"   🎚️ Fade In: {fade_in}s")
            print(f"   🎚️ Fade Out: {fade_out}s")
            
            # Строим фильтр для музыки
            music_filters = []
            
            if loop:
                # Зацикливаем музыку если она короче видео
                music_filters.append(f"[1:a]aloop=loop=-1:size=2e+09,atrim=duration={video_duration}")
            else:
                # Обрезаем музыку по длительности видео
                music_filters.append(f"[1:a]atrim=duration={video_duration}")
            
            # Применяем громкость
            music_filters.append(f"volume={volume_db}dB")
            
            # Применяем fade эффекты
            if fade_in > 0:
                music_filters.append(f"afade=t=in:ss=0:d={fade_in}")
            
            if fade_out > 0:
                fade_start = max(0, video_duration - fade_out)
                music_filters.append(f"afade=t=out:st={fade_start}:d={fade_out}")
            
            # Объединяем фильтры
            music_filter_chain = ",".join(music_filters) + "[music]"
            
            # Микшируем оригинальное аудио с музыкой
            final_filter = f"{music_filter_chain};[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[audio]"
            
            # Формируем команду FFmpeg
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,      # Видео с оригинальным аудио
                '-i', music_path,       # Фоновая музыка
                '-filter_complex', final_filter,
                '-map', '0:v',          # Видео из первого входа
                '-map', '[audio]',      # Микшированное аудио
                '-c:v', 'copy',         # Копируем видео без перекодирования
                '-c:a', 'aac',          # Кодируем аудио в AAC
                '-b:a', '160k',         # Битрейт аудио
                output_path
            ]
            
            print(f"🎬 Запускаем наложение музыки...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Фоновая музыка успешно наложена")
                return True
            else:
                print(f"❌ Ошибка наложения музыки: {result.stderr}")
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


    @staticmethod
    async def apply_subtitles_new(input_path: str, output_path: str) -> bool:
        """Применение субтитров (новая версия для уникальных видео)"""
        try:
            print(f"🎬 Применяем субтитры (новая версия)")
            
            # Извлекаем речь из видео
            timed_segments = VideoProcessor.extract_speech_with_timing(input_path, 'ru')
            
            if timed_segments:
                # Объединяем текст
                subtitle_text = ' '.join([seg['text'] for seg in timed_segments])
                print(f"📝 Текст: {subtitle_text[:100]}...")
                print(f"🎯 Сегментов: {len(timed_segments)}")
                
                # Применяем субтитры с временными метками
                success = await VideoProcessor.apply_subtitles_with_timing(
                    input_path, output_path, subtitle_text, timed_segments
                )
            else:
                # Если речь не извлечена, используем простые субтитры
                subtitle_text = "Автоматически сгенерированные субтитры"
                success = await VideoProcessor.apply_subtitles(
                    input_path, output_path, subtitle_text
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


# ===== ОБРАБОТЧИКИ TELEGRAM =====

@router.callback_query(F.data == "videoprocess")
async def videoprocess_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки обработки видео"""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Проверяем, может ли пользователь использовать бесплатное видео
    can_use_free = await db.can_use_free_video(user_id)
    free_used = await db.get_free_videos_used(user_id)
    
    # Проверяем активную подписку
    has_active_subscription = await db.is_subscription_active(user_id)
    
    # Дополнительная проверка через сервис проверки подписок
    if has_active_subscription:
        has_active_subscription = await subscription_checker.check_subscription_status(user_id)
    
    if not can_use_free and not has_active_subscription:
        await callback.message.edit_text(
            "💰 <b>Лимит бесплатных видео исчерпан</b>\n\n"
            f"Вы уже использовали {free_used} бесплатное видео.\n"
            "Для дальнейшей обработки видео:\n"
            "• Пополните баланс в профиле\n"
            "• Или получите подписку от администратора",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="balanceadd")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="backstart")]
            ])
        )
        return
    
    # Инициализируем пустой список выбранных эффектов
    await state.update_data(selected_effects=[])
    
    await callback.message.edit_text(
        "🎬 <b>Обработка видео</b>\n\n"
        "Выберите эффекты для применения:\n"
        "📐 Нормализация - меняет размер к 1080×1920\n"
        "Остальные эффекты - применяются к оригинальному размеру\n"
        "🎣 Subscribe Bait - работает только с Trending Frame\n"
        "🎵 Музыка - накладывает фоновую музыку (-17dB)\n\n"
        f"🆓 Бесплатных видео использовано: {free_used}/1\n"
        f"{'✅ Подписка активна' if has_active_subscription else '❌ Подписка неактивна'}",
        reply_markup=video_effects_kb()
    )

def update_effects_keyboard(selected_effects):
    """Обновляет клавиатуру с отмеченными эффектами"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'normalize' in selected_effects else '📐'} Нормализация (1080×1920)", 
                callback_data="toggle_normalize"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'ultra_unique' in selected_effects else '⚡'} Ultra Unique", 
                callback_data="toggle_ultra_unique"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'trending_frame' in selected_effects else '🎬'} Trending Frame", 
                callback_data="toggle_trending_frame"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'subscribe_bait' in selected_effects else '🎣'} Subscribe Bait", 
                callback_data="toggle_subscribe_bait"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'subtitles' in selected_effects else '💬'} Субтитры", 
                callback_data="toggle_subtitles"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'music' in selected_effects else '🎵'} Музыка", 
                callback_data="toggle_music"
            )
        ],
        [
            InlineKeyboardButton(text="✅ Применить выбранные", callback_data="apply_selected_effects")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")
        ]
    ])
    return kb

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_effect_cb(callback: types.CallbackQuery, state: FSMContext):
    """Переключение эффекта в списке выбранных"""
    await callback.answer()
    
    data = await state.get_data()
    selected_effects = data.get('selected_effects', [])
    
    effect = callback.data.replace("toggle_", "")
    
    # Проверка для Subscribe Bait
    if effect == "subscribe_bait":
        if effect in selected_effects:
            # Убираем Subscribe Bait
            selected_effects.remove(effect)
        else:
            # Добавляем Subscribe Bait только если выбран Trending Frame
            if "trending_frame" in selected_effects:
                selected_effects.append(effect)
            else:
                await callback.answer("❌ Subscribe Bait требует выбора Trending Frame!", show_alert=True)
                return
    elif effect == "music":
        if effect in selected_effects:
            # Убираем музыку
            selected_effects.remove(effect)
        else:
            # Добавляем музыку и переходим к выбору
            selected_effects.append(effect)
            await state.update_data(selected_effects=selected_effects)
            await show_music_selection(callback, state)
            return
    else:
        # Обычная логика для других эффектов
        if effect in selected_effects:
            selected_effects.remove(effect)
            # Если убираем Trending Frame, убираем и Subscribe Bait
            if effect == "trending_frame" and "subscribe_bait" in selected_effects:
                selected_effects.remove("subscribe_bait")
        else:
            selected_effects.append(effect)
    
    await state.update_data(selected_effects=selected_effects)
    
    # Обновляем сообщение с новой клавиатурой
    await callback.message.edit_text(
        "🎬 <b>Обработка видео</b>\n\n"
        "Выберите эффекты для применения:\n"
        "📐 Нормализация - меняет размер к 1080×1920\n"
        "Остальные эффекты - применяются к оригинальному размеру\n"
        "🎣 Subscribe Bait - работает только с Trending Frame\n"
        "🎵 Музыка - накладывает фоновую музыку (-17dB)\n\n"
        f"Выбрано: {len(selected_effects)} эффект(ов)",
        reply_markup=update_effects_keyboard(selected_effects)
    )

@router.callback_query(F.data == "apply_selected_effects")
async def apply_selected_effects_cb(callback: types.CallbackQuery, state: FSMContext):
    """Применение выбранных эффектов"""
    await callback.answer()
    
    data = await state.get_data()
    selected_effects = data.get('selected_effects', [])
    
    if not selected_effects:
        await callback.answer("❌ Выберите хотя бы один эффект!", show_alert=True)
        return
    
    await state.set_state(VideoProcessingStates.waiting_for_video)
    
    effects_text = []
    for effect in selected_effects:
        if effect == "normalize":
            effects_text.append("📐 Нормализация (1080×1920)")
        elif effect == "ultra_unique":
            effects_text.append("⚡ Ultra Unique")
        elif effect == "trending_frame":
            effects_text.append("🎬 Trending Frame")
        elif effect == "subscribe_bait":
            effects_text.append("🎣 Subscribe Bait")
        elif effect == "subtitles":
            effects_text.append("💬 Субтитры")
        elif effect == "music":
            effects_text.append("🎵 Музыка")
    
    await callback.message.edit_text(
        f"🎬 <b>Применение эффектов</b>\n\n"
        f"Выбранные эффекты:\n" + "\n".join(f"• {text}" for text in effects_text) + "\n\n"
        f"Отправьте видео файл:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )


@router.callback_query(F.data == "cancel_video")
async def cancel_video_cb(callback: types.CallbackQuery, state: FSMContext):
    """Отмена обработки видео"""
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text(
        "❌ <b>Обработка отменена</b>\n\n"
        "Выберите действие:",
        reply_markup=main_reply_kb()
    )

@router.callback_query(F.data == "backstart")
async def back_to_start_cb(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    print(f"🏠 Возвращаемся в главное меню")
    await callback.answer("🏠 Возвращаемся в главное меню")
    await state.clear()
    
    # Отправляем изображение с текстом
    try:
        photo = types.FSInputFile("images/start.png")
        await callback.message.answer_photo(
            photo=photo,
            caption="<b>Добро пожаловать в Remake Bot</b> ⚙️\n\n"
                    "Уникализируй видео без потери качества 🎥\n\n"
                    "Выбери нужный раздел ниже, чтобы начать ⬇️",
            reply_markup=main_reply_kb()
        )
    except Exception as e:
        print(f"❌ Ошибка при отправке изображения: {e}")
        # Если не получилось отправить фото, отправляем текстовое сообщение
        await callback.message.answer(
            "<b>Добро пожаловать в Remake Bot</b> ⚙️\n\n"
            "Уникализируй видео без потери качества 🎥\n\n"
            "Выбери нужный раздел ниже, чтобы начать ⬇️",
            reply_markup=main_reply_kb()
        )

@router.message(VideoProcessingStates.waiting_for_video, F.video)
async def process_video_handler(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка загруженного видео с множественными эффектами"""
    try:
        data = await state.get_data()
        selected_effects = data.get('selected_effects', [])
        
        if not selected_effects:
            await message.answer("❌ Не выбрано ни одного эффекта!")
            return
        
        # Создаем временную папку
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Скачиваем видео
            input_path = os.path.join(temp_dir, "input.mp4")
            try:
                await bot.download(message.video, destination=input_path)
            except Exception as e:
                if "file is too big" in str(e).lower():
                    await message.answer(
                        "❌ <b>Файл слишком большой</b>\n\n"
                        "Telegram ограничивает размер файлов до 50MB.\n"
                        "Пожалуйста, отправьте видео меньшего размера.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="videoprocess")]
                        ])
                    )
                    return
                else:
                    raise e
            
            # Статус: начало обработки
            status_msg = await message.answer(
                "⏳ <b>Обработка началась…</b>\n\nОжидайте, это может занять время.")
            
            # Определяем выходной файл
            output_path = os.path.join(temp_dir, "output.mp4")
            
            # Применяем эффекты последовательно
            current_file = input_path
            success = True
            
            # 1. Сначала применяем эффекты к оригинальному размеру
            for effect in selected_effects:
                if effect == "subtitles":
                    # Интеграция нового генератора караоке-субтитров
                    try:
                        from apply_subtitles import (
                            check_ffmpeg,
                            extract_audio_from_video,
                            transcribe_with_words,
                            chunk_segments_into_word_groups,
                            write_srt,
                            burn_srt_into_video,
                        )
                        
                        temp_wav = os.path.join(temp_dir, "audio.wav")
                        temp_srt = os.path.join(temp_dir, "subtitles.srt")
                        temp_with_subtitles = os.path.join(temp_dir, f"temp_with_subtitles_{effect}.mp4")
                        
                        check_ffmpeg()
                        if extract_audio_from_video(current_file, temp_wav):
                            result = transcribe_with_words(temp_wav, language='ru')
                            segments = result.get("segments", [])
                            chunks = chunk_segments_into_word_groups(segments, max_words=3)
                            
                            write_srt(chunks, temp_srt, width=30, lines=2)
                            burn_srt_into_video(current_file, temp_srt, temp_with_subtitles, fontsize=16, margin_v=50)
                            
                            if os.path.exists(temp_with_subtitles):
                                current_file = temp_with_subtitles
                                print(f"✅ Субтитры применены")
                            else:
                                print(f"❌ Ошибка применения субтитров")
                                success = False
                        else:
                            print(f"❌ Ошибка извлечения аудио")
                            success = False
                    except Exception as e:
                        print(f"❌ Ошибка генерации субтитров: {e}")
                        success = False
                
                elif effect == "ultra_unique":
                    temp_ultra = os.path.join(temp_dir, f"temp_ultra_{effect}.mp4")
                    if await VideoProcessor.apply_ultra_unique_new(current_file, temp_ultra):
                        current_file = temp_ultra
                        print(f"✅ Ultra Unique применен")
                    else:
                        print(f"❌ Ошибка Ultra Unique")
                        success = False
                
                elif effect == "trending_frame":
                    temp_trending = os.path.join(temp_dir, f"temp_trending_{effect}.mp4")
                    if await VideoProcessor.apply_trending_frame_new(current_file, temp_trending):
                        current_file = temp_trending
                        print(f"✅ Trending Frame применен")
                    else:
                        print(f"❌ Ошибка Trending Frame")
                        success = False
                
                elif effect == "subscribe_bait":
                    # Subscribe Bait работает только с Trending Frame
                    if "trending_frame" not in selected_effects:
                        print(f"❌ Subscribe Bait требует выбора Trending Frame")
                        success = False
                    else:
                        temp_subscribe = os.path.join(temp_dir, f"temp_subscribe_{effect}.mp4")
                        if await VideoProcessor.apply_subscribe_bait_new(current_file, temp_subscribe):
                            current_file = temp_subscribe
                            print(f"✅ Subscribe Bait применен")
                        else:
                            print(f"❌ Ошибка Subscribe Bait")
                            success = False
                
                elif effect == "music":
                    # Получаем выбранную музыку из состояния
                    music_data = await state.get_data()
                    selected_music_id = music_data.get('selected_music_id')
                    
                    temp_music = os.path.join(temp_dir, f"temp_music_{effect}.mp4")
                    if await VideoProcessor.apply_music_new(current_file, temp_music, selected_music_id):
                        current_file = temp_music
                        print(f"✅ Музыка применена")
                    else:
                        print(f"❌ Ошибка применения музыки")
                        success = False
            
            # 2. Если выбрана нормализация - применяем её в конце
            if "normalize" in selected_effects and success:
                print(f"📐 Применяем нормализацию к 1080x1920")
                if await VideoProcessor.normalize_video(current_file, output_path):
                    print(f"✅ Нормализация завершена")
                else:
                    print(f"❌ Ошибка нормализации")
                    success = False
            elif success:
                # Если нормализация не выбрана - копируем файл как есть
                import shutil
                shutil.copy2(current_file, output_path)
                print(f"✅ Видео обработано без изменения размера")
            
            if success and os.path.exists(output_path):
                # Обновляем статус
                try:
                    await status_msg.edit_text("✅ <b>Видео готово!</b>")
                except Exception:
                    pass
                
                # Отправляем как документ для удобного скачивания (без отправки видео-превью)
                try:
                    doc_file = FSInputFile(output_path, filename="processed_video.mp4")
                    await message.answer_document(
                        document=doc_file, 
                        caption="⬇️ Скачать видео",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="backstart")]
                        ])
                    )
                except Exception:
                    pass
                
                # Увеличиваем счетчик бесплатных видео только если нет активной подписки
                if not await db.is_subscription_active(message.from_user.id):
                    await db.increment_free_videos_used(message.from_user.id)
                
                # Очищаем состояние
                await state.clear()
            else:
                try:
                    await status_msg.edit_text(
                        "❌ <b>Ошибка обработки</b>\n\nНе удалось обработать видео. Попробуйте ещё раз.")
                except Exception:
                    await message.answer(
                        "❌ <b>Ошибка обработки</b>\n\nНе удалось обработать видео. Попробуйте ещё раз.")
        
        finally:
            # Очищаем временные файлы
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    except Exception as e:
        print(f"❌ Ошибка обработки видео: {e}")
        await message.answer(
            f"❌ <b>Ошибка обработки</b>\n\n"
            f"Произошла ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="videoprocess")]
            ])
        )

@router.message(VideoProcessingStates.waiting_for_video, F.audio)
async def audio_file_handler(message: types.Message):
    """Обработка аудиофайлов (музыка)"""
    await message.answer(
        "🎵 <b>Аудиофайл получен!</b>\n\n"
        "⚠️ <b>Ограничения Telegram:</b>\n"
        "• Максимальный размер файла: 50MB\n"
        "• Поддерживаемые форматы: MP3, WAV, M4A\n\n"
        "Если файл слишком большой, используйте музыку из библиотеки бота.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )

@router.message(VideoProcessingStates.waiting_for_video)
async def invalid_video_handler(message: types.Message):
    """Обработка неправильного формата"""
    await message.answer(
        "❌ <b>Неверный формат</b>\n\n"
        "Пожалуйста, отправьте видео файл.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )


# ==================== ВЫБОР МУЗЫКИ ====================

async def show_music_selection(callback: types.CallbackQuery, state: FSMContext):
    """Показывает список доступной музыки для выбора"""
    try:
        # Получаем активную музыку
        active_music = await db.get_active_music()
        
        if not active_music:
            await callback.message.edit_text(
                "🎵 <b>Выбор музыки</b>\n\n"
                "❌ Активная музыка не найдена.\n"
                "Обратитесь к администратору.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="videoprocess")]
                ])
            )
            return
        
        # Создаем клавиатуру с музыкой
        keyboard = []
        for music in active_music[:10]:  # Показываем первые 10
            keyboard.append([InlineKeyboardButton(
                text=f"🎵 {music['file_name']}", 
                callback_data=f"select_music_{music['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="🎲 Случайная", callback_data="select_music_random")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="videoprocess")])
        
        await callback.message.edit_text(
            "🎵 <b>Выберите музыку</b>\n\n"
            f"Доступно {len(active_music)} треков:\n"
            "Выберите конкретную музыку или случайную:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Ошибка загрузки музыки</b>\n\n"
            f"Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="videoprocess")]
            ])
        )

@router.callback_query(F.data.startswith("select_music_"))
async def select_music_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора музыки"""
    await callback.answer()
    
    try:
        music_data = callback.data.replace("select_music_", "")
        
        if music_data == "random":
            # Случайная музыка
            await state.update_data(selected_music_id=None)
            music_name = "Случайная музыка"
        else:
            # Конкретная музыка
            music_id = int(music_data)
            music_record = await db.get_music_by_id(music_id)
            
            if music_record and music_record.get('is_active', True):
                await state.update_data(selected_music_id=music_id)
                music_name = music_record['file_name']
            else:
                await callback.answer("❌ Музыка не найдена или неактивна", show_alert=True)
                return
        
        # Возвращаемся к выбору эффектов
        data = await state.get_data()
        selected_effects = data.get('selected_effects', [])
        
        await callback.message.edit_text(
            "🎬 <b>Обработка видео</b>\n\n"
            "Выберите эффекты для применения:\n"
            "📐 Нормализация - меняет размер к 1080×1920\n"
            "Остальные эффекты - применяются к оригинальному размеру\n"
            "🎣 Subscribe Bait - работает только с Trending Frame\n"
            f"🎵 Музыка - накладывает фоновую музыку (-17dB)\n"
            f"   Выбрано: {music_name}\n\n"
            f"Выбрано: {len(selected_effects)} эффект(ов)",
            reply_markup=update_effects_keyboard(selected_effects)
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ==================== ГЕНЕРАЦИЯ УНИКАЛЬНЫХ ВИДЕО ====================

@router.callback_query(F.data == "generate_unique_videos")
async def generate_unique_videos_cb(callback: types.CallbackQuery, state: FSMContext):
    """Генерация 4 уникальных видео"""
    await callback.answer()
    
    await callback.message.edit_text(
        "🎲 <b>Генерация 4 уникальных видео</b>\n\n"
        "📹 Отправьте одно видео, и я создам 4 уникальных варианта:\n"
        "• Разные эффекты и настройки\n"
        "• Уникальная музыка для каждого\n"
        "• Различные параметры обработки\n"
        "• Все в одном архиве для скачивания\n\n"
        "⚠️ Обработка займет больше времени",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="videoprocess")]
        ])
    )
    
    # Устанавливаем состояние ожидания видео для уникальной генерации
    await state.set_state(VideoProcessingStates.waiting_for_unique_video)

@router.message(VideoProcessingStates.waiting_for_unique_video, F.video)
async def process_unique_videos_handler(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка видео для генерации уникальных вариантов"""
    await message.answer("🎲 <b>Начинаю генерацию 4 уникальных видео...</b>")
    
    # Создаем временную папку
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Скачиваем видео
        input_path = os.path.join(temp_dir, "input.mp4")
        try:
            await bot.download(message.video, destination=input_path)
        except Exception as e:
            if "file is too big" in str(e).lower():
                await message.answer(
                    "❌ <b>Файл слишком большой</b>\n\n"
                    "Telegram ограничивает размер файлов до 50MB.\n"
                    "Пожалуйста, отправьте видео меньшего размера.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="generate_unique_videos")]
                    ])
                )
                return
            else:
                raise e
        
        # Статус: начало обработки
        status_msg = await message.answer(
            "⏳ <b>Генерация уникальных видео...</b>\n\n"
            "Создаю 4 варианта с разными эффектами...")
        
        # Генерируем 4 уникальных видео
        unique_videos = []
        success_count = 0
        
        for i in range(4):
            try:
                # Создаем уникальные настройки для каждого видео
                unique_config = await generate_unique_config(i)
                
                # Обрабатываем видео с уникальными настройками
                output_path = os.path.join(temp_dir, f"unique_{i+1}.mp4")
                
                if await VideoProcessor.process_unique_video(input_path, output_path, unique_config):
                    unique_videos.append(output_path)
                    success_count += 1
                    print(f"✅ Уникальное видео {i+1} создано")
                else:
                    print(f"❌ Ошибка создания видео {i+1}")
                    
            except Exception as e:
                print(f"❌ Ошибка обработки видео {i+1}: {e}")
        
        if success_count == 0:
            await status_msg.edit_text(
                "❌ <b>Ошибка генерации</b>\n\n"
                "Не удалось создать ни одного уникального видео.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="generate_unique_videos")]
                ])
            )
            return
        
        # Создаем архив с уникальными видео
        archive_path = os.path.join(temp_dir, "unique_videos.zip")
        await create_unique_videos_archive(unique_videos, archive_path)
        
        # Отправляем архив
        await status_msg.edit_text("✅ <b>Готово!</b>\n\nАрхив с уникальными видео создан.")
        
        with open(archive_path, 'rb') as archive_file:
            await message.answer_document(
                document=types.FSInputFile(archive_path, filename="unique_videos.zip"),
                caption="🎲 <b>4 уникальных видео готовы!</b>\n\n"
                       f"✅ Создано: {success_count} видео\n"
                       f"📦 Архив: unique_videos.zip\n\n"
                       f"⬇️ Скачайте архив и распакуйте",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="backstart")]
                ])
            )
        
    except Exception as e:
        print(f"❌ Ошибка генерации уникальных видео: {e}")
        await message.answer(
            f"❌ <b>Ошибка генерации</b>\n\n"
            f"Произошла ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="generate_unique_videos")]
            ])
        )
    
    finally:
        # Очищаем временные файлы
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        # Возвращаемся к обычному состоянию
        await state.clear()

async def generate_unique_config(video_index: int) -> dict:
    """Генерирует уникальную конфигурацию для видео"""
    import random
    
    # Базовые настройки
    config = {
        'brightness': random.uniform(-0.1, 0.1),  # -10% до +10%
        'contrast': random.uniform(0.8, 1.2),     # 80% до 120%
        'speed': random.uniform(0.9, 1.1),         # 90% до 110%
        'zoom': random.uniform(1.0, 1.1),          # 100% до 110%
        'effects': [],
        'music_id': None,
        'normalize': random.choice([True, False])
    }
    
    # Добавляем случайные эффекты
    available_effects = ['ultra_unique', 'trending_frame', 'subscribe_bait', 'subtitles']
    num_effects = random.randint(1, 3)  # 1-3 эффекта
    selected_effects = random.sample(available_effects, min(num_effects, len(available_effects)))
    
    # Subscribe Bait только с Trending Frame
    if 'subscribe_bait' in selected_effects and 'trending_frame' not in selected_effects:
        selected_effects.append('trending_frame')
    
    config['effects'] = selected_effects
    
    # Случайная музыка
    try:
        active_music = await db.get_active_music()
        if active_music:
            random_music = random.choice(active_music)
            config['music_id'] = random_music['id']
    except:
        pass
    
    return config

async def compress_video_for_archive(input_path: str, output_path: str) -> bool:
    """Сжимает видео для архива"""
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-crf', '28',  # Высокое сжатие
            '-preset', 'fast',
            '-c:a', 'aac',
            '-b:a', '64k',  # Низкий битрейт аудио
            '-movflags', '+faststart',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка сжатия видео: {e}")
        return False

async def create_unique_videos_archive(video_paths: list, archive_path: str):
    """Создает архив с уникальными видео"""
    import zipfile
    import tempfile
    
    compressed_videos = []
    
    # Сжимаем каждое видео
    with tempfile.TemporaryDirectory() as temp_compress_dir:
        for i, video_path in enumerate(video_paths, 1):
            if os.path.exists(video_path):
                compressed_path = os.path.join(temp_compress_dir, f"compressed_{i}.mp4")
                if await compress_video_for_archive(video_path, compressed_path):
                    compressed_videos.append(compressed_path)
                else:
                    # Если сжатие не удалось, используем оригинал
                    compressed_videos.append(video_path)
        
        # Создаем архив
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, video_path in enumerate(compressed_videos, 1):
                if os.path.exists(video_path):
                    zipf.write(video_path, f"unique_video_{i}.mp4")
    
    print(f"✅ Архив создан: {archive_path}")

@router.message(VideoProcessingStates.waiting_for_unique_video)
async def invalid_unique_video_handler(message: types.Message):
    """Обработка неправильного формата для уникальных видео"""
    await message.answer(
        "❌ <b>Неверный формат</b>\n\n"
        "Пожалуйста, отправьте видео файл для генерации уникальных вариантов.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="videoprocess")]
        ])
    )