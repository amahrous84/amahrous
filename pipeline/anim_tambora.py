#!/usr/bin/env python3
"""Code-rendered Short: Mount Tambora, Indonesia, April 1815.

One event, one growing measurement: side view of the volcano losing its top. The summit
drops from about 4,300 m to 2,851 m while a counter climbs in metres of mountain gone;
Empire State Buildings (443 m to the tip) stack up beside the missing part, and the red
line at today's height (2,851 m) is on screen from frame 0. Ash shoots up from the vent.

Heights are to scale vertically; the mountain's width is not (it is about 60 km across).
Not real time. Facts and sources: see the publish entry.

Usage: python3 pipeline/anim_tambora.py out.mp4 [audio_dir]
       python3 pipeline/anim_tambora.py prefix --still 0 0.5 1 2
"""
import math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, 'fonts', 'Anton-Regular.ttf')
H0, H1 = 4300.0, 2851.0
LOST = H0 - H1                              # about 1,450 m
ESB = 443.0
CLIMB = float(os.environ.get('CLIMB', '10.0'))
TOTAL = float(os.environ.get('TOTAL', '19.0'))
LINE_AT = [float(x) for x in os.environ.get('LINE_AT', '0.1,2.5,9.9,12.4').split(',')]
AFTER = float(os.environ.get('AFTER', str(LINE_AT[-1] - 0.1)))
END_Q = TOTAL - 0.7
YELLOW, RED, WHITE, ORANGE = (255, 225, 90), (235, 45, 45), (255, 255, 255), (255, 150, 50)
SEA = 1860
PX_M = (SEA - 700) / H0                     # 4,300 m peak at y = 700
MX = 470                                    # mountain axis
ESB_X = 880

random.seed(3)
PARTS = [(random.uniform(-1, 1), random.uniform(0, 1), random.uniform(0.6, 1.4)) for _ in range(90)]


def lost(t):
    u = min(max(t / CLIMB, 0), 1)
    return LOST * (0.03 + 0.97 * (1 - (1 - u) ** 1.5))


def t_of_lost(m):
    u = 1 - (1 - (m / LOST - 0.03) / 0.97) ** (1 / 1.5)
    return u * CLIMB


def ym(m):
    return SEA - m * PX_M


def font(size):
    return ImageFont.truetype(FONT, size)


def profile(h):
    """Cone outline (list of points) cut flat at height h, with a crater notch."""
    half_base = 520
    top = ym(h)
    full_top = ym(H0)
    # cone sides: x offset grows linearly with depth below the original peak
    k = half_base / (SEA - full_top)
    w = (top - full_top) * k
    pts = [(MX - half_base - 40, SEA), (MX - w - 10, top)]
    if w > 4:
        dip = min(120, (top - full_top) * 0.35)
        pts += [(MX - w * 0.7, top + dip * 0.6), (MX, top + dip), (MX + w * 0.7, top + dip * 0.6)]
    pts += [(MX + w + 10, top), (MX + half_base + 40, SEA)]
    return pts, top, w


def text_c(d, y, s, f, fill=WHITE, stroke=7, cx=W / 2):
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def fit(d, s, size, maxw):
    f = font(size)
    while d.textlength(s, font=f) > maxw and size > 30:
        size -= 4
        f = font(size)
    return f


def esb_icon(d, x, ybot, scale_h, frac, done_col):
    """Empire State Building silhouette from ybot up, height scale_h px; fill frac of it."""
    hh = scale_h
    parts = [(0.0, 0.62, 44), (0.62, 0.78, 30), (0.78, 0.86, 18), (0.86, 0.92, 9), (0.92, 1.0, 3)]
    for a, b, half in parts:
        y0, y1 = ybot - hh * b, ybot - hh * a
        d.rectangle([x - half, y0, x + half, y1], outline=(255, 255, 255, 200), width=2)
        cut = ybot - hh + frac * hh          # filled from the top down, like the summit
        if frac > 0 and cut > y0:
            d.rectangle([x - half, y0, x + half, min(y1, cut)], fill=done_col)


