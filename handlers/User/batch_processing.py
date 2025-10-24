"""
Модуль для пакетной обработки видео
"""
import asyncio
import os
import tempfile
import zipfile
from datetime import datetime
from typing import List

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from handlers.User.states import BatchVideoProcessingStates
from database.user import AsyncDB
from handlers.User.videoprocessing import VideoProcessor

router = Router()
db = AsyncDB(
    dbname=os.getenv('DB_NAME', 'botunik'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', 'password'),
    host=os.getenv('DB_HOST', 'localhost')
)


class VideoInBatch:
    """Класс для хранения информации о видео в пакете"""
    def __init__(self, file_path: str, file_name: str, file_id: str):
        self.file_path = file_path
        self.file_name = file_name
        self.file_id = file_id
        self.effects = []  # Список выбранных эффектов
        self.music_id = None  # ID выбранной музыки (None = случайная)


def batch_effects_kb(video_index: int, current_effects: list = None):
    """Клавиатура для выбора эффектов для конкретного видео в пакете"""
    if current_effects is None:
        current_effects = []
    
    # Добавляем timestamp для уникальности callback_data
    import time
    timestamp = int(time.time())
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'ultra_unique' in current_effects else '⚪'} Ultra Unique", 
                callback_data=f"batch_effect_{video_index}_ultra_unique_{timestamp}"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'trending_frame' in current_effects else '⚪'} Trending Frame", 
                callback_data=f"batch_effect_{video_index}_trending_frame_{timestamp}"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'subscribe_bait' in current_effects else '⚪'} Subscribe Bait", 
                callback_data=f"batch_effect_{video_index}_subscribe_bait_{timestamp}"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'subtitles' in current_effects else '⚪'} Субтитры", 
                callback_data=f"batch_effect_{video_index}_subtitles_{timestamp}"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if 'music' in current_effects else '⚪'} Музыка", 
                callback_data=f"batch_effect_{video_index}_music_{timestamp}"
            )
        ],
        [
            InlineKeyboardButton(text="✅ Готово", callback_data=f"batch_done_{video_index}")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_batch")
        ]
    ])
    return kb


async def show_batch_music_selection(callback: types.CallbackQuery, state: FSMContext, video_index: int):
    """Показывает список доступной музыки для выбора в пакетной обработке"""
    try:
        # Сначала пытаемся получить музыку из БД
        active_music = []
        try:
            if db.pool is None:
                await db.connect()
            active_music = await db.get_active_music()
        except Exception as db_error:
            print(f"⚠️ Ошибка БД: {db_error}")
        
        # Если БД недоступна или нет музыки, используем файлы из папки
        if not active_music:
            print("🔄 Получаем музыку из папки music")
            music_folder = "music"
            if os.path.exists(music_folder):
                music_files = []
                for file in os.listdir(music_folder):
                    if file.lower().endswith(('.mp3', '.wav', '.m4a', '.aac', '.ogg')):
                        music_files.append({
                            'id': f"file_{file}",  # Используем имя файла как ID
                            'file_name': file,
                            'file_path': os.path.join(music_folder, file)
                        })
                active_music = music_files
        
        if not active_music:
            await callback.message.edit_text(
                "🎵 <b>Выбор музыки</b>\n\n"
                "❌ Музыкальные файлы не найдены.\n"
                "Добавьте файлы в папку music.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"batch_back_to_effects_{video_index}")]
                ])
            )
            return
        
        # Создаем клавиатуру с музыкой
        keyboard = []
        for music in active_music[:10]:  # Показываем первые 10
            keyboard.append([InlineKeyboardButton(
                text=f"🎵 {music['file_name']}", 
                callback_data=f"batch_music_{video_index}_{music['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="🎲 Случайная", callback_data=f"batch_music_{video_index}_random")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"batch_back_to_effects_{video_index}")])
        
        await callback.message.edit_text(
            f"🎵 <b>Выберите музыку для видео {video_index + 1}</b>\n\n"
            f"Доступно {len(active_music)} треков:\n"
            "Выберите конкретную музыку или случайную:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        print(f"❌ Ошибка показа музыки: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка загрузки музыки</b>\n\n"
            "Не удалось загрузить список музыки.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"batch_back_to_effects_{video_index}")]
            ])
        )


@router.callback_query(F.data == "batch_process")
async def start_batch_processing(callback: types.CallbackQuery, state: FSMContext):
    """Начало пакетной обработки видео"""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Проверяем активную подписку (как в обычной обработке)
    try:
        try:
            has_active_subscription = await db.is_subscription_active(user_id)
            # print(f"has_active_subscription: {has_active_subscription}")
        except Exception as e:
            has_active_subscription = True
            pass
        
        # Дополнительная проверка через сервис проверки подписок
        if has_active_subscription:
            from services.subscription_checker import subscription_checker
            has_active_subscription = await subscription_checker.check_subscription_status(user_id)
            # print(f"has_active_subscription: {has_active_subscription}")
    except Exception as e:
        print(f"❌ Ошибка проверки подписки 2: {e}")
        # Если БД недоступна, разрешаем доступ (fallback)
        has_active_subscription = True
    
    if not has_active_subscription:
        await callback.message.edit_text(
            "🔒 <b>Пакетная обработка недоступна</b>\n\n"
            "📦 Пакетная обработка видео доступна только для пользователей с активной подпиской.\n\n"
            "💎 <b>Преимущества подписки:</b>\n"
            "• Пакетная обработка до 3 видео одновременно\n"
            "• Неограниченное количество обработок\n"
            "• Приоритетная поддержка\n\n"
            "🎯 Оформите подписку для доступа к этой функции!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Оформить подписку", callback_data="profile")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="videoprocess")]
            ])
        )
        return
    
    # Если подписка активна - продолжаем
    await callback.message.edit_text(
        "📦 <b>Пакетная обработка видео</b>\n\n"
        "Загрузите до 3 видео для обработки.\n"
        "После загрузки всех видео вы сможете выбрать эффекты для каждого из них.\n\n"
        "⚠️ <b>Ограничения:</b>\n"
        "• Максимум 3 видео за раз\n"
        "• Каждое видео до 50 МБ\n"
        "• Поддерживаемые форматы: MP4, MOV, AVI",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_batch")]
        ])
    )
    
    await state.set_state(BatchVideoProcessingStates.waiting_for_videos)
    await state.update_data(batch_videos=[])


