#!/usr/bin/env python3
"""Code-rendered Short: the 1960 Valdivia earthquake tsunami crossing the Pacific to Japan.

One event, one growing measurement: the tsunami front spreading across a real map
(azimuthal equidistant projection centred on the epicentre, turned so Japan is straight
up), with a clock counting the hours since the quake and the camera pulling back so the
front always fills the frame. Places light up as the front reaches them. A gauge on the
right shows the whole crossing to Japan, with the red JAPAN line, from frame 0.

The front is drawn as a circle of equal distance from the epicentre, timed so it reaches
Hilo and Japan at the reported arrival times. The real wave was bent by sea depth and
coastlines; places behind land were not reached the way the circle suggests.
Facts and sources: see the publish entry (publish/queue/2026-11-23-valdivia-tsunami.json).
Land outline: Natural Earth 1:50m land (public domain), rasterised once into a cache.

Usage: python3 pipeline/anim_valdivia.py out.mp4 [audio_dir]
       python3 pipeline/anim_valdivia.py prefix --still 0 0.5 1 2
"""
import json, math, os, subprocess, sys, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, 'fonts', 'Anton-Regular.ttf')
LAND_URL = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson'
LAND_CACHE = os.path.join(ROOT, '.cache', 'land_mask_4096.png')
RE = 6371.0
LAT0, LON0 = math.radians(-38.24), math.radians(-73.05)   # epicentre (USGS)
ROT = math.radians(80)  # turn the map so Japan (azimuth about -80 degrees) is straight up
HILO_H = float(os.environ.get('HILO_H', '15'))     # hours to Hilo (sources)
JAPAN_H = float(os.environ.get('JAPAN_H', '22'))   # hours to Japan (sources)
H0 = 0.45              # hours already gone in frame 0
CLIMB = float(os.environ.get('CLIMB', '12.5'))     # seconds for the front to reach Japan
TOTAL = float(os.environ.get('TOTAL', '20.0'))
LINE_AT = [float(x) for x in os.environ.get('LINE_AT', '0.1,3.6,9.0,13.6').split(',')]
END_Q = TOTAL - 0.7
CX, CY = 540, 1640
RING_PX = 760
HALF = math.pi * RE
YELLOW, RED, WHITE, GREEN = (255, 225, 90), (235, 45, 45), (255, 255, 255), (130, 240, 150)
OCEAN, LAND = np.array([28, 96, 168]), np.array([96, 164, 92])
OCEAN_IN, LAND_IN = np.array([58, 140, 206]), np.array([140, 186, 104])   # inside the front
SPACE = (8, 14, 28)

PLACES = [  # name on map, lat, lon, caption
    ('PERU', -12.05, -77.04, 'PERU'),
    ('EASTER ISLAND', -27.11, -109.35, 'EASTER ISLAND'),
    ('TAHITI', -17.53, -149.57, 'TAHITI'),
    ('NEW ZEALAND', -36.85, 174.76, 'NEW ZEALAND'),
    ('CALIFORNIA', 34.05, -118.24, 'CALIFORNIA'),
    ('HAWAII', 19.72, -155.08, 'HAWAII'),
    ('JAPAN', 38.44, 141.44, 'JAPAN'),
]


