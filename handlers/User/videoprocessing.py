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
import sys

router = Router()

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


# ===== ОБРАБОТЧИКИ TELEGRAM =====

@router.callback_query(F.data == "videoprocess")
async def videoprocess_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки обработки видео"""
    await callback.answer()
    
    await callback.message.edit_text(
        "🎬 <b>Обработка видео</b>\n\n"
        "Выберите эффект для применения:",
        reply_markup=video_effects_kb()
    )

@router.callback_query(F.data == "normalize")
async def select_normalize_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора эффекта нормализации"""
    await callback.answer()
    
    await state.update_data(effect="normalize")
    await state.set_state(VideoProcessingStates.waiting_for_video)
    
    await callback.message.edit_text(
        "📐 <b>Нормализация видео</b>\n\n"
        "Видео будет приведено к формату 9:16 (1080x1920)\n\n"
        "Отправьте видео файл:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )

@router.callback_query(F.data == "ultra_unique")
async def select_ultra_unique_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора эффекта Ultra Unique"""
    await callback.answer()
    
    await state.update_data(effect="ultra_unique")
    await state.set_state(VideoProcessingStates.waiting_for_video)
    
    await callback.message.edit_text(
        "🚀 <b>Ultra Unique эффект</b>\n\n"
        "Применяется яркость + скорость + уникализация\n\n"
        "Отправьте видео файл:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )

@router.callback_query(F.data == "trending_frame")
async def select_trending_frame_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора эффекта Trending Frame"""
    await callback.answer()
    
    await state.update_data(effect="trending_frame")
    await state.set_state(VideoProcessingStates.waiting_for_video)
    
    await callback.message.edit_text(
        "🔄 <b>Trending Frame</b>\n\n"
        "Применяются скругленные углы и уникализация\n\n"
        "Отправьте видео файл:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )

@router.callback_query(F.data == "subscribe_bait")
async def select_subscribe_bait_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора эффекта Subscribe Bait"""
    await callback.answer()
    
    await state.update_data(effect="subscribe_bait")
    await state.set_state(VideoProcessingStates.waiting_for_video)
    
    await callback.message.edit_text(
        "🎣 <b>Subscribe Bait</b>\n\n"
        "Добавляется призыв к подписке и уникализация\n\n"
        "Отправьте видео файл:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )

@router.callback_query(F.data == "subtitles")
async def select_subtitles_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора эффекта субтитров"""
    await callback.answer()
    
    # Получаем список шрифтов
    fonts = await db.get_all_fonts()
    if not fonts:
        await callback.message.edit_text(
            "❌ <b>Шрифты не найдены</b>\n\n"
            "Администратор не добавил шрифты для субтитров.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
            ])
        )
        return
    
    # Создаем клавиатуру с шрифтами
    keyboard = []
    for font in fonts[:10]:  # Показываем первые 10 шрифтов
        keyboard.append([InlineKeyboardButton(
            text=f"🔤 {font['file_name']}", 
            callback_data=f"select_font_{font['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")])
    
    await state.update_data(effect="subtitles")
    await state.set_state(VideoProcessingStates.choosing_font)
    
    await callback.message.edit_text(
        "🎬 <b>Субтитры</b>\n\n"
        "Выберите шрифт для субтитров:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("select_font_"))
async def select_font_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора шрифта"""
    await callback.answer()
    
    font_id = int(callback.data.split("_")[-1])
    font = await db.get_font_by_id(font_id)
    
    if not font:
        await callback.answer("❌ Шрифт не найден", show_alert=True)
        return
    
    # Преобразуем относительный путь в абсолютный
    font_path = font['file_path']
    if not os.path.isabs(font_path):
        font_path = os.path.abspath(font_path)
    
    # Проверяем существование файла шрифта
    if not os.path.exists(font_path):
        await callback.answer(f"❌ Файл шрифта не найден: {font_path}", show_alert=True)
        return
    
    # Сохраняем выбранный шрифт
    await state.update_data(font_id=font_id, font_path=font_path, font_name=font['file_name'])
    
    await callback.message.edit_text(
        "🎬 <b>Готово к обработке</b>\n\n"
        f"✅ Шрифт: {font['file_name']}\n\n"
        "Отправьте видео файл для обработки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
        ])
    )
    
    await state.set_state(VideoProcessingStates.waiting_for_video)

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

@router.message(VideoProcessingStates.waiting_for_video, F.video)
async def process_video_handler(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка загруженного видео"""
    try:
        data = await state.get_data()
        effect = data.get('effect', 'normalize')
        
        # Создаем временную папку
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Скачиваем видео
            input_path = os.path.join(temp_dir, "input.mp4")
            await bot.download(message.video, destination=input_path)
            
            # Определяем выходной файл
            output_path = os.path.join(temp_dir, "output.mp4")
            
            # Обрабатываем в зависимости от эффекта
            success = False
            
            if effect == "normalize":
                success = await VideoProcessor.normalize_video(input_path, output_path)
            elif effect == "ultra_unique":
                success = await VideoProcessor.apply_ultra_unique(input_path, output_path)
            elif effect == "trending_frame":
                success = await VideoProcessor.apply_trending_frame(input_path, output_path)
            elif effect == "subscribe_bait":
                success = await VideoProcessor.apply_subscribe_bait(input_path, output_path)
            elif effect == "subtitles":
                # Извлекаем речь из видео
                print(f"🎤 Извлекаем речь из видео (язык: ru)...")
                timed_segments = VideoProcessor.extract_speech_with_timing(input_path, 'ru')
                
                if timed_segments:
                    # Объединяем текст
                    subtitle_text = ' '.join([seg['text'] for seg in timed_segments])
                    print(f"📝 Текст: {subtitle_text[:100]}...")
                    print(f"🎯 Сегментов: {len(timed_segments)}")
                    
                    # Применяем субтитры с временными метками
                    success = await VideoProcessor.apply_subtitles_with_timing(
                        input_path, output_path, subtitle_text, timed_segments, data.get('font_path')
                    )
                else:
                    # Если речь не извлечена, используем простые субтитры
                    subtitle_text = "Автоматически сгенерированные субтитры"
                    success = await VideoProcessor.apply_subtitles(
                        input_path, output_path, subtitle_text, data.get('font_path')
                    )
            
            if success and os.path.exists(output_path):
                # Отправляем результат
                result_file = FSInputFile(output_path, filename="processed_video.mp4")
                await message.answer_video(
                    video=result_file,
                    caption=f"✅ <b>Видео обработано!</b>\n\n"
                           f"Эффект: {effect.replace('_', ' ').title()}\n"
                           f"Размер: {os.path.getsize(output_path) // 1024} KB"
                )
                
                # Очищаем состояние
                await state.clear()
            else:
                await message.answer(
                    "❌ <b>Ошибка обработки</b>\n\n"
                    "Не удалось обработать видео. Попробуйте еще раз.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="videoprocess")]
                    ])
                )
        
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
