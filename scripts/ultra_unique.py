#!/usr/bin/env python3
"""
Скрипт для применения Ultra Unique эффекта к видео
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
import argparse

class UltraUniqueProcessor:
    """Класс для обработки видео с Ultra Unique эффектом"""
    
    def __init__(self, brightness_percent=4.0, speed_percent=2.0, overlay_image_path=None):
        """
        Инициализация процессора Ultra Unique
        
        Args:
            brightness_percent (float): Увеличение яркости в процентах (по умолчанию 4.0%)
            speed_percent (float): Увеличение скорости в процентах (по умолчанию 2.0%)
            overlay_image_path (str): Путь к изображению для наложения (по умолчанию images/2.png)
        """
        self.brightness_percent = brightness_percent
        self.speed_percent = speed_percent
        
        # Определяем путь к изображению для наложения
        if overlay_image_path:
            self.overlay_image_path = Path(overlay_image_path)
        else:
            # Ищем изображение в папке images
            script_dir = Path(__file__).parent.parent
            self.overlay_image_path = script_dir / "images" / "2.png"
        
        # Конвертируем проценты в значения для FFmpeg
        self.brightness_value = brightness_percent / 100.0
        self.speed_value = 1.0 + (speed_percent / 100.0)
    
    def process_video(self, input_video_path, output_video_path, verbose=True):
        """
        Применяет Ultra Unique эффект к видео
        
        Args:
            input_video_path (str): Путь к входному видео
            output_video_path (str): Путь к выходному видео
            verbose (bool): Показывать подробную информацию
            
        Returns:
            bool: True если обработка успешна, False в противном случае
        """
        input_path = Path(input_video_path)
        output_path = Path(output_video_path)
        
        # Проверяем существование входного файла
        if not input_path.exists():
            print(f"❌ Входной файл не найден: {input_path}")
            return False
        
        # Проверяем существование изображения для наложения
        if not self.overlay_image_path.exists():
            print(f"❌ Изображение для наложения не найдено: {self.overlay_image_path}")
            print("💡 Убедитесь, что файл 2.png находится в папке images/")
            return False
        
        # Создаем директорию для выходного файла если не существует
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if verbose:
            print("=" * 60)
            print("🚀 Ultra Unique Video Processor")
            print("=" * 60)
            print(f"📁 Входное видео: {input_path}")
            print(f"📁 Выходное видео: {output_path}")
            print(f"🖼️  Изображение для наложения: {self.overlay_image_path}")
            print(f"💡 Яркость: +{self.brightness_percent}%")
            print(f"⚡ Скорость: +{self.speed_percent}%")
            print()
        
        # Создаем команду FFmpeg для Ultra Unique эффекта
        cmd = [
            'ffmpeg', '-y',
            '-i', str(input_path),  # Входное видео
            '-i', str(self.overlay_image_path),  # Изображение для наложения
            '-filter_complex', 
            f"[0:v]eq=brightness={self.brightness_value},setpts=PTS/{self.speed_value}[video_with_effects];"  # Яркость и скорость
            f"[1:v]scale=1080:1920,format=rgba[overlay_img];"  # Масштабируем изображение под размер видео
            f"[video_with_effects][overlay_img]overlay=(W-w)/2:(H-h)/2:format=auto[v];"  # Центрируем наложение
            f"[0:a]atempo={self.speed_value}[a]",  # Ускоряем аудио
            '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
            str(output_path)
        ]
        
        if verbose:
            print("💻 Выполняется команда FFmpeg:")
            print(" ".join(cmd))
            print()
        
        try:
            # Выполняем команду FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                if verbose:
                    print("✅ Ultra Unique обработка завершена успешно!")
                    print(f"📁 Результат сохранен: {output_path}")
                return True
            else:
                print(f"❌ Ошибка при обработке видео:")
                print(f"STDERR: {result.stderr}")
                print(f"STDOUT: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Обработка видео превысила лимит времени (5 минут)")
            return False
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return False
    
    def get_video_info(self, video_path):
        """Получает информацию о видео"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
            else:
                return None
        except Exception as e:
            print(f"Ошибка получения информации о видео: {e}")
            return None

def main():
    """Главная функция скрипта"""
    parser = argparse.ArgumentParser(
        description='Применяет Ultra Unique эффект к видео',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

1. Базовое использование:
   python ultra_unique.py input.mp4 output.mp4

2. С настройкой яркости и скорости:
   python ultra_unique.py input.mp4 output.mp4 --brightness 6.0 --speed 3.0

3. С собственным изображением для наложения:
   python ultra_unique.py input.mp4 output.mp4 --overlay my_overlay.png

4. Тихий режим (без подробного вывода):
   python ultra_unique.py input.mp4 output.mp4 --quiet
        """
    )
    
    parser.add_argument('input_video', help='Путь к входному видео')
    parser.add_argument('output_video', help='Путь к выходному видео')
    parser.add_argument('--brightness', type=float, default=4.0, 
                       help='Увеличение яркости в процентах (по умолчанию 4.0)')
    parser.add_argument('--speed', type=float, default=2.0,
                       help='Увеличение скорости в процентах (по умолчанию 2.0)')
    parser.add_argument('--overlay', type=str, default=None,
                       help='Путь к изображению для наложения (по умолчанию images/2.png)')
    parser.add_argument('--quiet', action='store_true',
                       help='Тихий режим (минимальный вывод)')
    parser.add_argument('--info', action='store_true',
                       help='Показать информацию о входном видео')
    
    args = parser.parse_args()
    
    # Проверяем доступность FFmpeg
    if not os.system('ffmpeg -version > /dev/null 2>&1') == 0:
        print("❌ FFmpeg не найден. Установите FFmpeg для работы скрипта.")
        sys.exit(1)
    
    # Создаем процессор
    processor = UltraUniqueProcessor(
        brightness_percent=args.brightness,
        speed_percent=args.speed,
        overlay_image_path=args.overlay
    )
    
    # Показываем информацию о видео если запрошено
    if args.info:
        print("📊 Информация о входном видео:")
        info = processor.get_video_info(args.input_video)
        if info:
            print(f"   Формат: {info.get('format', {}).get('format_name', 'Unknown')}")
            print(f"   Длительность: {info.get('format', {}).get('duration', 'Unknown')} сек")
            print(f"   Размер: {info.get('format', {}).get('size', 'Unknown')} байт")
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    print(f"   Разрешение: {stream.get('width', 'Unknown')}x{stream.get('height', 'Unknown')}")
                    break
        else:
            print("   Не удалось получить информацию о видео")
        print()
    
    # Обрабатываем видео
    success = processor.process_video(
        args.input_video, 
        args.output_video, 
        verbose=not args.quiet
    )
    
    if success:
        if not args.quiet:
            print("\n🎉 Готово! Видео успешно обработано с Ultra Unique эффектом.")
        sys.exit(0)
    else:
        print("\n❌ Ошибка при обработке видео.")
        sys.exit(1)

if __name__ == '__main__':
    main()

