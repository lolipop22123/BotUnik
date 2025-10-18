"""
Простая обработка субтитров
Основано на рабочем коде с Mac
"""

import os
import subprocess
import tempfile
from pathlib import Path

def apply_simple_subtitles(input_video_path, output_video_path, subtitle_text, 
                          timed_segments=None, theme="default", video_speed=1.0):
    """
    Применяет субтитры к видео с точной синхронизацией
    
    Args:
        input_video_path: путь к входному видео
        output_video_path: путь к выходному видео
        subtitle_text: текст субтитров
        timed_segments: сегменты с временными метками (опционально)
        theme: тема субтитров (default, dark, light)
        video_speed: скорость видео для корректировки субтитров
    """
    print(f"🎬 Применяем субтитры с точной синхронизацией")
    print(f"📝 Текст: {subtitle_text[:100]}...")
    
    if timed_segments:
        print(f"🎯 Сегментов: {len(timed_segments)}")
        return apply_subtitles_with_timing(input_video_path, output_video_path, 
                                         subtitle_text, timed_segments, theme, video_speed)
    else:
        print(f"⚡ Скорость: {video_speed}x")
        return apply_subtitles_simple(input_video_path, output_video_path, 
                                    subtitle_text, theme, video_speed)

def apply_subtitles_simple(input_video_path, output_video_path, subtitle_text, theme="default", video_speed=1.0):
    """Простое применение субтитров без временных меток"""
    
    # Разбиваем текст на фразы
    phrases = split_text_smart(subtitle_text)
    print(f"📊 Разбито на {len(phrases)} фраз")
    
    # Создаем временные файлы для текста
    temp_files = []
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем файлы с текстом для каждой фразы
            for i, phrase in enumerate(phrases):
                temp_file = Path(temp_dir) / f"phrase_{i}.txt"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(phrase)
                temp_files.append(str(temp_file))
            
            # Создаем фильтры drawtext
            drawtext_filters = []
            total_duration = 30.0  # Примерная длительность
            phrase_duration = total_duration / len(phrases)
            
            for i, temp_file in enumerate(temp_files):
                start_time = i * phrase_duration
                end_time = (i + 1) * phrase_duration
                
                # Корректируем время с учетом скорости видео
                start_time /= video_speed
                end_time /= video_speed
                
                # Создаем фильтры с тенью и основным текстом
                shadow_filter = create_drawtext_filter(
                    temp_file, start_time, end_time, 
                    fontcolor="black@0.8", offset_x=3, offset_y=3
                )
                main_filter = create_drawtext_filter(
                    temp_file, start_time, end_time,
                    fontcolor="white", offset_x=0, offset_y=0
                )
                
                drawtext_filters.extend([shadow_filter, main_filter])
            
            # Применяем субтитры
            return apply_drawtext_filters(input_video_path, output_video_path, drawtext_filters)
            
    except Exception as e:
        print(f"❌ Ошибка применения простых субтитров: {e}")
        return False

def apply_subtitles_with_timing(input_video_path, output_video_path, subtitle_text, 
                               timed_segments, theme="default", video_speed=1.0):
    """Применение субтитров с точными временными метками"""
    
    # Разбиваем текст на фразы
    phrases = split_text_smart(subtitle_text)
    print(f"📊 Разбито на {len(phrases)} фраз")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем файлы с текстом для каждой фразы
            temp_files = []
            for i, phrase in enumerate(phrases):
                temp_file = Path(temp_dir) / f"phrase_{i}.txt"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(phrase)
                temp_files.append(str(temp_file))
            
            # Создаем фильтры drawtext с точными временными метками
            drawtext_filters = []
            
            for i, (phrase, temp_file) in enumerate(zip(phrases, temp_files)):
                if i < len(timed_segments):
                    # Используем точные временные метки
                    start_time = timed_segments[i]['start']
                    end_time = timed_segments[i]['end']
                else:
                    # Если сегментов меньше чем фраз, используем примерное время
                    phrase_duration = 3.0
                    start_time = i * phrase_duration
                    end_time = (i + 1) * phrase_duration
                
                # Корректируем время с учетом скорости видео
                start_time /= video_speed
                end_time /= video_speed
                
                # Создаем фильтры с тенью и основным текстом
                shadow_filter = create_drawtext_filter(
                    temp_file, start_time, end_time, 
                    fontcolor="black@0.8", offset_x=3, offset_y=3
                )
                main_filter = create_drawtext_filter(
                    temp_file, start_time, end_time,
                    fontcolor="white", offset_x=0, offset_y=0
                )
                
                drawtext_filters.extend([shadow_filter, main_filter])
            
            # Применяем субтитры
            return apply_drawtext_filters(input_video_path, output_video_path, drawtext_filters)
            
    except Exception as e:
        print(f"❌ Ошибка применения субтитров с временными метками: {e}")
        return False

