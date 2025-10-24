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
        [InlineKeyboardButton(text="🚹 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="⚙️ Обработка видео", callback_data="videoprocess")],
        [InlineKeyboardButton(text="📦 Пакетная обработка (до 3)", callback_data="batch_process")],
        [InlineKeyboardButton(text="❗️ F.A.Q", url="https://telegra.ph/FAQ--Unikalizator-Video-Bot-10-24")],
        [InlineKeyboardButton(text="📑 Инструкция", url="https://telegra.ph/Instrukciya-po-botu-RemakeBot-10-24")],
        [InlineKeyboardButton(text="📍 Канал", url="https://t.me/RemakeBotNews")],
        [InlineKeyboardButton(text="🌐 Поддержка", url="https://t.me/makker_o")]
    ])
    
    return kb


def profile_reply_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="balanceadd")
        ],
        [
            InlineKeyboardButton(text="📅 Купить подписку", callback_data="buy_subscription")
        ],
        [
            InlineKeyboardButton(text=" ⬅️", callback_data="backstartprofilemain")
        ]
    ])
    
    return kb


def subscription_buy_kb():
    """Клавиатура для покупки подписок"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 1 день - $2", callback_data="buy_sub_1")
        ],
        [
            InlineKeyboardButton(text="📅 7 дней - $10", callback_data="buy_sub_7")
        ],
        [
            InlineKeyboardButton(text="📅 14 дней - $18", callback_data="buy_sub_14")
        ],
        [
            InlineKeyboardButton(text="📅 30 дней - $30", callback_data="buy_sub_30")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="profile")
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
            InlineKeyboardButton(text="🎲 4 Уникальных видео", callback_data="generate_unique_videos")
        ],
        [
            InlineKeyboardButton(text="✅ Применить выбранные", callback_data="apply_selected_effects")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_video")
        ]
    ])
    
    return kb