from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
    ForceReply,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def main_reply_kb():
    """Главная клавиатура с кнопками"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚹Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="⚙️Обработка видео", callback_data="videoprocess")],
        [InlineKeyboardButton(text="🌐Поддержка", url="https://t.me/makker_o")]
    ])
    
    return kb


def profile_reply_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Пополнить баланса", callback_data="balanceadd")
        ],
        [
            InlineKeyboardButton(text=" ⬅️", callback_data="backstart")
        ]
    ])
    
    return kb


def user_videproccess_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎥 Обработать видео", callback_data="videoprocessreal")
        ],
        [
            InlineKeyboardButton(text=" ⬅️", callback_data="backstart")
        ]
    ])
    
    return kb


def video_effects_kb():
    """Клавиатура с выбором эффектов обработки видео (мультивыбор)"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📐 Нормализация (1080×1920)", callback_data="toggle_normalize")
        ],
        [
            InlineKeyboardButton(text="⚡ Ultra Unique", callback_data="toggle_ultra_unique")
        ],
        [
            InlineKeyboardButton(text="🎬 Trending Frame", callback_data="toggle_trending_frame")
        ],
        [
            InlineKeyboardButton(text="🎣 Subscribe Bait", callback_data="toggle_subscribe_bait")
        ],
        [
            InlineKeyboardButton(text="💬 Субтитры", callback_data="toggle_subtitles")
        ],
        [
            InlineKeyboardButton(text="🎵 Музыка", callback_data="toggle_music")
        ],
        [
            InlineKeyboardButton(text="🎲 5 Уникальных видео", callback_data="generate_unique_videos")
        ],
        [
            InlineKeyboardButton(text="✅ Применить выбранные", callback_data="apply_selected_effects")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")
        ]
    ])
    
    return kb