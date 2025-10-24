#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import shlex, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

# -------- настройки --------
ZOOM      = 0.66
Y_SHIFT   = 0.24
RADIUS_PX = 120
BRIGHT    = 0.04
CONTRAST  = 1.06
SPEED     = 1.08
CRF       = 18
PRESET    = "medium"
AUDIO_BR  = "160k"
# ----------------------------

def run(cmd: str):
    print(">>", cmd)
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        sys.exit(r.returncode)

def ensure_frame_mask(png_path: Path, w=1000, h=1500, radius=RADIUS_PX):
    """Генерит временную PNG-маску с прозрачным окном и чёрным фоном"""
    if png_path.exists():
        return
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    drw = ImageDraw.Draw(img)
    drw.rounded_rectangle((0, 0, w, h), radius=radius, fill=(0, 0, 0, 0))
    png_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(png_path)

def main():
    base = Path(__file__).resolve().parent
    inp  = base / "download" / "test.mp4"
    outp = base / "download" / "test_out.mp4"
    mask = base / "download" / "frame_mask.png"

    if not inp.exists():
        print("Нет входного файла:", inp); sys.exit(1)

    ensure_frame_mask(mask, w=1000, h=1500, radius=RADIUS_PX)

    fc = (
        f"[0:v]scale=iw*{ZOOM}:ih*{ZOOM},format=rgba[sv];"
        f"[1:v][sv]scale2ref=w=iw:h=ih[mask][sv2];"
        f"[sv2][mask]overlay=0:0:format=auto[rounded];"
        f"[rounded]pad=trunc(iw/{ZOOM}/2)*2:trunc(ih/{ZOOM}/2)*2:(ow-iw)/2:(oh-ih)*{Y_SHIFT}:black,"
        f"eq=brightness={BRIGHT}:contrast={CONTRAST},"
        f"setpts=PTS/{SPEED},format=yuv420p[v];"
        f"[0:a]aresample=48000,atempo={SPEED}[a]"
    )

    cmd = (
        f'ffmpeg -y -i {shlex.quote(str(inp))} -i {shlex.quote(str(mask))} '
        f'-filter_complex "{fc}" -map "[v]" -map "[a]" '
        f'-c:v libx264 -crf {CRF} -preset {PRESET} -pix_fmt yuv420p '
        f'-c:a aac -b:a {AUDIO_BR} -movflags +faststart {shlex.quote(str(outp))}'
    )
    run(cmd)

    # Удаляем маску после использования
    try:
        mask.unlink(missing_ok=True)
        print("Временная маска удалена.")
    except Exception as e:
        print("Не удалось удалить маску:", e)

    print("Готово:", outp)

if __name__ == "__main__":
    main()
