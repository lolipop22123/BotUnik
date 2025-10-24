from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import os
from pathlib import Path

from database.user import db
from handlers.Admin.states import MediaManagementStates
from config import ADMIN_ID

router = Router()


def admin_main_kb():
    """Главная клавиатура админки"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_statistics")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="📝 Управление подписками", callback_data="admin_subscriptions")
        ],
        [
            InlineKeyboardButton(text="💰 Управление балансом", callback_data="admin_balance")
        ],
        [
            InlineKeyboardButton(text="🔤 Управление шрифтами", callback_data="admin_fonts")
        ],
        [
            InlineKeyboardButton(text="🎵 Управление музыкой", callback_data="admin_music")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="backstart")
        ]
    ])
    return kb


def fonts_management_kb():
    """Клавиатура управления шрифтами"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить шрифт", callback_data="add_font")
        ],
        [
            InlineKeyboardButton(text="📋 Список шрифтов", callback_data="list_fonts")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_panel")
        ]
    ])
    return kb


def music_management_kb():
    """Клавиатура управления музыкой"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить музыку", callback_data="add_music")
        ],
        [
            InlineKeyboardButton(text="📋 Список музыки", callback_data="list_music")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_panel")
        ]
    ])
    return kb


@router.callback_query(F.data == "admin_panel")
async def admin_panel_cb(callback: types.CallbackQuery):
    """Главная панель админа"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👨‍💼 <b>Админ панель</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=admin_main_kb()
    )
    await callback.answer()


# ==================== УПРАВЛЕНИЕ ШРИФТАМИ ====================

@router.callback_query(F.data == "admin_fonts")
async def admin_fonts_cb(callback: types.CallbackQuery):
    """Меню управления шрифтами"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    fonts_count = len(await db.get_all_fonts())
    
    await callback.message.edit_text(
        f"🔤 <b>Управление шрифтами</b>\n\n"
        f"📊 Всего шрифтов: {fonts_count}\n\n"
        "Выберите действие:",
        reply_markup=fonts_management_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "add_font")
async def add_font_cb(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления шрифта"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔤 <b>Добавление шрифта</b>\n\n"
        "Отправьте файл шрифта (.ttf, .otf)\n\n"
        "⚠️ Файл будет сохранен в папке `fonts/`",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_fonts")]
        ])
    )
    await state.set_state(MediaManagementStates.waiting_for_font)
    await callback.answer()


@router.message(MediaManagementStates.waiting_for_font, F.document)
async def process_font_upload(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка загруженного шрифта"""
    document = message.document
    
    # Проверка расширения
    if not document.file_name.lower().endswith(('.ttf', '.otf')):
        await message.answer(
            "❌ Неверный формат файла!\n"
            "Поддерживаются только .ttf и .otf",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_fonts")]
            ])
        )
        return
    
    try:
        # Создаем папку для шрифтов
        fonts_dir = Path("fonts")
        fonts_dir.mkdir(exist_ok=True)
        
        # Скачиваем файл
        file = await bot.get_file(document.file_id)
        file_path = fonts_dir / document.file_name
        await bot.download_file(file.file_path, file_path)
        
        # Сохраняем в БД
        font_id = await db.add_font(
            file_id=document.file_id,
            file_name=document.file_name,
            file_path=str(file_path),
            added_by=message.from_user.id
        )
        
        await message.answer(
            f"✅ <b>Шрифт успешно добавлен!</b>\n\n"
            f"📁 Имя файла: {document.file_name}\n"
            f"📂 Путь: {file_path}\n"
            f"🆔 ID в БД: {font_id}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_font")],
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_fonts")]
            ])
        )
        await state.clear()
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке шрифта: {e}")
        await message.answer(
            f"❌ Ошибка при загрузке: {e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_fonts")]
            ])
        )
        await state.clear()


