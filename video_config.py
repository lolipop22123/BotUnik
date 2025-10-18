"""
Конфигурация для обработки видео
Основано на рабочем коде с Mac
"""

class VideoConfig:
    # Основные параметры
    TARGET_WIDTH = 1080
    TARGET_HEIGHT = 1920
    TARGET_FPS = 30
    
    # Параметры уникализации
    BRIGHTNESS = 0.1
    CONTRAST = 1.1
    SPEED = 1.05
    ZOOM = 1.05
    
    # Параметры кодирования
    CRF = 18
    PRESET = 'medium'
    AUDIO_BITRATE = '128k'
    
    # Параметры маски для Trending Frame
    MASK_WIDTH = 1080
    MASK_HEIGHT = 1920
    RADIUS_PX = 20
    
    # Параметры Ultra Unique (по умолчанию)
    ULTRA_UNIQUE_BRIGHTNESS_PERCENT = 10
    ULTRA_UNIQUE_SPEED_PERCENT = 5
