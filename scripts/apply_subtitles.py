#!/usr/bin/env python3
"""
Скрипт для применения субтитров к видео
Использует drawtext фильтр FFmpeg с точной синхронизацией

Использование:
    python scripts/apply_subtitles.py input.mp4 output.mp4 "Текст субтитров" --theme "Comedy & Memes"
    python scripts/apply_subtitles.py input.mp4 output.mp4 --auto --language ru --theme "Motivational"
"""

import os
import sys
import argparse
import subprocess
import re
from typing import List, Dict, Optional
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_config import VideoConfig


def _get_word_class(word: str) -> str:
    """
    Определяет класс слова по длине (в Unicode символах)
    
    Args:
        word: Слово для анализа
        
    Returns:
        str: 'short' (1-5), 'medium' (6-9), 'long' (>=10)
    """
    # Убираем пунктуацию для подсчета длины
    clean_word = re.sub(r'[.,!?…:;]', '', word)
    length = len(clean_word)
    
    if length <= 5:
        return 'short'
    elif length <= 9:
        return 'medium'
    else:
        return 'long'


def _split_text_smart(words: List[str]) -> List[str]:
    """
    Умная разбивка текста на субтитры по правилам:
    - 1 строка на кадр саба (никаких \\n)
    - CPL: жёсткий лимит 18 символов
    - short (1-5 символов): до 3 слов
    - medium (6-9 символов): до 2 слов  
    - long (>=10 символов): ровно 1 слово
    - Пунктуация прилипает к предыдущему слову
    
    Args:
        words: Список слов
        
    Returns:
        List[str]: Список фраз для субтитров
    """
    if not words:
        return []
    
    phrases = []
    current_phrase = []
    current_length = 0
    
    i = 0
    while i < len(words):
        word = words[i]
        word_class = _get_word_class(word)
        
        # Проверяем, поместится ли слово в текущую фразу
        word_length = len(word)
        space_length = 1 if current_phrase else 0  # Пробел перед словом
        total_length = current_length + space_length + word_length
        
        # Проверяем лимит CPL (18 символов)
        if total_length > 18:
            # Сохраняем текущую фразу если она не пустая
            if current_phrase:
                phrases.append(' '.join(current_phrase))
                current_phrase = []
                current_length = 0
            
            # Начинаем новую фразу с текущего слова
            current_phrase = [word]
            current_length = word_length
        else:
            # Добавляем слово к текущей фразе
            current_phrase.append(word)
            current_length = total_length
        
        # Проверяем лимиты по классам слов
        should_break = False
        
        if word_class == 'long':
            # Long слова: ровно 1 слово в реплике
            should_break = True
        elif word_class == 'medium':
            # Medium слова: до 2 слов
            medium_count = sum(1 for w in current_phrase if _get_word_class(w) == 'medium')
            if medium_count >= 2:
                should_break = True
        elif word_class == 'short':
            # Short слова: до 3 слов
            short_count = sum(1 for w in current_phrase if _get_word_class(w) == 'short')
            if short_count >= 3:
                should_break = True
        
        # Если нужно разбить фразу
        if should_break:
            phrases.append(' '.join(current_phrase))
            current_phrase = []
            current_length = 0
        
        i += 1
    
    # Добавляем последнюю фразу если она есть
    if current_phrase:
        phrases.append(' '.join(current_phrase))
    
    return phrases


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


def extract_speech_with_timing(video_path: str, language: str = 'ru') -> List[Dict]:
    """Извлекает речь с временными метками через Whisper"""
    try:
        print(f"🎤 Извлекаем речь из видео (язык: {language})...")
        from utils.speech_to_text import get_speech_processor
        
        processor = get_speech_processor()
        timed_segments = processor.extract_speech_with_timing(video_path, language)
        
        if timed_segments and len(timed_segments) > 0:
            print(f"✅ Извлечено {len(timed_segments)} сегментов речи")
            return timed_segments
        else:
            print(f"⚠️ В видео не найдена речь")
            return []
    except Exception as e:
        print(f"❌ Ошибка извлечения речи: {e}")
        return []