@router.message(BatchVideoProcessingStates.waiting_for_videos, F.video)
async def handle_batch_video(message: types.Message, state: FSMContext):
    """Обработка загруженного видео в пакете"""
    data = await state.get_data()
    batch_videos = data.get('batch_videos', [])
    
    if len(batch_videos) >= 3:
        await message.answer("❌ Максимум 3 видео за раз!")
        return
    
    # Проверяем размер файла
    if message.video.file_size > 50 * 1024 * 1024:  # 50 МБ
        await message.answer("❌ Файл слишком большой! Максимум 50 МБ.")
        return
    
    # Скачиваем видео с безопасным именем файла
    file_info = await message.bot.get_file(message.video.file_id)
    safe_filename = f"video_{len(batch_videos) + 1}.mp4"
    file_path = f"temp/{message.from_user.id}_batch_{safe_filename}"
    
    await message.bot.download_file(file_info.file_path, file_path)
    
    # Добавляем видео в пакет
    video = VideoInBatch(
        file_path=file_path,
        file_name=message.video.file_name or f"video_{len(batch_videos) + 1}.mp4",
        file_id=message.video.file_id
    )
    batch_videos.append(video)
    
    await state.update_data(batch_videos=batch_videos)
    
    if len(batch_videos) < 3:
        await message.answer(
            f"✅ Видео {len(batch_videos)}/3 загружено!\n"
            f"Можете загрузить еще {3 - len(batch_videos)} видео или нажать 'Начать обработку'",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Начать обработку", callback_data="start_batch_processing")]
            ])
        )
    else:
        await message.answer(
            "✅ Все 3 видео загружены!\n"
            "Нажмите 'Начать обработку' для выбора эффектов",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Начать обработку", callback_data="start_batch_processing")]
            ])
        )


@router.callback_query(F.data == "start_batch_processing")
async def start_choosing_effects(callback: types.CallbackQuery, state: FSMContext):
    """Начало выбора эффектов для видео"""
    data = await state.get_data()
    batch_videos = data.get('batch_videos', [])
    
    if not batch_videos:
        await callback.answer("❌ Нет видео для обработки!", show_alert=True)
        return
    
    # Начинаем с первого видео
    await show_effects_for_video(callback, state, 0)


