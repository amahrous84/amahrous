"""
Render a YouTube Short (1080x1920, 30 fps) from a JSON spec.

Everything is made here: the voice (Kokoro TTS), the visuals (drawn with
Pillow and numpy), the captions, the sound effects and a low music bed.

    python3 pipeline/make_short.py pipeline/specs/krakatoa.json out.mp4

Spec format (see pipeline/specs/ for examples):
    title, description, tags      used for the upload
    voice, speed                  Kokoro voice name and speed
    palette                       bg1, bg2, accent, ink (hex colours)
    segments                      list of:
        text      what the captions show
        say       optional: what the voice says, if it differs from text
        big       optional: large label shown above the scene
        scene     one of SCENES below, plus its own options in "params"
        sfx       optional: boom, whoosh, rumble, ping
"""
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SR = 24000
GAP = 0.22          # silence between segments, in seconds
TAIL = 0.8          # extra time after the last word
SCENE_CY = 760      # vertical centre of the scene area
FONT = os.path.join(HERE, 'fonts', 'Anton-Regular.ttf')
TTS_DIR = os.environ.get('KOKORO_DIR', os.path.join(HERE, '.kokoro'))


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = min(max(x, 0.0), 1.0)
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


# ---------------------------------------------------------------- audio

def synth_voice(segments, voice, speed):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(TTS_DIR, 'kokoro-v1.0.onnx'),
               os.path.join(TTS_DIR, 'voices-v1.0.bin'))
    clips = []
    for seg in segments:
        samples, sr = k.create(seg.get('say', seg['text']), voice=voice,
                               speed=speed, lang='en-us')
        assert sr == SR
        clips.append(trim_silence(np.asarray(samples, dtype=np.float32)))
    return clips


def trim_silence(x, thresh=0.01):
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(idx[0] - int(0.03 * SR), 0)
    b = min(idx[-1] + int(0.08 * SR), len(x))
    return x[a:b]


def lowpass(x, alpha):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


def sfx(kind, rng):
    t = np.arange(int(SR * 2.5)) / SR
    if kind == 'boom':
        noise = rng.standard_normal(len(t)).astype(np.float32)
        body = lowpass(noise, 0.02) * 9 * np.exp(-t * 1.6)
        thump = np.sin(2 * np.pi * (70 * t - 18 * t ** 2)) * np.exp(-t * 3.0)
        crack = noise * np.exp(-t * 30) * 0.5
        out = body + thump * 0.9 + crack
    elif kind == 'rumble':
        noise = rng.standard_normal(len(t)).astype(np.float32)
        env = np.minimum(t / 0.4, 1) * np.exp(-t * 0.9)
        out = lowpass(noise, 0.01) * 12 * env
    elif kind == 'whoosh':
        t = t[:int(SR * 1.2)]
        noise = rng.standard_normal(len(t)).astype(np.float32)
        env = np.sin(np.pi * t / t[-1]) ** 2
        out = (lowpass(noise, 0.15) - lowpass(noise, 0.03)) * 2.2 * env
    elif kind == 'ping':
        t = t[:int(SR * 1.5)]
        out = (np.sin(2 * np.pi * 880 * t) + 0.4 * np.sin(2 * np.pi * 1320 * t)) * np.exp(-t * 4) * 0.35
    else:
        return np.zeros(1, dtype=np.float32)
    return out.astype(np.float32)


def music_bed(n, rng):
    t = np.arange(n) / SR
    root = 55.0
    pad = np.zeros(n, dtype=np.float32)
    for f, a in ((root, 0.5), (root * 1.5, 0.25), (root * 2, 0.2), (root * 2.4, 0.12)):
        pad += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t))
    pulse = np.sin(2 * np.pi * 0.5 * t) ** 8 * np.sin(2 * np.pi * 42 * t) * 0.5
    return (pad + pulse) * 0.06


