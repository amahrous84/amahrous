#!/usr/bin/env python3
"""Code-rendered Short: the 1958 Lituya Bay wave (Alaska), run-up 524 m.

One event, one growing measurement: water surging up a mountainside, with landmark
silhouettes as rulers. Follows pipeline/FORMAT.md: action in frame 0, no title card,
target line visible from the start, guess prompt in the first 2 s, a beat about every
second, payoff number at the end, short enough to loop.

Facts (two sources each, see the spec description):
  July 9, 1958, magnitude 7.8 earthquake; about 30 million cubic metres of rock fell
  into the bay; the water stripped trees to 524 m (1,720 ft) up the opposite slope.
Ruler heights: Statue of Liberty 93 m, Great Pyramid 139 m, Golden Gate Bridge tower
227 m, Eiffel Tower 330 m, Empire State Building 443 m (to tip).

Usage: python3 pipeline/anim_lituya.py out.mp4 [audio_dir]
       python3 pipeline/anim_lituya.py prefix --still 0 0.5 1 2
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, 'fonts', 'Anton-Regular.ttf')
TOP_M = 524
CLIMB = 9.6            # seconds for the water to reach the top
HOLD = 1.9             # payoff stays on screen while the last line finishes
TOTAL = CLIMB + HOLD
H0 = 28                # water height in frame 0 (already moving)
SEA_Y = 1700           # screen y of sea level
PXM = 2.02             # pixels per metre
YELLOW, RED, WHITE = (255, 225, 90), (230, 40, 40), (255, 255, 255)
RULERS = [  # name, height m, x centre, label
    ('LIBERTY', 93, 80, 'THE STATUE OF LIBERTY'),
    ('PYRAMID', 139, 215, 'THE GREAT PYRAMID'),
    ('GOLDEN GATE', 227, 350, 'THE GOLDEN GATE BRIDGE'),
    ('EIFFEL', 330, 472, 'THE EIFFEL TOWER'),
    ('EMPIRE STATE', 443, 592, 'THE EMPIRE STATE BUILDING'),
]
rng = np.random.default_rng(1958)


def font(size):
    return ImageFont.truetype(FONT, size)


def y_of(m):
    return SEA_Y - m * PXM


def height(t):
    """Water run-up height in metres at time t (fast start, eases into the top)."""
    u = min(max(t / CLIMB, 0), 1)
    return H0 + (TOP_M - H0) * (1 - (1 - u) ** 1.6)


def t_of(m):
    u = 1 - (1 - (m - H0) / (TOP_M - H0)) ** (1 / 1.6)
    return u * CLIMB


def slope_x(m):
    """Left edge of the mountainside at height m (the slope leans right going up)."""
    return 800 + (m / 560) * 130 + 14 * math.sin(m / 37)


TREES = []
for _ in range(230):
    m = rng.uniform(8, 600)
    TREES.append((m, slope_x(m) + rng.uniform(6, 270 - m * 0.12), rng.uniform(16, 30)))
TREES.sort()
SNOW = [(rng.uniform(0, W), rng.uniform(0, 1), rng.uniform(1, 3)) for _ in range(40)]


def sky():
    g = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([18, 34, 72]), np.array([120, 170, 215])
    col = top * (1 - g) + bot * g
    return Image.fromarray(np.repeat(col[:, None, :], W, 1).astype(np.uint8), 'RGB')


SKY = sky()


def draw_ruler(d, name, hm, x, sunk, hit):
    base, top = SEA_Y, y_of(hm)
    c = (70, 120, 170) if sunk else (245, 245, 250)
    o = (10, 20, 40)
    if name == 'LIBERTY':
        d.rectangle([x - 26, top + 110, x + 26, base], fill=c, outline=o, width=3)
        d.polygon([(x - 16, top + 110), (x + 16, top + 110), (x + 9, top + 40), (x - 9, top + 40)], fill=c, outline=o)
        d.ellipse([x - 11, top + 22, x + 11, top + 44], fill=c, outline=o)
        d.line([(x + 8, top + 50), (x + 22, top + 6)], fill=c, width=9)
        d.ellipse([x + 14, top - 6, x + 30, top + 10], fill=YELLOW if not sunk else c)
    elif name == 'PYRAMID':
        d.polygon([(x - 80, base), (x + 80, base), (x, top)], fill=c, outline=o)
    elif name == 'GOLDEN GATE':
        d.rectangle([x - 34, top, x - 20, base], fill=c, outline=o, width=2)
        d.rectangle([x + 20, top, x + 34, base], fill=c, outline=o, width=2)
        for k in range(5):
            yy = top + 30 + k * (base - top - 60) / 4
            d.rectangle([x - 34, yy, x + 34, yy + 14], fill=c, outline=o, width=2)
    elif name == 'EIFFEL':
        d.polygon([(x - 62, base), (x - 36, base), (x - 8, top + 60), (x - 5, top), (x + 5, top), (x + 8, top + 60),
                   (x + 36, base), (x + 62, base), (x + 14, top + 330), (x - 14, top + 330)], fill=c, outline=o)
        d.rectangle([x - 44, base - 150, x + 44, base - 132], fill=c, outline=o, width=2)
        d.rectangle([x - 24, top + 300, x + 24, top + 316], fill=c, outline=o, width=2)
    else:  # EMPIRE STATE
        d.rectangle([x - 52, top + 420, x + 52, base], fill=c, outline=o, width=3)
        d.rectangle([x - 40, top + 250, x + 40, top + 420], fill=c, outline=o, width=3)
        d.rectangle([x - 28, top + 140, x + 28, top + 250], fill=c, outline=o, width=3)
        d.rectangle([x - 14, top + 80, x + 14, top + 140], fill=c, outline=o, width=3)
        d.rectangle([x - 4, top, x + 4, top + 80], fill=c, outline=o)
    f = font(30)
    lab = name
    w = d.textlength(lab, font=f)
    col = YELLOW if hit else WHITE
    d.text((x - w / 2, top - 46 - (22 if name == 'LIBERTY' else 0)), lab, font=f, fill=col,
           stroke_width=3, stroke_fill=(0, 0, 0))


def text_c(d, y, s, f, fill=WHITE, stroke=7, cx=W / 2):
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def fit(d, s, size, maxw):
    f = font(size)
    while d.textlength(s, font=f) > maxw and size > 30:
        size -= 4
        f = font(size)
    return f


def frame(t):
    tt = min(t, CLIMB)
    hm = height(tt)
    wy = y_of(hm)                       # screen y of the water front
    img = SKY.copy()
    d = ImageDraw.Draw(img, 'RGBA')

    # far ridge
    d.polygon([(0, 1500), (160, 1340), (330, 1450), (520, 1300), (700, 1420), (780, 1380), (780, SEA_Y), (0, SEA_Y)],
              fill=(60, 84, 120, 255))
    # the mountainside on the right
    pts = [(slope_x(m), y_of(m)) for m in range(0, 700, 10)]
    d.polygon(pts + [(W, y_of(700)), (W, SEA_Y)], fill=(74, 82, 70, 255))

    # trees: standing above the water front, stripped (bare rock streak) below it
    for m, x, s in TREES:
        y = y_of(m)
        if m > hm + 4:
            if m < 540:
                d.polygon([(x, y - s * 1.7), (x - s * 0.6, y), (x + s * 0.6, y)], fill=(28, 74, 44, 255))
        else:
            d.line([(x - s * 0.5, y), (x + s * 0.5, y - 3)], fill=(150, 132, 104, 255), width=4)

    # target line: visible from frame 0
    ty = y_of(TOP_M)
    for x in range(20, W - 10, 44):
        d.line([(x, ty), (x + 24, ty)], fill=RED + (255,), width=7)
    reached = t >= CLIMB
    f_t = font(46)
    d.text((34, ty - 64), 'IT STOPS HERE' if not reached else '524 M', font=f_t, fill=RED if not reached else YELLOW,
           stroke_width=5, stroke_fill=(0, 0, 0))

    # rulers
    for name, rm, x, _ in RULERS:
        draw_ruler(d, name, rm, x, False, abs(tt - t_of(rm)) < 0.9 and hm >= rm)

    # water: the bay, and the surge climbing the slope
    wob = 6 * math.sin(t * 9)
    d.rectangle([0, SEA_Y - 6 + wob / 3, W, H], fill=(22, 86, 150, 255))
    surge = [(slope_x(0) - 150, SEA_Y)]
    for m in np.arange(0, hm + 1, 6):
        thick = 120 * (1 - m / (hm + 1)) ** 0.7 + 26
        surge.append((slope_x(m) - thick + 8 * math.sin(m / 19 + t * 14), y_of(m)))
    surge += [(slope_x(m) + 70 + 0.1 * m, y_of(m)) for m in np.arange(hm, -1, -6)]
    surge.append((W, SEA_Y))
    d.polygon(surge, fill=(40, 132, 208, 255))
    # foam at the front
    fx = slope_x(hm)
    for k in range(26):
        a = rng.uniform(-3.4, 0.3)
        r = rng.uniform(10, 34)
        ox, oy = fx - 20 + math.cos(a) * rng.uniform(0, 110), wy + math.sin(a) * rng.uniform(0, 70)
        d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=(240, 250, 255, 230))
    # level line from the water front across the rulers
    d.line([(20, wy), (fx - 30, wy)], fill=(255, 255, 255, 230), width=5)
    d.polygon([(fx - 30, wy - 16), (fx - 30, wy + 16), (fx + 4, wy)], fill=(255, 255, 255, 255))
    # bay waves
    for k in range(7):
        yy = SEA_Y + 26 + k * 30
        ph = t * 5 + k
        d.line([(x, yy + 7 * math.sin(x / 60 + ph)) for x in range(0, W + 30, 30)], fill=(120, 190, 240, 170), width=4)

    # ---- text
    d = ImageDraw.Draw(img)
    text_c(d, 150, f'{hm:,.0f} M', font(230), fill=YELLOW, stroke=10)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    d.text((W - 36 - d.textlength('ALASKA · 1958', font=font(46)), 48), 'ALASKA · 1958', font=font(46), fill=WHITE,
           stroke_width=4, stroke_fill=(0, 0, 0))
    passed = [(t_of(rm), lab) for _, rm, _, lab in RULERS if hm >= rm]
    if reached:
        text_c(d, 430, 'TALLER THAN THE EMPIRE STATE BUILDING', fit(d, 'TALLER THAN THE EMPIRE STATE BUILDING', 76, 1010),
               fill=WHITE, stroke=8)
        text_c(d, 536, 'WERE YOU RIGHT?', font(64), fill=YELLOW, stroke=7)
    elif passed and tt - passed[-1][0] < 1.5:
        tp, lab = passed[-1]
        pop = min(1, (tt - tp) / 0.12)
        s = 'PAST ' + lab
        f = fit(d, s, int(58 + 20 * pop), 1010)
        text_c(d, 440, s, f, fill=(130, 240, 150), stroke=8)
    elif tt < 2.3:
        text_c(d, 430, 'GUESS: HOW HIGH DID THIS WAVE CLIMB?', fit(d, 'GUESS: HOW HIGH DID THIS WAVE CLIMB?', 70, 1010),
               stroke=8)
    else:
        text_c(d, 440, 'A REAL WAVE. LITUYA BAY.', font(64), stroke=8)
    return img


def main():
    out = sys.argv[1]
    audio_dir = sys.argv[2] if len(sys.argv) > 2 else None
    tmp = out + '.frames'
    os.makedirs(tmp, exist_ok=True)
    for i in range(int(TOTAL * FPS)):
        frame(i / FPS).save(f'{tmp}/{i:04d}.png')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{tmp}/%04d.png']
    starts = [0.1, t_of(330) + 0.05, float(os.environ.get('LINE3_AT', '7.5'))]
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
    print('wrote', out, 'beats', [round(t_of(r[1]), 2) for r in RULERS], 'total', TOTAL)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--still':
        for s in map(float, sys.argv[3:]):
            frame(s).save(f'{sys.argv[1]}_{s:05.2f}.png')
    else:
        main()
