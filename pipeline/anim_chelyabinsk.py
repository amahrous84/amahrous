#!/usr/bin/env python3
"""Code-rendered Short: the Chelyabinsk meteor, Russia, 15 February 2013.

One event, one growing measurement: a rock about 20 m wide streaks down over the city
while an energy counter climbs in Hiroshima bombs, lighting 30 bomb icons one by one; a
gauge on the right shows the red 30 line from frame 0. At the end the fireball flashes
brighter than the Sun, the blast wave reaches the city and windows shatter.

Drawn side-on with a made-up city skyline; altitudes, the path angle and the timing are
not to scale or real time. The energy was released mostly in the final seconds of
break-up around 30 km up. Facts and sources: see the publish entry.

Usage: python3 pipeline/anim_chelyabinsk.py out.mp4 [audio_dir]
       python3 pipeline/anim_chelyabinsk.py prefix --still 0 0.5 1 2
"""
import math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, 'fonts', 'Anton-Regular.ttf')
TOP = 30                                   # Hiroshima bombs (about 440-500 kt / 15 kt)
CLIMB = float(os.environ.get('CLIMB', '10.0'))
TOTAL = float(os.environ.get('TOTAL', '18.8'))
LINE_AT = [float(x) for x in os.environ.get('LINE_AT', '0.1,2.5,9.9,12.4').split(',')]
AFTER = float(os.environ.get('AFTER', str(LINE_AT[-1] - 0.1)))
END_Q = TOTAL - 0.7
YELLOW, RED, WHITE, ORANGE = (255, 225, 90), (235, 45, 45), (255, 255, 255), (255, 150, 50)
GROUND = 1790
P0, P1 = (850, 780), (470, 1330)           # meteor path: top right -> burst point
SUN = (150, 1560)