def build_audio(clips, segments, rng):
    starts, t = [], 0.0
    for c in clips:
        starts.append(t)
        t += len(c) / SR + GAP
    total = t - GAP + TAIL
    n = int(total * SR)
    voice = np.zeros(n, dtype=np.float32)
    fx = np.zeros(n, dtype=np.float32)
    for s, c, seg in zip(starts, clips, segments):
        i = int(s * SR)
        voice[i:i + len(c)] += c[:n - i]
        if seg.get('sfx'):
            e = sfx(seg['sfx'], rng)
            j = max(i - int(0.05 * SR), 0)
            fx[j:j + len(e)] += e[:n - j]
    voice /= max(np.abs(voice).max(), 1e-6) / 0.9
    fx = fx / max(np.abs(fx).max(), 1e-6) * 0.55
    mix = voice + fx + music_bed(n, rng)
    mix /= max(np.abs(mix).max(), 1.0)
    fade = int(0.4 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix, starts, [len(c) / SR for c in clips], total


# ------------------------------------------------------------- captions

def caption_chunks(text, start, dur):
    """Split text into 1-3 word chunks timed by character length."""
    words = text.split()
    weights = [len(w) + (4 if re.search(r'[.,!?;:]$', w) else 1) for w in words]
    total = sum(weights)
    chunks, cur, cur_w, t = [], [], 0, start
    for w, wt in zip(words, weights):
        cur.append(w)
        cur_w += wt
        if len(cur) == 3 or re.search(r'[.,!?;:]$', w) or len(' '.join(cur)) > 14:
            d = dur * cur_w / total
            chunks.append((t, t + d, ' '.join(cur)))
            t += d
            cur, cur_w = [], 0
    if cur:
        chunks.append((t, start + dur, ' '.join(cur)))
    return chunks


def draw_text_centered(img, text, cy, size, fill, stroke=10, scale=1.0, alpha=255, max_w=W - 120):
    size = int(size * scale)
    f = font(size)
    while f.getlength(text) > max_w and size > 30:
        size -= 6
        f = font(size)
    layer = Image.new('RGBA', (W, size * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((W / 2, size), text, font=f, fill=fill + (alpha,), anchor='mm',
           stroke_width=stroke, stroke_fill=(0, 0, 0, alpha))
    img.alpha_composite(layer, (0, int(cy - size)))


def draw_caption(img, text, keywords, accent, age):
    pop = 0.85 + 0.15 * ease_back(age / 0.12)
    clean = re.sub(r'[^\w,\'%°.-]', '', text)
    hot = any(k in text.upper() for k in keywords)
    colour = accent if hot else (255, 255, 255)
    draw_text_centered(img, text.upper().replace('"', ''), 1420, 104, colour, stroke=12, scale=pop)
    return clean


# --------------------------------------------------------------- scenes

class Ctx:
    def __init__(self, pal, rng):
        self.pal = pal
        self.rng = rng
        self.accent = hex_rgb(pal['accent'])
        self.ink = hex_rgb(pal.get('ink', '#ffffff'))


def glow_circle(d, x, y, r, colour, a=255):
    d.ellipse((x - r, y - r, x + r, y + r), fill=colour + (a,))


def scene_explosion(layer, t, dur, p, c):
    d = ImageDraw.Draw(layer)
    base = SCENE_CY + 380
    rng = random.Random(7)
    # ash column
    grow = ease_out(t / 2.2)
    for i in range(70):
        k = i / 70
        y = base - 120 - k * 760 * grow
        spread = 40 + k * 260 * grow + 30 * math.sin(i * 1.7 + t)
        x = W / 2 + rng.uniform(-1, 1) * spread * 0.6
        r = 50 + k * 120 * grow + rng.uniform(0, 30)
        g = int(70 + 60 * rng.random())
        d.ellipse((x - r, y - r, x + r, y + r), fill=(g, g - 10, g - 15, 230))
    # fire at the vent
    for i in range(25):
        r = 30 + rng.uniform(0, 70) * (0.6 + 0.4 * math.sin(t * 9 + i))
        x = W / 2 + rng.uniform(-90, 90)
        y = base - 100 - rng.uniform(0, 160) * grow
        col = (255, int(90 + 120 * rng.random()), 20)
        d.ellipse((x - r, y - r, x + r, y + r), fill=col + (200,))
    # volcano
    d.polygon([(W / 2 - 520, base + 200), (W / 2 - 110, base - 110), (W / 2 + 110, base - 110),
               (W / 2 + 520, base + 200)], fill=(25, 18, 16, 255))
    # sea
    d.rectangle((0, base + 160, W, base + 420), fill=(12, 18, 30, 255))
    # shockwaves
    for k in range(3):
        age = t - k * 0.35
        if 0 < age < 2.5:
            r = age * 700
            a = int(200 * (1 - age / 2.5))
            d.ellipse((W / 2 - r, base - 110 - r * 0.35, W / 2 + r, base - 110 + r * 0.35),
                      outline=(255, 230, 200, a), width=10)
    # flash
    if p.get('flash', True) and t < 0.35:
        layer.alpha_composite(Image.new('RGBA', layer.size, (255, 240, 220, int(255 * (1 - t / 0.35)))))


def _blob(cx, cy, r, seed, n=40):
    rng = random.Random(seed)
    ph = [rng.uniform(0, 6.28) for _ in range(4)]
    amp = [rng.uniform(0.05, 0.22) for _ in range(4)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + sum(amp[j] * math.sin((j + 2) * a + ph[j]) for j in range(4))
        pts.append((cx + r[0] * k * math.cos(a), cy + r[1] * k * math.sin(a)))
    return pts


def scene_map(layer, t, dur, p, c):
    mapl = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    _draw_map(mapl, t, dur, p, c)
    mask = Image.new('L', layer.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((60, SCENE_CY - 520, W - 60, SCENE_CY + 520), 40, fill=255)
    mapl.putalpha(Image.composite(mapl.getchannel('A'), mask, mask))
    layer.alpha_composite(mapl)


def _draw_map(layer, t, dur, p, c):
    d = ImageDraw.Draw(layer)
    zoom = 1 + 0.25 * ease_out(t / dur)
    cy = SCENE_CY
    d.rounded_rectangle((60, cy - 520, W - 60, cy + 520), 40, fill=(14, 30, 48, 255))
    for i, (bx, by, rx, ry) in enumerate(p.get('land', [[0.3, 0.3, 0.32, 0.12], [0.62, 0.62, 0.3, 0.09]])):
        x = W / 2 + (bx - 0.5) * 900 * zoom
        y = cy + (by - 0.5) * 1000 * zoom
        d.polygon(_blob(x, y, (rx * 900 * zoom, ry * 1000 * zoom), seed=i + 3), fill=(58, 74, 52, 255))
    for gx in range(1, 6):
        x = 60 + gx * (W - 120) / 6
        d.line((x, cy - 520, x, cy + 520), fill=(255, 255, 255, 18), width=2)
    for gy in range(1, 8):
        y = cy - 520 + gy * 1040 / 8
        d.line((60, y, W - 60, y), fill=(255, 255, 255, 18), width=2)
    sx, sy = p.get('point', [0.47, 0.47])
    px, py = W / 2 + (sx - 0.5) * 900 * zoom, cy + (sy - 0.5) * 1000 * zoom
    if 'to' in p:
        tx, ty = p['to']
        qx, qy = W / 2 + (tx - 0.5) * 900 * zoom, cy + (ty - 0.5) * 1000 * zoom
        k = ease_out(t / (dur * 0.7))
        mx, my = (px + qx) / 2, min(py, qy) - 260
        pts = []
        for i in range(int(60 * k) + 1):
            u = i / 60
            pts.append(((1 - u) ** 2 * px + 2 * (1 - u) * u * mx + u ** 2 * qx,
                        (1 - u) ** 2 * py + 2 * (1 - u) * u * my + u ** 2 * qy))
        if len(pts) > 1:
            d.line(pts, fill=c.accent + (255,), width=9, joint='curve')
        if k > 0.98:
            glow_circle(d, qx, qy, 18, (255, 255, 255))
    pulse = (t * 1.5) % 1
    d.ellipse((px - 30 - pulse * 120, py - 30 - pulse * 120, px + 30 + pulse * 120, py + 30 + pulse * 120),
              outline=c.accent + (int(255 * (1 - pulse)),), width=8)
    glow_circle(d, px, py, 26, c.accent)


def _sphere(r, colour, light=(-0.5, -0.6)):
    yy, xx = np.mgrid[-r:r, -r:r].astype(np.float32) / r
    rr = xx ** 2 + yy ** 2
    inside = rr <= 1
    z = np.sqrt(np.clip(1 - rr, 0, 1))
    lx, ly = light
    lz = math.sqrt(max(1 - lx * lx - ly * ly, 0))
    shade = np.clip(xx * lx + yy * ly + z * lz, 0, 1) * 0.85 + 0.15
    rgb = np.stack([shade * colour[i] for i in range(3)], -1)
    a = (inside * 255).astype(np.uint8)
    return np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), a]), xx, yy, z, inside


def scene_globe(layer, t, dur, p, c):
    r = 380
    arr, xx, yy, z, inside = _sphere(r, (40, 90, 170))
    lon = np.arctan2(xx, z) + t * 0.35
    land = (np.sin(lon * 3) * np.cos(yy * 4) + 0.6 * np.sin(lon * 5 + 1) * np.sin(yy * 3)) > 0.55
    arr[..., :3][land & inside] = (arr[..., :3][land & inside] * np.array([0.6, 1.0, 0.5])).astype(np.uint8)
    img = Image.fromarray(arr, 'RGBA')
    d = ImageDraw.Draw(img)
    for k in range(6):
        w = abs(math.cos(k * math.pi / 6 + t * 0.35)) * r
        d.ellipse((r - w, 0, r + w, 2 * r), outline=(255, 255, 255, 40), width=2)
    layer.alpha_composite(img, (int(W / 2 - r), int(SCENE_CY - r)))
    ld = ImageDraw.Draw(layer)
    ox, oy = W / 2 - 120, SCENE_CY - 60
    period = p.get('period', 1.6)
    for k in range(int(t / period) + 1):
        age = t - k * period
        if age < 0:
            continue
        rr = min(age / period, 1) * r * 1.9
        a = int(230 * max(0, 1 - age / (period * 1.3)))
        if a > 0:
            ld.ellipse((ox - rr, oy - rr * 0.92, ox + rr, oy + rr * 0.92), outline=c.accent + (a,), width=10)
    glow_circle(ld, ox, oy, 18, c.accent)
    if p.get('counter'):
        n = min(int(t / period) + 1, p['counter'])
        draw_text_centered(layer, f"x{n}", SCENE_CY + r + 110, 150, c.accent, stroke=8)


def scene_waves(layer, t, dur, p, c):
    d = ImageDraw.Draw(layer)
    cx = p.get('x', 0.5) * W
    for k in range(8):
        age = (t * 0.9 + k / 8) % 1
        r = 60 + age * 520
        d.arc((cx - r, SCENE_CY - r, cx + r, SCENE_CY + r), -50, 50, fill=(255, 255, 255, int(220 * (1 - age))), width=12)
        d.arc((cx - r, SCENE_CY - r, cx + r, SCENE_CY + r), 130, 230, fill=(255, 255, 255, int(220 * (1 - age))), width=12)
    pts = []
    for i in range(0, W, 8):
        u = i / W
        amp = 160 * math.exp(-((u - 0.5) * 4) ** 2) * (0.6 + 0.4 * math.sin(t * 12))
        pts.append((i, SCENE_CY + 470 + amp * math.sin(u * 60 + t * 20)))
    d.line(pts, fill=c.accent + (255,), width=8)
    glow_circle(d, cx, SCENE_CY, 50, c.accent)


def scene_ship(layer, t, dur, p, c):
    d = ImageDraw.Draw(layer)
    sea = SCENE_CY + 260
    roll = math.sin(t * 2.2) * 0.12
    cx, cy = W / 2, sea - 40 + math.sin(t * 2.2 + 1) * 18

    def rot(x, y):
        return (cx + x * math.cos(roll) - y * math.sin(roll), cy + x * math.sin(roll) + y * math.cos(roll))
    d.polygon([rot(-330, 0), rot(330, 0), rot(260, 110), rot(-260, 110)], fill=(110, 72, 44, 255))
    for mx, h in ((-150, 520), (40, 600), (210, 440)):
        d.line([rot(mx, 0), rot(mx, -h)], fill=(30, 22, 16, 255), width=12)
        d.polygon([rot(mx - 70, -h + 60), rot(mx + 70, -h + 60), rot(mx + 80, -h * 0.3), rot(mx - 80, -h * 0.3)],
                  fill=(205, 195, 170, 235))
    for i in range(5):
        y = sea + 60 + i * 55
        pts = [(x, y + 24 * math.sin(x / 90 + t * 3 + i)) for x in range(0, W + 20, 20)]
        d.line(pts, fill=(90, 120, 150, 200 - i * 30), width=10)
    rng = random.Random(int(t * 30))
    for _ in range(80):
        x, y = rng.uniform(0, W), (rng.uniform(0, 1) * 1400 + t * 120) % 1400 + 80
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(170, 170, 170, 160))
    if p.get('shock', True):
        age = t % 2.4
        r = age * 600
        d.ellipse((W / 2 - r, SCENE_CY - 300 - r, W / 2 + r, SCENE_CY - 300 + r),
                  outline=(255, 255, 255, int(200 * max(0, 1 - age / 1.6))), width=14)


def scene_planet(layer, t, dur, p, c):
    r = p.get('r', 400)
    col = hex_rgb(p.get('colour', '#d9a35b'))
    arr, xx, yy, z, inside = _sphere(r, col)
    spin = p.get('spin', 1)
    lon = np.arctan2(xx, z) + spin * t * 0.4
    bands = (np.sin(yy * 9 + np.sin(lon * 2) * 0.6) * 0.12 + 1)
    arr[..., :3] = np.clip(arr[..., :3] * bands[..., None], 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, 'RGBA')
    halo = Image.new('RGBA', (2 * r + 200, 2 * r + 200), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((60, 60, 2 * r + 140, 2 * r + 140), fill=col + (90,))
    halo = halo.filter(ImageFilter.GaussianBlur(40))
    layer.alpha_composite(halo, (int(W / 2 - r - 100), int(SCENE_CY - r - 100)))
    layer.alpha_composite(img, (int(W / 2 - r), int(SCENE_CY - r)))
    if p.get('arrow'):
        d = ImageDraw.Draw(layer)
        y = SCENE_CY + r + 90
        k = (t * 0.8) % 1
        x0, x1 = (W / 2 + 260, W / 2 - 260) if spin < 0 else (W / 2 - 260, W / 2 + 260)
        x = x0 + (x1 - x0) * ease_out(k)
        d.line((x0, y, x, y), fill=c.accent + (255,), width=16)
        s = -1 if x1 < x0 else 1
        d.polygon([(x + s * 40, y), (x - s * 10, y - 34), (x - s * 10, y + 34)], fill=c.accent + (255,))


def scene_counter(layer, t, dur, p, c):
    k = ease_out(t / max(dur * 0.6, 0.1))
    val = p['to'] * k
    txt = (f"{val:,.0f}" if p.get('decimals', 0) == 0 else f"{val:,.{p['decimals']}f}") + p.get('unit', '')
    draw_text_centered(layer, p.get('prefix', '') + txt, SCENE_CY, 300, c.accent, stroke=14)
    if p.get('label'):
        draw_text_centered(layer, p['label'].upper(), SCENE_CY + 230, 90, c.ink, stroke=8)


def scene_shaft(layer, t, dur, p, c):
    d = ImageDraw.Draw(layer)
    depth = p.get('depth', 4000) * ease_out(t / dur)
    off = (t * 900) % 200
    d.rectangle((W / 2 - 300, 120, W / 2 + 300, SCENE_CY + 560), fill=(20, 16, 14, 255))
    for y in range(-200, 1600, 200):
        yy = y + off
        d.line((W / 2 - 300, yy, W / 2 - 240, yy + 30), fill=(90, 70, 50, 255), width=8)
        d.line((W / 2 + 300, yy, W / 2 + 240, yy + 30), fill=(90, 70, 50, 255), width=8)
    heat = min(depth / p.get('depth', 4000), 1)
    tint = Image.new('RGBA', layer.size, (255, 80, 20, int(90 * heat)))
    layer.alpha_composite(tint)
    d = ImageDraw.Draw(layer)
    d.rectangle((W / 2 - 150, SCENE_CY - 120, W / 2 + 150, SCENE_CY + 120), outline=(200, 200, 200, 255), width=10)
    d.line((W / 2, 120, W / 2, SCENE_CY - 120), fill=(160, 160, 160, 255), width=6)
    glow_circle(d, W / 2, SCENE_CY - 60, 22, (255, 240, 180))
    draw_text_centered(layer, f"-{depth:,.0f} M", SCENE_CY + 330, 150, c.accent, stroke=10)


def scene_drift(layer, t, dur, p, c):
    d = ImageDraw.Draw(layer)
    top = SCENE_CY - 420
    d.rectangle((0, top, W, SCENE_CY + 520), fill=(196, 170, 136, 255))
    rng = random.Random(5)
    for _ in range(60):
        x, y = rng.uniform(0, W), rng.uniform(top, SCENE_CY + 520)
        pts = [(x, y)]
        for _ in range(4):
            x += rng.uniform(-90, 90)
            y += rng.uniform(-90, 90)
            pts.append((x, y))
        d.line(pts, fill=(150, 125, 95, 255), width=4)
    d.polygon([(0, top), (200, top - 160), (420, top - 60), (640, top - 220), (900, top - 90), (W, top - 150), (W, top)],
              fill=(110, 80, 70, 255))
    k = t / dur
    pts = [(150 + u * 700, SCENE_CY + 380 - 520 * u + 80 * math.sin(u * 5)) for u in np.linspace(0, 0.3 + 0.6 * k, 50)]
    d.line(pts, fill=(130, 105, 80, 255), width=34, joint='curve')
    x, y = pts[-1]
    d.ellipse((x - 70, y - 50, x + 70, y + 50), fill=(70, 60, 55, 255))
    if p.get('ice'):
        a = int(110 * (0.5 + 0.5 * math.sin(t * 2)))
        layer.alpha_composite(Image.new('RGBA', layer.size, (200, 230, 255, a)))


def scene_stars(layer, t, dur, p, c):
    d = ImageDraw.Draw(layer)
    rng = random.Random(11)
    for _ in range(220):
        x, y, s = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 4)
        tw = 0.5 + 0.5 * math.sin(t * 3 + x)
        d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 255, 255, int(255 * tw)))


