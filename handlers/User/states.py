from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    waiting_for_amount = State()


class VideoProcessingStates(StatesGroup):
    choosing_font = State()  # Выбор шрифта
    choosing_music = State()  # Выбор музыки
    waiting_for_video = State()  # Ожидание загрузки видео
    waiting_for_unique_video = State()  # Ожидание видео для уникальной генерации

