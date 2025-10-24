#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Генератор «караоке»-субтитров: кусочки по 2–3 слова, синхронизированы с речью.
По умолчанию берёт видео ../download/test.mp4, создаёт SRT и test_out.mp4.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
import textwrap

# ----------------------------- утилиты -----------------------------

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, check=True)
    except Exception:
        print("❌ ffmpeg не найден. Установи ffmpeg и добавь в PATH.")
        sys.exit(1)

def ensure_whisper():
    try:
        import whisper
        if not hasattr(whisper, "load_model"):
            raise RuntimeError("Импортирован не тот 'whisper'. Удали пакет 'whisper' и установи 'openai-whisper'.")
        return whisper
    except ImportError:
        raise RuntimeError("Пакет 'openai-whisper' не установлен. Установи: pip install openai-whisper")

def extract_audio_from_video(video_path, audio_path):
    print(f"🎵 Извлекаем аудио из видео: {video_path}")
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le',
        '-ar', '16000', '-ac', '1',
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Ошибка извлечения аудио: {result.stderr}")
        return False
    print(f"✅ Аудио извлечено: {audio_path}")
    return True

def ts_srt(seconds: float) -> str:
    """HH:MM:SS,mmm c аккуратным округлением."""
    if seconds < 0: seconds = 0.0
    ms = int(round((seconds - int(seconds)) * 1000))
    s  = int(seconds)
    if ms == 1000: ms, s = 0, s + 1
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def wrap_to_max_lines(text: str, width=30, lines=2) -> str:
    """На всякий случай мягкий перенос в 1–2 строки."""
    parts = textwrap.wrap(text.strip(), width=width)
    if not parts: return ""
    if len(parts) <= lines: return "\n".join(parts)
    return "\n".join(parts[:lines-1] + [' '.join(parts[lines-1:])])

# --------------------- распознавание и нарезка ---------------------

def transcribe_with_words(audio_path: str, language='ru', model_name='base'):
    whisper = ensure_whisper()
    print(f"🤖 Загружаю Whisper модель: {model_name}")
    model = whisper.load_model(model_name)
    print("🎤 Распознаю речь (с таймингами слов)...")
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        condition_on_previous_text=True,
        temperature=0.0,
        no_speech_threshold=0.3,
        verbose=False
    )
    if not result or 'segments' not in result:
        raise RuntimeError("Не удалось распознать речь.")
    return result

def chunk_segments_into_word_groups(segments, max_words=3, min_dur=0.18):
    """
    Разбиваем на мини-сегменты по 2–3 слова.
    Если у слова нет точных таймингов (редко), берём тайминг сегмента.
    """
    chunks = []
    for seg in segments:
        seg_start = float(seg['start'])
        seg_end   = float(seg['end'])
        words = seg.get('words') or []
        # если модель не вернула words — падать нельзя
        if not words:
            text = seg['text'].strip()
            chunks.append({"start": seg_start, "end": seg_end, "text": text})
            continue

        group = []
        g_start = None
        for w in words:
            w_text = (w.get('word') or w.get('text') or '').strip()
            if not w_text:  # пропускаем пустые токены
                continue
            w_start = float(w.get('start', seg_start))
            w_end   = float(w.get('end',   w_start + 0.25))
            if g_start is None:
                g_start = w_start
            group.append((w_text, w_start, w_end))

            if len(group) >= max_words:
                # финализируем группу
                g_end = group[-1][2]
                if g_end <= g_start: g_end = g_start + min_dur
                text = " ".join([t for t, _, _ in group]).strip()
                chunks.append({"start": g_start, "end": g_end, "text": text})
                group, g_start = [], None

        # хвост
        if group:
            g_end = group[-1][2]
            if g_end <= g_start: g_end = g_start + min_dur
            text = " ".join([t for t, _, _ in group]).strip()
            chunks.append({"start": g_start, "end": g_end, "text": text})

    # лёгкая нормализация
    norm = []
    for ch in chunks:
        start = max(0.0, float(ch['start']))
        end   = max(start + 0.14, float(ch['end']))  # минимум ~0.14 c
        norm.append({"start": start, "end": end, "text": ch['text']})
    return norm

# --------------------------- вывод файлов --------------------------

def write_srt(chunks, path: str, width=30, lines=2):
    print(f"📝 Пишу SRT: {path}")
    with open(path, "w", encoding="utf-8") as f:
        for i, ch in enumerate(chunks, 1):
            text = wrap_to_max_lines(ch['text'], width=width, lines=lines)
            f.write(f"{i}\n{ts_srt(ch['start'])} --> {ts_srt(ch['end'])}\n{text}\n\n")
    print("✅ SRT готов.")

def burn_srt_into_video(input_video: str, srt_path: str, output_video: str,
                        fontsize=30, margin_v=120):
    print("🎬 Впечатываю субтитры в видео (снизу по центру)...")
    # Абсолютные пути — меньше сюрпризов на macOS
    iv = str(Path(input_video).resolve())
    sp = str(Path(srt_path).resolve())
    ov = str(Path(output_video).resolve())
    vf = (
        f"subtitles={sp}:"
        "charenc=UTF-8:"
        f"force_style='FontName=Arial,Fontsize={fontsize},"
        f"Alignment=2,MarginV={margin_v},Outline=3,Shadow=1,BorderStyle=1'"
    )
    cmd = ["ffmpeg", "-y", "-i", iv, "-vf", vf, "-c:a", "copy", ov]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("❌ Ошибка при впечатывании субтитров:")
        print(r.stderr)
    else:
        print(f"✅ Готово: {ov}")

# ------------------------------ main -------------------------------

def main():
    print("=" * 60)
    print("🎬 Караоке-субтитры (2–3 слова, синхронно, снизу по центру)")
    print("=" * 60)

    check_ffmpeg()

    # Где искать видео по умолчанию
    default_video = Path.cwd().parent / "download" / "test.mp4"
    test_video = str(default_video) if default_video.exists() else ""

    if not test_video:
        # запасной интерактив, если не нашли
        test_video = input("Путь к видео (mp4/mov): ").strip()
        if not test_video:
            print("❌ Видео не указано"); return
    if not os.path.exists(test_video):
        print(f"❌ Файл не найден: {test_video}"); return

    # язык
    lang = input("Язык распознавания [ru/en/uk] (по умолчанию ru): ").strip() or "ru"
    # сколько слов в кусочке
    try:
        max_words = int(input("Сколько слов в кусочке (2–3)? [3]: ").strip() or "3")
        max_words = max(2, min(max_words, 4))
    except:
        max_words = 3

    # временный WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    try:
        if not extract_audio_from_video(test_video, audio_path):
            return

        result = transcribe_with_words(audio_path, language=lang, model_name=os.environ.get("WHISPER_MODEL","base"))
        segments = result["segments"]
        chunks = chunk_segments_into_word_groups(segments, max_words=max_words)

        video_path = Path(test_video)
        srt_path = video_path.parent / f"{video_path.stem}_subtitles.srt"
        write_srt(chunks, str(srt_path), width=30, lines=2)

        out_mp4 = video_path.parent / f"{video_path.stem}_out.mp4"
        burn_srt_into_video(str(video_path), str(srt_path), str(out_mp4),
                    fontsize=16, margin_v=50)

        print("\n📝 Примеры первых 5 кусочков:")
        for i, ch in enumerate(chunks[:5], 1):
            print(f"  {i}. {ch['start']:.2f}–{ch['end']:.2f}  {ch['text']}")

    finally:
        try:
            os.unlink(audio_path)
            print("🗑️ Временный WAV удалён")
        except Exception:
            pass

if __name__ == "__main__":
    main()