SCENES = {
    'explosion': scene_explosion, 'map': scene_map, 'globe': scene_globe,
    'waves': scene_waves, 'ship': scene_ship, 'planet': scene_planet,
    'counter': scene_counter, 'shaft': scene_shaft, 'drift': scene_drift,
    'stars': scene_stars,
}


# --------------------------------------------------------------- render

def background(pal):
    top, bot = np.array(hex_rgb(pal['bg1'])), np.array(hex_rgb(pal['bg2']))
    k = np.linspace(0, 1, H)[:, None, None]
    grad = (top * (1 - k) + bot * k) * np.ones((1, W, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.55 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2
    return Image.fromarray(np.clip(grad * vig[..., None], 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def render(spec, out_path):
    rng = np.random.default_rng(spec.get('seed', 1))
    segs = spec['segments']
    clips = synth_voice(segs, spec.get('voice', 'am_michael'), spec.get('speed', 1.05))
    audio, starts, durs, total = build_audio(clips, segs, rng)

    pal = spec['palette']
    c = Ctx(pal, random.Random(1))
    bg = background(pal)
    keywords = [k.upper() for k in spec.get('keywords', [])] + [s['big'].upper() for s in segs if s.get('big')]
    chunks = []
    for s, st, du in zip(segs, starts, durs):
        chunks += caption_chunks(s['text'], st, du)
    ends = [st + du + GAP for st, du in zip(starts, durs)]
    ends[-1] = total

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, 'a.wav')
        sf.write(wav, audio, SR)
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', wav,
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out_path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n_frames = int(total * FPS)
        for f in range(n_frames):
            t = f / FPS
            i = next(j for j, e in enumerate(ends) if t < e or j == len(ends) - 1)
            seg, ts = segs[i], t - starts[i]
            seg_dur = ends[i] - starts[i]
            frame = bg.copy()
            layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            SCENES[seg.get('scene', 'stars')](layer, max(ts, 0), seg_dur, seg.get('params', {}), c)
            fade = ease_out(ts / 0.25) if i > 0 else 1.0
            if fade < 1:
                layer.putalpha(layer.getchannel('A').point(lambda a: int(a * fade)))
            frame.alpha_composite(layer)
            if seg.get('big'):
                age = ts
                draw_text_centered(frame, seg['big'].upper(), 250, 150, c.accent, stroke=12,
                                   scale=0.6 + 0.4 * ease_back(age / 0.3))
            for a, b, txt in chunks:
                if a <= t < b:
                    draw_caption(frame, txt, keywords, c.accent, t - a)
                    break
            if i == len(segs) - 1 and spec.get('subscribe', True):
                k = 1 + 0.06 * math.sin(t * 8)
                bw, bh = 520 * k, 130 * k
                dd = ImageDraw.Draw(frame)
                dd.rounded_rectangle((W / 2 - bw / 2, 1650 - bh / 2, W / 2 + bw / 2, 1650 + bh / 2), 30,
                                     fill=(230, 30, 30, 255))
                dd.text((W / 2, 1650), 'SUBSCRIBE', font=font(int(80 * k)), fill=(255, 255, 255), anchor='mm')
            # progress bar
            ImageDraw.Draw(frame).rectangle((0, 0, W * t / total, 12), fill=c.accent + (255,))
            shake = (6 * math.sin(t * 90), 6 * math.cos(t * 77)) if seg.get('sfx') == 'boom' and ts < 0.6 else (0, 0)
            rgb = frame.convert('RGB')
            if shake != (0, 0):
                rgb = rgb.transform(rgb.size, Image.AFFINE, (1, 0, shake[0], 0, 1, shake[1]))
            proc.stdin.write(rgb.tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise SystemExit('ffmpeg failed')
    return total


if __name__ == '__main__':
    spec_path, out = sys.argv[1], sys.argv[2]
    with open(spec_path) as fh:
        spec = json.load(fh)
    secs = render(spec, out)
    print(json.dumps({'out': out, 'seconds': round(secs, 2)}))
