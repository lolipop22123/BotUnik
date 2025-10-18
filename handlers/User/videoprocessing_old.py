from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw

from config import ADMIN_ID
from database.user import db
from keyboards.kb_user import main_reply_kb, video_effects_kb
from handlers.User.states import VideoProcessingStates

router = Router()


class VideoProcessor:
    """Обработчик видео для Telegram бота"""
    
    # Список временных файлов для очистки
    _temp_files = []
    
    @staticmethod
    def _ffmpeg_escape_path(path: str) -> str:
        """
        Подготовить путь для использования внутри фильтра ffmpeg.
        -> переводим '\' в '/', экранируем двойные кавычки внутри и оборачиваем в двойные кавычки.
        """
        if not path:
            return '""'
        p = path.replace('\\', '/')
        p = p.replace('"', '\\"')   # экранируем двойные кавычки внутри пути
        return f'"{p}"'
    
    @staticmethod
    async def normalize_video(input_path: str, output_path: str) -> bool:
        """Нормализация видео 16:9 → 9:16"""
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return result.returncode == 0
                
        except Exception as e:
            print(f"❌ Ошибка нормализации: {e}")
            return False
    
    @staticmethod
    async def apply_ultra_unique(input_path: str, output_path: str) -> bool:
        """Применить Ultra Unique"""
        try:
            brightness = 1.05  # +5%
            speed = 1.03  # +3%
            
            brightness_value = (brightness - 1.0) * 0.5
            speed_value = speed
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', f'eq=brightness={brightness_value}',
                '-filter_complex', f'[0:v]setpts=PTS/{speed_value}[v];[0:a]atempo={speed_value}[a]',
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return result.returncode == 0
                
        except Exception as e:
            print(f"❌ Ошибка Ultra Unique: {e}")
            return False
    
    @staticmethod
    async def apply_trending_frame(input_path: str, output_path: str) -> bool:
        """Применить Trending Frame с округлением"""
        try:
            # Параметры
            total_w, total_h = 1080, 1920
            frame_w, frame_h = 1000, 1380
            top_offset = 165
            side_margin = 40
            corner_radius = 50
            
            # Создаем маску
            mask_path = tempfile.mktemp(suffix='.png')
            mask_img = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 255))
            draw = ImageDraw.Draw(mask_img)
            draw.rounded_rectangle((0, 0, frame_w, frame_h), radius=corner_radius, fill=(0, 0, 0, 0))
            mask_img.save(mask_path)
            
            # FFmpeg команда
            fc = (
                f"[0:v]scale={frame_w}:{frame_h}:force_original_aspect_ratio=increase,crop={frame_w}:{frame_h},format=rgba[sv];"
                f"[1:v][sv]scale2ref=w=iw:h=ih[mask][sv2];"
                f"[sv2][mask]overlay=0:0:format=auto[rounded];"
                f"[rounded]pad={total_w}:{total_h}:{side_margin}:{top_offset}:black,format=yuv420p[v]"
            )
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-i', mask_path,
                '-filter_complex', fc,
                '-map', '[v]',
                '-map', '0:a?',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            # Удаляем временную маску
            try:
                os.unlink(mask_path)
            except:
                pass
            
            return result.returncode == 0
                
        except Exception as e:
            print(f"❌ Ошибка Trending Frame: {e}")
            return False
    
    @staticmethod
    async def apply_subscribe_bait(input_path: str, output_path: str) -> bool:
        """Применить Subscribe Bait"""
        try:
            # Путь к картинке (создаем простую картинку если нет)
            subscribe_image_path = Path(__file__).parent.parent.parent / "images" / "1.jpg"
            
            # Если картинки нет, создаем простую
            if not subscribe_image_path.exists():
                subscribe_image_path.parent.mkdir(parents=True, exist_ok=True)
                img = Image.new('RGB', (400, 100), color=(255, 0, 0))
                draw = ImageDraw.Draw(img)
                # Просто красный прямоугольник без текста (текст требует шрифт)
                img.save(subscribe_image_path)
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-i', str(subscribe_image_path),
                '-filter_complex',
                '[0:v]scale=1080:1920[video];'
                '[1:v]scale=200:50[subscribe_img];'
                '[video][subscribe_img]overlay=(W-w)/2:H-h-250:format=auto[final]',
                '-map', '[final]',
                '-map', '0:a?',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return result.returncode == 0
                
        except Exception as e:
            print(f"❌ Ошибка Subscribe Bait: {e}")
            return False
    
    @staticmethod
    def _split_text_smart(words: list) -> list:
        """Умная разбивка текста на субтитры"""
        import re
        
        if not words:
            return []
        
        def get_word_class(word: str) -> str:
            clean_word = re.sub(r'[.,!?…:;]', '', word)
            length = len(clean_word)
            if length <= 5:
                return 'short'
            elif length <= 9:
                return 'medium'
            else:
                return 'long'
        
        phrases = []
        current_phrase = []
        current_length = 0
        
        for word in words:
            word_class = get_word_class(word)
            word_length = len(word)
            space_length = 1 if current_phrase else 0
            total_length = current_length + space_length + word_length
            
            # Проверяем лимит CPL (18 символов)
            if total_length > 18:
                if current_phrase:
                    phrases.append(' '.join(current_phrase))
                    current_phrase = []
                    current_length = 0
                current_phrase = [word]
                current_length = word_length
            else:
                current_phrase.append(word)
                current_length = total_length
            
            # Проверяем лимиты по классам слов
            should_break = False
            if word_class == 'long':
                should_break = True
            elif word_class == 'medium':
                medium_count = sum(1 for w in current_phrase if get_word_class(w) == 'medium')
                if medium_count >= 2:
                    should_break = True
            elif word_class == 'short':
                short_count = sum(1 for w in current_phrase if get_word_class(w) == 'short')
                if short_count >= 3:
                    should_break = True
            
            if should_break:
                phrases.append(' '.join(current_phrase))
                current_phrase = []
                current_length = 0
        
        if current_phrase:
            phrases.append(' '.join(current_phrase))
        
        return phrases
    
    @staticmethod
    def get_video_duration(video_path: str) -> float:
        """Получает длительность видео через ffprobe"""
        try:
            import json
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return 0
            
            data = json.loads(result.stdout)
            duration = float(data.get('format', {}).get('duration', 0))
            return duration
        except Exception as e:
            print(f"❌ Ошибка анализа видео: {e}")
            return 0
    
    @staticmethod
    def _create_drawtext_filter_adapted(text: str, font_path: str, start_time: float, end_time: float,
                                       fontcolor: str = "white", offset_x: int = 0, offset_y: int = 0) -> str:
        """Создает фильтр drawtext для FFmpeg с поддержкой кириллицы (без проблем на Windows)"""
        import tempfile
        
        # Создаем временный файл с текстом в UTF-8
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            f.write(text)
            text_file = f.name
            VideoProcessor._temp_files.append(text_file)  # Добавляем в список для очистки
        
        # Экранируем пути специально для ffmpeg (оборачиваем в двойные кавычки)
        text_file_escaped = VideoProcessor._ffmpeg_escape_path(text_file)
        font_path_escaped = VideoProcessor._ffmpeg_escape_path(font_path)
        
        # DEBUG: выводим информацию о путях
        print(f"🔤 Шрифт: {font_path}")
        print(f"📝 Текст файл: {text_file}")
        print(f"🔤 Экранированный шрифт: {font_path_escaped}")
        
        # Возвращаем filter-е выражение. Путь в двойных кавычках, enable в одинарных кавычках
        return (
            f"textfile={text_file_escaped}:"
            f"fontfile={font_path_escaped}:"
            f"fontsize=56:"
            f"fontcolor={fontcolor}:"
            f"x=(w-text_w)/2+{offset_x}:"
            f"y=h-600+{offset_y}:"
            f"enable='between(t,{start_time},{end_time})'"
        )
    
    @staticmethod
    def _cleanup_temp_files():
        """Очищает временные файлы"""
        for temp_file in VideoProcessor._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        VideoProcessor._temp_files.clear()
    
    @staticmethod
    def extract_speech_with_timing(video_path: str, language: str = 'ru') -> list:
        """Извлекает речь с временными метками через Whisper"""
        try:
            print(f"🎤 Извлекаем речь из видео (язык: {language})...")
            
            # Используем whisper
            import whisper
            
            # Загружаем модель whisper
            model = whisper.load_model("base")
            
            # Извлекаем аудио из видео
            result = model.transcribe(video_path, language=language)
            
            # Формируем сегменты с временными метками
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
    async def apply_subtitles(input_path: str, output_path: str, text: str, font_path: str) -> bool:
        """Применить субтитры с выбранным шрифтом (простая версия без временных меток)"""
        try:
            # Получаем длительность видео
            video_duration = VideoProcessor.get_video_duration(input_path)
            if video_duration == 0:
                print(f"❌ Не удалось получить длительность видео")
                return False
            
            # Умная разбивка текста
            words = text.lower().split()
            phrases = VideoProcessor._split_text_smart(words)
            
            if not phrases:
                phrases = [text.lower()[:50]]
            
            # Создаем временные интервалы для каждой фразы
            duration_per_phrase = video_duration / len(phrases)
            min_duration = 2.0
            max_duration = 4.0
            duration_per_phrase = max(min_duration, min(duration_per_phrase, max_duration))
            
            # Строим drawtext фильтры
            drawtext_filters = []
            
            for i, phrase in enumerate(phrases):
                start_time = i * duration_per_phrase
                end_time = min(start_time + duration_per_phrase, video_duration)
                
                # Создаем фильтр с тенью и основным текстом
                shadow_filter = VideoProcessor._create_drawtext_filter_adapted(
                    phrase, font_path, start_time, end_time, 
                    fontcolor="black@0.8", offset_x=3, offset_y=3
                )
                main_filter = VideoProcessor._create_drawtext_filter_adapted(
                    phrase, font_path, start_time, end_time,
                    fontcolor="white", offset_x=0, offset_y=0
                )
                
                drawtext_filters.extend([shadow_filter, main_filter])
            
            # Применяем субтитры группами по 6 фильтров (рекомендация ChatGPT)
            current_file = input_path
            temp_files = []
            
            try:
                chunk_size = 1  # Минимальный размер для отладки
                for i in range(0, len(drawtext_filters), chunk_size):
                    chunk = drawtext_filters[i:i + chunk_size]
                    combined_filter = ",".join(f"drawtext={filter_text}" for filter_text in chunk)
                    
                    # DEBUG: распечатываем первые 1000 символов фильтра
                    print(f"DEBUG combined_filter (chunk {i//chunk_size+1}): {combined_filter[:1000]}...")
                    
                    if i + chunk_size < len(drawtext_filters):
                        # Промежуточный файл
                        temp_file = output_path.replace('.mp4', f'_temp_{i}.mp4')
                        temp_files.append(temp_file)
                    else:
                        # Финальный файл
                        temp_file = output_path
                    
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', current_file,
                        '-vf', combined_filter,
                        '-c:v', 'libx264',
                        '-crf', '18',
                        '-preset', 'medium',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy',
                        temp_file
                    ]
                    
                    print(f"💻 Обрабатываем чанк {i//chunk_size + 1}/{(len(drawtext_filters) + chunk_size - 1)//chunk_size}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode != 0:
                        print(f"❌ Ошибка FFmpeg в чанке {i//chunk_size + 1}:")
                        print(f"STDERR: {result.stderr}")
                        print(f"STDOUT: {result.stdout}")
                        return False
                    
                    current_file = temp_file
                
                # Очищаем временные файлы
                VideoProcessor._cleanup_temp_files()
                
                # Удаляем промежуточные файлы
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except:
                        pass
                
                return True
                
            except Exception as e:
                print(f"❌ Ошибка обработки чанков: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка Subtitles: {e}")
            return False
    
    @staticmethod
    def apply_subtitles_with_timing(input_path: str, output_path: str, subtitle_text: str, 
                                  font_path: str, timed_segments: list = None, 
                                  theme: str = "Comedy & Memes", video_speed: float = 1.0) -> bool:
        """Применяет субтитры с точной синхронизацией (с временными метками из Whisper)"""
        try:
            if not timed_segments:
                # Если нет временных меток, используем простые субтитры
                import asyncio
                return asyncio.run(VideoProcessor.apply_subtitles(input_path, output_path, subtitle_text, font_path))
            
            print(f"🎬 Применяем субтитры с точной синхронизацией")
            print(f"📝 Текст: {subtitle_text[:100]}...")
            print(f"🎯 Сегментов: {len(timed_segments)}")
            print(f"⚡ Скорость: {video_speed}x")
            
            # Проверяем переданный шрифт
            if not font_path or not os.path.exists(font_path):
                print(f"❌ Шрифт не найден: {font_path}")
                return False
            
            # Умная разбивка текста
            words = subtitle_text.lower().split()
            phrases = VideoProcessor._split_text_smart(words)
            
            print(f"📊 Разбито на {len(phrases)} фраз")
            
            # Создаем фильтры drawtext
            drawtext_filters = []
            
            # Используем точные временные метки
            for i, phrase in enumerate(phrases):
                if i < len(timed_segments):
                    segment = timed_segments[i]
                    start_time = segment["start"] / video_speed
                    end_time = segment["end"] / video_speed
                    
                    # Создаем фильтр с тенью и основным текстом
                    shadow_filter = VideoProcessor._create_drawtext_filter_adapted(
                        phrase, font_path, start_time, end_time, 
                        fontcolor="black@0.8", offset_x=3, offset_y=3
                    )
                    main_filter = VideoProcessor._create_drawtext_filter_adapted(
                        phrase, font_path, start_time, end_time,
                        fontcolor="white", offset_x=0, offset_y=0
                    )
                    
                    drawtext_filters.extend([shadow_filter, main_filter])
            
            if not drawtext_filters:
                print(f"❌ Не удалось создать фильтры субтитров")
                return False
            
            # Применяем субтитры группами по 6 фильтров
            current_file = input_path
            temp_files = []
            
            try:
                chunk_size = 1  # Минимальный размер для отладки
                for i in range(0, len(drawtext_filters), chunk_size):
                    chunk = drawtext_filters[i:i + chunk_size]
                    combined_filter = ",".join(f"drawtext={filter_text}" for filter_text in chunk)
                    
                    # DEBUG: распечатываем первые 1000 символов
                    print(f"DEBUG combined_filter (chunk {i//chunk_size+1}): {combined_filter[:1000]}...")
                    
                    if i + chunk_size < len(drawtext_filters):
                        # Промежуточный файл
                        temp_file = output_path.replace('.mp4', f'_temp_{i}.mp4')
                        temp_files.append(temp_file)
                    else:
                        # Финальный файл
                        temp_file = output_path
                    
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', current_file,
                        '-vf', combined_filter,
                        '-c:v', 'libx264',
                        '-crf', '18',
                        '-preset', 'medium',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy',
                        temp_file
                    ]
                    
                    print(f"💻 Обрабатываем чанк {i//chunk_size + 1}/{(len(drawtext_filters) + chunk_size - 1)//chunk_size}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode != 0:
                        print(f"❌ Ошибка FFmpeg в чанке {i//chunk_size + 1}:")
                        print(f"STDERR: {result.stderr}")
                        print(f"STDOUT: {result.stdout}")
                        return False
                    
                    current_file = temp_file
                
                # Очищаем временные файлы
                VideoProcessor._cleanup_temp_files()
                
                # Удаляем промежуточные файлы
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except:
                        pass
                
                print(f"✅ Субтитры применены успешно")
                return True
                
            except Exception as e:
                print(f"❌ Ошибка обработки чанков: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка применения субтитров: {e}")
            return False
    
    @staticmethod
    async def apply_music(input_path: str, output_path: str, music_path: str, 
                         volume_db: float = -15, fade_in: float = 2.0, 
                         fade_out: float = 2.0, loop: bool = True) -> bool:
        """Добавить фоновую музыку (с fade эффектами и зацикливанием)"""
        try:
            # Получаем длительность видео
            video_duration = VideoProcessor.get_video_duration(input_path)
            if video_duration == 0:
                print(f"❌ Не удалось получить длительность видео")
                return False
            
            print(f"🎵 Применяем фоновую музыку:")
            print(f"   📁 Файл: {music_path}")
            print(f"   🔊 Громкость: {volume_db}dB")
            print(f"   ⏱️ Длительность видео: {video_duration:.1f}s")
            
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
                '-i', music_path,      # Фоновая музыка
                '-filter_complex', final_filter,
                '-map', '0:v',         # Видео из первого входа
                '-map', '[audio]',     # Микшированное аудио
                '-c:v', 'copy',        # Копируем видео без перекодирования
                '-c:a', 'aac',         # Кодируем аудио в AAC
                '-b:a', '160k',        # Битрейт аудио
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return result.returncode == 0
                
        except Exception as e:
            print(f"❌ Ошибка Music: {e}")
            return False


@router.callback_query(F.data == "videoprcess")
async def videoprcess_cb(callback: types.CallbackQuery):
    """Главное меню обработки видео"""
    try:
        await callback.message.delete()
        
        user_id = callback.from_user.id
        
        # Админ имеет полный доступ
        if user_id == ADMIN_ID:
            await callback.message.answer(
                "🎬 <b>Обработка видео</b>\n\n"
                "Выберите эффект для обработки видео:",
                reply_markup=video_effects_kb()
            )
            return
        
        # Проверка подписки
        if not await db.has_subscription(user_id):
            await callback.message.answer(
                "🚫 <b>У вас нет подписки</b>\n\n"
                "Для обработки видео необходима активная подписка.\n"
                "Пожалуйста, приобретите подписку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💰 Купить подписку", callback_data="balanceadd")],
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="backstart")]
                ])
            )
            return
        
        if not await db.is_subscription_active(user_id):
            await callback.message.answer(
                "⌛ <b>Ваша подписка истекла</b>\n\n"
                "Пожалуйста, продлите подписку для обработки видео.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💰 Продлить подписку", callback_data="balanceadd")],
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="backstart")]
                ])
            )
            return
        
        # Подписка активна - показываем меню эффектов
        end_date = await db.get_subscription_end_date(user_id)
        await callback.message.answer(
            f"✅ <b>Подписка активна</b>\n"
            f"📅 Действует до: {end_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            "🎬 Выберите эффект для обработки видео:",
            reply_markup=video_effects_kb()
        )
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=main_reply_kb()
        )


