"""
Утилиты для обработки видео
Основано на рабочем коде с Mac
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from PIL import Image, ImageDraw
from video_config import VideoConfig

def ensure_frame_mask(png_path, w=None, h=None, radius=None):
    """Генерит временную PNG-маску с прозрачным окном и чёрным фоном"""
    # Используем параметры из конфигурации если не переданы
    w = w or VideoConfig.MASK_WIDTH
    h = h or VideoConfig.MASK_HEIGHT  
    radius = radius or VideoConfig.RADIUS_PX
    
    if png_path.exists():
        return
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    drw = ImageDraw.Draw(img)
    drw.rounded_rectangle((0, 0, w, h), radius=radius, fill=(0, 0, 0, 0))
    png_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(png_path)

def process_video_advanced(input_path, output_path, apply_ultra_unique=False, 
                          apply_trending_frame=False, apply_subscribe_bait=False):
    """Двухэтапная обработка: 1) нормализация к 1080x1920, 2) уникализация"""
    print(f"   🎬 Используем двухэтапный алгоритм обработки")
    print(f"   📋 Параметры: яркость={VideoConfig.BRIGHTNESS}, контраст={VideoConfig.CONTRAST}, скорость={VideoConfig.SPEED}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        mask_path = Path(temp_dir) / "frame_mask.png"
        normalized_path = Path(temp_dir) / "normalized.mp4"
        
        # Шаг 0: Принудительное масштабирование ВСЕХ видео к 1080x1920
        print(f"   📐 Шаг 0: Принудительное масштабирование к 1080x1920")
        temp_scaled_input = Path(temp_dir) / "scaled_input.mp4"
        
        # Масштабируем любое видео к 1080x1920 с черными полосами (letterboxing)
        scale_cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
            '-c:a', 'copy',
            str(temp_scaled_input)
        ]
        
        print(f"   💻 Команда масштабирования: {' '.join(scale_cmd)}")
        scale_result = subprocess.run(scale_cmd, capture_output=True, text=True, timeout=300)
        
        if scale_result.returncode == 0:
            print(f"   ✅ Видео масштабировано к 1080x1920")
            # Используем масштабированное видео как вход для дальнейшей обработки
            input_path = str(temp_scaled_input)
        else:
            print(f"   ❌ Ошибка масштабирования: {scale_result.stderr}")
            # Продолжаем с исходным видео если масштабирование не сработало
        
        # Проверяем Ultra Unique (применяется в самом начале на исходное видео)
        if apply_ultra_unique:
            brightness_value = VideoConfig.ULTRA_UNIQUE_BRIGHTNESS_PERCENT / 100.0
            speed_value = 1.0 + (VideoConfig.ULTRA_UNIQUE_SPEED_PERCENT / 100.0)
            
            print(f"   🚀 Применяем Ultra Unique эффект (яркость +{VideoConfig.ULTRA_UNIQUE_BRIGHTNESS_PERCENT}% + скорость +{VideoConfig.ULTRA_UNIQUE_SPEED_PERCENT}%)")
            
            # Создаем временный файл для Ultra Unique
            temp_ultra_input = Path(temp_dir) / "ultra_input.mp4"
            
            # Ultra Unique: яркость + скорость (без картинки для упрощения)
            ultra_unique_cmd = [
                'ffmpeg', '-y',
                '-i', input_path,  # Используем исходное видео
                '-filter_complex', 
                f"[0:v]eq=brightness={brightness_value},setpts=PTS/{speed_value}[v];"  # Яркость и скорость
                f"[0:a]atempo={speed_value}[a]",  # Ускорение аудио
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', str(VideoConfig.CRF), '-preset', VideoConfig.PRESET, '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', VideoConfig.AUDIO_BITRATE, '-movflags', '+faststart',
                str(temp_ultra_input)
            ]
            
            print(f"   💻 Команда Ultra Unique: {' '.join(ultra_unique_cmd)}")
            ultra_result = subprocess.run(ultra_unique_cmd, capture_output=True, text=True, timeout=300)
            
            if ultra_result.returncode == 0:
                print(f"   ✅ Ultra Unique обработка завершена")
                input_path = str(temp_ultra_input)
            else:
                print(f"   ❌ Ошибка Ultra Unique: {ultra_result.stderr}")
        
        # Шаг 1: Нормализация к 1080x1920 с черными полосами
        print(f"   📐 Шаг 1: Нормализация к {VideoConfig.TARGET_WIDTH}x{VideoConfig.TARGET_HEIGHT}")
        
        if apply_trending_frame:
            print(f"   🔄 Применяем Trending Frame с скруглёнными углами")
            
            # Создаём маску для Trending Frame с правильными параметрами
            ensure_frame_mask(mask_path)
            
            # Используем маску для Trending Frame
            trending_cmd = [
                'ffmpeg', '-y', 
                '-i', input_path,
                '-i', str(mask_path),
                '-filter_complex', 
                f"[0:v]scale={VideoConfig.TARGET_WIDTH}:{VideoConfig.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,pad={VideoConfig.TARGET_WIDTH}:{VideoConfig.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,fps={VideoConfig.TARGET_FPS}[scaled];"
                f"[1:v][scaled]scale2ref=w=iw:h=ih[mask][scaled2];"
                f"[scaled2][mask]alphamerge[rounded];"
                f"[rounded]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:0:0[v];"
                f"[0:a]aresample=48000[a]",
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', str(VideoConfig.CRF), '-preset', VideoConfig.PRESET, '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', VideoConfig.AUDIO_BITRATE, '-movflags', '+faststart',
                str(normalized_path)
            ]
            
            print(f"   💻 Команда Trending Frame: {' '.join(trending_cmd)}")
            trending_result = subprocess.run(trending_cmd, capture_output=True, text=True, timeout=300)
            
            if trending_result.returncode != 0:
                print(f"   ❌ Ошибка Trending Frame: {trending_result.stderr}")
                return False
            print(f"   ✅ Trending Frame обработка завершена")
        else:
            # Обычная нормализация без скруглённых углов
            normalize_cmd = [
                'ffmpeg', '-y', 
                '-i', input_path,
                '-vf', f'scale={VideoConfig.TARGET_WIDTH}:{VideoConfig.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,pad={VideoConfig.TARGET_WIDTH}:{VideoConfig.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,fps={VideoConfig.TARGET_FPS}',
                '-c:a', 'copy',
                str(normalized_path)
            ]
            
            print(f"   💻 Команда нормализации: {' '.join(normalize_cmd)}")
            normalize_result = subprocess.run(normalize_cmd, capture_output=True, text=True, timeout=300)
            
            if normalize_result.returncode != 0:
                print(f"   ❌ Ошибка нормализации: {normalize_result.stderr}")
                return normalize_result
            
            print(f"   ✅ Нормализация завершена успешно")
        
        # Если применяется Trending Frame, то обработка уже завершена
        if apply_trending_frame:
            print(f"   ✅ Trending Frame обработка завершена")
            
            # Проверяем Subscribe Bait
            if apply_subscribe_bait:
                print(f"   🎣 Применяем Subscribe Bait")
                
                # Путь к картинке Subscribe Bait
                subscribe_bait_image_path = Path(__file__).parent.parent / "images" / "1.jpg"
                print(f"   📁 Путь к Subscribe Bait картинке: {subscribe_bait_image_path}")
                
                if subscribe_bait_image_path.exists():
                    print(f"   ✅ Файл Subscribe Bait найден: {subscribe_bait_image_path}")
                    
                    # Создаем временный файл для Subscribe Bait
                    temp_subscribe_bait = Path(temp_dir) / "subscribe_bait.mp4"
                    
                    # Применяем Subscribe Bait - накладываем картинку снизу
                    subscribe_bait_cmd = [
                        'ffmpeg', '-y',
                        '-i', str(normalized_path),  # Обработанное видео
                        '-i', str(subscribe_bait_image_path),  # Картинка Subscribe Bait
                        '-filter_complex', 
                        f"[0:v]scale=1080:1920[video];"  # Масштабируем видео до 1080x1920
                        f"[1:v]scale=200:50[subscribe_img];"  # Масштабируем картинку до меньшего размера
                        f"[video][subscribe_img]overlay=(W-w)/2:H-h-250:format=auto[final]",  # Накладываем картинку снизу по центру с отступом 250px
                        '-map', '[final]',
                        '-map', '0:a',  # Копируем аудио из исходного видео
                        '-c:v', 'libx264', '-crf', str(VideoConfig.CRF), '-preset', VideoConfig.PRESET, '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy',
                        str(temp_subscribe_bait)
                    ]
                    
                    print(f"   💻 Команда Subscribe Bait: {' '.join(subscribe_bait_cmd)}")
                    subscribe_bait_result = subprocess.run(subscribe_bait_cmd, capture_output=True, text=True, timeout=300)
                    
                    if subscribe_bait_result.returncode == 0:
                        print(f"   ✅ Subscribe Bait применен")
                        normalized_path = temp_subscribe_bait
                    else:
                        print(f"   ❌ Ошибка Subscribe Bait: {subscribe_bait_result.stderr}")
                else:
                    print(f"   ⚠️ Файл Subscribe Bait не найден: {subscribe_bait_image_path}")
            
            # Финальное принудительное масштабирование к 1080x1920
            print(f"   📐 Финальное масштабирование к 1080x1920")
            final_scale_cmd = [
                'ffmpeg', '-y',
                '-i', str(normalized_path),
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
                '-c:a', 'copy',
                output_path
            ]
            
            print(f"   💻 Финальная команда масштабирования: {' '.join(final_scale_cmd)}")
            final_scale_result = subprocess.run(final_scale_cmd, capture_output=True, text=True, timeout=300)
            
            if final_scale_result.returncode == 0:
                print(f"   ✅ Финальное видео масштабировано к 1080x1920")
                return True
            else:
                print(f"   ❌ Ошибка финального масштабирования: {final_scale_result.stderr}")
                # Копируем без масштабирования как fallback
                shutil.copy2(str(normalized_path), output_path)
                print(f"   📁 Файл скопирован в: {output_path} (без масштабирования)")
                return True
        
        # Шаг 2: Применяем уникализацию
        print(f"   🎨 Шаг 2: Применение уникализации")
        
        # Создаём обычную маску для уникализации
        print(f"   🖤 Используем стандартную маску для уникализации")
        ensure_frame_mask(mask_path)
        
        # Формируем filter_complex с параметрами из конфигурации
        crop_filter = ""

        # Обработка с маской
        fc = (
            f"[0:v]scale=iw*{VideoConfig.ZOOM}:ih*{VideoConfig.ZOOM}{crop_filter},format=rgba[sv];"
            f"[1:v][sv]scale2ref=w=iw:h=ih[mask][sv2];"
            f"[sv2][mask]alphamerge[rounded];"
            f"[rounded]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:0:0,"
            f"eq=brightness={VideoConfig.BRIGHTNESS}:contrast={VideoConfig.CONTRAST},"
            f"setpts=PTS/{VideoConfig.SPEED},format=yuv420p[v];"
            f"[0:a]aresample=48000,atempo={VideoConfig.SPEED}[a]"
        )
        
        # Команда FFmpeg для уникализации нормализованного видео
        cmd = [
            'ffmpeg', '-y', 
            '-i', str(normalized_path),  # Используем нормализованное видео
            '-i', str(mask_path),
            '-filter_complex', fc,
            '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-crf', str(VideoConfig.CRF), '-preset', VideoConfig.PRESET, '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', VideoConfig.AUDIO_BITRATE, '-movflags', '+faststart',
            output_path
        ]
        
        print(f"   💻 Команда уникализации: {' '.join(cmd)}")
        
        # Выполняем уникализацию
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"   ❌ Ошибка уникализации: {result.stderr}")
        else:
            print(f"   ✅ Уникализация завершена успешно")
        
        return result
