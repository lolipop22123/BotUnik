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
    async def apply_subtitles(input_path: str, output_path: str, text: str, font_path: str) -> bool:
        """Применить субтитры с выбранным шрифтом"""
        try:
            # Экранируем спецсимволы в тексте
            text = text.replace("'", "'\\\\\\''").replace(":", "\\:")
            font_path = font_path.replace("\\", "/").replace(":", "\\:")
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', f"drawtext=fontfile='{font_path}':text='{text}':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=h-150:box=1:boxcolor=black@0.5:boxborderw=10",
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return result.returncode == 0
                
        except Exception as e:
            print(f"❌ Ошибка Subtitles: {e}")
            return False
    
    @staticmethod
    async def apply_music(input_path: str, output_path: str, music_path: str) -> bool:
        """Добавить фоновую музыку"""
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-i', music_path,
                '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2',
                '-c:v', 'copy',
                '-c:a', 'aac',
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
    
    # ВРЕМЕННО ОТКЛЮЧЕНО - ждем правильный код от пользователя
    # # Если выбраны субтитры - предлагаем выбрать шрифт
    # if effect == "subtitles":
    #     fonts = await db.get_all_fonts()
    #     
    #     if not fonts:
    #         await callback.message.answer(
    #             "❌ <b>Нет доступных шрифтов</b>\n\n"
    #             "Администратор еще не добавил шрифты.\n"
    #             "Попробуйте другой эффект.",
    #             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
    #                 [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="videoprcess")]
    #             ])
    #         )
    #         await callback.answer()
    #         return
    #     
    #     # Формируем кнопки выбора шрифта
    #     buttons = []
    #     for font in fonts:
    #         buttons.append([
    #             InlineKeyboardButton(
    #                 text=f"🔤 {font['file_name']}",
    #                 callback_data=f"select_font_{font['id']}"
    #             )
    #         ])
    #     buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")])
    #     
    #     await callback.message.edit_text(
    #         "💬 <b>Субтитры</b>\n\n"
    #         f"📊 Доступно шрифтов: {len(fonts)}\n\n"
    #         "Выберите шрифт для субтитров:",
    #         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    #     )
    #     await state.set_state(VideoProcessingStates.choosing_font)
    #     await callback.answer()
    #     return
    # 
    # # Если выбрана музыка - предлагаем выбрать трек
    # if effect == "music":
    #     music_list = await db.get_all_music()
    #     
    #     if not music_list:
    #         await callback.message.answer(
    #             "❌ <b>Нет доступной музыки</b>\n\n"
    #             "Администратор еще не добавил музыку.\n"
    #             "Попробуйте другой эффект.",
    #             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
    #                 [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="videoprcess")]
    #             ])
    #         )
    #         await callback.answer()
    #         return
    #     
    #     # Формируем кнопки выбора музыки
    #     buttons = []
    #     for music in music_list:
    #         duration_min = music['duration'] // 60
    #         duration_sec = music['duration'] % 60
    #         buttons.append([
    #             InlineKeyboardButton(
    #                 text=f"🎵 {music['file_name']} ({duration_min}:{duration_sec:02d})",
    #                 callback_data=f"select_music_{music['id']}"
    #             )
    #         ])
    #     buttons.append([
    #         InlineKeyboardButton(text="🎲 Случайная", callback_data="select_music_random")
    #     ])
    #     buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")])
    #     
    #     await callback.message.edit_text(
    #         "🎵 <b>Добавить музыку</b>\n\n"
    #         f"📊 Доступно треков: {len(music_list)}\n\n"
    #         "Выберите музыку для видео:",
    #         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    #     )
    #     await state.set_state(VideoProcessingStates.choosing_music)
    #     await callback.answer()
    #     return
    
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
# ВРЕМЕННО ОТКЛЮЧЕНО - ждем правильный код от пользователя