@router.callback_query(F.data.startswith("effect_"))
async def select_effect_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора эффекта"""
    effect = callback.data.replace("effect_", "")
    
    # Сохраняем выбранный эффект в состоянии
    await state.update_data(effect=effect)
    
    # Если выбраны субтитры - предлагаем выбрать шрифт
    if effect == "subtitles":
        fonts = await db.get_all_fonts()
        
        if not fonts:
            await callback.message.answer(
                "❌ <b>Нет доступных шрифтов</b>\n\n"
                "Администратор еще не добавил шрифты.\n"
                "Попробуйте другой эффект.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="videoprcess")]
                ])
            )
            await callback.answer()
            return
        
        # Формируем кнопки выбора шрифта
        buttons = []
        for font in fonts:
            buttons.append([
                InlineKeyboardButton(
                    text=f"🔤 {font['file_name']}",
                    callback_data=f"select_font_{font['id']}"
                )
            ])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")])
        
        await callback.message.edit_text(
            "💬 <b>Субтитры</b>\n\n"
            f"📊 Доступно шрифтов: {len(fonts)}\n\n"
            "Выберите шрифт для субтитров:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await state.set_state(VideoProcessingStates.choosing_font)
        await callback.answer()
        return
    # Если выбрана музыка - предлагаем выбрать трек
    if effect == "music":
        music_list = await db.get_all_music()
        
        if not music_list:
            await callback.message.answer(
                "❌ <b>Нет доступной музыки</b>\n\n"
                "Администратор еще не добавил музыку.\n"
                "Попробуйте другой эффект.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="videoprcess")]
                ])
            )
            await callback.answer()
            return
        
        # Формируем кнопки выбора музыки
        buttons = []
        for music in music_list:
            duration_min = music['duration'] // 60
            duration_sec = music['duration'] % 60
            buttons.append([
                InlineKeyboardButton(
                    text=f"🎵 {music['file_name']} ({duration_min}:{duration_sec:02d})",
                    callback_data=f"select_music_{music['id']}"
                )
            ])
        buttons.append([
            InlineKeyboardButton(text="🎲 Случайная", callback_data="select_music_random")
        ])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")])
        
        await callback.message.edit_text(
            "🎵 <b>Добавить музыку</b>\n\n"
            f"📊 Доступно треков: {len(music_list)}\n\n"
            "Выберите музыку для видео:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await state.set_state(VideoProcessingStates.choosing_music)
        await callback.answer()
        return
    
    # Для остальных эффектов - сразу просим видео
    await state.set_state(VideoProcessingStates.waiting_for_video)
    
    effect_names = {
        "ultra_unique": "⚡ Ultra Unique",
        "trending_frame": "🎬 Trending Frame",
        "subscribe_bait": "🎣 Subscribe Bait",
        "all": "🌟 Все эффекты",
        "normalize": "📐 Нормализация 16:9 → 9:16"
    }
    
    await callback.message.answer(
        f"✅ Выбран эффект: <b>{effect_names.get(effect, effect)}</b>\n\n"
        "📹 Отправьте видео для обработки\n\n"
        "⚠️ Максимальный размер: 50 МБ\n"
        "⏱ Обработка может занять несколько минут",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_video")
async def cancel_video_cb(callback: types.CallbackQuery, state: FSMContext):
    """Отмена обработки видео"""
    await state.clear()
    await callback.message.answer(
        "❌ Обработка отменена",
        reply_markup=main_reply_kb()
    )
    await callback.answer()


# ==================== ОБРАБОТЧИКИ ВЫБОРА ШРИФТА ====================

@router.callback_query(F.data.startswith("select_font_"))
async def select_font_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора шрифта"""
    font_id = int(callback.data.split("_")[-1])
    
    # Получаем информацию о шрифте
    font = await db.get_font_by_id(font_id)
    
    if not font:
        await callback.answer("❌ Шрифт не найден", show_alert=True)
        return
    
    # Преобразуем относительный путь в абсолютный
    font_path = font['file_path']
    if not os.path.isabs(font_path):
        # Если путь относительный, делаем его абсолютным относительно корня проекта
        font_path = os.path.abspath(font_path)
    
    # Проверяем существование файла шрифта
    if not os.path.exists(font_path):
        await callback.answer(f"❌ Файл шрифта не найден: {font_path}", show_alert=True)
        return
    
    # Сохраняем выбранный шрифт
    await state.update_data(font_id=font_id, font_path=font_path, font_name=font['file_name'])
    
    # Переходим к выбору музыки (текст будет извлечен автоматически из видео)
    music_tracks = await db.get_all_music()
    if not music_tracks:
        await callback.message.edit_text(
            f"✅ <b>Шрифт выбран:</b> {font['file_name']}\n\n"
            "🎤 <b>Текст субтитров будет извлечен автоматически из видео</b>\n\n"
            "❌ Музыкальные треки не найдены. Обработка видео без музыки.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📹 Загрузить видео", callback_data="process_video_no_music")]
            ])
        )
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎵 {music['file_name']}", callback_data=f"music_{music['id']}")]
        for music in music_tracks
    ] + [
        [InlineKeyboardButton(text="📹 Без музыки", callback_data="process_video_no_music")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
    ])
    
    await callback.message.edit_text(
        f"✅ <b>Шрифт выбран:</b> {font['file_name']}\n\n"
        "🎵 <b>Выберите музыкальный трек:</b>\n"
        "<i>Текст субтитров будет извлечен автоматически из видео</i>",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "process_video_no_music")
