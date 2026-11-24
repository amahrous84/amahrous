#!/usr/bin/env python3
"""Code-rendered Short: the Chicxulub crater, Yucatan, Mexico. About 180 km wide.

One event, one growing measurement: the crater spreading across a real map of the
Yucatan (azimuthal equidistant projection centred on the crater, north up), with the
camera pulling back so the rim always fills the frame. Towns light up as the rim passes
them. A gauge on the right shows the whole width, with the red 180 KM line, from frame 0.
At the end the camera pulls back to the Gulf of Mexico to show where it is.

The rim is drawn as a circle of the crater's reported diameter around its centre; the
real crater is buried and not a perfect circle. Facts and sources: see the publish entry.
Land outline: Natural Earth 1:50m land (public domain), rasterised once into a cache.

Usage: python3 pipeline/anim_chicxulub.py out.mp4 [audio_dir]
       python3 pipeline/anim_chicxulub.py prefix --still 0 0.5 1 2
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
LAT0, LON0 = math.radians(21.4), math.radians(-89.52)   # crater centre (Wikipedia: 21 24 N, 89 31 W)
ROT = 0.0
TOP = float(os.environ.get('TOP_KM', '180'))       # crater diameter, km
R0 = 6.0                                           # rim radius in frame 0, km
CLIMB = float(os.environ.get('CLIMB', '11.0'))
PULL = float(os.environ.get('PULL', '1.4'))        # seconds for the pull-back to the Gulf
TOTAL = float(os.environ.get('TOTAL', '20.0'))
LINE_AT = [float(x) for x in os.environ.get('LINE_AT', '0.1,2.8,10.2,14.6').split(',')]
END_Q = TOTAL - 0.7
CX, CY = 520, 1250
RING_PX = 400
FAR_PK = 540 / 1100                                # final view: about 1,100 km to each side
HALF = math.pi * RE
YELLOW, RED, WHITE, GREEN = (255, 225, 90), (235, 45, 45), (255, 255, 255), (130, 240, 150)
OCEAN, LAND = np.array([28, 96, 168]), np.array([96, 164, 92])
OCEAN_IN, LAND_IN = np.array([96, 58, 40]), np.array([120, 74, 44])   # inside the crater
SPACE = (8, 14, 28)

PLACES = [  # name on map, lat, lon, caption
    ('CHICXULUB', 21.29, -89.61, 'THE TOWN OF CHICXULUB'),
    ('MOTUL', 21.09, -89.28, 'MOTUL'),
    ('MERIDA', 20.97, -89.62, 'THE CITY OF MERIDA'),
    ('HUNUCMA', 21.02, -89.88, 'HUNUCMA'),
    ('SISAL', 21.17, -90.03, 'SISAL'),
    ('DZILAM', 21.39, -88.89, 'DZILAM'),
    ('IZAMAL', 20.93, -89.02, 'IZAMAL'),
]
FAR = [('MEXICO CITY', 19.43, -99.13), ('CANCUN', 21.16, -86.85), ('CUBA', 22.0, -79.5),
       ('HOUSTON', 29.76, -95.37), ('MIAMI', 25.76, -80.19)]


def gc(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    c = math.acos(min(1.0, math.sin(LAT0) * math.sin(la) + math.cos(LAT0) * math.cos(la) * math.cos(lo - LON0)))
    az = math.atan2(math.sin(lo - LON0) * math.cos(la),
                    math.cos(LAT0) * math.sin(la) - math.sin(LAT0) * math.cos(la) * math.cos(lo - LON0))
    return RE * c, az + ROT


PL = [(n, *gc(la, lo), cap) for n, la, lo, cap in PLACES]
PL.sort(key=lambda p: p[1])
FL = [(n, *gc(la, lo)) for n, la, lo in FAR]


def rim(t):
    """Crater radius in km (fast start, eases into the final width)."""
    u = min(max(t / CLIMB, 0), 1)
    return R0 + (TOP / 2 - R0) * (1 - (1 - u) ** 1.35)


def t_of_km(km):
    u = 1 - (1 - (km - R0) / (TOP / 2 - R0)) ** (1 / 1.35)
    return u * CLIMB


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


def frame(t):
    tt = min(t, CLIMB)
    r = rim(tt)
    done = t >= CLIMB
    pk = RING_PX / r
    if done:
        z = min(1, (t - CLIMB) / PULL)
        z = z * z * (3 - 2 * z)
        pk = math.exp(math.log(RING_PX / r) * (1 - z) + math.log(FAR_PK) * z)
    img = map_layer(pk, r)
    full = Image.new('RGB', (W, H), SPACE)
    full.paste(img, (0, 598))
    img = full
    d = ImageDraw.Draw(img, 'RGBA')

    # 180 km target circle (dashed red) once it is near the screen
    rt = TOP / 2 * pk
    if rt < 1500 and not done:
        n = 64
        for k in range(n):
            a0 = 360 * k / n
            d.arc([CX - rt, CY - rt, CX + rt, CY + rt], a0, a0 + 2.8, fill=RED + (255,), width=7)

    # the crater rim: a raised ring of rock with a glowing edge
    rp = r * pk
    wob = 4 * math.sin(t * 20) if not done else 0
    for k, (wd, col) in enumerate([(max(10, rp * 0.12), (176, 120, 70, 255)), (max(4, rp * 0.03), (255, 200, 120, 255))]):
        rr = rp + wob * (k == 1)
        d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline=col, width=int(wd))
    if not done:
        for k in range(1, 4):   # shock rings inside
            rr = rp * (1 - 0.18 * k) + 5 * math.sin(t * 7 + k)
            d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline=(255, 170, 90, 90 - 20 * k), width=5)
    glow = max(0.0, 1 - t / 3.5)
    if glow > 0:
        gr = rp * 0.45
        d.ellipse([CX - gr, CY - gr, CX + gr, CY + gr], fill=(255, 190, 90, int(150 * glow)))

    # towns
    f_m = font(40)
    if not done or t < CLIMB + 0.4:
        for name, km, az, cap in PL:
            x, y = CX + km * pk * math.sin(az), CY - km * pk * math.cos(az)
            if not (-20 < x < W + 20 and 600 < y < H + 20):
                continue
            inside = r >= km
            hit = inside and tt - t_of_km(km) < 1.1
            rr = 13 if hit else 9
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(YELLOW if inside else WHITE) + (255,),
                      outline=(0, 0, 0, 255), width=3)
            if hit or name == 'MERIDA':
                w = d.textlength(name, font=f_m)
                lx = min(max(x - w / 2, 14), W - 96 - w)
                ly = y + 18 if y < 720 else y - 62
                d.text((lx, ly), name, font=f_m, fill=YELLOW if inside else WHITE, stroke_width=5, stroke_fill=(0, 0, 0))
    else:
        for name, km, az in FL:
            x, y = CX + km * pk * math.sin(az), CY - km * pk * math.cos(az)
            if not (20 < x < W - 100 and 640 < y < H - 30):
                continue
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=WHITE + (255,), outline=(0, 0, 0, 255), width=3)
            w = d.textlength(name, font=f_m)
            d.text((min(max(x - w / 2, 14), W - 100 - w), y + 14), name, font=f_m, fill=WHITE, stroke_width=5, stroke_fill=(0, 0, 0))

    # impact flash
    if t < 0.5:
        img = Image.blend(img, Image.new('RGB', (W, H), (255, 245, 220)), 0.35 * (1 - t / 0.5))
        d = ImageDraw.Draw(img, 'RGBA')

    # top band
    d.rectangle([0, 0, W, 590], fill=(10, 18, 34, 255))
    d.rectangle([0, 590, W, 598], fill=(255, 225, 90, 255))

    # gauge on the right: crater width, red 180 KM line from frame 0
    gx, g0, g1 = 1026, 1820, 760
    d.rounded_rectangle([gx - 34, g1 - 70, gx + 34, g0 + 26], 14, fill=(0, 0, 0, 170))
    d.rectangle([gx - 6, g1, gx + 6, g0], fill=(255, 255, 255, 110))
    gy = g0 - (2 * r) / TOP * (g0 - g1)
    d.rectangle([gx - 6, gy, gx + 6, g0], fill=(255, 170, 60, 255))
    for _, km, *_ in PL:
        yy = g0 - 2 * km / TOP * (g0 - g1)
        d.line([(gx - 16, yy), (gx + 16, yy)], fill=(255, 255, 255, 255) if r < km else YELLOW + (255,), width=4)
    d.rectangle([gx - 30, g1 - 5, gx + 30, g1 + 5], fill=RED + (255,))
    d.ellipse([gx - 20, gy - 14, gx + 20, gy + 14], fill=(250, 250, 250, 255), outline=(0, 0, 0, 255), width=3)

    # ---- text
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([36, 40, 392, 112], 16, fill=RED)
    d.text((56, 48), 'UNREAL BUT TRUE', font=font(46), fill=WHITE)
    tag = 'MEXICO · 66 MILLION YEARS AGO'
    ft = fit(d, tag, 46, 600)
    d.text((W - 36 - d.textlength(tag, font=ft), 50), tag, font=ft, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    f_t = font(40)
    s = f'{TOP:.0f} KM'
    d.text((gx - 48 - d.textlength(s, font=f_t), g1 - 30), s, font=f_t, fill=RED if not done else YELLOW,
           stroke_width=5, stroke_fill=(0, 0, 0))

    s = f'{2 * r:,.0f} KM WIDE'
    text_c(d, 132, s, fit(d, s, 220, 1030), fill=YELLOW, stroke=10)
    text_c(d, 392, 'THE CRATER OF THE DINOSAUR ASTEROID', fit(d, 'THE CRATER OF THE DINOSAUR ASTEROID', 50, 1010), fill=WHITE, stroke=6)

    y_cap = 478
    passed = [(t_of_km(km), cap) for _, km, _, cap in PL if r >= km]
    if t >= END_Q:
        text_c(d, y_cap, 'WERE YOU RIGHT?', font(80), fill=YELLOW, stroke=8)
    elif t >= AFTER:
        text_c(d, y_cap, CAP_AFTER, fit(d, CAP_AFTER, 72, 1010), fill=WHITE, stroke=8)
    elif done:
        pop = min(1, (t - CLIMB) / 0.12)
        s = CAP_DONE
        text_c(d, y_cap, s, fit(d, s, int(60 + 20 * pop), 1010), fill=GREEN, stroke=8)
    elif tt < 2.3:
        s = 'GUESS: HOW WIDE IS THE CRATER?'
        text_c(d, y_cap, s, fit(d, s, 72, 1010), stroke=8)
    elif passed and tt - passed[-1][0] < 1.2:
        tp, cap = passed[-1]
        pop = min(1, (tt - tp) / 0.12)
        s = 'SWALLOWING ' + cap
        text_c(d, y_cap, s, fit(d, s, int(58 + 20 * pop), 1010), fill=GREEN, stroke=8)
    else:
        text_c(d, y_cap, 'STILL SPREADING' + ('...' if int(tt * 2) % 2 else ''), font(64), stroke=8)
    return img


AFTER = float(os.environ.get('AFTER', str(LINE_AT[-1] - 0.1)))
CAP_DONE = os.environ.get('CAP_DONE', 'FROM A ROCK ABOUT 10 KM WIDE')
CAP_AFTER = os.environ.get('CAP_AFTER', 'STILL BURIED UNDER 1 KM OF ROCK')


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