@router.callback_query(F.data == "list_fonts")
async def list_fonts_cb(callback: types.CallbackQuery):
    """Показать список шрифтов"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    fonts = await db.get_all_fonts()
    
    if not fonts:
        await callback.message.edit_text(
            "📋 <b>Список шрифтов пуст</b>\n\n"
            "Добавьте шрифты для использования в обработке видео.",
            reply_markup=fonts_management_kb()
        )
        await callback.answer()
        return
    
    # Формируем список с кнопками удаления
    text = "📋 <b>Список шрифтов:</b>\n\n"
    buttons = []
    
    for i, font in enumerate(fonts, 1):
        text += f"{i}. {font['file_name']}\n"
        text += f"   📅 Добавлен: {font['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 Удалить {font['file_name'][:20]}...",
                callback_data=f"delete_font_{font['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_fonts")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_font_"))
async def delete_font_cb(callback: types.CallbackQuery):
    """Удаление шрифта"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    font_id = int(callback.data.split("_")[-1])
    
    try:
        # Получаем информацию о шрифте
        font = await db.get_font_by_id(font_id)
        
        if font:
            # Удаляем файл
            if font.get('file_path') and os.path.exists(font['file_path']):
                os.remove(font['file_path'])
            
            # Удаляем из БД
            await db.delete_font(font_id)
            
            await callback.answer(f"✅ Шрифт {font['file_name']} удален", show_alert=True)
        else:
            await callback.answer("❌ Шрифт не найден", show_alert=True)
        
        # Обновляем список
        await list_fonts_cb(callback)
        
    except Exception as e:
        print(f"❌ Ошибка при удалении шрифта: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# ==================== УПРАВЛЕНИЕ МУЗЫКОЙ ====================

@router.callback_query(F.data == "admin_music")
async def admin_music_cb(callback: types.CallbackQuery):
    """Меню управления музыкой"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    music_count = len(await db.get_all_music())
    
    await callback.message.edit_text(
        f"🎵 <b>Управление музыкой</b>\n\n"
        f"📊 Всего треков: {music_count}\n\n"
        "Выберите действие:",
        reply_markup=music_management_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "add_music")
async def add_music_cb(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления музыки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎵 <b>Добавление музыки</b>\n\n"
        "Отправьте аудио файл (.mp3, .wav, .m4a)\n\n"
        "⚠️ Файл будет сохранен в папке `music/`",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_music")]
        ])
    )
    await state.set_state(MediaManagementStates.waiting_for_music)
    await callback.answer()


@router.message(MediaManagementStates.waiting_for_music, F.audio)
async def process_music_upload(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка загруженной музыки"""
    audio = message.audio
    
    try:
        # Создаем папку для музыки
        music_dir = Path("music")
        music_dir.mkdir(exist_ok=True)
        
        # Формируем имя файла
        file_name = audio.file_name or f"music_{audio.file_id[:8]}.mp3"
        
        # Скачиваем файл
        file = await bot.get_file(audio.file_id)
        file_path = music_dir / file_name
        await bot.download_file(file.file_path, file_path)
        
        # Сохраняем в БД
        music_id = await db.add_music(
            file_id=audio.file_id,
            file_name=file_name,
            file_path=str(file_path),
            duration=audio.duration or 0,
            added_by=message.from_user.id
        )
        
        await message.answer(
            f"✅ <b>Музыка успешно добавлена!</b>\n\n"
            f"📁 Имя файла: {file_name}\n"
            f"📂 Путь: {file_path}\n"
            f"⏱ Длительность: {audio.duration}с\n"
            f"🆔 ID в БД: {music_id}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_music")],
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_music")]
            ])
        )
        await state.clear()
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке музыки: {e}")
        await message.answer(
            f"❌ Ошибка при загрузке: {e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_music")]
            ])
        )
        await state.clear()


@router.callback_query(F.data == "list_music")
async def list_music_cb(callback: types.CallbackQuery):
    """Показать список музыки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    music_list = await db.get_all_music()
    
    if not music_list:
        await callback.message.edit_text(
            "📋 <b>Список музыки пуст</b>\n\n"
            "Добавьте музыку для использования в обработке видео.",
            reply_markup=music_management_kb()
        )
        await callback.answer()
        return
    
    # Формируем список с кнопками удаления
    text = "📋 <b>Список музыки:</b>\n\n"
    buttons = []
    
    for i, music in enumerate(music_list, 1):
        duration_min = music['duration'] // 60
        duration_sec = music['duration'] % 60
        text += f"{i}. {music['file_name']}\n"
        text += f"   ⏱ Длительность: {duration_min}:{duration_sec:02d}\n"
        text += f"   📅 Добавлен: {music['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 Удалить {music['file_name'][:20]}...",
                callback_data=f"delete_music_{music['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_music")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_music_"))
async def delete_music_cb(callback: types.CallbackQuery):
    """Удаление музыки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    music_id = int(callback.data.split("_")[-1])
    
    try:
        # Получаем информацию о музыке
        music = await db.get_music_by_id(music_id)
        
        if music:
            # Удаляем файл
            if music.get('file_path') and os.path.exists(music['file_path']):
                os.remove(music['file_path'])
            
            # Удаляем из БД
            await db.delete_music(music_id)
            
            await callback.answer(f"✅ Музыка {music['file_name']} удалена", show_alert=True)
        else:
            await callback.answer("❌ Музыка не найдена", show_alert=True)
        
        # Обновляем список
        await list_music_cb(callback)
        
    except Exception as e:
        print(f"❌ Ошибка при удалении музыки: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.message(MediaManagementStates.waiting_for_font)
@router.message(MediaManagementStates.waiting_for_music)
async def invalid_media_format(message: types.Message):
    """Обработка неверного формата файла"""
    await message.answer(
        "❌ Неверный формат файла!\n"
        "Пожалуйста, отправьте правильный файл.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ])
    )


# ==================== УПРАВЛЕНИЕ МУЗЫКОЙ ====================

def music_management_kb():
    """Клавиатура управления музыкой"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Синхронизировать папку", callback_data="sync_music_folder")
        ],
        [
            InlineKeyboardButton(text="📋 Список музыки", callback_data="list_music")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_panel")
        ]
    ])
    return kb

@router.callback_query(F.data == "admin_music")
async def admin_music_menu(callback: types.CallbackQuery):
    """Меню управления музыкой"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎵 <b>Управление музыкой</b>\n\n"
        "Здесь вы можете управлять музыкой для пользователей:\n"
        "• Синхронизировать файлы из папки music/\n"
        "• Включать/отключать музыку для пользователей\n"
        "• Просматривать список доступной музыки",
        reply_markup=music_management_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "sync_music_folder")
