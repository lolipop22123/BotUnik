from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    waiting_for_amount = State()


class VideoProcessingStates(StatesGroup):
    choosing_font = State()  # Выбор шрифта
    choosing_music = State()  # Выбор музыки
    waiting_for_video = State()  # Ожидание загрузки видео
    waiting_for_unique_video = State()  # Ожидание видео для уникальной генерации


class BatchVideoProcessingStates(StatesGroup):
    """Состояния для пакетной обработки видео"""
    waiting_for_videos = State()  # Ожидание загрузки видео (до 3)
    choosing_effects_for_video = State()  # Выбор эффектов для конкретного видео
    processing_batch = State()  # Обработка пакета видео