def split_text_smart(text, max_chars_per_line=25, max_lines=2):
    """Умная разбивка текста на фразы для субтитров"""
    words = text.split()
    phrases = []
    current_phrase = ""
    
    for word in words:
        # Проверяем, поместится ли слово в текущую фразу
        test_phrase = current_phrase + (" " if current_phrase else "") + word
        
        # Проверяем ограничения
        lines = test_phrase.split('\n') if '\n' in test_phrase else [test_phrase]
        too_long = any(len(line) > max_chars_per_line for line in lines)
        too_many_lines = len(lines) > max_lines
        
        if too_long or too_many_lines:
            # Сохраняем текущую фразу и начинаем новую
            if current_phrase:
                phrases.append(current_phrase.strip())
            current_phrase = word
        else:
            # Добавляем слово к текущей фразе
            current_phrase = test_phrase
    
    # Добавляем последнюю фразу
    if current_phrase:
        phrases.append(current_phrase.strip())
    
    return phrases

def create_drawtext_filter(text_file, start_time, end_time, fontcolor="white", offset_x=0, offset_y=0):
    """Создает фильтр drawtext для FFmpeg"""
    
    # Путь к шрифту (используем системный шрифт)
    font_path = "C:/Windows/Fonts/arial.ttf"  # Windows
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Arial.ttf"  # macOS
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux
    
    # Экранируем пути для FFmpeg
    text_file_escaped = escape_path_for_ffmpeg(text_file)
    font_path_escaped = escape_path_for_ffmpeg(font_path)
    
    return (
        f"textfile={text_file_escaped}:"
        f"fontfile={font_path_escaped}:"
        f"fontsize=56:"
        f"fontcolor={fontcolor}:"
        f"x=(w-text_w)/2+{offset_x}:"
        f"y=h-600+{offset_y}:"
        f"enable='between(t,{start_time},{end_time})'"
    )

def escape_path_for_ffmpeg(path):
    """Экранирует путь для использования в FFmpeg"""
    if not path:
        return '""'
    
    # Заменяем обратные слеши на прямые
    path = path.replace('\\', '/')
    
    # Экранируем двойные кавычки
    path = path.replace('"', '\\"')
    
    # Оборачиваем в двойные кавычки
    return f'"{path}"'

def apply_drawtext_filters(input_video_path, output_video_path, drawtext_filters):
    """Применяет фильтры drawtext к видео"""
    
    if not drawtext_filters:
        print("❌ Нет фильтров для применения")
        return False
    
    print(f"🎬 Применяем {len(drawtext_filters)} фильтров субтитров")
    
    # Разбиваем фильтры на чанки для избежания слишком длинных команд
    chunk_size = 6
    current_file = input_video_path
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(0, len(drawtext_filters), chunk_size):
                chunk = drawtext_filters[i:i + chunk_size]
                
                # Создаем команду для чанка - добавляем drawtext= перед каждым фильтром
                combined_filter = ",".join(f"drawtext={filter_text}" for filter_text in chunk)
                
                # DEBUG: выводим первые 500 символов команды
                print(f"DEBUG combined_filter (chunk {i//chunk_size + 1}): {combined_filter[:500]}...")
                
                # Определяем выходной файл
                if i + chunk_size < len(drawtext_filters):
                    # Промежуточный файл
                    temp_file = Path(temp_dir) / f"subtitles_temp_{i//chunk_size}.mp4"
                else:
                    # Финальный файл
                    temp_file = output_video_path
                
                cmd = [
                    'ffmpeg', '-y',
                    '-i', current_file,
                    '-vf', combined_filter,
                    '-c:v', 'libx264',
                    '-crf', '18',
                    '-preset', 'medium',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'copy',
                    str(temp_file)
                ]
                
                # DEBUG: выводим полную команду FFmpeg
                print(f"DEBUG full cmd: {cmd}")
                
                print(f"💻 Обрабатываем чанк {i//chunk_size + 1}/{(len(drawtext_filters) + chunk_size - 1)//chunk_size}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    print(f"❌ Ошибка FFmpeg в чанке {i//chunk_size + 1}:")
                    print(f"STDERR: {result.stderr}")
                    print(f"STDOUT: {result.stdout}")
                    return False
                
                current_file = str(temp_file)
            
            print("✅ Субтитры применены успешно")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка применения субтитров: {e}")
        return False