def get_font_path(theme: str = None) -> tuple:
    """Получает путь к шрифту из базы данных или использует дефолтный"""
    font_path = ""
    font_option = ""
    
    # Пытаемся получить шрифт из базы данных по теме
    if theme:
        try:
            from app import app, db
            from models import SubtitleFont
            
            with app.app_context():
                font_record = SubtitleFont.query.filter_by(theme=theme, is_active=True).first()
                
                if font_record and os.path.exists(font_record.font_path):
                    font_path = font_record.font_path
                    font_option = f":fontfile='{font_path}'"
                    print(f"🎨 Используем шрифт из БД: {font_record.font_name} для темы '{theme}'")
                    return font_path, font_option
                else:
                    print(f"⚠️ Шрифт для темы '{theme}' не найден в БД, используем дефолтный")
        except Exception as e:
            print(f"⚠️ Ошибка получения шрифта из БД: {e}, используем дефолтный")
    
    # Используем шрифт по умолчанию
    font_path = "fonts/Gilroy-ExtraBold.ttf"
    if os.path.exists(font_path):
        font_option = f":fontfile='{font_path}'"
        print(f"🎨 Используем шрифт по умолчанию: Gilroy-ExtraBold.ttf")
    else:
        print(f"⚠️ Шрифт по умолчанию не найден, используем системный")
        font_option = ""
    
    return font_path, font_option


