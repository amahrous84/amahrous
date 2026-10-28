#!/usr/bin/env python3
"""Upload every video listed in publish/queue/*.json to YouTube, then move the
entry to publish/done/ with the new video ID (or to publish/failed/ with the error).

A queue entry looks like:
    {"video": "shorts/videos/<date>-<slug>.mp4", "thumbnail": "thumbnails/<slug>.jpg",
     "title": "...", "description": "...", "tags": [...],
     "category_id": "28", "privacy_status": "public"}
An entry of {"check": true} only tests the sign-in and records the channel name.
An entry of {"stats": true} records live counts and 14-day analytics for the last
10 uploads (for the daily review when Ahmed's PC is off).
An entry of {"vitals": true} records a channel health check: channel settings, every
upload's settings, and 28-day analytics split by day, traffic source, subscriber
status, country, device and audience.

Credentials come from the YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN
repository secrets (the same Google sign-in the my-youtube tool uses).
"""
import glob
import json
import os
import traceback

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


CREDS = None


def service():
    global CREDS
    creds = CREDS = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'],
                        client_id=os.environ['YT_CLIENT_ID'],
                        client_secret=os.environ['YT_CLIENT_SECRET'],
                        token_uri='https://oauth2.googleapis.com/token')
    return build('youtube', 'v3', credentials=creds)


def stats(yt):
    import datetime
    ch = yt.channels().list(part='contentDetails', mine=True).execute()['items'][0]
    uploads = ch['contentDetails']['relatedPlaylists']['uploads']
    items = yt.playlistItems().list(part='contentDetails', playlistId=uploads,
                                    maxResults=10).execute()['items']
    ids = [i['contentDetails']['videoId'] for i in items]
    live = yt.videos().list(part='snippet,statistics', id=','.join(ids)).execute()['items']
    out = {'live': [{'id': v['id'], 'title': v['snippet']['title'],
                     'published': v['snippet']['publishedAt'], **v['statistics']} for v in live]}
    try:
        ya = build('youtubeAnalytics', 'v2', credentials=CREDS)
        end = datetime.date.today()
        out['analytics'] = ya.reports().query(
            ids='channel==MINE', startDate=str(end - datetime.timedelta(days=14)), endDate=str(end),
            metrics='views,engagedViews,averageViewPercentage,averageViewDuration,likes,comments,shares,subscribersGained',
            dimensions='video', sort='-views', maxResults=15).execute()
    except Exception as e:  # analytics scope may be missing; live counts still help
        out['analytics'] = f'failed: {e}'
    return out


def vitals(yt):
    import datetime
    ch = yt.channels().list(part='snippet,brandingSettings,statistics,status,contentDetails,topicDetails',
                            mine=True).execute()['items'][0]
    out = {'channel': {k: ch.get(k) for k in ('snippet', 'brandingSettings', 'statistics', 'status',
                                               'topicDetails')}}
    out['channel']['snippet'].pop('thumbnails', None)
    out['playlists'] = [{'title': p['snippet']['title'], 'count': p['contentDetails']['itemCount']}
                        for p in yt.playlists().list(part='snippet,contentDetails', mine=True,
                                                     maxResults=50).execute().get('items', [])]
    uploads = ch['contentDetails']['relatedPlaylists']['uploads']
    ids, token = [], None
    while True:
        r = yt.playlistItems().list(part='contentDetails', playlistId=uploads, maxResults=50,
                                    pageToken=token).execute()
        ids += [i['contentDetails']['videoId'] for i in r['items']]
        token = r.get('nextPageToken')
        if not token:
            break
    vids = []
    for i in range(0, len(ids), 50):
        for v in yt.videos().list(part='snippet,statistics,status,contentDetails',
                                  id=','.join(ids[i:i + 50])).execute()['items']:
            sn, st = v['snippet'], v['status']
            vids.append({'id': v['id'], 'title': sn['title'], 'published': sn['publishedAt'],
                         'duration': v['contentDetails']['duration'], 'privacy': st['privacyStatus'],
                         'madeForKids': st.get('madeForKids'), 'category': sn.get('categoryId'),
                         'lang': sn.get('defaultAudioLanguage'), 'tags': len(sn.get('tags', [])),
                         'desc_chars': len(sn.get('description', '')),
                         'thumb_custom': 'maxres' in sn.get('thumbnails', {}),
                         **v['statistics']})
    out['videos'] = vids
    ya = build('youtubeAnalytics', 'v2', credentials=CREDS)
    end = datetime.date.today()
    start = str(end - datetime.timedelta(days=28))
    reports = {
        'by_day': dict(metrics='views,engagedViews,subscribersGained,subscribersLost', dimensions='day', sort='day'),
        'traffic': dict(metrics='views,engagedViews', dimensions='insightTrafficSourceType', sort='-views'),
        'subscribed': dict(metrics='views,averageViewPercentage', dimensions='subscribedStatus'),
        'country': dict(metrics='views', dimensions='country', sort='-views', maxResults=10),
        'device': dict(metrics='views', dimensions='deviceType', sort='-views'),
        'audience': dict(metrics='viewerPercentage', dimensions='ageGroup,gender'),
        'sharing': dict(metrics='shares', dimensions='sharingService', sort='-shares'),
        'by_video': dict(metrics='views,engagedViews,averageViewPercentage,likes,comments,shares,subscribersGained',
                         dimensions='video', sort='-views', maxResults=25),
    }
    out['analytics'] = {}
    for name, q in reports.items():
        try:
            out['analytics'][name] = ya.reports().query(ids='channel==MINE', startDate=start,
                                                        endDate=str(end), **q).execute().get('rows')
        except Exception as e:
            out['analytics'][name] = f'failed: {e}'
    return out


def publish(yt, entry):
    if entry.get('vitals'):
        return vitals(yt)
    if entry.get('stats'):
        return stats(yt)
    if entry.get('check'):  # sign-in test only: read the channel, upload nothing
        item = yt.channels().list(part='snippet', mine=True).execute()['items'][0]
        return {'channel': item['snippet']['title']}
    body = {
        'snippet': {'title': entry['title'], 'description': entry.get('description', ''),
                    'tags': entry.get('tags', []), 'categoryId': entry.get('category_id', '28'),
                    'defaultLanguage': 'en', 'defaultAudioLanguage': 'en'},
        'status': {'privacyStatus': entry.get('privacy_status', 'public'),
                   'selfDeclaredMadeForKids': False},
    }
    media = MediaFileUpload(entry['video'], chunksize=-1, resumable=True)
    request = yt.videos().insert(part='snippet,status', body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    result = {'video_id': response['id'], 'url': f"https://youtu.be/{response['id']}"}
    if entry.get('thumbnail'):
        try:
            yt.thumbnails().set(videoId=response['id'],
                                media_body=MediaFileUpload(entry['thumbnail'])).execute()
            result['thumbnail'] = 'set'
        except Exception as e:  # the video is up even if the thumbnail fails
            result['thumbnail'] = f'failed: {e}'
    return result


def main():
    files = sorted(glob.glob('publish/queue/*.json'))
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
            dest = 'publish/done'
            print(name, entry['result'])
        except Exception:
            entry['error'] = traceback.format_exc(limit=3)
            dest = 'publish/failed'
            print(name, 'FAILED', entry['error'])
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, name), 'w') as fh:
            json.dump(entry, fh, indent=2)
        os.remove(path)


if __name__ == '__main__':
    main()