async def process_video_no_music_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка видео без музыки"""
    # Просим отправить видео
    await callback.message.edit_text(
        "📹 <b>Отправьте видео для обработки</b>\n\n"
        "⚠️ Максимальный размер: 50 МБ\n"
        "⏱ Обработка может занять несколько минут\n\n"
        "🎤 <b>Текст субтитров будет извлечен автоматически</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )
    await state.set_state(VideoProcessingStates.waiting_for_video)
    await callback.answer()


# ==================== ОБРАБОТЧИКИ ВЫБОРА МУЗЫКИ ====================

@router.callback_query(F.data.startswith("music_"))
async def select_music_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора музыки"""
    music_id = int(callback.data.split("_")[-1])
    music = await db.get_music_by_id(music_id)
    
    if not music:
        await callback.answer("❌ Музыка не найдена", show_alert=True)
        return
    
    # Сохраняем выбранную музыку
    await state.update_data(
        music_id=music['id'],
        music_path=music['file_path'],
        music_name=music['file_name']
    )
    
    # Просим отправить видео
    duration_min = music['duration'] // 60
    duration_sec = music['duration'] % 60
    
    await callback.message.edit_text(
        f"✅ <b>Музыка выбрана:</b> {music['file_name']}\n"
        f"⏱ Длительность: {duration_min}:{duration_sec:02d}\n\n"
        "📹 Отправьте видео для обработки\n\n"
        "⚠️ Максимальный размер: 50 МБ\n"
        "⏱ Обработка может занять несколько минут",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )
    await state.set_state(VideoProcessingStates.waiting_for_video)
    await callback.answer()