def apply_subtitles_with_timing(input_video: str, output_video: str, timed_segments: List[Dict], 
                                theme: str = None, video_speed: float = 1.0) -> bool:
    """Применяет субтитры с точными временными метками"""
    try:
        _, font_option = get_font_path(theme)
        
        print(f"🎯 Используем точную синхронизацию ({len(timed_segments)} сегментов)")
        print(f"⚡ Скорость видео: {video_speed}x")
        
        # Строим drawtext фильтры по точным временным меткам
        drawtext_filters = []
        
        for i, segment in enumerate(timed_segments):
            # Корректируем временные метки с учетом скорости видео
            start_time = segment['start'] / video_speed
            end_time = segment['end'] / video_speed
            text = segment['text'].strip()
            
            if not text:
                continue
            
            # Применяем умную разбивку к тексту сегмента
            words = text.lower().split()
            smart_phrases = _split_text_smart(words)
            
            # Если в сегменте больше одной фразы, разбиваем временной интервал
            if len(smart_phrases) > 1:
                segment_duration = end_time - start_time
                phrase_duration = segment_duration / len(smart_phrases)
                
                for j, phrase in enumerate(smart_phrases):
                    phrase_start = start_time + (j * phrase_duration)
                    phrase_end = min(phrase_start + phrase_duration, end_time)
                    
                    # Экранируем текст для FFmpeg
                    escaped_text = phrase.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")
                    
                    # Создаем двойной эффект: тень + основной текст
                    shadow_filter = f"drawtext=text='{escaped_text}':fontsize=56{font_option}:fontcolor=black@0.8:x=(w-text_w)/2+3:y=h-600+3:enable='between(t,{phrase_start},{phrase_end})'"
                    main_filter = f"drawtext=text='{escaped_text}':fontsize=56{font_option}:fontcolor=white:x=(w-text_w)/2:y=h-600:enable='between(t,{phrase_start},{phrase_end})'"
                    
                    drawtext_filters.extend([shadow_filter, main_filter])
                    
                    if i < 3 and j == 0:
                        print(f"   {i+1}: {phrase_start:.1f}s-{phrase_end:.1f}s: {phrase}")
            else:
                phrase = smart_phrases[0] if smart_phrases else text
                
                # Экранируем текст для FFmpeg
                escaped_text = phrase.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")
                
                # Создаем двойной эффект: тень + основной текст
                shadow_filter = f"drawtext=text='{escaped_text}':fontsize=56{font_option}:fontcolor=black@0.8:x=(w-text_w)/2+3:y=h-600+3:enable='between(t,{start_time},{end_time})'"
                main_filter = f"drawtext=text='{escaped_text}':fontsize=56{font_option}:fontcolor=white:x=(w-text_w)/2:y=h-600:enable='between(t,{start_time},{end_time})'"
                
                drawtext_filters.extend([shadow_filter, main_filter])
                
                if i < 3:
                    print(f"   {i+1}: {start_time:.1f}s-{end_time:.1f}s: {phrase}")
        
        if len(timed_segments) > 3:
            print(f"   ... и еще {len(timed_segments) - 3} сегментов")
        
        # Объединяем все фильтры
        combined_filter = ",".join(drawtext_filters)
        
        # Формируем команду FFmpeg
        cmd = [
            'ffmpeg', '-y',
            '-i', input_video,
            '-vf', combined_filter,
            '-c:v', 'libx264',
            '-crf', '18',
            '-preset', 'medium',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'copy',
            output_video
        ]
        
        print(f"🎬 Применяем субтитры...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Субтитры успешно применены")
            return True
        else:
            print(f"❌ Ошибка применения субтитров: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False


def apply_subtitles_manual(input_video: str, output_video: str, subtitle_text: str, 
                          theme: str = None) -> bool:
    """Применяет субтитры с равномерным распределением"""
    try:
        _, font_option = get_font_path(theme)
        
        # Получаем длительность видео
        video_duration = get_video_duration(input_video)
        if video_duration == 0:
            print(f"❌ Не удалось получить длительность видео")
            return False
        
        print(f"⏱️ Длительность видео: {video_duration:.1f}s")
        
        # Разбиваем текст на фразы по умным правилам
        words = subtitle_text.lower().split()
        phrases = _split_text_smart(words)
        
        print(f"📝 Умная разбивка:")
        print(f"   🔤 Исходных слов: {len(words)}")
        print(f"   📋 Фраз создано: {len(phrases)}")
        for i, phrase in enumerate(phrases[:3]):
            word_classes = [_get_word_class(w) for w in phrase.split()]
            print(f"   {i+1}: '{phrase}' (длина: {len(phrase)}, классы: {word_classes})")
        if len(phrases) > 3:
            print(f"   ... и еще {len(phrases) - 3} фраз")
        
        if not phrases:
            phrases = [subtitle_text.lower()[:50]]
        
        # Создаем временные интервалы для каждой фразы
        duration_per_phrase = video_duration / len(phrases)
        min_duration = 2.0
        max_duration = 4.0
        
        duration_per_phrase = max(min_duration, min(duration_per_phrase, max_duration))
        
        # Строим drawtext фильтры
        drawtext_filters = []
        
        for i, phrase in enumerate(phrases):
            start_time = i * duration_per_phrase
            end_time = min(start_time + duration_per_phrase, video_duration)
            
            # Экранируем текст для FFmpeg
            escaped_phrase = phrase.replace("'", "\\'").replace(":", "\\:")
            
            # Создаем двойной эффект: тень + основной текст
            shadow_filter = f"drawtext=text='{escaped_phrase}':fontsize=56{font_option}:fontcolor=black@0.8:x=(w-text_w)/2+3:y=h-600+3:enable='between(t,{start_time},{end_time})'"
            main_filter = f"drawtext=text='{escaped_phrase}':fontsize=56{font_option}:fontcolor=white:x=(w-text_w)/2:y=h-600:enable='between(t,{start_time},{end_time})'"
            
            drawtext_filters.extend([shadow_filter, main_filter])
        
        # Объединяем все фильтры
        combined_filter = ",".join(drawtext_filters)
        
        # Формируем команду FFmpeg
        cmd = [
            'ffmpeg', '-y',
            '-i', input_video,
            '-vf', combined_filter,
            '-c:v', 'libx264',
            '-crf', '18',
            '-preset', 'medium',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'copy',
            output_video
        ]
        
        print(f"🎬 Применяем субтитры...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Субтитры успешно применены")
            return True
        else:
            print(f"❌ Ошибка применения субтитров: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Применить субтитры к видео')
    parser.add_argument('input', help='Путь к входному видео')
    parser.add_argument('output', help='Путь к выходному видео')
    parser.add_argument('text', nargs='?', help='Текст субтитров (если не --auto)')
    parser.add_argument('--auto', action='store_true', help='Автоматическое извлечение речи')
    parser.add_argument('--language', default='ru', help='Язык речи для автоизвлечения (по умолчанию: ru)')
    parser.add_argument('--theme', help='Тема для выбора шрифта')
    parser.add_argument('--speed', type=float, default=1.0, help='Скорость видео для корректировки меток')
    
    args = parser.parse_args()
    
    # Проверяем входной файл
    if not os.path.exists(args.input):
        print(f"❌ Входной файл не найден: {args.input}")
        sys.exit(1)
    
    print(f"📹 Входное видео: {args.input}")
    print(f"📹 Выходное видео: {args.output}")
    
    if args.auto:
        # Автоматическое извлечение речи
        timed_segments = extract_speech_with_timing(args.input, args.language)
        if not timed_segments:
            print(f"❌ Не удалось извлечь речь из видео")
            sys.exit(1)
        
        success = apply_subtitles_with_timing(
            args.input, 
            args.output, 
            timed_segments, 
            args.theme,
            args.speed
        )
    else:
        # Ручной ввод текста
        if not args.text:
            print(f"❌ Укажите текст субтитров или используйте --auto")
            sys.exit(1)
        
        print(f"📝 Текст субтитров: {args.text[:100]}...")
        success = apply_subtitles_manual(args.input, args.output, args.text, args.theme)
    
    if success:
        print(f"✅ Готово! Файл сохранен: {args.output}")
        sys.exit(0)
    else:
        print(f"❌ Ошибка обработки")
        sys.exit(1)


if __name__ == '__main__':
    main()