random.seed(7)
BUILD = []
x = 0
while x < W:
    w = random.randint(50, 120)
    h = random.randint(40, 150)
    wins = [(x + 8 + 18 * i, GROUND + 18 - h + 22 * j) for i in range(max(1, (w - 12) // 18))
            for j in range(max(1, (h - 20) // 22)) if random.random() < 0.6]
    BUILD.append((x, w, h, wins))
    x += w + random.randint(4, 14)
SHARDS = [(random.uniform(0, W), random.uniform(GROUND - 140, GROUND + 60), random.uniform(-1, 1),
           random.uniform(-2.2, -0.6), random.uniform(0, 6.28)) for _ in range(140)]


def energy(t):
    u = min(max(t / CLIMB, 0), 1)
    return TOP * (0.04 + 0.96 * u ** 1.35)


def t_of_n(n):
    return CLIMB * ((n / TOP - 0.04) / 0.96) ** (1 / 1.35)


def font(size):
    return ImageFont.truetype(FONT, size)


YY = np.linspace(0, 1, H - 598)[:, None]
SKY_TOP, SKY_BOT = np.array([40, 70, 130], np.float32), np.array([250, 170, 120], np.float32)
SKY = (SKY_TOP * (1 - YY) + SKY_BOT * YY)[:, None, :].repeat(W, axis=1)


def text_c(d, y, s, f, fill=WHITE, stroke=7, cx=W / 2):
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def fit(d, s, size, maxw):
    f = font(size)
    while d.textlength(s, font=f) > maxw and size > 30:
        size -= 4
        f = font(size)
    return f


def bomb(d, x, y, lit, pop):
    s = 1 + 0.35 * pop
    col = (ORANGE + (255,)) if lit else (255, 255, 255, 70)
    out = (0, 0, 0, 255) if lit else (255, 255, 255, 150)
    d.rectangle([x - 6 * s, y, x + 6 * s, y + 22 * s], fill=col, outline=out, width=2)
    d.ellipse([x - 20 * s, y - 22 * s, x + 20 * s, y + 6 * s], fill=col, outline=out, width=3)


def frame(t):
    tt = min(t, CLIMB)
    n = energy(tt)
    done = t >= CLIMB
    sky = Image.fromarray(SKY.astype(np.uint8))
    img = Image.new('RGB', (W, H), (10, 18, 34))
    img.paste(sky, (0, 598))
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    # the Sun, low in the morning sky, for comparison
    g.ellipse([SUN[0] - 60, SUN[1] - 60, SUN[0] + 60, SUN[1] + 60], fill=(255, 240, 200, 120))
    # meteor position along its path (accelerates into the frame, then stops at the burst)
    u = min(1, tt / CLIMB)
    pu = u ** 0.9
    mx, my = P0[0] + (P1[0] - P0[0]) * pu, P0[1] + (P1[1] - P0[1]) * pu
    br = 0.3 + 0.7 * u ** 1.3
    if not done:
        # smoke trail back to the top right
        for k in range(26):
            f = k / 26
            tx, ty = mx + (P0[0] + 520 - mx) * f, my + (P0[1] - 760 - my) * f
            r = 50 + 80 * f + 6 * math.sin(t * 5 + k)
            g.ellipse([tx - r, ty - r, tx + r, ty + r], fill=(255, 235, 210, int(215 * (1 - f) ** 0.7 * (0.6 + br * 0.4))))
        r = 120 + 110 * br + 10 * math.sin(t * 30)
        g.ellipse([mx - r, my - r, mx + r, my + r], fill=(255, 200, 120, 170))
        r2 = r * 0.5
        g.ellipse([mx - r2, my - r2, mx + r2, my + r2], fill=(255, 255, 235, 255))
    else:
        # burst cloud and expanding blast wave
        a = t - CLIMB
        r = 190 + 60 * min(1, a / 2)
        g.ellipse([P1[0] - r, P1[1] - r * 0.7, P1[0] + r, P1[1] + r * 0.7], fill=(255, 220, 170, 220))
        for k in range(3):
            rw = 80 + 380 * ((a * 0.55 + k * 0.33) % 1.0) * 2.2
            alpha = int(200 * max(0, 1 - rw / 900))
            g.ellipse([P1[0] - rw, P1[1] - rw, P1[0] + rw, P1[1] + rw], outline=(255, 255, 255, alpha), width=10)
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img.convert('RGBA'), glow)
    d = ImageDraw.Draw(img, 'RGBA')
    d.ellipse([SUN[0] - 34, SUN[1] - 34, SUN[0] + 34, SUN[1] + 34], fill=(255, 250, 220, 255))
    d.text((SUN[0] - 40, SUN[1] + 44), 'SUN', font=font(40), fill=WHITE, stroke_width=5, stroke_fill=(0, 0, 0))
    if not done:   # sharp rock in the middle of the glow
        d.ellipse([mx - 16, my - 14, mx + 16, my + 14], fill=(90, 60, 40, 255))

    # city skyline
    hit = done and t - CLIMB > 1.2
    for x, w, h, wins in BUILD:
        d.rectangle([x, GROUND - h, x + w, H], fill=(30, 30, 48, 255))
        for wx, wy in wins:
            on = (255, 255, 255, 255) if hit and int(t * 12 + wx) % 3 == 0 else (255, 220, 140, 230)
            d.rectangle([wx, wy, wx + 9, wy + 12], fill=on)
    d.rectangle([0, GROUND + 60, W, H], fill=(22, 22, 34, 255))
    if hit:
        a = t - CLIMB - 1.2
        for sx, sy, vx, vy, ph in SHARDS:
            px, py = sx + vx * 140 * a, sy + vy * 120 * a + 160 * a * a
            if py > H:
                continue
            s = 7
            d.polygon([(px, py - s), (px + s * math.cos(ph), py + s), (px - s, py + s * math.sin(ph))],
                      fill=(220, 240, 255, 220))
    d.text((24, GROUND + 70), 'CHELYABINSK, RUSSIA', font=font(44), fill=WHITE, stroke_width=5, stroke_fill=(0, 0, 0))

    # flash: brighter than the Sun
    if done and t - CLIMB < 0.5:
        a = 1 - (t - CLIMB) / 0.5
        img = Image.blend(img.convert('RGB'), Image.new('RGB', (W, H), (255, 255, 245)), 0.85 * a).convert('RGBA')
        d = ImageDraw.Draw(img, 'RGBA')

    # bomb icons: one per Hiroshima, lit as the counter passes them
    shown = min(TOP, int(n + 1e-6))
    for k in range(TOP):
        cx, cy = 70 + (k % 6) * 72, 700 + (k // 6) * 78
        lit = k < shown
        pop = max(0, 1 - (tt - t_of_n(k + 1)) / 0.25) if lit and k + 1 >= 2 and not done else 0
        bomb(d, cx, cy, lit, pop)

    # top band
    d.rectangle([0, 0, W, 590], fill=(10, 18, 34, 255))
    d.rectangle([0, 590, W, 598], fill=ORANGE + (255,))

    # gauge on the right: Hiroshima bombs, red 30 line from frame 0
    gx, g0, g1 = 1026, 1720, 700
    d.rounded_rectangle([gx - 34, g1 - 70, gx + 34, g0 + 26], 14, fill=(0, 0, 0, 170))
    d.rectangle([gx - 6, g1, gx + 6, g0], fill=(255, 255, 255, 110))
    gy = g0 - n / TOP * (g0 - g1)
    d.rectangle([gx - 6, gy, gx + 6, g0], fill=ORANGE + (255,))
    for m in (5, 10, 15, 20, 25):
        yy = g0 - m / TOP * (g0 - g1)
        d.line([(gx - 16, yy), (gx + 16, yy)], fill=YELLOW + (255,) if n >= m else (255, 255, 255, 255), width=4)
    d.rectangle([gx - 30, g1 - 5, gx + 30, g1 + 5], fill=RED + (255,))
    d.ellipse([gx - 20, gy - 14, gx + 20, gy + 14], fill=(250, 250, 250, 255), outline=(0, 0, 0, 255), width=3)

    # ---- text
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    tag = 'RUSSIA · 2013'
    ft = font(46)
    d.text((W - 36 - d.textlength(tag, font=ft), 50), tag, font=ft, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    f_t = font(40)
    d.text((gx - 48 - d.textlength('30', font=f_t), g1 - 30), '30', font=f_t, fill=RED if not done else YELLOW,
           stroke_width=5, stroke_fill=(0, 0, 0))

    k_ = int(n + 1e-6)
    s = f'{k_} HIROSHIMA BOMB' + ('S' if k_ != 1 else '')
    text_c(d, 132, s, fit(d, s, 200, 1030), fill=ORANGE, stroke=10)
    s2 = 'OF ENERGY, FROM A ROCK ABOUT 20 M WIDE'
    text_c(d, 392, s2, fit(d, s2, 50, 1010), fill=WHITE, stroke=6)

    y_cap = 478
    if t >= END_Q:
        text_c(d, y_cap, 'WERE YOU RIGHT?', font(80), fill=YELLOW, stroke=8)
    elif t >= AFTER:
        text_c(d, y_cap, CAP_AFTER, fit(d, CAP_AFTER, 72, 1010), fill=WHITE, stroke=8)
    elif done:
        pop = min(1, (t - CLIMB) / 0.12)
        text_c(d, y_cap, CAP_DONE, fit(d, CAP_DONE, int(60 + 20 * pop), 1010), fill=YELLOW, stroke=8)
    elif tt < 2.3:
        s = 'GUESS: HOW MANY BOMBS?'
        text_c(d, y_cap, s, fit(d, s, 76, 1010), stroke=8)
    else:
        m = max([v for v in (5, 10, 15, 20, 25) if n >= v] or [0])
        if m and tt - t_of_n(m) < 1.1:
            pop = min(1, (tt - t_of_n(m)) / 0.12)
            s = f'PAST {m}!'
            text_c(d, y_cap, s, font(int(64 + 20 * pop)), fill=YELLOW, stroke=8)
        else:
            text_c(d, y_cap, 'STILL FALLING' + ('...' if int(tt * 2) % 2 else ''), font(64), stroke=8)
    return img.convert('RGB')


CAP_DONE = os.environ.get('CAP_DONE', 'BRIGHTER THAN THE SUN')
CAP_AFTER = os.environ.get('CAP_AFTER', 'ABOUT 1,500 PEOPLE HURT, MOSTLY BY GLASS')


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
    print('wrote', out, 'milestones', [(m, round(t_of_n(m), 2)) for m in (2, 5, 10, 15, 20, 25, 30)], 'total', TOTAL)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--still':
        for s in map(float, sys.argv[3:]):
            frame(s).save(f'{sys.argv[1]}_{s:05.2f}.png')
    else:
        main()
