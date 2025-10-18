#!/usr/bin/env python3
"""
Скрипт для применения фоновой музыки к видео
Накладывает музыку с настройками громкости и fade эффектами

Использование:
    python scripts/apply_music.py input.mp4 output.mp4 --theme "Motivational"
    python scripts/apply_music.py input.mp4 output.mp4 --music music/природа.wav --volume -15
    python scripts/apply_music.py input.mp4 output.mp4 --theme "Comedy & Memes" --no-loop
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_config import VideoConfig


def get_video_duration(video_path: str) -> float:
    """Получает длительность видео через ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Ошибка получения информации о видео: {result.stderr}")
            return 0
        
        import json
        data = json.loads(result.stdout)
        duration = float(data.get('format', {}).get('duration', 0))
        return duration
    except Exception as e:
        print(f"❌ Ошибка анализа видео: {e}")
        return 0


def get_theme_music_path(theme: str = None) -> str:
    """Получает путь к музыкальному файлу для указанной темы"""
    # Пытаемся получить музыку из базы данных по теме
    if theme:
        try:
            from app import app, db
            from models import TrendingMusic
            
            with app.app_context():
                music_record = TrendingMusic.query.filter_by(theme=theme, is_active=True).first()
                
                if music_record and os.path.exists(music_record.music_path):
                    print(f"🎵 Используем музыку из БД: {music_record.music_name} для темы '{theme}'")
                    return music_record.music_path
                else:
                    print(f"⚠️ Музыка для темы '{theme}' не найдена в БД")
        except Exception as e:
            print(f"⚠️ Ошибка получения музыки из БД: {e}")
    
    # Fallback: используем статичные файлы
    if theme and theme in VideoConfig.THEME_MUSIC:
        music_filename = VideoConfig.THEME_MUSIC[theme]
        music_path = f"music/{music_filename}"
        
        if os.path.exists(music_path):
            print(f"🎵 Используем статичную музыку для темы '{theme}': {music_filename}")
            return music_path
    
    # По умолчанию используем природа.wav
    music_filename = 'природа.wav'
    music_path = f"music/{music_filename}"
    
    if os.path.exists(music_path):
        print(f"🎵 Используем музыку по умолчанию: {music_filename}")
        return music_path
    else:
        print(f"❌ Музыкальный файл не найден: {music_path}")
        return None


