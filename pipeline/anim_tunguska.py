#!/usr/bin/env python3
"""Code-rendered Short: the Tunguska event, 30 June 1908. Forest flattened: 2,150 km2.

One event, one growing measurement: the blast front spreading through the forest, seen
from above, with the camera pulling back so the ring always fills the frame. City areas
are drawn as circles of equal area centred on the blast. A gauge on the right shows the
whole spread and the red "IT STOPS HERE" line from frame 0. Follows pipeline/FORMAT.md.

Facts (see the publish entry for sources):
  2,150 km2 (830 sq mi) of forest flattened; the object exploded 5-10 km up; no crater.
  The often-quoted "80 million trees" is disputed, so the Short says "millions of trees".
City areas (Wikipedia): Manhattan 59 km2 land, Paris 105, Washington DC 177, Chicago 607,
New York City 778 land, Berlin 891, Los Angeles 1,215 land, Greater London 1,572.
The real flattened area was butterfly-shaped; the circle here has the same area.

Usage: python3 pipeline/anim_tunguska.py out.mp4 [audio_dir]
       python3 pipeline/anim_tunguska.py prefix --still 0 0.5 1 2
Timing via env: CLIMB, TOTAL, LINE_AT="0.1,2.7,11.0,17.0", CRATER_AT.
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, 'fonts', 'Anton-Regular.ttf')
TOP = 2150.0           # km2
MANH = 58.7
CLIMB = float(os.environ.get('CLIMB', '11.0'))
TOTAL = float(os.environ.get('TOTAL', '20.5'))
LINE_AT = [float(x) for x in os.environ.get('LINE_AT', '0.1,2.7,11.0,17.0').split(',')]
CRATER_AT = float(os.environ.get('CRATER_AT', str(LINE_AT[-1] - 0.2)))
END_Q = TOTAL - 0.7
A0 = 34.0              # area already flattened in frame 0
CX, CY = 500, 1190     # blast centre on screen
RING_PX = 400          # the blast ring is always this many pixels in radius
YELLOW, RED, WHITE, GREEN = (255, 225, 90), (230, 40, 40), (255, 255, 255), (130, 240, 150)
MARKS = [  # km2, label on the map, caption, label angle in degrees
    (58.7, 'MANHATTAN', 'ALL OF MANHATTAN', -90),
    (105.4, 'PARIS', 'ALL OF PARIS', -40),
    (177.0, 'WASHINGTON DC', 'WASHINGTON DC', -140),
    (607.0, 'CHICAGO', 'CHICAGO', -90),
    (778.0, 'NEW YORK CITY', 'ALL OF NEW YORK CITY', -35),
    (891.0, 'BERLIN', 'BERLIN', -145),
    (1215.0, 'LOS ANGELES', 'LOS ANGELES', -90),
    (1572.0, 'LONDON', 'ALL OF LONDON', -38),
]
rng = np.random.default_rng(1908)


def font(size):
    return ImageFont.truetype(FONT, size)


def area(t):
    u = min(max(t / CLIMB, 0), 1)
    return A0 + (TOP - A0) * (1 - (1 - u) ** 1.2)


def t_of(a):
    return (1 - (1 - (a - A0) / (TOP - A0)) ** (1 / 1.2)) * CLIMB


def rad(a):
    return math.sqrt(a / math.pi)


R_END = rad(TOP)
TREES = []
for _ in range(5200):
    r = 60 * rng.uniform(0, 1) ** 0.8
    a = rng.uniform(0, 2 * math.pi)
    TREES.append((r, a, rng.uniform(0.8, 1.2), rng.uniform(-0.25, 0.25)))


def text_c(d, y, s, f, fill=WHITE, stroke=7, cx=W / 2):
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def fit(d, s, size, maxw):
    f = font(size)
    while d.textlength(s, font=f) > maxw and size > 30:
        size -= 4
        f = font(size)
    return f


def dashed_circle(d, r, col, width, n):
    for k in range(n):
        a0 = 360 * k / n
        d.arc([CX - r, CY - r, CX + r, CY + r], a0, a0 + 360 / n * 0.55, fill=col, width=width)


def frame(t):
    tt = min(t, CLIMB)
    a_now = area(tt)
    r_km = rad(a_now)
    pk = RING_PX / r_km                         # pixels per km
    reached = t >= CLIMB
    img = Image.new('RGB', (W, H), (26, 70, 44))
    d = ImageDraw.Draw(img, 'RGBA')
    # flattened ground inside the ring
    d.ellipse([CX - RING_PX, CY - RING_PX, CX + RING_PX, CY + RING_PX], fill=(124, 104, 78, 255))
    # trees: standing outside the front, knocked flat and pointing away inside it
    s0 = min(30, max(6, pk * 0.3))
    for r, a, sc, jit in TREES:
        x, y = CX + r * pk * math.cos(a), CY + r * pk * math.sin(a)
        if x < -40 or x > W + 40 or y < 560 or y > H + 40:
            continue
        s = s0 * sc
        if r > r_km:
            d.polygon([(x, y - s * 1.5), (x - s * 0.62, y + s * 0.5), (x + s * 0.62, y + s * 0.5)], fill=(44, 124, 66, 255))
            d.polygon([(x, y - s * 1.5), (x - s * 0.3, y - s * 0.4), (x + s * 0.3, y - s * 0.4)], fill=(86, 170, 96, 255))
        else:
            aa = a + jit
            d.line([(x, y), (x + s * 1.7 * math.cos(aa), y + s * 1.7 * math.sin(aa))], fill=(70, 52, 34, 255),
                   width=max(2, int(s * 0.22)))
    # scorched centre and fading fireball
    cr = min(RING_PX * 0.5, 3.2 * pk)
    d.ellipse([CX - cr, CY - cr, CX + cr, CY + cr], fill=(40, 30, 24, 150))
    hot = max(0.0, 1 - t / 3.0)
    for k in range(6):
        rr = RING_PX * (0.62 - k * 0.09)
        d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], fill=(255, 170 + k * 14, 60, int(60 * hot)))
    # city circles of equal area
    f_m = font(36)
    for a_c, lab, _, ang in MARKS:
        rc = rad(a_c) * pk
        if rc > 900:
            continue
        passed = a_now >= a_c
        hit = passed and tt - t_of(a_c) < 1.1
        col = YELLOW if hit else ((235, 235, 240) if not passed else (190, 196, 206))
        dashed_circle(d, rc, col + (255,), 6 if hit else 4, 48)
        if rc > 120 or hit:
            lx, ly = CX + rc * math.cos(math.radians(ang)), CY + rc * math.sin(math.radians(ang))
            w = d.textlength(lab, font=f_m)
            lx = min(max(lx - w / 2, 16), 950 - w)
            if 590 < ly - 44 < H - 60:
                d.text((lx, ly - 46), lab, font=f_m, fill=col, stroke_width=4, stroke_fill=(0, 0, 0))
    # target circle
    rt = R_END * pk
    if rt < 900:
        dashed_circle(d, rt, RED + (255,), 8, 40)
    # the blast front
    wob = 5 * math.sin(t * 22)
    for k, (wd, al) in enumerate([(46, 60), (28, 120), (12, 255)]):
        rr = RING_PX + wob * (k == 2)
        d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline=(255, 240, 200, al), width=wd)
    # no-crater beat: an X where a crater would be
    ct = t - CRATER_AT
    if ct > 0:
        k = min(1, ct / 0.15)
        rr = 70 * k
        d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline=WHITE + (255,), width=8)
        d.line([(CX - rr * 1.3, CY - rr * 1.3), (CX + rr * 1.3, CY + rr * 1.3)], fill=RED + (255,), width=16)
        f = font(60)
        s = 'NO CRATER'
        d.text((CX - d.textlength(s, font=f) / 2, CY + 96), s, font=f, fill=WHITE, stroke_width=6, stroke_fill=(0, 0, 0))

    # top band so the text stays readable
    d.rectangle([0, 0, W, 590], fill=(10, 22, 18, 255))
    d.rectangle([0, 590, W, 598], fill=(255, 225, 90, 255))

    # gauge on the right: the whole spread, with the stop line, from frame 0
    gx, g0, g1 = 1022, 1790, 720
    d.rounded_rectangle([gx - 34, g1 - 70, gx + 34, g0 + 26], 14, fill=(0, 0, 0, 170))
    d.rectangle([gx - 6, g1, gx + 6, g0], fill=(255, 255, 255, 110))
    gy = g0 - (a_now / TOP) * (g0 - g1)
    d.rectangle([gx - 6, gy, gx + 6, g0], fill=(255, 170, 60, 255))
    for a_c, *_ in MARKS:
        yy = g0 - a_c / TOP * (g0 - g1)
        d.line([(gx - 16, yy), (gx + 16, yy)], fill=(255, 255, 255, 255) if a_now < a_c else (255, 225, 90, 255), width=4)
    d.rectangle([gx - 30, g1 - 5, gx + 30, g1 + 5], fill=RED + (255,))
    d.ellipse([gx - 20, gy - 14, gx + 20, gy + 14], fill=(250, 250, 250, 255), outline=(0, 0, 0, 255), width=3)

    if t < 0.45:
        fl = Image.new('RGB', (W, H), (255, 250, 230))
        img = Image.blend(img, fl, 0.3 * (1 - t / 0.45))

    # ---- text
    d = ImageDraw.Draw(img)
    s = f'{a_now:,.0f} KM²'
    text_c(d, 132, s, fit(d, s, 220, 1030), fill=YELLOW, stroke=10)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    tag = 'TUNGUSKA · 1908'
    d.text((W - 36 - d.textlength(tag, font=font(46)), 48), tag, font=font(46), fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    f_t = font(40)
    s = 'IT STOPS HERE' if not reached else '2,150 KM²'
    d.text((gx - 48 - d.textlength(s, font=f_t), g1 - 30), s, font=f_t, fill=RED if not reached else YELLOW,
           stroke_width=5, stroke_fill=(0, 0, 0))
    text_c(d, 392, f'FOREST FLATTENED  =  {a_now / MANH:.0f} × MANHATTAN', font(50), fill=WHITE, stroke=6)

    passed = [(t_of(a_c), cap) for a_c, _, cap, _ in MARKS if a_now >= a_c]
    y_cap = 478
    if t >= END_Q:
        text_c(d, y_cap, 'WERE YOU RIGHT?', font(80), fill=YELLOW, stroke=8)
    elif ct > 0:
        s = 'NO CRATER: IT BLEW APART IN THE SKY'
        text_c(d, y_cap, s, fit(d, s, 76, 1010), fill=WHITE, stroke=8)
    elif reached:
        k = t - CLIMB
        s = 'BIGGER THAN LONDON' if k < 2.4 else 'MILLIONS OF TREES KNOCKED FLAT'
        pop = min(1, (k if k < 2.4 else k - 2.4) / 0.12)
        text_c(d, y_cap, s, fit(d, s, int(60 + 20 * pop), 1010), fill=GREEN, stroke=8)
    elif tt < 2.3:
        s = 'GUESS: HOW MUCH FOREST DID IT FLATTEN?'
        text_c(d, y_cap, s, fit(d, s, 72, 1010), stroke=8)
    elif passed and tt - passed[-1][0] < 1.6:
        tp, cap = passed[-1]
        pop = min(1, (tt - tp) / 0.12)
        s = 'BIGGER THAN ' + cap
        text_c(d, y_cap, s, fit(d, s, int(58 + 20 * pop), 1010), fill=GREEN, stroke=8)
    else:
        text_c(d, y_cap, 'STILL SPREADING' + ('...' if int(tt * 2) % 2 else ''), font(64), stroke=8)
    return img


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
    print('wrote', out, 'beats', [round(t_of(m[0]), 2) for m in MARKS], 'total', TOTAL)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--still':
        for s in map(float, sys.argv[3:]):
            frame(s).save(f'{sys.argv[1]}_{s:05.2f}.png')
    else:
        main()
