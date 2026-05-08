"""Demo prep — render the 17-month Jagersfontein backtest as a 1-fps MP4.

Drives the demo-video's 0:25-0:50 'the signal was already there' beat:
17 monthly Sentinel-2 RGB acquisitions 2021-06 → 2022-10, with a date label
overlaid in the lower-left, encoded at 1 fps. The final frame is held for
~8 seconds so the post-failure lobe-runout signature lingers on screen.

Output: demo/jagersfontein_timelapse.mp4 (~25 s clip at 1024×1024).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import xarray as xr
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from phase2.render import render_pass  # noqa: E402

DATES = [
    "2021-06-15", "2021-07-15", "2021-08-15", "2021-09-15",
    "2021-10-15", "2021-11-15", "2021-12-15", "2022-01-15",
    "2022-02-15", "2022-03-15", "2022-04-15", "2022-05-15",
    "2022-06-15", "2022-07-15", "2022-08-15", "2022-09-15",
    "2022-11-15",
]
HOLD_FINAL_FRAMES = 15

OUT_DIR = REPO / "demo"
TMP_DIR = OUT_DIR / "_frames"
TILE_DIR = REPO / "phase1" / "data" / "jagersfontein"


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_frame(date: str, font: ImageFont.ImageFont) -> Image.Image:
    nc = TILE_DIR / f"{date}.nc"
    if not nc.exists():
        raise FileNotFoundError(nc)
    ds = xr.open_dataset(nc)
    img = render_pass(ds)["rgb"]
    img = img.resize((1024, 1024), Image.BILINEAR)

    draw = ImageDraw.Draw(img)
    text = date
    x, y = 28, 940
    # drop shadow + white text
    for dx in (3, 4):
        draw.text((x + dx, y + dx), text, fill=(0, 0, 0), font=font)
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    return img


def main() -> int:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    font = _font(56)

    print(f"[timelapse] rendering {len(DATES)} frames…", flush=True)
    for i, date in enumerate(DATES):
        img = render_frame(date, font)
        out_png = TMP_DIR / f"frame_{i:03d}.png"
        img.save(out_png)
        print(f"  [{i + 1:2d}/{len(DATES)}] {date}")

    last_idx = len(DATES) - 1
    last_path = TMP_DIR / f"frame_{last_idx:03d}.png"
    print(f"[timelapse] holding final frame for {HOLD_FINAL_FRAMES} extra seconds…")
    for j in range(len(DATES), len(DATES) + HOLD_FINAL_FRAMES):
        shutil.copy(last_path, TMP_DIR / f"frame_{j:03d}.png")

    mp4_path = OUT_DIR / "jagersfontein_timelapse.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-framerate", "1",
        "-i", str(TMP_DIR / "frame_%03d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30",  # output 30 fps for smooth playback (frames repeated)
        str(mp4_path),
    ]
    print(f"[timelapse] encoding → {mp4_path}", flush=True)
    subprocess.run(cmd, check=True)
    print(f"[timelapse] wrote {mp4_path}")

    shutil.rmtree(TMP_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
