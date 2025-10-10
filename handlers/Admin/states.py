from aiogram.fsm.state import State, StatesGroup


class MediaManagementStates(StatesGroup):
    """Состояния для управления медиа файлами"""
    waiting_for_font = State()  # Ожидание загрузки шрифта
    waiting_for_music = State()  # Ожидание загрузки музыки