async def show_effects_for_video(callback: types.CallbackQuery, state: FSMContext, video_index: int):
    """Показ эффектов для конкретного видео"""
    data = await state.get_data()
    batch_videos = data.get('batch_videos', [])
    
    if video_index >= len(batch_videos):
        await callback.answer("❌ Ошибка: видео не найдено", show_alert=True)
        return
    
    video = batch_videos[video_index]
    
    # Показываем выбранную музыку
    music_text = ""
    if video.music_id is not None:
        if video.music_id.startswith("file_"):
            # Музыка из папки
            file_name = video.music_id.replace("file_", "")
            music_text = f"\n🎵 Музыка: {file_name}"
        else:
            # Музыка из БД
            try:
                if db.pool is None:
                    await db.connect()
                music_record = await db.get_music_by_id(video.music_id)
                if music_record:
                    music_text = f"\n🎵 Музыка: {music_record['file_name']}"
            except:
                music_text = "\n🎵 Музыка: Выбрана"
    elif 'music' in video.effects:
        music_text = "\n🎵 Музыка: Случайная"
    
    await callback.message.edit_text(
        f"🎬 <b>Выбор эффектов для видео {video_index + 1}/{len(batch_videos)}</b>\n\n"
        f"📁 Файл: {video.file_name}{music_text}\n"
        f"🎨 Выберите эффекты для этого видео:",
        reply_markup=batch_effects_kb(video_index, video.effects)
    )
    
    await state.set_state(BatchVideoProcessingStates.choosing_effects_for_video)


