#!/usr/bin/env python3
"""Render a long YouTube video (1920x1080, 30 fps) from a JSON spec.

    python3 pipeline/make_long.py pipeline/long/<slug>.json shorts/videos/<name>.mp4

The spec has "title", "seed", "accent" and a list of "segments". Each segment has:
    text      the caption text
    say       optional: what the voice says, if it differs from text
    audio     optional: a recorded voice file; defaults to pipeline/audio/<slug>/NN.mp3
    image     a picture prompt (fal.ai FLUX schnell, landscape)
    chapter   optional: starts a new chapter; its name shows top left for a few seconds

Voice only, no music or sound effects (Ahmed's preference since 2026-10-15).
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import urllib.request

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

import make_short as ms

W, H, FPS = 1920, 1080, 30
SR = ms.SR
GAP = 0.45            # silence between segments
CHAPTER_GAP = 0.9     # silence before a new chapter
XFADE = 0.5           # picture crossfade, in seconds
TAIL = 1.5
STYLE = ('wide 16:9 landscape, photorealistic, cinematic documentary still, dramatic natural light, '
         'rich detail, no text, no letters, no watermark')
IMG_CACHE = os.path.join(ms.HERE, '.images')


def fetch_image(prompt, seed):
    full = f'{prompt}, {STYLE}'
    os.makedirs(IMG_CACHE, exist_ok=True)
    path = os.path.join(IMG_CACHE, 'L' + hashlib.sha1(f'{full}|{seed}'.encode()).hexdigest()[:16] + '.jpg')
    if os.path.exists(path):
        return path
    body = json.dumps({'prompt': full, 'image_size': {'width': 1920, 'height': 1088},
                       'num_images': 1, 'seed': seed, 'num_inference_steps': 4}).encode()
    req = urllib.request.Request('https://fal.run/fal-ai/flux/schnell', data=body, headers={
        'Authorization': 'Key ' + os.environ['FAL_KEY'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        url = json.load(r)['images'][0]['url']
    url = url.replace('://v3b.fal.media/', '://v3.fal.media/')
    with urllib.request.urlopen(url, timeout=120) as r, open(path, 'wb') as fh:
        fh.write(r.read())
    return path


def caption_chunks(text, start, dur, max_words=6, max_chars=34):
    words = text.split()
    weights = [len(w) + (4 if w[-1] in '.,!?;:' else 1) for w in words]
    total = sum(weights)
    chunks, cur, cur_w, t = [], [], 0, start
    for w, wt in zip(words, weights):
        cur.append(w)
        cur_w += wt
        if len(cur) == max_words or w[-1] in '.,!?;:' or len(' '.join(cur)) > max_chars:
            d = dur * cur_w / total
            chunks.append((t, t + d, ' '.join(cur)))
            t += d
            cur, cur_w = [], 0
    if cur:
        chunks.append((t, start + dur, ' '.join(cur)))
    return chunks


def text_layer(img, text, xy, size, fill, anchor='mm', stroke=8):
    d = ImageDraw.Draw(img)
    d.text(xy, text, font=ms.font(size), fill=fill, anchor=anchor,
           stroke_width=stroke, stroke_fill=(0, 0, 0, fill[3] if len(fill) == 4 else 255))


class Picture:
    """A picture with a slow zoom and pan, pre-scaled once."""

    def __init__(self, path, k):
        img = Image.open(path).convert('RGB')
        self.img = img.resize((int(W * 1.2), int(H * 1.2)), Image.LANCZOS)
        self.zoom_out = k % 2 == 1
        self.pan = [-1, 1, 0][k % 3] * 0.6

    def frame(self, x):
        x = min(max(x, 0.0), 1.0)
        z = 1.16 - 0.12 * x if self.zoom_out else 1.04 + 0.12 * x
        cw, ch = W * 1.2 / z, H * 1.2 / z
        cx = self.img.width / 2 + self.pan * (self.img.width - cw) / 2 * (2 * x - 1)
        cy = self.img.height / 2
        return self.img.resize((W, H), Image.BILINEAR,
                               box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))


def bottom_shade():
    a = np.zeros((H, 1), dtype=np.float32)
    y = np.arange(H)
    a[:, 0] = np.clip((y - H * 0.62) / (H * 0.38), 0, 1) ** 1.4 * 170
    top = np.clip((H * 0.22 - y) / (H * 0.22), 0, 1) ** 1.6 * 110
    a[:, 0] = np.maximum(a[:, 0], top)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, 'RGBA')


def render(spec, out_path):
    slug = spec['slug']
    segs = spec['segments']
    accent = ms.hex_rgb(spec.get('accent', '#ffd23f'))
    clips = []
    for k, s in enumerate(segs):
        path = s.get('audio') or f'pipeline/audio/{slug}/{k + 1:02d}.mp3'
        clips.append(ms.trim_silence(ms.load_audio(path)))

    starts, t = [], 0.4
    for k, (c, s) in enumerate(zip(clips, segs)):
        if k and s.get('chapter'):
            t += CHAPTER_GAP - GAP
        starts.append(t)
        t += len(c) / SR + GAP
    total = t - GAP + TAIL
    n = int(total * SR)
    voice = np.zeros(n, dtype=np.float32)
    for st, c in zip(starts, clips):
        i = int(st * SR)
        voice[i:i + len(c)] += c[:n - i]
    voice /= max(np.abs(voice).max(), 1e-6) / 0.9
    durs = [len(c) / SR for c in clips]

    print('images...', file=sys.stderr)
    pics = [Picture(fetch_image(s['image'], spec.get('seed', 1) + k), k) for k, s in enumerate(segs)]
    # each picture shows from its segment start until the next one starts
    shows = starts[1:] + [total]
    chunks = []
    for s, st, du in zip(segs, starts, durs):
        chunks += caption_chunks(s['text'], st, du)
    chapters = [(st, s['chapter']) for s, st in zip(segs, starts) if s.get('chapter')]
    shade = bottom_shade()

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, 'a.wav')
        sf.write(wav, voice, SR)
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', wav,
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out_path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n_frames = int(total * FPS)
        for f in range(n_frames):
            t = f / FPS
            i = max(j for j in range(len(segs)) if j == 0 or t >= starts[j])
            span0 = starts[i] if i else 0.0
            span = shows[i] - span0 + XFADE
            frame = pics[i].frame((t - span0) / span)
            if i and t - starts[i] < XFADE:
                prev_span = shows[i - 1] - (starts[i - 1] if i > 1 else 0.0) + XFADE
                prev = pics[i - 1].frame((t - (starts[i - 1] if i > 1 else 0.0)) / prev_span)
                frame = Image.blend(prev, frame, (t - starts[i]) / XFADE)
            frame = frame.convert('RGBA')
            frame.alpha_composite(shade)
            for cs, name in chapters:
                age = t - cs
                if 0 <= age < 3.5:
                    a = int(255 * min(1, age / 0.3, (3.5 - age) / 0.4))
                    d = ImageDraw.Draw(frame)
                    d.rectangle((70, 70, 82, 140), fill=accent + (a,))
                    text_layer(frame, name.upper(), (104, 105), 64, (255, 255, 255, a), anchor='lm', stroke=6)
            for a0, b0, txt in chunks:
                if a0 <= t < b0:
                    pop = 0.9 + 0.1 * ms.ease_back((t - a0) / 0.12)
                    size = int(78 * pop)
                    while ms.font(size).getlength(txt.upper()) > W - 240 and size > 40:
                        size -= 4
                    text_layer(frame, txt.upper(), (W / 2, H - 150), size, (255, 255, 255, 255), stroke=8)
                    break
            if i == len(segs) - 1:
                k = 1 + 0.05 * math.sin(t * 7)
                bw, bh = 420 * k, 100 * k
                d = ImageDraw.Draw(frame)
                d.rounded_rectangle((W - 80 - bw, 80, W - 80, 80 + bh), 24, fill=(230, 30, 30, 255))
                d.text((W - 80 - bw / 2, 80 + bh / 2), 'SUBSCRIBE', font=ms.font(int(62 * k)),
                       fill=(255, 255, 255), anchor='mm')
            proc.stdin.write(frame.convert('RGB').tobytes())
            if f % 900 == 0:
                print(f'{f}/{n_frames}', file=sys.stderr)
        proc.stdin.close()
        if proc.wait() != 0:
            raise SystemExit('ffmpeg failed')
    return total, starts, chapters


if __name__ == '__main__':
    with open(sys.argv[1]) as fh:
        spec = json.load(fh)
    total, starts, chapters = render(spec, sys.argv[2])
    print(json.dumps({'out': sys.argv[2], 'seconds': round(total, 2),
                      'chapters': [(f'{int(s // 60)}:{int(s % 60):02d}', n) for s, n in chapters]}))