def gc(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    c = math.acos(math.sin(LAT0) * math.sin(la) + math.cos(LAT0) * math.cos(la) * math.cos(lo - LON0))
    az = math.atan2(math.sin(lo - LON0) * math.cos(la),
                    math.cos(LAT0) * math.sin(la) - math.sin(LAT0) * math.cos(la) * math.cos(lo - LON0))
    return RE * c, az + ROT


PL = [(n, *gc(la, lo), cap) for n, la, lo, cap in PLACES]
PL.sort(key=lambda p: p[1])
HILO_KM = [p[1] for p in PL if p[0] == 'HAWAII'][0]
TOP = [p[1] for p in PL if p[0] == 'JAPAN'][0]   # km to Japan (Onagawa)


def hours(t):
    """Clock: hours since the quake. Even speed on screen."""
    return H0 + (JAPAN_H - H0) * min(max(t / CLIMB, 0), 1)


def km_at(h):
    """Front distance for a clock time, through the reported Hilo and Japan arrivals."""
    if h <= HILO_H:
        return HILO_KM * h / HILO_H
    return HILO_KM + (TOP - HILO_KM) * (h - HILO_H) / (JAPAN_H - HILO_H)


def t_of_km(km):
    h = km / HILO_KM * HILO_H if km <= HILO_KM else HILO_H + (km - HILO_KM) / (TOP - HILO_KM) * (JAPAN_H - HILO_H)
    return (h - H0) / (JAPAN_H - H0) * CLIMB


def font(size):
    return ImageFont.truetype(FONT, size)


def land_mask():
    if os.path.exists(LAND_CACHE):
        return np.array(Image.open(LAND_CACHE)) > 127
    os.makedirs(os.path.dirname(LAND_CACHE), exist_ok=True)
    src = os.environ.get('LAND_GEOJSON')
    data = json.load(open(src)) if src else json.load(urllib.request.urlopen(LAND_URL))
    mw, mh = 4096, 2048
    im = Image.new('L', (mw, mh), 0)
    d = ImageDraw.Draw(im)
    for f in data['features']:
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys:
            for k, ring in enumerate(poly):
                pts = [((lo + 180) / 360 * mw, (90 - la) / 180 * mh) for lo, la in ring]
                d.polygon(pts, fill=0 if k else 255)
    im.save(LAND_CACHE)
    return np.array(im) > 127


MASK = land_mask()
MASKF = MASK.astype(np.float32)
MH, MW = MASK.shape
YY, XX = np.mgrid[598:H, 0:W].astype(np.float32)
DX, DY = XX - CX, YY - CY
RHO_PX = np.hypot(DX, DY)
AZ = np.arctan2(DX, -DY) - ROT


def map_layer(pk, ring_km):
    """Map below the top band. pk = pixels per km. Water/land inside the wave is lighter."""
    rho = RHO_PX / pk
    c = rho / RE
    sl, cl = math.sin(LAT0), math.cos(LAT0)
    sc, cc = np.sin(c), np.cos(c)
    lat = np.arcsin(np.clip(sl * cc + cl * sc * np.cos(AZ), -1, 1))
    lon = LON0 + np.arctan2(sc * np.sin(AZ), cl * cc - sl * sc * np.cos(AZ))
    # bilinear sample of the land mask, so coastlines stay smooth when zoomed in
    fx = ((np.degrees(lon) + 180) % 360) / 360 * MW - 0.5
    fy = np.clip((90 - np.degrees(lat)) / 180 * MH - 0.5, 0, MH - 1.001)
    x0, y0 = np.floor(fx).astype(np.int32), np.floor(fy).astype(np.int32)
    ax, ay = fx - x0, fy - y0
    x0m, x1m = x0 % MW, (x0 + 1) % MW
    y1 = y0 + 1
    v = (MASKF[y0, x0m] * (1 - ax) + MASKF[y0, x1m] * ax) * (1 - ay) + \
        (MASKF[y1, x0m] * (1 - ax) + MASKF[y1, x1m] * ax) * ay
    land = v > 0.5
    inside = rho <= ring_km
    out = np.empty(rho.shape + (3,), np.uint8)
    out[:] = OCEAN
    out[land] = LAND
    out[inside & ~land] = OCEAN_IN
    out[inside & land] = LAND_IN
    out[rho > HALF] = SPACE
    return Image.fromarray(out)


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
    h = hours(tt)
    ring = km_at(h)
    pk = RING_PX / max(ring, 1)
    reached_all = t >= CLIMB
    img = map_layer(pk, ring)
    full = Image.new('RGB', (W, H), SPACE)
    full.paste(img, (0, 598))
    img = full
    d = ImageDraw.Draw(img, 'RGBA')

    # Japan target arc (dashed red) once it is near the screen
    rt = TOP * pk
    if rt < 1800 and not reached_all:
        n = 70
        for k in range(n):
            a0 = 360 * k / n
            d.arc([CX - rt, CY - rt, CX + rt, CY + rt], a0, a0 + 2.6, fill=RED + (255,), width=7)

    # the tsunami front
    rp = ring * pk
    wob = 5 * math.sin(t * 22)
    for k, (wd, al) in enumerate([(50, 55), (28, 115), (12, 255)]):
        rr = rp + wob * (k == 2)
        d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline=(235, 250, 255, al), width=wd)
    # wave crests behind the front
    for k in range(1, 4):
        rr = rp * (1 - 0.09 * k) + 6 * math.sin(t * 6 + k)
        d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline=(220, 240, 255, 70 - 15 * k), width=6)

    # places
    f_m = font(40)
    for name, km, az, cap in PL:
        x, y = CX + km * pk * math.sin(az), CY - km * pk * math.cos(az)
        if not (-20 < x < W + 20 and 600 < y < H + 20):
            continue
        reached = ring >= km
        hit = reached and tt - t_of_km(km) < 1.2
        rr = 15 if hit or (name == 'JAPAN' and reached_all) else 10
        if name == 'JAPAN' and reached_all:
            pr = 15 + 40 * ((t - CLIMB) * 1.4 % 1)
            d.ellipse([x - pr, y - pr, x + pr, y + pr], outline=RED + (int(255 * (1 - (pr - 15) / 40)),), width=6)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(YELLOW if reached else WHITE) + (255,),
                  outline=(0, 0, 0, 255), width=3)
        if hit or name in ('JAPAN', 'HAWAII'):
            w = d.textlength(name, font=f_m)
            lx = min(max(x - w / 2, 14), W - 96 - w)
            ly = y - 64 if y > 700 else y + 20
            col = YELLOW if reached else (RED if name == 'JAPAN' else WHITE)
            d.text((lx, ly), name, font=f_m, fill=col, stroke_width=5, stroke_fill=(0, 0, 0))
    # epicentre
    er = 14 + 5 * math.sin(t * 9)
    ex, ey = CX, CY
    if 600 < ey < H:
        d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=(255, 90, 40, 255), outline=(0, 0, 0, 255), width=3)
        if t < 3:
            f_v = font(36)
            d.text((ex - d.textlength('CHILE', font=f_v) / 2, ey + 22), 'CHILE', font=f_v, fill=WHITE,
                   stroke_width=4, stroke_fill=(0, 0, 0))

    # shake in the first frames
    if t < 0.5:
        img = Image.blend(img, Image.new('RGB', (W, H), (255, 245, 220)), 0.3 * (1 - t / 0.5))
        d = ImageDraw.Draw(img, 'RGBA')

    # top band
    d.rectangle([0, 0, W, 590], fill=(10, 18, 34, 255))
    d.rectangle([0, 590, W, 598], fill=(255, 225, 90, 255))

    # gauge on the right: hours from Chile to Japan, red JAPAN line from frame 0
    gx, g0, g1 = 1026, 1820, 760
    d.rounded_rectangle([gx - 34, g1 - 70, gx + 34, g0 + 26], 14, fill=(0, 0, 0, 170))
    d.rectangle([gx - 6, g1, gx + 6, g0], fill=(255, 255, 255, 110))
    gy = g0 - h / JAPAN_H * (g0 - g1)
    d.rectangle([gx - 6, gy, gx + 6, g0], fill=(255, 170, 60, 255))
    for hh in range(0, int(JAPAN_H) + 1, 2):
        yy = g0 - hh / JAPAN_H * (g0 - g1)
        d.line([(gx - 10, yy), (gx + 10, yy)], fill=(255, 255, 255, 170) if h < hh else YELLOW + (255,), width=3)
    yh = g0 - HILO_H / JAPAN_H * (g0 - g1)
    d.line([(gx - 18, yh), (gx + 18, yh)], fill=(255, 255, 255, 255) if h < HILO_H else YELLOW + (255,), width=6)
    d.rectangle([gx - 30, g1 - 5, gx + 30, g1 + 5], fill=RED + (255,))
    d.ellipse([gx - 20, gy - 14, gx + 20, gy + 14], fill=(250, 250, 250, 255), outline=(0, 0, 0, 255), width=3)

    # ---- text
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    tag = 'CHILE · 1960'
    d.text((W - 36 - d.textlength(tag, font=font(46)), 48), tag, font=font(46), fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    f_t = font(40)
    d.text((gx - 48 - d.textlength('JAPAN', font=f_t), g1 - 30), 'JAPAN', font=f_t,
           fill=RED if not reached_all else YELLOW, stroke_width=5, stroke_fill=(0, 0, 0))

    hh, mm = int(h), int((h - int(h)) * 60)
    s = f'{hh} H {mm:02d} M' if not reached_all else f'{int(JAPAN_H)} HOURS'
    text_c(d, 132, s, fit(d, s, 220, 1030), fill=YELLOW, stroke=10)
    s = f'{ring:,.0f} KM ACROSS THE PACIFIC'
    text_c(d, 392, s, font(50), fill=WHITE, stroke=6)

    y_cap = 478
    passed = [(t_of_km(km), cap) for _, km, _, cap in PL if ring >= km]
    if t >= END_Q:
        text_c(d, y_cap, 'WERE YOU RIGHT?', font(80), fill=YELLOW, stroke=8)
    elif t >= AFTER:
        s = CAP_AFTER
        text_c(d, y_cap, s, fit(d, s, 72, 1010), fill=WHITE, stroke=8)
    elif reached_all:
        pop = min(1, (t - CLIMB) / 0.12)
        s = 'IT HIT JAPAN, 22 HOURS LATER'
        text_c(d, y_cap, s, fit(d, s, int(60 + 20 * pop), 1010), fill=GREEN, stroke=8)
    elif tt < 2.3:
        s = 'GUESS: HOW LONG UNTIL IT HITS JAPAN?'
        text_c(d, y_cap, s, fit(d, s, 72, 1010), stroke=8)
    elif passed and tt - passed[-1][0] < 1.3:
        tp, cap = passed[-1]
        pop = min(1, (tt - tp) / 0.12)
        s = 'PAST ' + cap if cap != 'HAWAII' else 'HAWAII: 15 HOURS'
        text_c(d, y_cap, s, fit(d, s, int(58 + 20 * pop), 1010), fill=GREEN, stroke=8)
    else:
        text_c(d, y_cap, 'STILL CROSSING' + ('...' if int(tt * 2) % 2 else ''), font(64), stroke=8)
    return img


AFTER = float(os.environ.get('AFTER', str(LINE_AT[-1] - 0.1)))
CAP_AFTER = os.environ.get('CAP_AFTER', 'MORE THAN 120 PEOPLE DIED IN JAPAN')


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
    print('wrote', out, 'beats', [(p[0], round(p[1]), round(t_of_km(p[1]), 2)) for p in PL], 'total', TOTAL)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--still':
        for s in map(float, sys.argv[3:]):
            frame(s).save(f'{sys.argv[1]}_{s:05.2f}.png')
    else:
        main()
