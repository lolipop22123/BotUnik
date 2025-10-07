#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Консольный скрипт для обработки видео
Использует те же функции, что и веб-приложение
"""

import os
import sys
from pathlib import Path

# Добавляем родительскую папку в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import tempfile
from datetime import datetime


class VideoProcessor:
    """Обработчик видео через консоль"""
    
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Видео не найдено: {video_path}")
        
        self.output_dir = self.video_path.parent
        self.temp_dir = None
        
    def show_menu(self):
        """Показать меню выбора"""
        print("\n" + "="*60)
        print("🎬 ОБРАБОТКА ВИДЕО")
        print("="*60)
        print(f"📁 Файл: {self.video_path.name}")
        print(f"📂 Папка: {self.output_dir}")
        print("\n" + "="*60)
        print("ВЫБЕРИТЕ ЭФФЕКТЫ:")
        print("="*60)
        
        options = {
            '1': ('Ultra Unique', 'apply_ultra_unique'),
            '2': ('Trending Frame', 'apply_trending_frame'),
            '3': ('Subscribe Bait', 'apply_subscribe_bait'),
            '4': ('Все эффекты', 'all'),
            '5': ('Только нормализация (16:9 → 9:16)', 'normalize_only'),
            '0': ('Выход', 'exit')
        }
        
        for key, (name, _) in options.items():
            print(f"  {key}. {name}")
        
        print("="*60)
        
        choice = input("\n👉 Ваш выбор: ").strip()
        
        if choice not in options:
            print("❌ Неверный выбор!")
            return None
        
        if choice == '0':
            print("👋 Выход...")
            sys.exit(0)
        
        return options[choice][1]
    
    def normalize_video(self, input_path: str, output_path: str) -> bool:
        """Нормализация видео 16:9 → 9:16"""
        print("\n📐 Нормализация видео...")
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ Нормализация завершена")
                return True
            else:
                print(f"❌ Ошибка нормализации: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def apply_ultra_unique(self, input_path: str, output_path: str) -> bool:
        """Применить Ultra Unique"""
        print("\n⚡ Применяем Ultra Unique...")
        
        try:
            # Параметры из базы данных (по умолчанию)
            brightness = 1.05  # +5%
            speed = 1.03  # +3%
            
            # Вычисляем значения для FFmpeg
            brightness_value = (brightness - 1.0) * 0.5  # для eq=brightness
            speed_value = speed
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', f'eq=brightness={brightness_value}',
                '-filter_complex', f'[0:v]setpts=PTS/{speed_value}[v];[0:a]atempo={speed_value}[a]',
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ Ultra Unique применен")
                return True
            else:
                print(f"❌ Ошибка Ultra Unique: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def apply_trending_frame(self, input_path: str, output_path: str) -> bool:
        """Применить Trending Frame с округлением"""
        print("\n🎬 Применяем Trending Frame...")
        
        try:
            from PIL import Image, ImageDraw
            
            # Параметры
            total_w, total_h = 1080, 1920
            frame_w, frame_h = 1000, 1380
            top_offset = 165
            side_margin = 40
            corner_radius = 50
            
            # Создаем маску
            mask_path = tempfile.mktemp(suffix='.png')
            mask_img = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 255))
            draw = ImageDraw.Draw(mask_img)
            draw.rounded_rectangle((0, 0, frame_w, frame_h), radius=corner_radius, fill=(0, 0, 0, 0))
            mask_img.save(mask_path)
            
            # FFmpeg команда
            fc = (
                f"[0:v]scale={frame_w}:{frame_h}:force_original_aspect_ratio=increase,crop={frame_w}:{frame_h},format=rgba[sv];"
                f"[1:v][sv]scale2ref=w=iw:h=ih[mask][sv2];"
                f"[sv2][mask]overlay=0:0:format=auto[rounded];"
                f"[rounded]pad={total_w}:{total_h}:{side_margin}:{top_offset}:black,format=yuv420p[v]"
            )
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-i', mask_path,
                '-filter_complex', fc,
                '-map', '[v]',
                '-map', '0:a?',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Удаляем временную маску
            try:
                os.unlink(mask_path)
            except:
                pass
            
            if result.returncode == 0:
                print("✅ Trending Frame применен")
                return True
            else:
                print(f"❌ Ошибка Trending Frame: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def apply_subscribe_bait(self, input_path: str, output_path: str) -> bool:
        """Применить Subscribe Bait"""
        print("\n🎣 Применяем Subscribe Bait...")
        
        try:
            # Путь к картинке
            subscribe_image = Path(__file__).parent.parent / "images" / "1.jpg"
            
            if not subscribe_image.exists():
                print(f"⚠️ Картинка не найдена: {subscribe_image}")
                return False
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-i', str(subscribe_image),
                '-filter_complex',
                '[0:v]scale=1080:1920[video];'
                '[1:v]scale=200:50[subscribe_img];'
                '[video][subscribe_img]overlay=(W-w)/2:H-h-250:format=auto[final]',
                '-map', '[final]',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ Subscribe Bait применен")
                return True
            else:
                print(f"❌ Ошибка Subscribe Bait: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def process(self, mode: str):
        """Обработать видео"""
        print("\n" + "="*60)
        print("🚀 НАЧАЛО ОБРАБОТКИ")
        print("="*60)
        
        # Создаем имя выходного файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{self.video_path.stem}_processed_{timestamp}{self.video_path.suffix}"
        output_path = self.output_dir / output_name
        
        # Создаем временную директорию
        self.temp_dir = tempfile.mkdtemp()
        
        try:
            current_file = str(self.video_path)
            
            # Только нормализация
            if mode == 'normalize_only':
                if not self.normalize_video(current_file, str(output_path)):
                    raise Exception("Ошибка нормализации")
                print(f"\n✅ Готово: {output_path}")
                return
            
            # Ultra Unique
            if mode in ['apply_ultra_unique', 'all']:
                temp_ultra = os.path.join(self.temp_dir, 'ultra_unique.mp4')
                if not self.apply_ultra_unique(current_file, temp_ultra):
                    raise Exception("Ошибка Ultra Unique")
                current_file = temp_ultra
            
            # Trending Frame
            if mode in ['apply_trending_frame', 'all']:
                temp_trending = os.path.join(self.temp_dir, 'trending_frame.mp4')
                if not self.apply_trending_frame(current_file, temp_trending):
                    raise Exception("Ошибка Trending Frame")
                current_file = temp_trending
            
            # Subscribe Bait
            if mode in ['apply_subscribe_bait', 'all']:
                temp_subscribe = os.path.join(self.temp_dir, 'subscribe_bait.mp4')
                if not self.apply_subscribe_bait(current_file, temp_subscribe):
                    raise Exception("Ошибка Subscribe Bait")
                current_file = temp_subscribe
            
            # Копируем финальный результат
            import shutil
            shutil.copy2(current_file, str(output_path))
            
            print("\n" + "="*60)
            print("✅ ОБРАБОТКА ЗАВЕРШЕНА!")
            print("="*60)
            print(f"📁 Результат: {output_path}")
            print(f"📊 Размер: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Ошибка обработки: {e}")
            
        finally:
            # Очищаем временные файлы
            import shutil
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)


def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("🎬 КОНСОЛЬНЫЙ ОБРАБОТЧИК ВИДЕО")
    print("="*60)
    
    # Получаем путь к видео
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = input("\n📁 Введите путь к видео: ").strip()
    
    try:
        processor = VideoProcessor(video_path)
        mode = processor.show_menu()
        
        if mode:
            processor.process(mode)
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