@router.callback_query(F.data.startswith("batch_effect_"))
async def batch_effect_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора эффекта для видео в пакете"""
    # Парсим callback_data: batch_effect_{video_index}_{effect_name}_{timestamp}
    parts = callback.data.split("_")
    video_index = int(parts[2])
    
    # Объединяем все части после video_index в название эффекта (исключая timestamp)
    effect_parts = parts[3:-1]  # Убираем последнюю часть (timestamp)
    effect_name = "_".join(effect_parts)
    
    data = await state.get_data()
    batch_videos = data.get('batch_videos', [])
    
    if video_index >= len(batch_videos):
        await callback.answer("❌ Ошибка: видео не найдено", show_alert=True)
        return
    
    video = batch_videos[video_index]
    
    # Переключаем эффект
    if effect_name == "music":
        if effect_name in video.effects:
            # Убираем музыку
            video.effects.remove(effect_name)
            video.music_id = None
            await callback.answer(f"❌ {effect_name} отключен")
        else:
            # Добавляем музыку и переходим к выбору
            video.effects.append(effect_name)
            await state.update_data(batch_videos=batch_videos)
            await show_batch_music_selection(callback, state, video_index)
            return
    else:
        # Обычная логика для других эффектов
        if effect_name in video.effects:
            video.effects.remove(effect_name)
            await callback.answer(f"❌ {effect_name} отключен")
        else:
            video.effects.append(effect_name)
            await callback.answer(f"✅ {effect_name} включен")
    
    await state.update_data(batch_videos=batch_videos)
    
    # Обновляем только клавиатуру, не трогая текст сообщения
    try:
        await callback.message.edit_reply_markup(
            reply_markup=batch_effects_kb(video_index, video.effects)
        )
    except Exception as e:
        print(f"❌ Ошибка обновления клавиатуры: {e}")
        # Если не удалось обновить клавиатуру, просто отвечаем на callback
        pass


@router.callback_query(F.data.startswith("batch_music_"))
async def batch_music_selection_cb(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора конкретной музыки"""
    # Парсим callback_data: batch_music_{video_index}_{music_data}
    parts = callback.data.split("_", 3)  # Разделяем максимум на 3 части
    video_index = int(parts[2])
    music_data = parts[3]  # Остальная часть после video_index
    
    data = await state.get_data()
    batch_videos = data.get('batch_videos', [])
    
    if video_index >= len(batch_videos):
        await callback.answer("❌ Ошибка: видео не найдено", show_alert=True)
        return
    
    video = batch_videos[video_index]
    
    try:
        if music_data == "random":
            # Случайная музыка
            video.music_id = None
            music_name = "Случайная музыка"
        else:
            # Конкретная музыка - может быть из БД или из папки
            if music_data.startswith("file_"):
                # Музыка из папки
                file_name = music_data.replace("file_", "")
                video.music_id = music_data  # Сохраняем как строку
                music_name = file_name
            else:
                # Музыка из БД
                try:
                    music_id = int(music_data)
                    # Переподключаемся к БД если нужно
                    try:
                        if db.pool is None:
                            await db.connect()
                        music_record = await db.get_music_by_id(music_id)
                    except Exception as db_error:
                        print(f"⚠️ Ошибка БД, переподключаемся: {db_error}")
                        await db.connect()
                        music_record = await db.get_music_by_id(music_id)
                    
                    if music_record and music_record.get('is_active', True):
                        video.music_id = music_id
                        music_name = music_record['file_name']
                    else:
                        await callback.answer("❌ Музыка не найдена или неактивна", show_alert=True)
                        return
                except ValueError:
                    await callback.answer("❌ Неверный ID музыки", show_alert=True)
                    return
        
        await state.update_data(batch_videos=batch_videos)
        await callback.answer(f"✅ Выбрана музыка: {music_name}")
        
        # Возвращаемся к выбору эффектов (как в одиночной обработке)
        await show_effects_for_video(callback, state, video_index)
        
    except Exception as e:
        print(f"❌ Ошибка выбора музыки: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("batch_back_to_effects_"))
async def batch_back_to_effects_cb(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору эффектов"""
    # Парсим callback_data: batch_back_to_effects_{video_index}
    parts = callback.data.split("_")
    video_index = int(parts[3])
    await show_effects_for_video(callback, state, video_index)


@router.callback_query(F.data.startswith("batch_done_"))
async def batch_done_cb(callback: types.CallbackQuery, state: FSMContext):
    """Завершение выбора эффектов для видео"""
    video_index = int(callback.data.split("_")[2])
    
    data = await state.get_data()
    batch_videos = data.get('batch_videos', [])
    
    if video_index >= len(batch_videos):
        await callback.answer("❌ Ошибка: видео не найдено", show_alert=True)
        return
    
    video = batch_videos[video_index]
    
    # Показываем выбранные эффекты
    if video.effects:
        effects_text = ", ".join(video.effects)
    else:
        effects_text = "Без эффектов"
    
    try:
        await callback.message.edit_text(
            f"✅ <b>Эффекты для видео {video_index + 1} выбраны</b>\n\n"
            f"📁 Файл: {video.file_name}\n"
            f"🎨 Эффекты: {effects_text}\n\n"
            f"Переходим к следующему видео...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏳ Обрабатываем...", callback_data="processing")]
            ])
        )
    except Exception as e:
        print(f"❌ Ошибка обновления сообщения: {e}")
        await callback.message.answer(
            f"✅ <b>Эффекты для видео {video_index + 1} выбраны</b>\n\n"
            f"📁 Файл: {video.file_name}\n"
            f"🎨 Эффекты: {effects_text}\n\n"
            f"Переходим к следующему видео..."
        )
    
    # Переходим к следующему видео или начинаем обработку
    next_video_index = video_index + 1
    if next_video_index < len(batch_videos):
        await asyncio.sleep(1)  # Небольшая пауза для UX
        await show_effects_for_video(callback, state, next_video_index)
    else:
        # Все видео обработаны, начинаем обработку
        await start_actual_processing(callback, state)


async def start_actual_processing(callback: types.CallbackQuery, state: FSMContext):
    """Начало фактической обработки видео"""
    data = await state.get_data()
    batch_videos = data.get('batch_videos', [])
    
    await callback.message.edit_text(
        "🚀 <b>Начинаем обработку видео...</b>\n\n"
        f"📦 Обрабатываем {len(batch_videos)} видео\n"
        "⏳ Это может занять некоторое время...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Обрабатываем...", callback_data="processing")]
        ])
    )
    
    await state.set_state(BatchVideoProcessingStates.processing_batch)
    
    try:
        # Обрабатываем все видео
        processed_files = []
        for i, video in enumerate(batch_videos):
            try:
                processed_file = await process_single_video_in_batch(video, i)
                processed_files.append(processed_file)
                
                # Обновляем прогресс (с обработкой ошибок)
                try:
                    await callback.message.edit_text(
                        f"🚀 <b>Обрабатываем видео...</b>\n\n"
                        f"📦 Прогресс: {i + 1}/{len(batch_videos)}\n"
                        f"📁 Текущее: {video.file_name}\n"
                        f"🎨 Эффекты: {', '.join(video.effects) if video.effects else 'Без эффектов'}",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⏳ Обрабатываем...", callback_data="processing")]
                        ])
                    )
                except Exception as edit_error:
                    print(f"⚠️ Не удалось обновить прогресс: {edit_error}")
                    # Продолжаем обработку даже если не удалось обновить сообщение
                
            except Exception as e:
                print(f"❌ Ошибка обработки видео {video.file_name}: {e}")
                # Продолжаем с следующим видео
                continue
        
        if not processed_files:
            await callback.message.edit_text(
                "❌ <b>Ошибка обработки</b>\n\n"
                "Не удалось обработать ни одного видео. Попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="batch_process")]
                ])
            )
            await state.clear()
            return
        
        # Отправляем каждое обработанное видео отдельно
        for i, file_path in enumerate(processed_files):
            if os.path.exists(file_path):
                try:
                    from aiogram.types import FSInputFile
                    video_input = FSInputFile(file_path)
                    
                    await callback.message.answer_document(
                        document=video_input,
                        caption=f"🎉 <b>Видео {i+1} обработано!</b>\n\n"
                               f"📁 Файл: {batch_videos[i].file_name}\n"
                               f"🎨 Эффекты: {', '.join(batch_videos[i].effects) if batch_videos[i].effects else 'Без эффектов'}"
                    )
                except Exception as e:
                    print(f"❌ Ошибка отправки видео {i+1}: {e}")
                    continue
        
        # Очищаем временные файлы
        await cleanup_temp_files(processed_files)
        
        # Инкрементируем счетчик бесплатных видео если нет активной подписки
        try:
            user_id = callback.from_user.id
            # Переподключаемся к БД если нужно
            try:
                if db.pool is None:
                    await db.connect()
                has_active_subscription = await db.is_subscription_active(user_id)
            except Exception as db_error:
                print(f"⚠️ Ошибка БД, переподключаемся: {db_error}")
                await db.connect()
                has_active_subscription = await db.is_subscription_active(user_id)
            
            if not has_active_subscription:
                await db.increment_free_videos_used(user_id)
        except Exception as db_error:
            print(f"⚠️ Ошибка работы с БД: {db_error}")
            # Продолжаем работу даже если БД недоступна
        
        await state.clear()
        
    except Exception as e:
        print(f"❌ Ошибка пакетной обработки: {e}")
        
        # Если есть обработанные файлы, отправляем их
        if processed_files:
            await callback.message.edit_text(
                "⚠️ <b>Обработка завершена с предупреждениями</b>\n\n"
                f"📦 Обработано видео: {len(processed_files)}/{len(batch_videos)}\n"
                "Отправляем готовые видео...",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏳ Отправляем...", callback_data="processing")]
                ])
            )
            
            # Отправляем обработанные видео
            for i, file_path in enumerate(processed_files):
                if os.path.exists(file_path):
                    try:
                        from aiogram.types import FSInputFile
                        video_input = FSInputFile(file_path)
                        
                        await callback.message.answer_document(
                            document=video_input,
                            caption=f"🎉 <b>Видео {i+1} обработано!</b>\n\n"
                                   f"📁 Файл: {batch_videos[i].file_name}\n"
                                   f"🎨 Эффекты: {', '.join(batch_videos[i].effects) if batch_videos[i].effects else 'Без эффектов'}"
                        )
                    except Exception as send_error:
                        print(f"❌ Ошибка отправки видео {i+1}: {send_error}")
                        continue
            
            # Очищаем временные файлы
            await cleanup_temp_files(processed_files)
            
            # Инкрементируем счетчик бесплатных видео если нет активной подписки
            try:
                user_id = callback.from_user.id
                # Переподключаемся к БД если нужно
                try:
                    if db.pool is None:
                        await db.connect()
                    has_active_subscription = await db.is_subscription_active(user_id)
                except Exception as db_error:
                    print(f"⚠️ Ошибка БД, переподключаемся: {db_error}")
                    await db.connect()
                    has_active_subscription = await db.is_subscription_active(user_id)
                
                if not has_active_subscription:
                    await db.increment_free_videos_used(user_id)
            except Exception as db_error:
                print(f"⚠️ Ошибка работы с БД: {db_error}")
                # Продолжаем работу даже если БД недоступна
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка обработки</b>\n\n"
                "Произошла ошибка при обработке видео. Попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="batch_process")]
                ])
            )
        
        await state.clear()


@router.callback_query(F.data == "start")
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    
    await callback.message.edit_text(
        "🤖 <b>Добро пожаловать в BotUnik!</b>\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚹Профиль", callback_data="profile")],
            [InlineKeyboardButton(text="⚙️Обработка видео", callback_data="videoprocess")],
            [InlineKeyboardButton(text="📦 Пакетная обработка (до 3)", callback_data="batch_process")],
            [InlineKeyboardButton(text="🌐Поддержка", url="https://t.me/makker_o")]
        ])
    )
    await callback.answer()


async def process_single_video_in_batch(video: VideoInBatch, index: int) -> str:
    """Обработка одного видео в пакете"""
    try:
        # Используем безопасные имена файлов без русских символов
        safe_name = f"video_{index}.mp4"
        output_path = f"temp/processed_{index}_{safe_name}"
        
        if not video.effects:
            import shutil
            shutil.copy2(video.file_path, output_path)
            return output_path
        
        current_file = video.file_path
        
        for effect in video.effects:
            temp_file = f"temp/temp_{index}_{effect}_{safe_name}"
            print(f"🎬 Применяем эффект {effect} к файлу {current_file}")
            
            if effect == "ultra_unique":
                success = await VideoProcessor.apply_ultra_unique_new(current_file, temp_file)
            elif effect == "trending_frame":
                success = await VideoProcessor.apply_trending_frame_new(current_file, temp_file)
            elif effect == "subscribe_bait":
                success = await VideoProcessor.apply_subscribe_bait_new(current_file, temp_file)
            elif effect == "subtitles":
                success = await VideoProcessor.apply_subtitles_new(current_file, temp_file)
            elif effect == "music":
                # Используем выбранную музыку из видео
                if video.music_id and video.music_id.startswith("file_"):
                    # Музыка из папки
                    file_name = video.music_id.replace("file_", "")
                    music_path = os.path.join("music", file_name)
                    if os.path.exists(music_path):
                        # Используем старый метод для файлов из папки
                        success = await VideoProcessor.apply_music(current_file, temp_file, music_path)
                    else:
                        print(f"⚠️ Файл музыки не найден: {music_path}")
                        continue
                else:
                    # Музыка из БД
                    success = await VideoProcessor.apply_music_new(current_file, temp_file, video.music_id)
            else:
                print(f"⚠️ Неизвестный эффект: {effect}")
                continue
            
            if success:
                # Проверяем, что файл действительно создался
                if os.path.exists(temp_file):
                    current_file = temp_file
                    print(f"✅ Эффект {effect} применен успешно, файл: {temp_file}")
                else:
                    print(f"❌ Файл {temp_file} не создался после применения эффекта {effect}")
                    continue
            else:
                print(f"❌ Ошибка применения эффекта {effect}")
                # Если эффект не применился, пропускаем его и продолжаем с текущим файлом
                continue
        
        import shutil
        shutil.copy2(current_file, output_path)
        
        return output_path
        
    except Exception as e:
        print(f"❌ Ошибка обработки видео {video.file_name}: {e}")
        raise


async def cleanup_temp_files(file_paths: List[str]):
    """Очистка временных файлов"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"⚠️ Не удалось удалить файл {file_path}: {e}")


@router.callback_query(F.data == "cancel_batch")
async def cancel_batch_processing(callback: types.CallbackQuery, state: FSMContext):
    """Отмена пакетной обработки"""
    data = await state.get_data()
    batch_videos = data.get('batch_videos', [])
    
    # Очищаем временные файлы
    temp_files = [video.file_path for video in batch_videos]
    await cleanup_temp_files(temp_files)
    
    await callback.message.edit_text(
        "❌ <b>Пакетная обработка отменена</b>\n\n"
        "Все загруженные файлы удалены.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Начать заново", callback_data="batch_process")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
    )
    
    await state.clear()