@router.message(VideoProcessingStates.waiting_for_video, F.video)
async def process_video_handler(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка загруженного видео"""
    user_data = await state.get_data()
    effect = user_data.get("effect")
    
    # Проверка размера файла
    if message.video.file_size > 50 * 1024 * 1024:  # 50 МБ
        await message.answer(
            "❌ <b>Файл слишком большой</b>\n\n"
            "Максимальный размер: 50 МБ\n"
            "Попробуйте загрузить меньшее видео."
        )
        return
    
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer(
        "⏳ <b>Обработка началась...</b>\n\n"
        "Пожалуйста, подождите. Это может занять несколько минут."
    )
    
    temp_dir = None
    
    try:
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        
        # Скачиваем видео
        file = await bot.get_file(message.video.file_id)
        input_path = os.path.join(temp_dir, f"input{Path(file.file_path).suffix}")
        await bot.download_file(file.file_path, input_path)
        
        await processing_msg.edit_text(
            "⏳ <b>Видео загружено</b>\n\n"
            f"Применяем эффект: {effect}..."
        )
        
        # Обрабатываем видео
        current_file = input_path
        processor = VideoProcessor()
        
        # Применяем эффекты последовательно
        if effect == "normalize":
            output_path = os.path.join(temp_dir, 'result.mp4')
            if not await processor.normalize_video(current_file, output_path):
                raise Exception("Ошибка нормализации")
            current_file = output_path
            
        elif effect == "ultra_unique":
            output_path = os.path.join(temp_dir, 'result.mp4')
            if not await processor.apply_ultra_unique(current_file, output_path):
                raise Exception("Ошибка Ultra Unique")
            current_file = output_path
            
        elif effect == "trending_frame":
            output_path = os.path.join(temp_dir, 'result.mp4')
            if not await processor.apply_trending_frame(current_file, output_path):
                raise Exception("Ошибка Trending Frame")
            current_file = output_path
            
        elif effect == "subscribe_bait":
            output_path = os.path.join(temp_dir, 'result.mp4')
            if not await processor.apply_subscribe_bait(current_file, output_path):
                raise Exception("Ошибка Subscribe Bait")
            current_file = output_path
        
        elif effect == "subtitles":
            # Применяем субтитры с автоматическим извлечением текста
            font_path = user_data.get("font_path")
            music_path = user_data.get("music_path")
            
            if not font_path:
                raise Exception("Не указан шрифт")
            
            await processing_msg.edit_text(
                "⏳ <b>Извлекаем текст из видео...</b>\n\n"
                "Это может занять несколько минут..."
            )
            
            # Автоматически извлекаем текст из видео с временными метками
            segments = processor.extract_speech_with_timing(current_file, language='ru')
            
            if not segments:
                raise Exception("Не удалось извлечь текст из видео")
            
            # Объединяем весь текст
            subtitle_text = " ".join([segment["text"] for segment in segments])
            
            await processing_msg.edit_text(
                "⏳ <b>Применяем субтитры с точной синхронизацией...</b>\n\n"
                f"Извлеченный текст: {subtitle_text[:100]}...\n"
                f"Сегментов: {len(segments)}"
            )
            
            # Применяем субтитры с временными метками
            temp_subtitles = os.path.join(temp_dir, 'subtitles.mp4')
            
            # Определяем скорость видео (по умолчанию 1.0)
            video_speed = 1.0
            
            if not processor.apply_subtitles_with_timing(
                current_file, temp_subtitles, subtitle_text, font_path, 
                segments, "Comedy & Memes", video_speed
            ):
                raise Exception("Ошибка Subtitles")
            
            # Если есть музыка, применяем её
            if music_path:
                await processing_msg.edit_text(
                    "⏳ <b>Добавляем музыку...</b>"
                )
                
                output_path = os.path.join(temp_dir, 'result.mp4')
                if not await processor.apply_music(temp_subtitles, output_path, music_path):
                    raise Exception("Ошибка Music")
                current_file = output_path
            else:
                current_file = temp_subtitles
        
        elif effect == "music":
            # Применяем музыку
            music_path = user_data.get("music_path")
            
            if not music_path:
                raise Exception("Не указана музыка")
            
            output_path = os.path.join(temp_dir, 'result.mp4')
            if not await processor.apply_music(current_file, output_path, music_path):
                raise Exception("Ошибка Music")
            current_file = output_path
            
        elif effect == "all":
            # Применяем все эффекты последовательно
            temp_ultra = os.path.join(temp_dir, 'ultra.mp4')
            if not await processor.apply_ultra_unique(current_file, temp_ultra):
                raise Exception("Ошибка Ultra Unique")
            
            temp_trending = os.path.join(temp_dir, 'trending.mp4')
            if not await processor.apply_trending_frame(temp_ultra, temp_trending):
                raise Exception("Ошибка Trending Frame")
            
            output_path = os.path.join(temp_dir, 'result.mp4')
            if not await processor.apply_subscribe_bait(temp_trending, output_path):
                raise Exception("Ошибка Subscribe Bait")
            
            current_file = output_path
        
        # Отправляем результат
        await processing_msg.edit_text(
            "📤 <b>Отправляем результат...</b>"
        )
        
        video_file = FSInputFile(current_file)
        await message.answer_video(
            video=video_file,
            caption="✅ <b>Обработка завершена!</b>\n\n"
                   f"Эффект: {effect}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎬 Обработать еще", callback_data="videoprcess")],
                [InlineKeyboardButton(text=" ⬅️ Главное меню", callback_data="backstart")]
            ])
        )
        
        await processing_msg.delete()
        await state.clear()
        
    except Exception as e:
        print(f"❌ Ошибка обработки видео: {e}")
        await processing_msg.edit_text(
            "❌ <b>Ошибка при обработке видео</b>\n\n"
            "Попробуйте еще раз или обратитесь в поддержку.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="videoprcess")],
                [InlineKeyboardButton(text="🌐 Поддержка", url="https://t.me/makker_o")]
            ])
        )
        await state.clear()
        
    finally:
        # Очищаем временные файлы
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


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

