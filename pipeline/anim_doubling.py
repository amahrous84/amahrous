#!/usr/bin/env python3
"""Code-rendered animated comparison Short: "What if Earth doubled in size every second?"

The timer on screen runs in real time. Earth's radius is 6,371 km x 2^t. The camera
zooms out a little slower than Earth grows, so Earth visibly swells while the Moon and
then the Sun slide in from the top and disappear behind it.

Facts used (average values): Earth radius 6,371 km, Moon distance 384,400 km and radius
1,737 km, Sun distance 149.6 million km and radius 696,000 km.
Moon fully covered when 6371*2^t >= 384,400 + 1,737  -> t = 5.92 s
Sun fully covered  when 6371*2^t >= 149.6e6 + 696,000 -> t = 14.53 s (Earth then ~216x the Sun's width)

Usage: python3 pipeline/anim_doubling.py out.mp4 [audio_dir]
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, 'fonts', 'Anton-Regular.ttf')
R_E, D_MOON, R_MOON, D_SUN, R_SUN = 6371, 384400, 1737, 149.6e6, 696000
T_MOON = math.log2((D_MOON + R_MOON) / R_E)
T_SUN = math.log2((D_SUN + R_SUN) / R_E)
T_JUP = math.log2(69911 / R_E)    # Earth wider than Jupiter: 3.46 s
T_SUNW = math.log2(R_SUN / R_E)   # Earth wider than the Sun: 6.77 s
END = 15.0            # timer stops here
HOLD = 2.0            # payoff card
TOTAL = END + HOLD
CX, CY = W // 2, 1420  # Earth centre on screen
R0 = 170               # Earth radius on screen at t=0 (px)
GROW = 0.12            # on-screen radius grows as 2^(GROW*t)
MOON_ANG = math.radians(-112)
SUN_ANG = math.radians(-82)
rng = np.random.default_rng(7)


def font(size):
    return ImageFont.truetype(FONT, size)


def noise(n, octaves=5, seed=1):
    g = np.random.default_rng(seed)
    out = np.zeros((n, n))
    for o in range(octaves):
        k = 4 * 2 ** o
        small = g.random((k, k))
        img = Image.fromarray((small * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
        out += np.asarray(img, float) / 255 / (1.6 ** o)
    out -= out.min()
    return out / out.max()


def sphere(n, tex_rgb, light=(-0.55, -0.45, 0.70), rim=None, rot=0.0):
    """Shade an equirectangular texture onto a sphere of diameter n."""
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    r2 = x ** 2 + y ** 2
    mask = r2 <= 1
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    lon = (np.arctan2(x, z) / (2 * np.pi) + 0.5 + rot) % 1.0
    lat = np.arcsin(np.clip(y, -1, 1)) / np.pi + 0.5
    th, tw = tex_rgb.shape[:2]
    col = tex_rgb[(lat * (th - 1)).astype(int), (lon * (tw - 1)).astype(int)].astype(float)
    lx, ly, lz = light
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    shade = np.clip((x * lx + y * ly + z * lz) / ln, 0, 1) * 0.9 + 0.12
    col *= shade[..., None]
    if rim is not None:
        edge = np.clip((r2 - 0.80) / 0.20, 0, 1) ** 2
        col = col * (1 - edge[..., None] * 0.6) + np.array(rim) * edge[..., None] * 0.6
    alpha = np.clip((1 - r2) * n / 3, 0, 1) * 255
    rgba = np.dstack([np.clip(col, 0, 255), alpha]).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA')


def earth_texture():
    n = noise(512, seed=3)
    lat = np.linspace(-1, 1, 512)[:, None] * np.ones((1, 512))
    land = n > 0.55
    ocean = np.dstack([18 + 30 * n, 70 + 60 * n, 150 + 80 * n])
    green = np.dstack([60 + 60 * n, 120 + 50 * n, 50 + 30 * n])
    tex = np.where(land[..., None], green, ocean)
    ice = np.abs(lat) > 0.86
    tex[ice] = [235, 240, 245]
    clouds = noise(512, seed=11)
    c = np.clip((clouds - 0.58) * 4, 0, 0.85)[..., None]
    tex = tex * (1 - c) + 250 * c
    tex = np.concatenate([tex, tex[:, ::-1]], axis=1)  # mirrored copy: seamless wrap
    return tex.astype(np.uint8)


def moon_texture():
    n = noise(256, seed=5)
    tex = np.dstack([150 + 70 * n] * 3)
    g = np.random.default_rng(9)
    yy, xx = np.mgrid[0:256, 0:512]
    tex = np.concatenate([tex, tex[:, ::-1]], axis=1)
    for _ in range(40):
        cx, cy, r = g.integers(0, 512), g.integers(0, 256), g.integers(4, 18)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        tex[d < r] *= 0.78
    return np.clip(tex, 0, 255).astype(np.uint8)


EARTH_TEX = earth_texture()
MOON_IMG = sphere(400, moon_texture(), rim=None)
STARS = [(rng.integers(0, W), rng.integers(0, H), rng.random() * 1.8 + 0.4, rng.random() * 6.28)
         for _ in range(260)]


def sun_sprite(size):
    s = max(8, int(size))
    pad = s * 3
    img = Image.new('RGBA', (pad * 2, pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(30, 0, -1):
        rr = s * (1 + i / 10)
        a = int(110 * (1 - i / 30) ** 2)
        d.ellipse([pad - rr, pad - rr, pad + rr, pad + rr], fill=(255, 190, 60, a))
    d.ellipse([pad - s, pad - s, pad + s, pad + s], fill=(255, 236, 160, 255))
    return img.filter(ImageFilter.GaussianBlur(max(1, s // 6)))


def fmt_km(km):
    if km < 1e6:
        return f'{km:,.0f} KM'
    if km < 1e9:
        return f'{km / 1e6:,.1f} MILLION KM'
    return f'{km / 1e9:,.2f} BILLION KM'


def text_c(d, y, s, f, fill=(255, 255, 255), stroke=6):
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def wrap(d, s, f, maxw):
    lines, cur = [], ''
    for word in s.split():
        t = (cur + ' ' + word).strip()
        if d.textlength(t, font=f) > maxw and cur:
            lines.append(cur)
            cur = word
        else:
            cur = t
    return lines + [cur]


def frame(t):
    tt = min(t, END)
    img = Image.new('RGB', (W, H), (4, 6, 16))
    d = ImageDraw.Draw(img)
    for x, y, s, ph in STARS:
        b = int(150 + 100 * math.sin(ph + t * 2))
        d.ellipse([x - s, y - s, x + s, y + s], fill=(b, b, b + 10))

    R = R_E * 2 ** tt                 # Earth radius in km
    r_px = R0 * 2 ** (GROW * tt)      # Earth radius on screen
    k = r_px / R                      # px per km

    labels = []
    # Sun (behind the Moon and Earth)
    if tt < T_SUN + 0.05:
        dpx = D_SUN * k
        sx, sy = CX + dpx * math.cos(SUN_ANG), CY + dpx * math.sin(SUN_ANG)
        if sy > -400:
            spr = sun_sprite(max(R_SUN * k, 34))
            img.paste(spr, (int(sx - spr.width / 2), int(sy - spr.height / 2)), spr)
            labels.append((sx, sy, max(R_SUN * k, 34), 'SUN'))
    # Moon
    if tt < T_MOON + 0.05:
        dpx = D_MOON * k
        mx, my = CX + dpx * math.cos(MOON_ANG), CY + dpx * math.sin(MOON_ANG)
        mr = max(R_MOON * k, 24)
        if my > -200:
            m = MOON_IMG.resize((int(mr * 2), int(mr * 2)), Image.LANCZOS)
            img.paste(m, (int(mx - mr), int(my - mr)), m)
            labels.append((mx, my, mr, 'MOON'))

    # Earth with a thin atmosphere glow
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(14, 0, -1):
        rr = r_px * (1 + i * 0.012)
        gd.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], fill=(80, 150, 255, int(10 + 4 * (14 - i))))
    img.paste(glow, (0, 0), glow.filter(ImageFilter.GaussianBlur(6)))
    n = int(r_px * 2)
    e = sphere(min(n, 1200), EARTH_TEX, rim=(120, 180, 255), rot=t * 0.02)
    if n != e.width:
        e = e.resize((n, n), Image.LANCZOS)
    img.paste(e, (int(CX - r_px), int(CY - r_px)), e)

    # Text
    d = ImageDraw.Draw(img)
    for lx, ly, lr, name in labels:
        if ly - lr - 60 > 380 and math.hypot(lx - CX, ly - CY) > r_px + lr:
            fl = font(46)
            w = d.textlength(name, font=fl)
            d.text((lx - w / 2, ly - lr - 62), name, font=fl, fill=(230, 230, 230), stroke_width=4, stroke_fill=(0, 0, 0))
    f_title, f_timer, f_small, f_event = font(78), font(190), font(54), font(70)
    if t < 2.8:
        for i, line in enumerate(wrap(d, 'WHAT IF EARTH DOUBLED IN SIZE EVERY SECOND?', f_title, 960)):
            text_c(d, 110 + i * 96, line, f_title)
    else:
        text_c(d, 90, f'{tt:0.1f} s', f_timer, fill=(255, 225, 90), stroke=8)
        text_c(d, 330, "EARTH'S WIDTH: " + fmt_km(2 * R), f_small)
    events = [(T_JUP, 'WIDER THAN JUPITER', (120, 230, 140)), (T_MOON, 'THE MOON: GONE', (255, 120, 90)),
              (T_SUNW, 'WIDER THAN THE SUN', (120, 230, 140)), (T_SUN, 'THE SUN: GONE', (255, 120, 90))]
    for j, (te, label, colr) in enumerate(events):
        nxt = events[j + 1][0] if j + 1 < len(events) else 99
        if te <= tt < min(te + 2.5, nxt) and t <= END:
            pop = min(1, (tt - te) / 0.15)
            f = font(int(70 + 30 * pop))
            text_c(d, 470, label, f, fill=colr, stroke=7)
    if t > END:
        a = min(1, (t - END) / 0.3)
        over = Image.new('RGBA', (W, H), (0, 0, 0, int(150 * a)))
        img.paste(over, (0, 0), over)
        d = ImageDraw.Draw(img)
        text_c(d, 560, 'UNDER 15 SECONDS', font(110), fill=(255, 225, 90), stroke=8)
        for i, line in enumerate(wrap(d, "and Earth is now 216 times wider than the Sun", font(80), 900)):
            text_c(d, 720 + i * 100, line.upper(), font(80))
        text_c(d, 1720, 'WHAT IF #12', font(54), fill=(180, 200, 255), stroke=5)
    return img


def main():
    out = sys.argv[1]
    audio_dir = sys.argv[2] if len(sys.argv) > 2 else None
    tmp = out + '.frames'
    os.makedirs(tmp, exist_ok=True)
    nframes = int(TOTAL * FPS)
    for i in range(nframes):
        frame(i / FPS).save(f'{tmp}/{i:04d}.png')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{tmp}/%04d.png']
    starts = [0.15, T_MOON + 0.05, 13.6]
    clips = []
    if audio_dir:
        for j, s in enumerate(starts, 1):
            p = os.path.join(audio_dir, f'{j:02d}.mp3')
            if os.path.exists(p):
                clips.append((p, s))
    for p, _ in clips:
        cmd += ['-i', p]
    if clips:
        parts = ''.join(f'[{k + 1}:a]adelay={int(s * 1000)}|{int(s * 1000)}[a{k}];' for k, (_, s) in enumerate(clips))
        mix = ''.join(f'[a{k}]' for k in range(len(clips)))
        cmd += ['-filter_complex', parts + f'{mix}amix=inputs={len(clips)}:normalize=0[aout]',
                '-map', '0:v', '-map', '[aout]', '-c:a', 'aac', '-b:a', '160k', '-t', str(TOTAL)]
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', out]
    subprocess.run(cmd, check=True)
    print('wrote', out, f'moon {T_MOON:.2f}s sun {T_SUN:.2f}s')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--still':
        for s in map(float, sys.argv[3:]):
            frame(s).save(f'{sys.argv[1]}_{s:05.2f}.png')
    else:
        main()
