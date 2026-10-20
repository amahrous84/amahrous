#!/usr/bin/env python3
"""Make a 1280x720 YouTube thumbnail: an AI picture plus big text and a red badge.

    python3 pipeline/make_thumbnail.py "<picture prompt>" thumbnails/<slug>.jpg "BIG TEXT" "BADGE"

Set SEED to try another picture.
"""
import json,os,sys,urllib.request
from PIL import Image,ImageDraw,ImageFont
prompt,out,big,badge=sys.argv[1:5]
body=json.dumps({'prompt':prompt+', no text, no letters','image_size':{'width':1280,'height':720},'num_images':1,'seed':int(os.environ.get('SEED','7')),'num_inference_steps':4}).encode()
r=urllib.request.Request('https://fal.run/fal-ai/flux/schnell',data=body,headers={'Authorization':'Key '+os.environ['FAL_KEY'],'Content-Type':'application/json'})
url=json.load(urllib.request.urlopen(r,timeout=180))['images'][0]['url'].replace('://v3b.fal.media/','://v3.fal.media/')
tmp=out+'.src.jpg'; open(tmp,'wb').write(urllib.request.urlopen(url,timeout=120).read())
im=Image.open(tmp).convert('RGB').resize((1280,720)); os.remove(tmp)
d=ImageDraw.Draw(im); f=ImageFont.truetype('pipeline/fonts/Anton-Regular.ttf',190)
d.text((60,40),big,font=f,fill=(255,210,63),stroke_width=12,stroke_fill=(0,0,0))
fb=ImageFont.truetype('pipeline/fonts/Anton-Regular.ttf',90)
w=fb.getlength(badge); d.rounded_rectangle((60,560,60+w+60,680),20,fill=(220,30,30))
d.text((90,565),badge,font=fb,fill=(255,255,255))
im.save(out,quality=92)
