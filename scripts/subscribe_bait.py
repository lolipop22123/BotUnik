#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для применения Subscribe Bait эффекта
Накладывает картинку по центру под рамкой видео

Требования:
- Должен работать только с Trending Frame
- Картинка должна быть в папке images/
"""

import os
import sys
import subprocess
import shlex
from pathlib import Path

def run(cmd: str):
    """Выполняет команду и проверяет результат"""
    print(">>", cmd)
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        print(f"❌ Ошибка выполнения команды: {cmd}")
        sys.exit(r.returncode)

def find_subscribe_image():
    """Ищет картинку для Subscribe Bait в папке images"""
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"  # Путь к папке images в корне проекта
    
    # Возможные имена файлов
    possible_names = [
        "subscribe_bait.png",
        "subscribe_bait.jpg", 
        "subscribe.png",
        "subscribe.jpg",
        "bait.png",
        "bait.jpg",
        "1.jpg",  # как в коде
        "1.png"
    ]
    
    for name in possible_names:
        image_path = images_dir / name
        if image_path.exists():
            print(f"✅ Найдена картинка: {image_path}")
            return str(image_path)
    
    print(f"❌ Картинка для Subscribe Bait не найдена в {images_dir}")
    print(f"Доступные файлы: {list(images_dir.glob('*')) if images_dir.exists() else 'Папка не существует'}")
    return None

def apply_subscribe_bait(input_video: str, output_video: str, subscribe_image: str):
    """
    Применяет Subscribe Bait эффект
    
    Args:
        input_video: Путь к входному видео (уже с Trending Frame)
        output_video: Путь к выходному видео
        subscribe_image: Путь к картинке Subscribe Bait
    """
    
    if not os.path.exists(input_video):
        print(f"❌ Входное видео не найдено: {input_video}")
        return False
    
    if not os.path.exists(subscribe_image):
        print(f"❌ Картинка Subscribe Bait не найдена: {subscribe_image}")
        return False
    
    print(f"🎣 Применяем Subscribe Bait")
    print(f"📁 Входное видео: {input_video}")
    print(f"🖼 Картинка: {subscribe_image}")
    print(f"📁 Выходное видео: {output_video}")
    
    # Команда FFmpeg для наложения картинки по центру под рамкой
    # Картинка масштабируется до небольшого размера и размещается снизу по центру
    cmd = (
        f'ffmpeg -y '
        f'-i {shlex.quote(input_video)} '
        f'-i {shlex.quote(subscribe_image)} '
        f'-filter_complex '
        f'"[0:v]scale=1080:1920[video];'
        f'[1:v]scale=200:50[subscribe_img];'
        f'[video][subscribe_img]overlay=(W-w)/2:H-h-250:format=auto[final]" '
        f'-map "[final]" '
        f'-map 0:a '
        f'-c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p '
        f'-c:a copy '
        f'{shlex.quote(output_video)}'
    )
    
    try:
        run(cmd)
        print(f"✅ Subscribe Bait применен успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка применения Subscribe Bait: {e}")
        return False

def main():
    """Основная функция"""
    print("=" * 60)
    print("🎣 Subscribe Bait - наложение картинки под рамкой")
    print("=" * 60)
    
    # Пути к файлам
    script_dir = Path(__file__).resolve().parent
    input_video = script_dir / "download" / "test.mp4"
    output_video = script_dir / "download" / "test_subscribe_bait.mp4"
    
    # Проверяем входное видео
    if not input_video.exists():
        print(f"❌ Входное видео не найдено: {input_video}")
        print("Поместите видео в папку download/ с именем test.mp4")
        sys.exit(1)
    
    # Ищем картинку Subscribe Bait
    subscribe_image = find_subscribe_image()
    if not subscribe_image:
        sys.exit(1)
    
    # Применяем эффект
    success = apply_subscribe_bait(str(input_video), str(output_video), subscribe_image)
    
    if success:
        print(f"✅ Готово: {output_video}")
    else:
        print("❌ Ошибка обработки")
        sys.exit(1)

if __name__ == "__main__":
    main()
