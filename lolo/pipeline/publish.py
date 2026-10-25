#!/usr/bin/env python3
"""Upload every video listed in lolo/publish/queue/*.json to the Lolo's Learning
Lagoon channel, then move the entry to lolo/publish/done/ with the new video ID
(or to lolo/publish/failed/ with the error).

Kept apart from the Unreal But True publisher on purpose: its own queue, its
own sign-in (LOLO_YT_REFRESH_TOKEN), and every upload is marked made for kids.

A queue entry looks like:
    {"video": "lolo/videos/<date>-<slug>.mp4", "thumbnail": "lolo/thumbnails/<slug>.jpg",
     "title": "...", "description": "...", "tags": [...],
     "publish_at": "2026-10-27T11:00:00Z", "playlist": "ABC Songs with Lolo"}
With publish_at the video is uploaded private and YouTube makes it public at
that time on its own. Without it the video goes public at once.
An entry of {"check": true} only tests the sign-in and records the channel name.
"""
import glob
import json
import os
import traceback

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

QUEUE = 'lolo/publish/queue'
DONE = 'lolo/publish/done'
FAILED = 'lolo/publish/failed'
EDUCATION = '27'


def service():
    creds = Credentials(None, refresh_token=os.environ['LOLO_YT_REFRESH_TOKEN'],
                        client_id=os.environ['YT_CLIENT_ID'],
                        client_secret=os.environ['YT_CLIENT_SECRET'],
                        token_uri='https://oauth2.googleapis.com/token')
    return build('youtube', 'v3', credentials=creds)


def channel(yt):
    item = yt.channels().list(part='snippet', mine=True).execute()['items'][0]
    return item['snippet']['title']


def add_to_playlist(yt, video_id, title):
    playlists = yt.playlists().list(part='snippet', mine=True, maxResults=50).execute()['items']
    match = [p['id'] for p in playlists if p['snippet']['title'] == title]
    if not match:
        return f'playlist not found: {title}'
    yt.playlistItems().insert(part='snippet', body={'snippet': {
        'playlistId': match[0], 'resourceId': {'kind': 'youtube#video', 'videoId': video_id}}}).execute()
    return 'added'


def publish(yt, entry):
    name = channel(yt)
    if entry.get('check'):
        return {'channel': name}
    # Refuse to post to the wrong channel if the token was made with another account.
    if 'lolo' not in name.lower():
        raise RuntimeError(f'Signed in to "{name}", not the Lolo channel. Nothing uploaded.')
    status = {'selfDeclaredMadeForKids': True, 'privacyStatus': 'public'}
    if entry.get('publish_at'):
        status.update(privacyStatus='private', publishAt=entry['publish_at'])
    body = {
        'snippet': {'title': entry['title'], 'description': entry.get('description', ''),
                    'tags': entry.get('tags', []), 'categoryId': entry.get('category_id', EDUCATION),
                    'defaultLanguage': 'en', 'defaultAudioLanguage': 'en'},
        'status': status,
    }
    media = MediaFileUpload(entry['video'], chunksize=-1, resumable=True)
    request = yt.videos().insert(part='snippet,status', body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    result = {'video_id': response['id'], 'url': f"https://youtu.be/{response['id']}",
              'publish_at': entry.get('publish_at', 'now')}
    if entry.get('thumbnail'):
        try:
            yt.thumbnails().set(videoId=response['id'],
                                media_body=MediaFileUpload(entry['thumbnail'])).execute()
            result['thumbnail'] = 'set'
        except Exception as e:  # the video is up even if the thumbnail fails
            result['thumbnail'] = f'failed: {e}'
    if entry.get('playlist'):
        try:
            result['playlist'] = add_to_playlist(yt, response['id'], entry['playlist'])
        except Exception as e:
            result['playlist'] = f'failed: {e}'
    return result


def main():
    files = sorted(glob.glob(f'{QUEUE}/*.json'))
    if not files:
        print('Nothing queued.')
        return
    yt = service()
    for path in files:
        name = os.path.basename(path)
        with open(path) as fh:
            entry = json.load(fh)
        try:
            entry['result'] = publish(yt, entry)
            dest = DONE
            print(name, entry['result'])
        except Exception:
            entry['error'] = traceback.format_exc(limit=3)
            dest = FAILED
            print(name, 'FAILED', entry['error'])
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, name), 'w') as fh:
            json.dump(entry, fh, indent=2)
        os.remove(path)


if __name__ == '__main__':
    main()
