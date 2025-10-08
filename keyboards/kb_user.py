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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚹Профиль", callback_data="profile"),
            InlineKeyboardButton(text="⚙️Обработка видео", callback_data="videoprcess")
        ],
        [
            InlineKeyboardButton(text="🌐Поддержка", url="https://t.me/makker_o"),
        ]
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