"""Fetch free assets for a spec: FLUX images from Pollinations (no account) and
voice lines from Microsoft Edge TTS. Runs inside GitHub Actions, because the
cloud session cannot reach these hosts. Images are saved under
pipeline/free/images/ with the same file names make_short.py uses for its cache,
so copying them into pipeline/.images makes the renderer use them.

usage: python pipeline/free_assets.py pipeline/specs/<slug>.json
"""
import asyncio, hashlib, json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG_W, IMG_H = 864, 1536
STYLE = ('vertical 9:16, photorealistic, cinematic documentary still, dramatic natural light, '
         'rich detail, no text, no letters, no watermark')  # must match make_short.py
OUT = os.path.join(HERE, 'free', 'images')


def image(prompt, seed):
    full = f'{prompt}, {STYLE}'
    name = hashlib.sha1(f'{full}|{seed}'.encode()).hexdigest()[:16] + '.jpg'
    path = os.path.join(OUT, name)
    if os.path.exists(path):
        return path
    url = ('https://image.pollinations.ai/prompt/' + urllib.parse.quote(full) +
           f'?width={IMG_W}&height={IMG_H}&seed={seed}&model=flux&nologo=true&enhance=false')
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'unreal-but-true-shorts'})
            with urllib.request.urlopen(req, timeout=240) as r:
                data = r.read()
            if len(data) > 20000:
                with open(path, 'wb') as fh:
                    fh.write(data)
                print('image ok', name, len(data))
                return path
            print('image too small, retrying', len(data))
        except Exception as e:  # rate limits are common on the free tier
            print('image failed', attempt, e)
        time.sleep(20 * (attempt + 1))
    raise SystemExit('could not fetch image: ' + prompt[:60])


async def voice(text, path, name, rate):
    import edge_tts
    await edge_tts.Communicate(text, name, rate=rate).save(path)
    print('voice ok', path)


def main():
    spec_path = sys.argv[1]
    spec = json.load(open(spec_path))
    os.makedirs(OUT, exist_ok=True)
    for k, seg in enumerate(spec['segments']):
        if seg.get('image'):
            image(seg['image'], spec.get('seed', 1) + k)
            time.sleep(8)
        if seg.get('audio_url') and seg.get('audio'):  # pre-made voice line (e.g. ElevenLabs) to fetch
            import urllib.request
            path = os.path.join(ROOT, seg['audio'])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            urllib.request.urlretrieve(seg['audio_url'], path)
            print('audio ok', path)
            continue
        if spec.get('free_voice') and seg.get('audio'):
            path = os.path.join(ROOT, seg['audio'])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            asyncio.run(voice(seg.get('say', seg['text']), path, spec['free_voice'],
                              spec.get('free_rate', '+8%')))


if __name__ == '__main__':
    main()
