#!/usr/bin/env python3
"""Code-rendered Short: the Carrington Event, 1-2 September 1859.

One event, one growing measurement: the southern edge of the northern lights sliding
down a real night map of North America (azimuthal equidistant projection centred on the
North Pole, the Caribbean straight down), with the latitude counter falling from 68 N to
23 N, the latitude of Havana and the Tropic of Cancer. The red tropic line and CUBA are
on screen from frame 0. Cities light up as the aurora passes them; at the end, telegraph
stations spark.

The aurora is drawn as a smooth band along one latitude; the real aurora was patchy and
its edge is reconstructed from scattered reports. Facts and sources: see the publish entry.
Land outline: Natural Earth 1:50m land (public domain), rasterised once into a cache.

Usage: python3 pipeline/anim_carrington.py out.mp4 [audio_dir]
       python3 pipeline/anim_carrington.py prefix --still 0 0.5 1 2
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, 'fonts', 'Anton-Regular.ttf')
LAND_CACHE = os.path.join(ROOT, '.cache', 'land_mask_4096.png')
KM_DEG = 111.19
LON0 = -80.0                     # this longitude points straight down
LAT_A = 68.0                     # aurora edge in frame 0
LAT_B = float(os.environ.get('LAT_B', '23'))   # final edge: Havana 23.1 N, Tropic of Cancer 23.4 N
CLIMB = float(os.environ.get('CLIMB', '10.4'))
TOTAL = float(os.environ.get('TOTAL', '18.6'))
LINE_AT = [float(x) for x in os.environ.get('LINE_AT', '0.1,2.5,10.3,12.9').split(',')]
AFTER = float(os.environ.get('AFTER', str(LINE_AT[-1] - 0.1)))
END_Q = TOTAL - 0.7
CX, CY = 540, 640                # North Pole on screen
PK = (1700 - CY) / ((90 - 23.4) * KM_DEG)     # px per km: tropic sits at y = 1700 below the pole
YELLOW, RED, WHITE, GREEN = (255, 225, 90), (235, 45, 45), (255, 255, 255), (120, 255, 160)
OCEAN, LAND = np.array([16, 34, 70], np.float32), np.array([44, 70, 58], np.float32)
SPACE = (6, 10, 24)

PLACES = [  # name, lat, lon, caption
    ('ANCHORAGE', 61.22, -149.90, 'ALASKA'),
    ('SEATTLE', 47.61, -122.33, 'SEATTLE'),
    ('MONTREAL', 45.50, -73.57, 'MONTREAL'),
    ('DENVER', 39.74, -104.99, 'DENVER'),
    ('NEW YORK', 40.71, -74.01, 'NEW YORK'),
    ('NEW ORLEANS', 29.95, -90.07, 'NEW ORLEANS'),
    ('HAVANA', 23.13, -82.38, 'CUBA'),
]


def lat_at(t):
    u = min(max(t / CLIMB, 0), 1)
    return LAT_A - (LAT_A - LAT_B) * (1 - (1 - u) ** 1.5)


def t_of_lat(la):
    u = 1 - (1 - (LAT_A - la) / (LAT_A - LAT_B)) ** (1 / 1.5)
    return u * CLIMB


def xy(lat, lon):
    r = (90 - lat) * KM_DEG * PK
    az = math.pi - math.radians(lon - LON0)
    return CX + r * math.sin(az), CY - r * math.cos(az)


PL = sorted([(n, la, *xy(la, lo), cap) for n, la, lo, cap in PLACES], key=lambda p: -p[1])


def font(size):
    return ImageFont.truetype(FONT, size)


MASKF = (np.array(Image.open(LAND_CACHE)) > 127).astype(np.float32)
MH, MW = MASKF.shape
YY, XX = np.mgrid[598:H, 0:W].astype(np.float32)
DX, DY = XX - CX, YY - CY
RHO = np.hypot(DX, DY)                       # px from the pole
AZ = np.arctan2(DX, -DY)
LATG = 90 - RHO / PK / KM_DEG
LONG = LON0 + 180 - np.degrees(AZ)
fx = ((LONG + 180) % 360) / 360 * MW - 0.5
fy = np.clip((90 - LATG) / 180 * MH - 0.5, 0, MH - 1.001)
x0, y0 = np.floor(fx).astype(np.int32), np.floor(fy).astype(np.int32)
ax, ay = fx - x0, fy - y0
x0m, x1m = x0 % MW, (x0 + 1) % MW
V = (MASKF[y0, x0m] * (1 - ax) + MASKF[y0, x1m] * ax) * (1 - ay) + \
    (MASKF[y0 + 1, x0m] * (1 - ax) + MASKF[y0 + 1, x1m] * ax) * ay
LANDV = np.clip((V - 0.35) / 0.3, 0, 1)[..., None]
BASE = OCEAN * (1 - LANDV) + LAND * LANDV
# faint graticule every 10 degrees of latitude
GRID = (np.abs(((LATG + 5) % 10) - 5) < 0.12)[..., None] * 18


def map_layer(t, edge):
    """Night map with the aurora band: green at its southern edge, red above it."""
    ring = (90 - edge) * KM_DEG * PK
    d = RHO - ring                               # >0 south of the edge
    curt = 0.55 + 0.45 * np.sin(AZ * 46 + t * 2.6) * np.sin(AZ * 17 - t * 1.7)
    green = np.exp(-(d / 34) ** 2) * (d < 0) + np.exp(-(d / 12) ** 2) * (d >= 0)
    green = green * (0.6 + 0.4 * curt)
    red = np.exp(-((d + 150) / 110) ** 2) * (0.5 + 0.5 * curt)
    veil = np.clip(-d / 600, 0, 1) * 0.35       # sky glow poleward of the edge
    img = BASE + GRID
    img = img + green[..., None] * np.array([90, 255, 150], np.float32) * 1.15
    img = img + red[..., None] * np.array([230, 50, 110], np.float32) * 0.75
    img = img + veil[..., None] * np.array([40, 120, 80], np.float32)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def text_c(d, y, s, f, fill=WHITE, stroke=7, cx=W / 2):
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def fit(d, s, size, maxw):
    f = font(size)
    while d.textlength(s, font=f) > maxw and size > 30:
        size -= 4
        f = font(size)
    return f


def spark(d, x, y, t, k):
    ph = (t * 3.1 + k * 0.37) % 1.0
    if ph > 0.55:
        return
    s = 1 - ph / 0.55
    for j in range(8):
        a = j * math.pi / 4 + k
        r1, r2 = 10, 10 + 36 * s
        d.line([(x + r1 * math.cos(a), y + r1 * math.sin(a)), (x + r2 * math.cos(a), y + r2 * math.sin(a))],
               fill=(255, 240, 140, int(255 * s)), width=5)


def frame(t):
    tt = min(t, CLIMB)
    edge = lat_at(tt)
    done = t >= CLIMB
    full = Image.new('RGB', (W, H), SPACE)
    full.paste(map_layer(t, edge), (0, 598))
    img = full
    d = ImageDraw.Draw(img, 'RGBA')

    # target: the Tropic of Cancer, dashed red, from frame 0
    rt = (90 - 23.4) * KM_DEG * PK
    n = 90
    for k in range(n):
        a0 = 360 * k / n
        d.arc([CX - rt, CY - rt, CX + rt, CY + rt], a0, a0 + 2.0, fill=RED + (255,) if not done else YELLOW + (255,), width=7)
    lab = 'TROPIC OF CANCER'
    f_s = font(38)
    d.text((660, 1625), lab, font=f_s, fill=RED if not done else YELLOW, stroke_width=5, stroke_fill=(0, 0, 0))
    if done:   # pulse on the reached line
        u = ((t - CLIMB) / 1.0) % 1.0
        pr = rt + 8 + 70 * u
        d.arc([CX - pr, CY - pr, CX + pr, CY + pr], 50, 130, fill=(150, 255, 180, int(220 * (1 - u))), width=8)

    # cities
    f_m = font(40)
    for k, (name, la, x, y, cap) in enumerate(PL):
        if not (-20 < x < W + 20 and 600 < y < H + 20):
            continue
        lit = edge <= la
        hit = lit and tt - t_of_lat(la) < 1.1
        rr = 14 if hit else 9
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(GREEN if lit else WHITE) + (255,), outline=(0, 0, 0, 255), width=3)
        if hit or name == 'HAVANA' or (done and t < AFTER):
            s = 'CUBA' if name == 'HAVANA' else name
            w = d.textlength(s, font=f_m)
            lx = min(max(x - w / 2, 14), W - 110 - w)
            ly = y + 18
            d.text((lx, ly), s, font=f_m, fill=(GREEN if lit else (RED if name == 'HAVANA' else WHITE)),
                   stroke_width=5, stroke_fill=(0, 0, 0))
        if t >= AFTER and name != 'HAVANA':
            spark(d, x, y, t, k)

    # top band
    d.rectangle([0, 0, W, 590], fill=(10, 18, 34, 255))
    d.rectangle([0, 590, W, 598], fill=(120, 255, 160, 255))

    # gauge on the right: latitude, red 23 N line from frame 0
    gx, g0, g1 = 1026, 760, 1820          # top = 70 N, bottom = 20 N
    def gy_of(la):
        return g0 + (70 - la) / 50 * (g1 - g0)
    d.rounded_rectangle([gx - 34, g0 - 26, gx + 34, g1 + 26], 14, fill=(0, 0, 0, 170))
    d.rectangle([gx - 6, g0, gx + 6, g1], fill=(255, 255, 255, 110))
    gy = gy_of(edge)
    d.rectangle([gx - 6, g0, gx + 6, gy], fill=(120, 255, 160, 255))
    for _, la, *_ in PL:
        yy = gy_of(la)
        d.line([(gx - 16, yy), (gx + 16, yy)], fill=GREEN + (255,) if edge <= la else (255, 255, 255, 255), width=4)
    ty = gy_of(23.4)
    d.rectangle([gx - 30, ty - 5, gx + 30, ty + 5], fill=RED + (255,))
    d.ellipse([gx - 20, gy - 14, gx + 20, gy + 14], fill=(250, 250, 250, 255), outline=(0, 0, 0, 255), width=3)

    # ---- text
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    tag = 'SEPTEMBER 1859'
    ft = font(46)
    d.text((W - 36 - d.textlength(tag, font=ft), 50), tag, font=ft, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))

    s = f'{edge:.0f}°N'
    text_c(d, 120, s, fit(d, s, 230, 1030), fill=GREEN, stroke=10)
    s2 = 'HOW FAR SOUTH THE NORTHERN LIGHTS WENT'
    text_c(d, 392, s2, fit(d, s2, 50, 1010), fill=WHITE, stroke=6)

    y_cap = 478
    passed = [(t_of_lat(la), cap) for _, la, _, _, cap in PL if edge <= la]
    if t >= END_Q:
        text_c(d, y_cap, 'WERE YOU RIGHT?', font(80), fill=YELLOW, stroke=8)
    elif t >= AFTER:
        text_c(d, y_cap, CAP_AFTER, fit(d, CAP_AFTER, 72, 1010), fill=YELLOW, stroke=8)
    elif done:
        pop = min(1, (t - CLIMB) / 0.12)
        text_c(d, y_cap, CAP_DONE, fit(d, CAP_DONE, int(60 + 20 * pop), 1010), fill=GREEN, stroke=8)
    elif tt < 2.3:
        s = 'GUESS: HOW FAR SOUTH?'
        text_c(d, y_cap, s, fit(d, s, 76, 1010), stroke=8)
    elif passed and tt - passed[-1][0] < 1.2:
        tp, cap = passed[-1]
        pop = min(1, (tt - tp) / 0.12)
        s = 'NOW OVER ' + cap
        text_c(d, y_cap, s, fit(d, s, int(58 + 20 * pop), 1010), fill=GREEN, stroke=8)
    else:
        text_c(d, y_cap, 'STILL SLIDING SOUTH' + ('...' if int(tt * 2) % 2 else ''), font(64), stroke=8)
    return img


CAP_DONE = os.environ.get('CAP_DONE', 'SEEN AS FAR SOUTH AS CUBA')
CAP_AFTER = os.environ.get('CAP_AFTER', 'TELEGRAPH WIRES THREW SPARKS')


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
    print('wrote', out, 'beats', [(p[0], p[1], round(t_of_lat(p[1]), 2)) for p in PL], 'total', TOTAL)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--still':
        for s in map(float, sys.argv[3:]):
            frame(s).save(f'{sys.argv[1]}_{s:05.2f}.png')
    else:
        main()
