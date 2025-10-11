from aiogram.fsm.state import State, StatesGroup


class MediaManagementStates(StatesGroup):
    """Состояния для управления медиа файлами"""
    waiting_for_font = State()  # Ожидание загрузки шрифта
    waiting_for_music = State()  # Ожидание загрузки музыки


class BroadcastStates(StatesGroup):
    """Состояния для рассылки"""
    waiting_for_text = State()  # Ожидание текста
    waiting_for_photo = State()  # Ожидание фото
    waiting_for_photo_with_text = State()  # Ожидание фото
    waiting_for_text_with_photo = State()  # Ожидание текста после фото


class SubscriptionManagementStates(StatesGroup):
    """Состояния для управления подписками"""
    waiting_for_user_id_give = State()  # Ожидание User ID для выдачи
    waiting_for_user_id_remove = State()  # Ожидание User ID для удаления
    waiting_for_user_id_check = State()  # Ожидание User ID для проверки
    choosing_days = State()  # Выбор количества дней
    waiting_for_custom_days = State()  # Ожидание ввода своего количества дней