async def sync_music_folder_cb(callback: types.CallbackQuery):
    """Синхронизация папки music с базой данных"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text("🔄 <b>Синхронизация музыки...</b>")
    
    try:
        # Путь к папке music
        project_root = Path(__file__).resolve().parent.parent.parent
        music_folder = project_root / "music"
        
        if not music_folder.exists():
            await callback.message.edit_text(
                "❌ <b>Папка music не найдена</b>\n\n"
                f"Создайте папку: {music_folder}",
                reply_markup=music_management_kb()
            )
            return
        
        # Синхронизируем музыку
        added_count = await db.sync_music_from_folder(str(music_folder))
        
        await callback.message.edit_text(
            f"✅ <b>Синхронизация завершена</b>\n\n"
            f"📁 Папка: {music_folder}\n"
            f"➕ Добавлено файлов: {added_count}\n\n"
            f"Все новые файлы помечены как активные.",
            reply_markup=music_management_kb()
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Ошибка синхронизации</b>\n\n"
            f"Ошибка: {str(e)}",
            reply_markup=music_management_kb()
        )
    
    await callback.answer()

@router.callback_query(F.data == "list_music")
async def list_music_cb(callback: types.CallbackQuery):
    """Список всей музыки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        all_music = await db.get_all_music()
        
        if not all_music:
            await callback.message.edit_text(
                "📋 <b>Список музыки</b>\n\n"
                "Музыка не найдена. Сначала синхронизируйте папку music/",
                reply_markup=music_management_kb()
            )
            return
        
        # Разделяем на активную и неактивную
        active_music = [m for m in all_music if m.get('is_active', True)]
        inactive_music = [m for m in all_music if not m.get('is_active', True)]
        
        text = f"📋 <b>Список музыки</b>\n\n"
        text += f"✅ Активная: {len(active_music)}\n"
        text += f"❌ Неактивная: {len(inactive_music)}\n\n"
        
        if active_music:
            text += "<b>✅ Активная музыка:</b>\n"
            for music in active_music[:10]:  # Показываем первые 10
                text += f"• {music['file_name']}\n"
            if len(active_music) > 10:
                text += f"... и еще {len(active_music) - 10}\n"
        
        if inactive_music:
            text += f"\n<b>❌ Неактивная музыка:</b>\n"
            for music in inactive_music[:5]:  # Показываем первые 5
                text += f"• {music['file_name']}\n"
            if len(inactive_music) > 5:
                text += f"... и еще {len(inactive_music) - 5}\n"
        
        # Создаем клавиатуру с музыкой
        keyboard = []
        for music in all_music[:15]:  # Показываем первые 15
            status = "✅" if music.get('is_active', True) else "❌"
            keyboard.append([InlineKeyboardButton(
                text=f"{status} {music['file_name']}", 
                callback_data=f"toggle_music_{music['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_music")])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Ошибка получения списка</b>\n\n"
            f"Ошибка: {str(e)}",
            reply_markup=music_management_kb()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_music_"))
async def toggle_music_cb(callback: types.CallbackQuery):
    """Переключение статуса музыки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        music_id = int(callback.data.split("_")[-1])
        new_status = await db.toggle_music_status(music_id)
        
        status_text = "активна" if new_status else "неактивна"
        await callback.answer(f"🎵 Музыка теперь {status_text}", show_alert=True)
        
        # Обновляем список
        await list_music_cb(callback)
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

