#!/usr/bin/env python3
"""Code-rendered Short: Tsar Bomba, 30 October 1961. Mushroom cloud about 64 km high.

One event, one growing measurement: the cloud top climbing, with the camera pulling back
so the cloud always fills the frame while Everest, jets and the highest skydive shrink
below it. A gauge on the right shows the whole climb and the red "IT STOPS HERE" line
from frame 0. Follows pipeline/FORMAT.md (18-22 s, 3-4 voice lines).

Facts (see the publish entry for sources):
  50 megatons; cloud about 64 km (40 miles) high (sources give 60+ to 67 km);
  the blast wave circled the Earth three times; burst about 4 km above the ground.
Scale marks: Everest 8.85 km, passenger jets about 11 km, Concorde 18 km, SR-71 about
26 km, weather balloons about 35 km, highest skydive 41.4 km (Alan Eustace, 2014),
top of the stratosphere about 50 km.

Usage: python3 pipeline/anim_tsar_bomba.py out.mp4 [audio_dir]
       python3 pipeline/anim_tsar_bomba.py prefix --still 0 0.5 1 2
Audio starts can be set with LINE_AT="0.1,2.4,11.6,16.4".
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, 'fonts', 'Anton-Regular.ttf')
TOP_KM = 64.0
EVEREST = 8.85
CLIMB = float(os.environ.get('CLIMB', '12.0'))
TOTAL = float(os.environ.get('TOTAL', '20.0'))
H0 = 6.5               # cloud top in frame 0 (already rising)
GY = 1770              # screen y of the ground
VIEW_TOP_Y = 610       # screen y of the top of the scene
ZOOM = 1.45            # the view always shows 1.45x the cloud height
CX = 500               # cloud centre x
YELLOW, RED, WHITE, GREEN = (255, 225, 90), (230, 40, 40), (255, 255, 255), (130, 240, 150)
MARKS = [  # km, short label, caption, side (-1 left, 1 right), icon
    (EVEREST, 'EVEREST', 'MOUNT EVEREST', -1, 'peak'),
    (11.0, 'PASSENGER JETS', 'EVERY PASSENGER JET', 1, 'jet'),
    (18.0, 'CONCORDE', 'CONCORDE', -1, 'jet'),
    (26.0, 'SR-71 SPY PLANE', 'THE SR-71 SPY PLANE', 1, 'jet'),
    (35.0, 'WEATHER BALLOONS', 'WEATHER BALLOONS', -1, 'balloon'),
    (41.4, 'HIGHEST SKYDIVE', 'THE HIGHEST SKYDIVE EVER', 1, 'diver'),
    (50.0, 'STRATOSPHERE ENDS', 'THE WHOLE STRATOSPHERE', -1, 'line'),
]
rng = np.random.default_rng(1961)


def font(size):
    return ImageFont.truetype(FONT, size)


def height(t):
    u = min(max(t / CLIMB, 0), 1)
    return H0 + (TOP_KM - H0) * (1 - (1 - u) ** 1.5)


def t_of(km):
    u = 1 - (1 - (km - H0) / (TOP_KM - H0)) ** (1 / 1.5)
    return u * CLIMB


PUFFS = []
for _ in range(120):
    a = rng.uniform(0, 2 * math.pi)
    r = rng.uniform(0.25, 1.0) ** 0.6
    PUFFS.append((r * math.cos(a), r * math.sin(a) * 0.9, rng.uniform(0.2, 0.42), rng.uniform(0, 6.28),
                  rng.uniform(0.8, 1.0)))
PUFFS.sort(key=lambda p: -p[1])       # top ones first, lower ones overlap them
STARS = [(rng.uniform(0, W), rng.uniform(0, 1), rng.uniform(1, 2.6)) for _ in range(110)]
SKY_KM = [0, 12, 30, 55, 100]
SKY_COL = np.array([[176, 208, 236], [86, 140, 214], [30, 60, 140], [10, 18, 58], [3, 4, 16]], float)


def sky(vtop):
    km = np.interp(np.arange(H), [VIEW_TOP_Y - 610 * 1.0, GY], [vtop * (1 + 610 / (GY - VIEW_TOP_Y)), 0])
    col = np.stack([np.interp(km, SKY_KM, SKY_COL[:, c]) for c in range(3)], 1)
    return Image.fromarray(np.repeat(col[:, None, :], W, 1).astype(np.uint8), 'RGB')


def text_c(d, y, s, f, fill=WHITE, stroke=7, cx=W / 2):
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def fit(d, s, size, maxw):
    f = font(size)
    while d.textlength(s, font=f) > maxw and size > 30:
        size -= 4
        f = font(size)
    return f


def mix(a, b, k):
    return tuple(int(a[i] * (1 - k) + b[i] * k) for i in range(3))


def icon(d, kind, x, y, col):
    o = (0, 0, 0)
    if kind == 'jet':
        d.polygon([(x - 44, y), (x + 30, y - 7), (x + 46, y), (x + 30, y + 7)], fill=col, outline=o)
        d.polygon([(x - 6, y), (x - 26, y - 26), (x - 12, y - 26), (x + 14, y)], fill=col, outline=o)
        d.polygon([(x - 40, y), (x - 50, y - 16), (x - 42, y - 16), (x - 30, y)], fill=col, outline=o)
    elif kind == 'balloon':
        d.ellipse([x - 22, y - 52, x + 22, y - 4], fill=col, outline=o, width=2)
        d.line([(x, y - 4), (x, y + 16)], fill=col, width=3)
        d.rectangle([x - 6, y + 14, x + 6, y + 24], fill=col, outline=o)
    elif kind == 'diver':
        d.ellipse([x - 9, y - 30, x + 9, y - 12], fill=col, outline=o)
        d.line([(x, y - 12), (x, y + 10)], fill=col, width=8)
        d.line([(x - 22, y - 14), (x + 22, y - 14)], fill=col, width=6)
        d.line([(x, y + 10), (x - 14, y + 28)], fill=col, width=6)
        d.line([(x, y + 10), (x + 14, y + 28)], fill=col, width=6)


def cloud(img, t, hm, pk):
    """The fireball and mushroom cloud. pk = pixels per km."""
    d = ImageDraw.Draw(img, 'RGBA')
    S = hm * pk                                   # cloud height in pixels
    grow = min(1, t / CLIMB)
    hot = max(0.0, 1 - t / 4.5)                   # fireball glow fading into cloud
    capw = S * (0.84 + 0.46 * grow)               # cap spreads as it rises
    rx, ry = capw / 2, S * (0.21 + 0.03 * grow)
    cy = GY - S + ry
    # glow
    if hot > 0:
        for k in range(6):
            r = S * (0.75 - k * 0.09)
            d.ellipse([CX - r, cy - r * 0.8, CX + r, cy + r * 0.8], fill=(255, 150 + k * 16, 40, int(34 * hot)))
    # dust skirt on the ground
    gw = S * (0.5 + 0.35 * grow)
    for k in range(9):
        ox = (k - 4) / 4 * gw
        r = S * 0.07 * (1 + 0.25 * math.sin(t * 3 + k))
        d.ellipse([CX + ox - r * 1.6, GY - r, CX + ox + r * 1.6, GY + r * 0.6], fill=mix((196, 186, 176), (255, 190, 110), hot) + (255,))
    # stem
    sw = S * 0.085
    pts_l, pts_r = [], []
    for k in range(0, 21):
        f = k / 20
        y = GY - f * (S - ry * 1.1)
        wv = sw * (1 + 1.4 * (1 - f) ** 3 + 0.5 * f ** 4) + S * 0.012 * math.sin(f * 16 - t * 5)
        pts_l.append((CX - wv, y))
        pts_r.append((CX + wv, y))
    d.polygon(pts_l + pts_r[::-1], fill=mix((150, 142, 140), (255, 140, 50), hot) + (255,))
    d.polygon([(CX - sw * 0.35, GY)] + [(CX - w_ * 0.0 - (CX - x) * 0.35, y) for (x, y), w_ in zip(pts_l, range(21))][1:] +
              [(CX + (x - CX) * 0.1, y) for x, y in pts_r[::-1]], fill=mix((186, 178, 174), (255, 200, 90), hot) + (255,))
    # collar ring under the cap
    r = S * 0.2
    d.ellipse([CX - r, cy + ry * 0.75, CX + r, cy + ry * 1.25], fill=mix((170, 162, 160), (255, 170, 70), hot) + (255,))
    # cap: base shape then boiling puffs
    d.ellipse([CX - rx, cy - ry, CX + rx, cy + ry], fill=mix((150, 144, 146), (240, 110, 40), hot) + (255,))
    for px, py, pr, ph, br in PUFFS:
        wob = 1 + 0.1 * math.sin(t * 2.6 + ph)
        x = CX + px * rx * 0.92
        y = cy + py * ry * 0.95
        r = pr * ry * wob
        shade = 0.5 - 0.5 * py                    # 1 at the top, 0 underneath
        base = mix((118, 112, 118), (246, 244, 240), shade * br)
        fire = mix((230, 70, 20), (255, 236, 150), shade * br)
        c = mix(base, fire, hot)
        d.ellipse([x - r, y - r + r * 0.18, x + r, y + r + r * 0.18], fill=mix(c, (60, 50, 60), 0.35) + (255,))
        d.ellipse([x - r, y - r, x + r, y + r], fill=c + (255,))
    # hot core seen through the cap early on
    if hot > 0.05:
        r = ry * 0.55 * hot
        d.ellipse([CX - r * 1.5, cy - r, CX + r * 1.5, cy + r], fill=(255, 250, 200, int(120 * hot)))


def frame(t):
    tt = min(t, CLIMB)
    hm = height(tt)
    vtop = hm * ZOOM
    pk = (GY - VIEW_TOP_Y) / vtop                 # pixels per km in the main view
    y_of = lambda km: GY - km * pk
    reached = t >= CLIMB
    img = sky(vtop)
    d = ImageDraw.Draw(img, 'RGBA')

    # stars fade in as the view reaches the dark sky
    sa = min(1, max(0, (vtop - 45) / 40))
    if sa > 0:
        for x, fy, r in STARS:
            y = fy * 1100
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(200 * sa)))

    # ground: Arctic ice and sea
    d.rectangle([0, GY, W, H], fill=(226, 236, 244, 255))
    for k in range(6):
        yy = GY + 30 + k * 24
        d.line([(0, yy), (W, yy)], fill=(150, 180, 205, 120), width=3)
    d.rectangle([0, GY - 3, W, GY + 5], fill=(120, 150, 180, 255))

    # Everest, drawn to scale at the left
    ex, eh = 170, EVEREST * pk
    d.polygon([(ex - eh * 1.25, GY), (ex - eh * 0.35, GY - eh * 0.62), (ex, GY - eh), (ex + eh * 0.5, GY - eh * 0.5),
               (ex + eh * 1.3, GY)], fill=(84, 94, 116, 255), outline=(20, 26, 40, 255))
    d.polygon([(ex - eh * 0.2, GY - eh * 0.78), (ex, GY - eh), (ex + eh * 0.2, GY - eh * 0.8), (ex, GY - eh * 0.7)],
              fill=(245, 248, 252, 255))

    # target line in the main view once the camera has pulled back far enough
    ty = y_of(TOP_KM)
    if ty > VIEW_TOP_Y - 30:
        for x in range(20, 960, 44):
            d.line([(x, ty), (x + 24, ty)], fill=RED + (255,), width=7)

    cloud(img, t, hm, pk)
    d = ImageDraw.Draw(img, 'RGBA')

    # the cloud-top level line
    cy_top = y_of(hm)
    d.line([(20, cy_top), (960, cy_top)], fill=(255, 255, 255, 235), width=5)
    d.polygon([(30, cy_top - 16), (30, cy_top + 16), (64, cy_top)], fill=(255, 255, 255, 255))

    # scale marks: icons and labels at their real heights
    f_m = font(34)
    for km, lab, _, side, kind in MARKS:
        y = y_of(km)
        if y < VIEW_TOP_Y + 20:
            continue
        passed = hm >= km
        hit = passed and tt - t_of(km) < 1.1
        col = YELLOW if hit else ((200, 208, 220) if passed else WHITE)
        w = d.textlength(lab, font=f_m)
        if kind == 'peak':
            x0 = 30
            yl = y - 50
        else:
            x0 = 30 if side < 0 else 960 - w
            yl = y - 22
            d.line([(20, y + 24), (960, y + 24)], fill=col + (120,), width=3)
            if kind != 'line' and y < GY - 70:
                icon(d, kind, x0 + (w + 60 if side < 0 else -60), y - 4, col)
        d.text((x0, yl), lab, font=f_m, fill=col, stroke_width=4, stroke_fill=(0, 0, 0))

    # gauge on the right: the whole climb, with the stop line, from frame 0
    gx, g0, g1 = 1022, 1730, 660
    d.rounded_rectangle([gx - 34, g1 - 70, gx + 34, g0 + 26], 14, fill=(0, 0, 0, 150))
    d.rectangle([gx - 6, g1, gx + 6, g0], fill=(255, 255, 255, 110))
    gy = g0 - (hm / TOP_KM) * (g0 - g1)
    d.rectangle([gx - 6, gy, gx + 6, g0], fill=(255, 170, 60, 255))
    for km, *_ in MARKS:
        yy = g0 - km / TOP_KM * (g0 - g1)
        d.line([(gx - 16, yy), (gx + 16, yy)], fill=(255, 255, 255, 255) if hm < km else (255, 225, 90, 255), width=4)
    d.rectangle([gx - 30, g1 - 5, gx + 30, g1 + 5], fill=RED + (255,))
    d.ellipse([gx - 20, gy - 16, gx + 20, gy + 12], fill=(250, 250, 250, 255), outline=(0, 0, 0, 255), width=3)

    # blast wave circling the Earth (payoff)
    lap_t = t - LAPS_AT
    if lap_t > 0:
        ox, oy, r = 270, 1430, 150
        d.rounded_rectangle([ox - 210, oy - 205, ox + 210, oy + 235], 26, fill=(0, 0, 0, 185))
        d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=(40, 110, 200, 255), outline=(255, 255, 255, 255), width=4)
        for bx, by, bw, bh in [(-70, -60, 90, 70), (10, -20, 80, 100), (-40, 40, 60, 50), (50, -90, 40, 30)]:
            d.ellipse([ox + bx, oy + by, ox + bx + bw, oy + by + bh], fill=(70, 160, 100, 255))
        laps = min(3.0, lap_t / LAP_LEN)
        a = laps * 2 * math.pi - math.pi / 2
        for k in range(26):
            aa = a - k * 0.09
            if aa < -math.pi / 2:
                break
            x, y = ox + (r + 22) * math.cos(aa), oy + (r + 22) * math.sin(aa)
            rr = 13 - k * 0.4
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 225, 90, max(0, 255 - k * 10)))
        n = min(3, int(laps) + (0 if laps >= 3 else 1))
        f = font(54)
        s = f'LAP {n} OF 3' if laps < 3 else '3 TIMES AROUND'
        d.text((ox - d.textlength(s, font=f) / 2, oy + r + 12), s, font=f, fill=YELLOW, stroke_width=4, stroke_fill=(0, 0, 0))

    # white flash in the first moments
    if t < 0.45:
        fl = Image.new('RGB', (W, H), (255, 250, 230))
        img = Image.blend(img, fl, 0.32 * (1 - t / 0.45))

    # ---- text
    d = ImageDraw.Draw(img)
    text_c(d, 138, f'{hm:,.0f} KM', font(230), fill=YELLOW, stroke=10)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    tag = 'TSAR BOMBA · 1961'
    d.text((W - 36 - d.textlength(tag, font=font(46)), 48), tag, font=font(46), fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    f_t = font(40)
    s = 'IT STOPS HERE' if not reached else 'ABOUT 64 KM'
    d.text((gx - 48 - d.textlength(s, font=f_t), g1 - 30), s, font=f_t, fill=RED if not reached else YELLOW,
           stroke_width=5, stroke_fill=(0, 0, 0))
    # live multiple of Everest
    text_c(d, 404, f'{hm / EVEREST:.1f} × EVEREST', font(60), fill=WHITE, stroke=7)

    passed = [(t_of(km), cap) for km, _, cap, _, _ in MARKS if hm >= km]
    y_cap = 492
    if t >= END_Q:
        text_c(d, y_cap, 'WERE YOU RIGHT?', font(80), fill=YELLOW, stroke=8)
    elif lap_t > 0:
        s = 'ITS BLAST WAVE CIRCLED THE EARTH 3 TIMES'
        text_c(d, y_cap, s, fit(d, s, 76, 1010), fill=WHITE, stroke=8)
    elif reached:
        s = '7 TIMES HIGHER THAN EVEREST'
        pop = min(1, (t - CLIMB) / 0.12)
        text_c(d, y_cap, s, fit(d, s, int(60 + 20 * pop), 1010), fill=GREEN, stroke=8)
    elif tt < 2.3:
        s = 'GUESS: HOW HIGH DID THIS CLOUD GO?'
        text_c(d, y_cap, s, fit(d, s, 72, 1010), stroke=8)
    elif passed and tt - passed[-1][0] < 1.6:
        tp, cap = passed[-1]
        pop = min(1, (tt - tp) / 0.12)
        s = 'PAST ' + cap
        text_c(d, y_cap, s, fit(d, s, int(58 + 20 * pop), 1010), fill=GREEN, stroke=8)
    else:
        s = 'STILL CLIMBING' if int(tt * 2) % 2 == 0 else 'STILL CLIMBING...'
        text_c(d, y_cap, 'THE BIGGEST BOMB EVER SET OFF' if tt < 4.5 else s, font(64), stroke=8)
    return img


LINE_AT = [float(x) for x in os.environ.get('LINE_AT', '0.1,2.4,11.6,16.2').split(',')]
LAPS_AT = float(os.environ.get('LAPS_AT', str(LINE_AT[-1] - 0.2)))
LAP_LEN = 0.9
END_Q = TOTAL - 0.7


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
