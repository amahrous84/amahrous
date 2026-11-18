#!/usr/bin/env python3
"""Code-rendered Short: Hunga Tonga eruption, 15 January 2022. The boom heard in Alaska.

One event, one growing measurement: the pressure wave from the eruption spreading across a
real map (azimuthal equidistant projection centred on the volcano, so every circle around
it is a true distance), with the camera pulling back so the ring always fills the frame.
Places light up as the ring reaches their true distance. A gauge on the right shows the
whole run to Alaska, with the red ALASKA line, from frame 0. Then the camera pulls back to
the whole planet and the wave keeps circling. Follows pipeline/FORMAT.md.

Facts (sources in the publish entry):
  Booms were heard across Alaska, more than 10,000 km (6,200 mi) away (Live Science; Univ.
  of Liverpool, Science 2022). The pressure (Lamb) wave circled Earth four times in one
  direction and three times in the other (same sources).
Distances are great-circle distances from the volcano (-20.546, -175.390).
Land outline: Natural Earth 1:50m land (public domain), rasterised once into a cache.

Usage: python3 pipeline/anim_hunga_tonga.py out.mp4 [audio_dir]
       python3 pipeline/anim_hunga_tonga.py prefix --still 0 0.5 1 2
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
LAT0, LON0 = math.radians(-20.546), math.radians(-175.390)
TOP = 10000.0          # km, where Alaska heard it
R0 = 150.0             # km already covered in frame 0
CLIMB = float(os.environ.get('CLIMB', '11.0'))
HOLD = float(os.environ.get('HOLD', '13.0'))      # end of the "heard in Alaska" beat
ZOOM = 1.0                                         # seconds to pull back to the whole planet
TOTAL = float(os.environ.get('TOTAL', '20.0'))
LINE_AT = [float(x) for x in os.environ.get('LINE_AT', '0.1,3.6,8.9,13.6').split(',')]
END_Q = TOTAL - 0.7
LAPS = 4
CX, CY = 540, 1300
RING_PX = 430
HALF = math.pi * RE    # 20,015 km: the far side of the planet
YELLOW, RED, WHITE, GREEN = (255, 225, 90), (235, 45, 45), (255, 255, 255), (130, 240, 150)
OCEAN, LAND = np.array([28, 96, 168]), np.array([96, 164, 92])
OCEAN_IN, LAND_IN = np.array([52, 128, 196]), np.array([140, 186, 104])   # inside the wave
SPACE = (8, 14, 28)

PLACES = [  # name on map, lat, lon, caption, show in caption
    ('FIJI', -18.14, 178.44, 'FIJI'),
    ('NEW ZEALAND', -36.85, 174.76, 'NEW ZEALAND'),
    ('TAHITI', -17.53, -149.57, 'TAHITI'),
    ('SYDNEY', -33.87, 151.21, 'AUSTRALIA'),
    ('PAPUA NEW GUINEA', -9.44, 147.18, 'PAPUA NEW GUINEA'),
    ('HAWAII', 21.31, -157.86, 'HAWAII'),
    ('GUAM', 13.44, 144.79, 'GUAM'),
    ('ANTARCTICA', -77.85, 166.67, 'ANTARCTICA'),
    ('PERTH', -31.95, 115.86, 'PERTH'),
    ('JAPAN', 35.68, 139.69, 'JAPAN'),
    ('LOS ANGELES', 34.05, -118.24, 'LOS ANGELES'),
    ('SEATTLE', 47.6, -122.3, 'SEATTLE'),
    ('ALASKA', 61.22, -149.9, 'ALASKA'),
]


def gc(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    c = math.acos(math.sin(LAT0) * math.sin(la) + math.cos(LAT0) * math.cos(la) * math.cos(lo - LON0))
    az = math.atan2(math.sin(lo - LON0) * math.cos(la),
                    math.cos(LAT0) * math.sin(la) - math.sin(LAT0) * math.cos(la) * math.cos(lo - LON0))
    return RE * c, az


PL = [(n, *gc(la, lo), cap) for n, la, lo, cap in PLACES]
PL.sort(key=lambda p: p[1])


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
AZ = np.arctan2(DX, -DY)


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


def climb_km(t):
    return R0 + (TOP - R0) * min(max(t / CLIMB, 0), 1)   # constant speed: it is a sound wave


def t_of(km):
    return (km - R0) / (TOP - R0) * CLIMB


def lap_state(t):
    """After HOLD: the wave runs to the far side of Earth and back home, LAPS times."""
    u = min(max((t - HOLD) / (END_Q - HOLD), 0), 1) * LAPS
    lap = min(int(u), LAPS - 1)
    f = u - lap
    start = TOP if lap == 0 else 0.0
    km = start + (HALF - start) * f / 0.5 if f < 0.5 else HALF * (1 - (f - 0.5) / 0.5)
    return lap, f, km


def frame(t):
    if t < HOLD:
        ring = climb_km(min(t, CLIMB))
        pk = RING_PX / ring
        laps_done = 0
    else:
        lap, f, ring = lap_state(min(t, END_Q - 1e-3))
        laps_done = lap + (1 if f >= 0.99 else 0)
        z = min(1, (t - HOLD) / ZOOM)
        z = z * z * (3 - 2 * z)
        pk0, pk1 = RING_PX / TOP, 470 / HALF
        pk = pk0 + (pk1 - pk0) * z
    img = map_layer(pk, ring)
    full = Image.new('RGB', (W, H), SPACE)
    full.paste(img, (0, 598))
    img = full
    d = ImageDraw.Draw(img, 'RGBA')

    # Alaska target circle (dashed red) once it is near the screen
    rt = TOP * pk
    if rt < 1400 and t < HOLD + ZOOM:
        n = 60
        for k in range(n):
            a0 = 360 * k / n
            d.arc([CX - rt, CY - rt, CX + rt, CY + rt], a0, a0 + 3.3, fill=RED + (255,), width=7)

    # places
    f_m = font(38)
    for name, km, az, cap in PL:
        x, y = CX + km * pk * math.sin(az), CY - km * pk * math.cos(az)
        if not (-20 < x < W + 20 and 600 < y < H + 20):
            continue
        reached = ring >= km or t >= HOLD
        hit = t < HOLD and reached and min(t, CLIMB) - t_of(km) < 1.0
        rr = 13 if hit else 9
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(YELLOW if reached else WHITE) + (255,),
                  outline=(0, 0, 0, 255), width=3)
        if (hit or name == 'ALASKA') and t < HOLD + ZOOM:
            w = d.textlength(name, font=f_m)
            lx = min(max(x - w / 2, 14), W - 90 - w)
            ly = y - 62 if y > 680 else y + 18
            col = YELLOW if hit else (RED if name == 'ALASKA' and not reached else YELLOW)
            d.text((lx, ly), name, font=f_m, fill=col, stroke_width=5, stroke_fill=(0, 0, 0))

    # the pressure wave
    rp = ring * pk
    if rp > 2:
        wob = 4 * math.sin(t * 25)
        for k, (wd, al) in enumerate([(44, 55), (26, 110), (11, 255)]):
            rr = rp + wob * (k == 2)
            d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline=(255, 246, 215, al), width=wd)
    # volcano
    vr = 16 + 6 * math.sin(t * 9)
    d.ellipse([CX - vr, CY - vr, CX + vr, CY + vr], fill=(255, 120, 40, 255), outline=(0, 0, 0, 255), width=3)
    if t < HOLD:
        s = 'TONGA'
        f_v = font(34)
        d.text((CX - d.textlength(s, font=f_v) / 2, CY + 24), s, font=f_v, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    # whole-planet outline in the last part
    if t >= HOLD:
        rr = HALF * pk
        d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline=(150, 190, 255, 200), width=4)

    # flash of the eruption in the first frames
    if t < 0.5:
        img = Image.blend(img, Image.new('RGB', (W, H), (255, 245, 220)), 0.35 * (1 - t / 0.5))
        d = ImageDraw.Draw(img, 'RGBA')

    # top band
    d.rectangle([0, 0, W, 590], fill=(10, 18, 34, 255))
    d.rectangle([0, 590, W, 598], fill=(255, 225, 90, 255))

    # gauge on the right: Tonga to Alaska, red ALASKA line from frame 0
    gx, g0, g1 = 1026, 1820, 760
    d.rounded_rectangle([gx - 34, g1 - 70, gx + 34, g0 + 26], 14, fill=(0, 0, 0, 170))
    d.rectangle([gx - 6, g1, gx + 6, g0], fill=(255, 255, 255, 110))
    gk = min(ring if t < HOLD else TOP, TOP)
    gy = g0 - gk / TOP * (g0 - g1)
    d.rectangle([gx - 6, gy, gx + 6, g0], fill=(255, 170, 60, 255))
    for name, km, *_ in PL:
        if km <= TOP:
            yy = g0 - km / TOP * (g0 - g1)
            d.line([(gx - 16, yy), (gx + 16, yy)], fill=(255, 255, 255, 255) if gk < km else YELLOW + (255,), width=4)
    d.rectangle([gx - 30, g1 - 5, gx + 30, g1 + 5], fill=RED + (255,))
    d.ellipse([gx - 20, gy - 14, gx + 20, gy + 14], fill=(250, 250, 250, 255), outline=(0, 0, 0, 255), width=3)

    # ---- text
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    tag = 'HUNGA TONGA · 2022'
    d.text((W - 36 - d.textlength(tag, font=font(46)), 48), tag, font=font(46), fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    f_t = font(40)
    s = 'ALASKA'
    d.text((gx - 48 - d.textlength(s, font=f_t), g1 - 30), s, font=f_t, fill=RED if gk < TOP else YELLOW,
           stroke_width=5, stroke_fill=(0, 0, 0))

    if t < HOLD:
        s = f'{ring:,.0f} KM'
        text_c(d, 132, s, fit(d, s, 220, 1030), fill=YELLOW, stroke=10)
        text_c(d, 392, 'HOW FAR THE BOOM HAS TRAVELLED', font(50), fill=WHITE, stroke=6)
    else:
        s = f'AROUND EARTH ×{laps_done}' if laps_done else 'AROUND EARTH...'
        text_c(d, 150, s, fit(d, s, 170, 1030), fill=YELLOW, stroke=10)
        text_c(d, 392, 'THE PRESSURE WAVE KEPT GOING', font(50), fill=WHITE, stroke=6)

    y_cap = 478
    tt = min(t, CLIMB)
    passed = [(t_of(km), cap) for _, km, _, cap in PL if ring >= km]
    if t >= END_Q:
        text_c(d, y_cap, 'WERE YOU RIGHT?', font(80), fill=YELLOW, stroke=8)
    elif t >= HOLD:
        s = '4 TIMES ONE WAY, 3 TIMES BACK'
        text_c(d, y_cap, s, fit(d, s, 72, 1010), fill=GREEN, stroke=8)
    elif t >= CLIMB:
        k = t - CLIMB
        pop = min(1, k / 0.12)
        s = 'PEOPLE IN ALASKA HEARD IT'
        text_c(d, y_cap, s, fit(d, s, int(60 + 20 * pop), 1010), fill=GREEN, stroke=8)
    elif tt < 2.3:
        s = 'GUESS: COULD THEY HEAR IT IN ALASKA?'
        text_c(d, y_cap, s, fit(d, s, 72, 1010), stroke=8)
    elif passed and tt - passed[-1][0] < 1.3:
        tp, cap = passed[-1]
        pop = min(1, (tt - tp) / 0.12)
        s = 'PAST ' + cap
        text_c(d, y_cap, s, fit(d, s, int(58 + 20 * pop), 1010), fill=GREEN, stroke=8)
    else:
        text_c(d, y_cap, 'STILL GOING' + ('...' if int(tt * 2) % 2 else ''), font(64), stroke=8)
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
    print('wrote', out, 'beats', [(p[0], round(t_of(p[1]), 2)) for p in PL], 'total', TOTAL)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--still':
        for s in map(float, sys.argv[3:]):
            frame(s).save(f'{sys.argv[1]}_{s:05.2f}.png')
    else:
        main()
