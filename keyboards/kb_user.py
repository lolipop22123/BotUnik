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


def main_reply_kb(is_admin=False):
    """Главная клавиатура с кнопками"""
    keyboard = [
        [
            InlineKeyboardButton(text="🚹Профиль", callback_data="profile"),
            InlineKeyboardButton(text="⚙️Обработка видео", callback_data="videoprcess")
        ],
    ]
    
    # Добавляем кнопку админ панели для админа
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_panel")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🌐Поддержка", url="https://t.me/makker_o"),
    ])
    
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
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
    """Клавиатура с выбором эффектов обработки видео"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Ultra Unique", callback_data="effect_ultra_unique")
        ],
        [
            InlineKeyboardButton(text="🎬 Trending Frame", callback_data="effect_trending_frame")
        ],
        [
            InlineKeyboardButton(text="🎣 Subscribe Bait", callback_data="effect_subscribe_bait")
        ],
        # [
        #     InlineKeyboardButton(text="💬 Субтитры", callback_data="effect_subtitles")
        # ],
        # [
        #     InlineKeyboardButton(text="🎵 Добавить музыку", callback_data="effect_music")
        # ],
        [
            InlineKeyboardButton(text="🌟 Все эффекты", callback_data="effect_all")
        ],
        [
            InlineKeyboardButton(text="📐 Только нормализация (16:9 → 9:16)", callback_data="effect_normalize")
        ],
        [
            InlineKeyboardButton(text="❌ Выход", callback_data="backstart")
        ]
    ])
    
    return kb