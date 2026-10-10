"""
Convert a photo into ASCII art (assets/ascii.txt).

The background is removed automatically (the subject is sharp, the backdrop is
blurred), so only the person shows up - like a terminal-style portrait.

Usage:
    python generate_ascii.py
    python generate_ascii.py --width 80 --contrast 1.6
"""
import argparse
import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageDraw

RAMP = " .:;+=xjzXYUOQ0#%&@"        # short ramp = cleaner portrait


# Portrait outline as fractions of the ORIGINAL photo (x, y). Tuned for assets/me.jpeg:
# head + hair + shoulders + dupatta. Edit these points if you use another photo.
OUTLINE = [
    (0.155, 0.340), (0.200, 0.255), (0.250, 0.150), (0.310, 0.080), (0.390, 0.032),
    (0.480, 0.028), (0.560, 0.055), (0.620, 0.120), (0.645, 0.190), (0.648, 0.260),
    (0.620, 0.325), (0.585, 0.370), (0.550, 0.385), (0.552, 0.470), (0.575, 0.560),
    (0.600, 0.650), (0.620, 0.730), (0.000, 0.730), (0.000, 0.560), (0.030, 0.500),
    (0.090, 0.425),
]


def subject_mask(img, crop, orig_size, feather=0.012):
    """Soft portrait mask (1 = person, 0 = background) in cropped-image coordinates."""
    W, H = orig_size
    l, t, r, b = crop
    cw, ch = img.size
    pts = [((x * W - l * W) * cw / ((r - l) * W), (y * H - t * H) * ch / ((b - t) * H))
           for x, y in OUTLINE]
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(cw * feather))
    return np.asarray(m, dtype=np.float32) / 255.0


def to_ascii(path, width=70, crop=(0.10, 0.0, 0.70, 0.55), contrast=1.25,
             gamma=1.0, invert=False, keep_bg=False):
    img = ImageOps.exif_transpose(Image.open(path).convert("RGB"))
    w, h = img.size
    l, t, r, b = crop
    img = img.crop((int(l * w), int(t * h), int(r * w), int(b * h)))

    mask = np.ones(img.size[::-1], dtype=np.float32) if keep_bg else subject_mask(img, crop, (w, h))

    # local-contrast enhancement: keeps facial features instead of blowing out skin
    g = ImageOps.grayscale(img)
    arr = np.asarray(g, dtype=np.float32) / 255.0
    blur = np.asarray(g.filter(ImageFilter.GaussianBlur(img.size[0] * 0.06)),
                      dtype=np.float32) / 255.0
    arr = 0.55 * arr + 0.45 + 2.6 * (arr - blur)          # mid-grey base + detail
    arr = np.clip(arr, 0, 1)
    g = Image.fromarray((arr * 255).astype(np.uint8))

    cw, ch = g.size
    height = int(width * (ch / cw) * 0.5)          # chars are ~2x taller than wide
    g = g.resize((width, height), Image.LANCZOS)
    m = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize(
        (width, height), Image.LANCZOS), dtype=np.float32) / 255.0

    a = (np.asarray(g, dtype=np.float32) / 255.0) ** gamma
    a = np.clip((a - 0.5) * contrast + 0.5, 0, 1)
    if invert:
        a = 1 - a
    a = a * m                                      # background -> blank

    idx = (a * (len(RAMP) - 1)).astype(int)
    idx[m < 0.35] = 0
    return "\n".join("".join(RAMP[i] for i in row).rstrip() for row in idx)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--image", default="assets/me.jpeg")
    p.add_argument("--out", default="assets/ascii.txt")
    p.add_argument("--width", type=int, default=72)
    p.add_argument("--contrast", type=float, default=1.25)
    p.add_argument("--invert", action="store_true")
    p.add_argument("--keep-bg", action="store_true", help="don't remove background")
    p.add_argument("--crop", type=float, nargs=4, default=[0.10, 0.0, 0.70, 0.55],
                   metavar=("L", "T", "R", "B"))
    a = p.parse_args()
    art = to_ascii(a.image, a.width, tuple(a.crop), a.contrast, 1.0,
                   a.invert, a.keep_bg)
    open(a.out, "w").write(art + "\n")
    print(f"Saved {a.out}  ({a.width} cols x {len(art.splitlines())} rows)")