def frame(t):
    tt = min(t, CLIMB)
    m = lost(tt)
    h = H0 - m
    done = t >= CLIMB
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img, 'RGBA')
    # sky gradient, darkening as the ash spreads
    dark = 0.25 + 0.5 * min(1, t / CLIMB)
    for y in range(598, H, 6):
        f = (y - 598) / (H - 598)
        c = (int((120 + 100 * f) * (1 - dark)), int((150 + 70 * f) * (1 - dark)), int((200 + 20 * f) * (1 - dark)))
        d.rectangle([0, y, W, y + 6], fill=c + (255,))
    d.rectangle([0, SEA, W, H], fill=(20, 60, 110, 255))

    # ash column from the current vent (blurred layer)
    ash = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    a = ImageDraw.Draw(ash)
    top = ym(h)
    for k, (dx, ph, sz) in enumerate(PARTS):
        u = (ph + t * 0.55 * sz) % 1.0
        y = top - u * (top - 560)
        x = MX + dx * (30 + 260 * u) + 25 * math.sin(t * 2 + k)
        r = (30 + 110 * u) * sz
        g = int(60 + 60 * (1 - u))
        a.ellipse([x - r, y - r, x + r, y + r], fill=(g + 20, g, g - 10, int(220 * (1 - u * 0.5))))
    if not done or t < CLIMB + 3:
        a.ellipse([MX - 70, top - 60, MX + 70, top + 40], fill=(255, 140, 40, 230))
    ash = ash.filter(ImageFilter.GaussianBlur(6))
    img = Image.alpha_composite(img, ash)
    d = ImageDraw.Draw(img, 'RGBA')

    # the missing top: dashed outline of the original peak
    pts0, _, _ = profile(H0)
    pts, top, w = profile(h)
    full_top = ym(H0)
    left = [(MX - 10, full_top), (MX - w - 10, top)]
    right = [(MX + 10, full_top), (MX + w + 10, top)]
    for (x0, y0), (x1, y1) in (left, right):
        n = 14
        for i in range(n):
            if i % 2:
                continue
            fa, fb = i / n, (i + 1) / n
            d.line([(x0 + (x1 - x0) * fa, y0 + (y1 - y0) * fa), (x0 + (x1 - x0) * fb, y0 + (y1 - y0) * fb)],
                   fill=(255, 255, 255, 230), width=5)
    d.text((MX - 150, full_top - 64), 'BEFORE: 4,300 M', font=font(42), fill=WHITE, stroke_width=5, stroke_fill=(0, 0, 0))

    # mountain body
    d.polygon(pts, fill=(96, 70, 52, 255))
    d.line(pts, fill=(60, 40, 30, 255), width=6)
    # glowing lava at the vent
    if w > 4:
        d.line([(MX - w * 0.5, top + 20), (MX, top + min(120, (top - full_top) * 0.35) - 4), (MX + w * 0.5, top + 20)],
               fill=(255, 120, 30, 255) if not done else (200, 80, 30, 255), width=8)

    # target line: today's height, red from frame 0
    yt = ym(H1)
    for x in range(0, W - 10, 40):
        d.line([(x, yt), (x + 24, yt)], fill=RED + (255,) if not done else YELLOW + (255,), width=6)
    d.text((24, yt + 10), 'TODAY: 2,851 M', font=font(42), fill=RED if not done else YELLOW, stroke_width=5, stroke_fill=(0, 0, 0))

    # Empire State Buildings stacked in the missing band, filling as metres are lost
    hh = ESB * PX_M
    d.rounded_rectangle([ESB_X - 70, ym(H0) - 20, ESB_X + 70, yt + 20], 14, fill=(0, 0, 0, 150))
    for i in range(4):
        yb = ym(H0) + hh * (i + 1)
        if yb - hh > yt + 1:
            break
        frac = min(max((m - i * ESB) / ESB, 0), 1)
        # buildings are stacked from the top down, matching the summit being removed from the top
        esb_icon(d, ESB_X, min(yb, yt), hh if yb <= yt else hh - (yb - yt), frac, ORANGE + (255,))
    nb = m / ESB
    s = f'x{nb:.1f}'
    d.text((ESB_X - d.textlength(s, font=font(46)) / 2, yt + 26), s, font=font(46), fill=ORANGE, stroke_width=5, stroke_fill=(0, 0, 0))
    d.text((ESB_X - 62, ym(H0) - 72), 'EMPIRE STATE', font=font(30), fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))

    d.text((24, SEA + 14), 'MOUNT TAMBORA, INDONESIA', font=font(44), fill=WHITE, stroke_width=5, stroke_fill=(0, 0, 0))

    # top band
    d.rectangle([0, 0, W, 590], fill=(10, 18, 34, 255))
    d.rectangle([0, 590, W, 598], fill=ORANGE + (255,))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    tag = 'INDONESIA · 1815'
    ft = font(46)
    d.text((W - 36 - d.textlength(tag, font=ft), 50), tag, font=ft, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    s = f'{round(m / 10) * 10:,.0f} M GONE'
    text_c(d, 128, s, fit(d, s, 220, 1030), fill=ORANGE, stroke=10)
    s2 = 'OF MOUNTAIN BLOWN OFF THE TOP'
    text_c(d, 392, s2, fit(d, s2, 52, 1010), fill=WHITE, stroke=6)

    y_cap = 478
    if t >= END_Q:
        text_c(d, y_cap, 'WERE YOU RIGHT?', font(80), fill=YELLOW, stroke=8)
    elif t >= AFTER:
        text_c(d, y_cap, CAP_AFTER, fit(d, CAP_AFTER, 72, 1010), fill=WHITE, stroke=8)
    elif done:
        pop = min(1, (t - CLIMB) / 0.12)
        text_c(d, y_cap, CAP_DONE, fit(d, CAP_DONE, int(60 + 20 * pop), 1010), fill=YELLOW, stroke=8)
    elif tt < 2.3:
        text_c(d, y_cap, 'GUESS: HOW MUCH WAS LOST?', fit(d, 'GUESS: HOW MUCH WAS LOST?', 76, 1010), stroke=8)
    else:
        ms = [(t_of_lost(v), f'PAST {v:,} M!') for v in (500, 1000)] + \
             [(t_of_lost(ESB * k), f'{k} EMPIRE STATE BUILDING' + ('S' if k > 1 else '')) for k in (1, 2, 3)]
        ms = [x for x in ms if x[0] <= tt]
        if ms:
            tp, s = max(ms)
        if ms and tt - tp < 1.1:
            pop = min(1, (tt - tp) / 0.12)
            text_c(d, y_cap, s, fit(d, s, int(60 + 18 * pop), 1010), fill=YELLOW, stroke=8)
        else:
            text_c(d, y_cap, 'STILL SHRINKING' + ('...' if int(tt * 2) % 2 else ''), font(64), stroke=8)
    return img.convert('RGB')


CAP_DONE = os.environ.get('CAP_DONE', 'A THIRD OF THE MOUNTAIN, GONE')
CAP_AFTER = os.environ.get('CAP_AFTER', '1816: THE YEAR WITHOUT A SUMMER')


def main():
    out = sys.argv[1]
    audio_dir = sys.argv[2] if len(sys.argv) > 2 else None
    tmp = out + '.frames'
    os.makedirs(tmp, exist_ok=True)
    for i in range(int(TOTAL * FPS)):
        frame(i / FPS).save(f'{tmp}/{i:04d}.png')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{tmp}/%04d.png']
    clips = []
    if audio_dir:
        for j, s in enumerate(LINE_AT, 1):
            p = os.path.join(audio_dir, f'{j:02d}.mp3')
            if os.path.exists(p):
                clips.append((p, s))
    for p, _ in clips:
        cmd += ['-i', p]
    if clips:
        parts = ''.join(f'[{k + 1}:a]adelay={int(s * 1000)}|{int(s * 1000)}[a{k}];' for k, (_, s) in enumerate(clips))
        mx = ''.join(f'[a{k}]' for k in range(len(clips)))
        cmd += ['-filter_complex', parts + f'{mx}amix=inputs={len(clips)}:normalize=0[aout]',
                '-map', '0:v', '-map', '[aout]', '-c:a', 'aac', '-b:a', '160k', '-t', str(TOTAL)]
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', out]
    subprocess.run(cmd, check=True)
    print('wrote', out, 'milestones', [(v, round(t_of_lost(v), 2)) for v in (500, 1000, ESB, 2 * ESB, 3 * ESB)], 'total', TOTAL)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--still':
        for s in map(float, sys.argv[3:]):
            frame(s).save(f'{sys.argv[1]}_{s:05.2f}.png')
    else:
        main()