# @router.callback_query(F.data.startswith("select_font_"))
# async def select_font_cb(callback: types.CallbackQuery, state: FSMContext):
#     """Обработка выбора шрифта"""
#     font_id = int(callback.data.split("_")[-1])
#     
#     # Получаем информацию о шрифте
#     font = await db.get_font_by_id(font_id)
#     
#     if not font:
#         await callback.answer("❌ Шрифт не найден", show_alert=True)
#         return
#     
#     # Сохраняем выбранный шрифт
#     await state.update_data(font_id=font_id, font_path=font['file_path'], font_name=font['file_name'])
#     
#     # Просим ввести текст субтитров
#     await callback.message.edit_text(
#         f"✅ <b>Шрифт выбран:</b> {font['file_name']}\n\n"
#         "💬 Теперь введите текст субтитров:\n\n"
#         "Например: Subscribe to my channel!",
#         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
#         ])
#     )
#     await state.set_state(VideoProcessingStates.waiting_for_subtitle_text)
#     await callback.answer()


# @router.message(VideoProcessingStates.waiting_for_subtitle_text)
# async def process_subtitle_text(message: types.Message, state: FSMContext):
#     """Обработка введенного текста субтитров"""
#     subtitle_text = message.text
#     
#     # Сохраняем текст
#     await state.update_data(subtitle_text=subtitle_text)
#     
#     # Просим отправить видео
#     await message.answer(
#         f"✅ <b>Текст субтитров:</b> {subtitle_text}\n\n"
#         "📹 Отправьте видео для обработки\n\n"
#         "⚠️ Максимальный размер: 50 МБ\n"
#         "⏱ Обработка может занять несколько минут",
#         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
#         ])
#     )
#     await state.set_state(VideoProcessingStates.waiting_for_video)


# ==================== ОБРАБОТЧИКИ ВЫБОРА МУЗЫКИ ====================
# ВРЕМЕННО ОТКЛЮЧЕНО - ждем правильный код от пользователя

# @router.callback_query(F.data.startswith("select_music_"))
# async def select_music_cb(callback: types.CallbackQuery, state: FSMContext):
#     """Обработка выбора музыки"""
#     music_id_str = callback.data.split("_")[-1]
#     
#     # Если выбрана случайная музыка
#     if music_id_str == "random":
#         music = await db.get_random_music()
#     else:
#         music_id = int(music_id_str)
#         music = await db.get_music_by_id(music_id)
#     
#     if not music:
#         await callback.answer("❌ Музыка не найдена", show_alert=True)
#         return
#     
#     # Сохраняем выбранную музыку
#     await state.update_data(
#         music_id=music['id'],
#         music_path=music['file_path'],
#         music_name=music['file_name']
#     )
#     
#     # Просим отправить видео
#     duration_min = music['duration'] // 60
#     duration_sec = music['duration'] % 60
#     
#     await callback.message.edit_text(
#         f"✅ <b>Музыка выбрана:</b> {music['file_name']}\n"
#         f"⏱ Длительность: {duration_min}:{duration_sec:02d}\n\n"
#         "📹 Отправьте видео для обработки\n\n"
#         "⚠️ Максимальный размер: 50 МБ\n"
#         "⏱ Обработка может занять несколько минут",
#         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")]
#         ])
#     )
#     await state.set_state(VideoProcessingStates.waiting_for_video)
#     await callback.answer()


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
        
        # ВРЕМЕННО ОТКЛЮЧЕНО - ждем правильный код от пользователя
        # elif effect == "subtitles":
        #     # Применяем субтитры с выбранным шрифтом
        #     subtitle_text = user_data.get("subtitle_text")
        #     font_path = user_data.get("font_path")
        #     
        #     if not subtitle_text or not font_path:
        #         raise Exception("Не указан текст субтитров или шрифт")
        #     
        #     output_path = os.path.join(temp_dir, 'result.mp4')
        #     if not await processor.apply_subtitles(current_file, output_path, subtitle_text, font_path):
        #         raise Exception("Ошибка Subtitles")
        #     current_file = output_path
        # 
        # elif effect == "music":
        #     # Применяем музыку
        #     music_path = user_data.get("music_path")
        #     
        #     if not music_path:
        #         raise Exception("Не указана музыка")
        #     
        #     output_path = os.path.join(temp_dir, 'result.mp4')
        #     if not await processor.apply_music(current_file, output_path, music_path):
        #         raise Exception("Ошибка Music")
        #     current_file = output_path
            
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