def apply_background_music(input_video: str, output_video: str, music_path: str,
                          volume_db: float = -15, fade_in: float = 2.0, 
                          fade_out: float = 2.0, loop: bool = True) -> bool:
    """
    Накладывает фоновую музыку на видео
    
    Args:
        input_video: Путь к входному видео
        output_video: Путь к выходному видео
        music_path: Путь к музыкальному файлу
        volume_db: Громкость музыки в dB (по умолчанию -15)
        fade_in: Длительность fade in эффекта в секундах (по умолчанию 2.0)
        fade_out: Длительность fade out эффекта в секундах (по умолчанию 2.0)
        loop: Зацикливать музыку если она короче видео (по умолчанию True)
        
    Returns:
        bool: True если успешно, False при ошибке
    """
    try:
        # Проверяем наличие музыкального файла
        if not music_path or not os.path.exists(music_path):
            print(f"❌ Музыкальный файл не найден: {music_path}")
            return False
        
        # Получаем длительность видео
        video_duration = get_video_duration(input_video)
        if video_duration == 0:
            print(f"❌ Не удалось получить длительность видео")
            return False
        
        print(f"🎵 Применяем фоновую музыку:")
        print(f"   📁 Файл: {music_path}")
        print(f"   🔊 Громкость: {volume_db}dB")
        print(f"   ⏱️ Длительность видео: {video_duration:.1f}s")
        print(f"   🔄 Зацикливание: {'Да' if loop else 'Нет'}")
        print(f"   🎚️ Fade In: {fade_in}s")
        print(f"   🎚️ Fade Out: {fade_out}s")
        
        # Строим фильтр для музыки
        music_filters = []
        
        if loop:
            # Зацикливаем музыку если она короче видео
            music_filters.append(f"[1:a]aloop=loop=-1:size=2e+09,atrim=duration={video_duration}")
        else:
            # Обрезаем музыку по длительности видео
            music_filters.append(f"[1:a]atrim=duration={video_duration}")
        
        # Применяем громкость
        music_filters.append(f"volume={volume_db}dB")
        
        # Применяем fade эффекты
        if fade_in > 0:
            music_filters.append(f"afade=t=in:ss=0:d={fade_in}")
        
        if fade_out > 0:
            fade_start = max(0, video_duration - fade_out)
            music_filters.append(f"afade=t=out:st={fade_start}:d={fade_out}")
        
        # Объединяем фильтры
        music_filter_chain = ",".join(music_filters) + "[music]"
        
        # Микшируем оригинальное аудио с музыкой
        final_filter = f"{music_filter_chain};[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[audio]"
        
        # Формируем команду FFmpeg
        cmd = [
            'ffmpeg', '-y',
            '-i', input_video,      # Видео с оригинальным аудио
            '-i', music_path,       # Фоновая музыка
            '-filter_complex', final_filter,
            '-map', '0:v',          # Видео из первого входа
            '-map', '[audio]',      # Микшированное аудио
            '-c:v', 'copy',         # Копируем видео без перекодирования
            '-c:a', 'aac',          # Кодируем аудио в AAC
            '-b:a', '160k',         # Битрейт аудио
            output_video
        ]
        
        print(f"🎬 Запускаем наложение музыки...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Фоновая музыка успешно наложена")
            return True
        else:
            print(f"❌ Ошибка наложения музыки: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False


def get_audio_info(audio_path: str) -> dict:
    """Получает информацию об аудио файле"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format',
            '-show_streams', audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Ошибка получения информации об аудио: {result.stderr}")
            return {}
        
        import json
        data = json.loads(result.stdout)
        
        # Ищем аудио поток
        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break
        
        if not audio_stream:
            print(f"❌ Аудио поток не найден в файле")
            return {}
        
        duration = float(data.get('format', {}).get('duration', 0))
        sample_rate = int(audio_stream.get('sample_rate', 0))
        channels = int(audio_stream.get('channels', 0))
        
        return {
            'duration': duration,
            'sample_rate': sample_rate, 
            'channels': channels
        }
        
    except Exception as e:
        print(f"❌ Ошибка анализа аудио файла: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description='Применить фоновую музыку к видео')
    parser.add_argument('input', help='Путь к входному видео')
    parser.add_argument('output', help='Путь к выходному видео')
    parser.add_argument('--theme', help='Тема для выбора музыки из БД')
    parser.add_argument('--music', help='Прямой путь к музыкальному файлу')
    parser.add_argument('--volume', type=float, default=-15, help='Громкость музыки в dB (по умолчанию: -15)')
    parser.add_argument('--fade-in', type=float, default=2.0, help='Длительность fade in в секундах (по умолчанию: 2.0)')
    parser.add_argument('--fade-out', type=float, default=2.0, help='Длительность fade out в секундах (по умолчанию: 2.0)')
    parser.add_argument('--no-loop', action='store_true', help='Не зацикливать музыку')
    parser.add_argument('--info', action='store_true', help='Показать информацию о музыкальном файле')
    
    args = parser.parse_args()
    
    # Проверяем входной файл
    if not os.path.exists(args.input):
        print(f"❌ Входной файл не найден: {args.input}")
        sys.exit(1)
    
    print(f"📹 Входное видео: {args.input}")
    print(f"📹 Выходное видео: {args.output}")
    
    # Определяем путь к музыке
    if args.music:
        music_path = args.music
        if not os.path.exists(music_path):
            print(f"❌ Музыкальный файл не найден: {music_path}")
            sys.exit(1)
    elif args.theme:
        music_path = get_theme_music_path(args.theme)
        if not music_path:
            print(f"❌ Не удалось найти музыку для темы: {args.theme}")
            sys.exit(1)
    else:
        # Используем музыку по умолчанию
        music_path = get_theme_music_path()
        if not music_path:
            print(f"❌ Не удалось найти музыку по умолчанию")
            sys.exit(1)
    
    # Показываем информацию о музыке если запрошено
    if args.info:
        audio_info = get_audio_info(music_path)
        if audio_info:
            print(f"\n📊 Информация о музыкальном файле:")
            print(f"   ⏱️ Длительность: {audio_info['duration']:.1f}s")
            print(f"   🎚️ Sample Rate: {audio_info['sample_rate']}Hz")
            print(f"   🔊 Каналы: {audio_info['channels']}")
            print()
    
    # Применяем музыку
    success = apply_background_music(
        args.input,
        args.output,
        music_path,
        volume_db=args.volume,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
        loop=not args.no_loop
    )
    
    if success:
        print(f"✅ Готово! Файл сохранен: {args.output}")
        sys.exit(0)
    else:
        print(f"❌ Ошибка обработки")
        sys.exit(1)


if __name__ == '__main__':
    main()

