import json
import os
import re
import tempfile
import urllib.request
from googleapiclient.discovery import Resource
from googleapiclient.http import MediaFileUpload
from pydantic import BaseModel, Field
from tools.google.google_apis import create_service


class PlaylistInfo(BaseModel):
    playlist_id: str | None = Field(None, description='Playlist ID')
    playlist_title: str | None = Field(None, description='Playlist Title')
    channel_id: str | None = Field(None, description='Channel ID')
    description: str | None = Field(None, description='Playlist Description')
    published_at: str | None = Field(None, description='Playlist Published Time')


class PlaylistResults(BaseModel):
    total_results: int = Field(..., description='Total Number of results')
    playlists: list[PlaylistInfo] = Field(..., description='Playlist Information')


class ChannelInfo(BaseModel):
    channel_id: str | None = Field(None, description='Channel ID')
    channel_title: str | None = Field(None, description='Channel Title')
    description: str | None = Field(None, description='Channel Description')
    published_at: str | None = Field(None, description='Channel Published Time')

    # Only filled in by get_channel_info (search results do not include these)
    country: str | None = Field(None, description='Channel Country')
    view_count: str | None = Field(None, description='View Count')
    subscriber_count: str | None = Field(None, description='Subscriber Count')
    video_count: str | None = Field(None, description='Video Count')


class ChannelResults(BaseModel):
    total_results: int = Field(..., description='Total Number of results')
    channels: list[ChannelInfo] = Field(..., description='Channel Information')


class VideoInfo(BaseModel):
    channel_id: str | None = Field(None, description='Channel ID')
    channel_title: str | None = Field(None, description='Channel Title')
    video_id: str | None = Field(None, description='Video ID')
    video_title: str | None = Field(None, description='Video Title')
    description: str | None = Field(None, description='Video Description')
    published_at: str | None = Field(None, description='Video Published Time')

    # Additional Information (optional)
    tags: list[str] | None = Field(None, description='Video Tags')
    duration: str | None = Field(None, description='Video Duration')
    dimension: str | None = Field(None, description='Video Dimension')
    view_count: int | None = Field(None, description='View Count')
    like_count: int | None = Field(None, description='Like Count')
    comment_count: int | None = Field(None, description='Comment Count')
    topic_categories: list[str] | None = Field(None, description='Topic Categories')
    has_paid_product_placement: bool | None = Field(None, description='Has Paid Product Placement')


class VideoResults(BaseModel):
    total_results: int = Field(..., description='Total Number of results')
    videos: list[VideoInfo] = Field(..., description='Video Information')


def extract_video_id(input_str: str) -> str | None:
    """
    Extract YouTube video ID from a URL or ID string.

    Args:
        input_str: URL or ID string to extract video ID from.

    Returns:
        The extracted YouTube video ID, or None if nothing matched.
    """
    url_pattern = re.compile(
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    )
    match = url_pattern.match(input_str)

    if match:
        return match.group(1)

    id_pattern = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    if id_pattern.match(input_str):
        return input_str

    return None


class YouTubeTool:
    """
    Toolkit for interacting with the YouTube Data API.

    Based on https://developers.google.com/youtube/v3/docs
    """
    API_NAME = 'youtube'
    API_VERSION = 'v3'
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.readonly',
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/yt-analytics.readonly',
    ]

    def __init__(self, client_secret: str) -> None:
        self.client_secret = client_secret
        self.analytics_service = None
        self._init_youtube_service()

    def _init_youtube_service(self):
        """
        Initialize the YouTube Data API service.
        """
        self.service = create_service(
            self.client_secret,
            self.API_NAME,
            self.API_VERSION,
            self.SCOPES
        )
        if not self.service:
            raise Exception("Failed to create YouTube service")

    @property
    def youtube_service(self) -> Resource:
        """
        Return YouTube Data API service instance.
        """
        return self.service

    def get_channel_info(self, channel_id: str) -> str:
        """
        Get information about a YouTube channel based on the provided channel ID.

        Args:
            channel_id (str): The ID of the YouTube channel (starts with 'UC'),
                or its handle (starts with '@').

        Returns:
            str: Information about the YouTube channel.
        """
        if channel_id.startswith('UC'):
            request = self.service.channels().list(
                part='snippet,statistics',
                id=channel_id
            )
        elif channel_id.startswith('@'):
            request = self.service.channels().list(
                part='snippet,statistics',
                forHandle=channel_id
            )
        else:
            return 'Invalid Channel ID'

        response = request.execute()

        items = response.get('items')
        if not items:
            return 'Channel not found'

        channel = items[0]
        snippet = channel['snippet']
        statistics = channel['statistics']

        channel_info = ChannelInfo(
            channel_id=channel.get('id'),
            channel_title=snippet.get('title'),
            description=snippet.get('description'),
            published_at=snippet.get('publishedAt'),
            country=snippet.get('country', ''),
            view_count=statistics.get('viewCount'),
            subscriber_count=statistics.get('subscriberCount'),
            video_count=statistics.get('videoCount'),
        )
        return channel_info.model_dump_json()

    def search_channel(
        self,
        channel_name: str,
        published_after: str = None,
        published_before: str = None,
        region_code: str = 'US',
        order: str = 'relevance',
        max_results: int = 50
    ) -> str:
        """
        Searches for YouTube channels based on the provided channel name.

        Args:
            channel_name (str): The name of the channel to search for.
            published_after (str): Only return resources created at or after this time.
                RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            published_before (str): Only return resources created before this time.
                RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            region_code (str): Return search results for the specified country.
                ISO 3166-1 alpha-2 country code.
            order (str): The order in which to return results. Default is 'relevance'.
                Options include 'date', 'rating', 'relevance', 'title', 'videoCount', and 'viewCount'.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            ChannelResults: A list of channels that match the search.
        """
        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            current_max = min(50, max_results - len(lst))

            request = self.service.search().list(
                part='snippet',
                q=channel_name,
                type='channel',
                maxResults=current_max,
                order=order,
                publishedAfter=published_after,
                publishedBefore=published_before,
                regionCode=region_code,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                channel_info = ChannelInfo(
                    channel_id=item['id'].get('channelId'),
                    channel_title=item['snippet'].get('title'),
                    description=item['snippet'].get('description'),
                    published_at=item['snippet'].get('publishedAt')
                )
                lst.append(channel_info)

            total_results = response['pageInfo']['totalResults']
            next_page_token = response.get('nextPageToken')

            if not next_page_token:
                break

        return ChannelResults(
            total_results=total_results,
            channels=lst
        ).model_dump_json()

    def search_playlist(
        self,
        query: str,
        published_after: str = None,
        published_before: str = None,
        region_code: str = 'US',
        order: str = 'date',
        max_results: int = 50
    ) -> str:
        """
        Searches for YouTube playlists based on the provided query.

        Args:
            query (str): The query to search for.
            published_after (str): Only return resources created at or after this time.
                RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            published_before (str): Only return resources created before this time.
                RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            region_code (str): Return search results for the specified country.
                ISO 3166-1 alpha-2 country code.
            order (str): The order in which to return results. Default is 'date'.
                Options include 'date', 'rating', 'relevance', 'title', 'videoCount', and 'viewCount'.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            PlaylistResults: A list of playlists that match the search.
        """
        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            current_max = min(50, max_results - len(lst))

            request = self.service.search().list(
                part='snippet',
                q=query,
                type='playlist',
                maxResults=current_max,
                order=order,
                publishedAfter=published_after,
                publishedBefore=published_before,
                regionCode=region_code,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                playlist_info = PlaylistInfo(
                    playlist_id=item['id'].get('playlistId'),
                    playlist_title=item['snippet'].get('title'),
                    channel_id=item['snippet'].get('channelId'),
                    description=item['snippet'].get('description'),
                    published_at=item['snippet'].get('publishedAt')
                )
                lst.append(playlist_info)

            total_results = response['pageInfo']['totalResults']
            next_page_token = response.get('nextPageToken')

            if not next_page_token:
                break

        return PlaylistResults(
            total_results=total_results,
            playlists=lst
        ).model_dump_json()

    def search_videos(
        self,
        query: str,
        published_after: str = None,
        published_before: str = None,
        region_code: str = 'US',
        video_duration: str = 'any',
        order: str = 'date',
        max_results: int = 50
    ) -> str:
        """
        Searches for YouTube videos based on the provided query.

        Args:
            query (str): The query to search for.
            published_after (str): Only return resources created at or after this time.
                RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            published_before (str): Only return resources created before this time.
                RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            region_code (str): Return search results for the specified country.
                ISO 3166-1 alpha-2 country code.
            video_duration (str): Filters video search results based on their duration.
                Default is 'any'. Options include 'any', 'long', 'medium', 'short'.
            order (str): The order in which to return results. Default is 'date'.
                Options include 'date', 'rating', 'relevance', 'title', 'videoCount', and 'viewCount'.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            VideoResults: A list of videos that match the search.
        """
        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            current_max = min(50, max_results - len(lst))

            request = self.service.search().list(
                part='snippet',
                q=query,
                type='video',
                maxResults=current_max,
                order=order,
                publishedAfter=published_after,
                publishedBefore=published_before,
                regionCode=region_code,
                videoDuration=video_duration,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                video_info = VideoInfo(
                    channel_id=item['snippet'].get('channelId'),
                    channel_title=item['snippet'].get('channelTitle'),
                    video_id=item['id'].get('videoId'),
                    video_title=item['snippet'].get('title'),
                    description=item['snippet'].get('description'),
                    published_at=item['snippet'].get('publishTime')
                )
                lst.append(video_info)

            total_results = response['pageInfo']['totalResults']
            next_page_token = response.get('nextPageToken')

            if not next_page_token:
                break

        return VideoResults(
            total_results=total_results,
            videos=lst
        ).model_dump_json()

    def get_video_info(
        self,
        video_ids: str,
        max_results: int = 50
    ) -> str:
        """
        Retrieves detailed information about YouTube videos based on the provided video IDs.

        Args:
            video_ids (str): A single video ID or URL, or a comma-separated string of them.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            str: A list of videos with detailed information.
        """
        ids = []
        for raw_id in video_ids.split(','):
            raw_id = raw_id.strip()
            if not raw_id:
                continue
            video_id = extract_video_id(raw_id)
            if not video_id:
                return f'Error: Invalid Video ID or URL: {raw_id}'
            ids.append(video_id)

        if not ids:
            return 'Error: Invalid Video ID or URL.'

        ids = ids[:max_results]
        lst = []

        # The API accepts at most 50 IDs per request
        for start in range(0, len(ids), 50):
            request = self.service.videos().list(
                part='id,snippet,contentDetails,statistics,paidProductPlacementDetails,topicDetails',
                id=','.join(ids[start:start + 50])
            )
            response = request.execute()

            for item in response.get('items', []):
                snippet = item['snippet']
                content_details = item.get('contentDetails', {})
                statistics = item.get('statistics', {})
                topic_details = item.get('topicDetails', {})
                paid_details = item.get('paidProductPlacementDetails', {})

                video_info = VideoInfo(
                    channel_id=snippet.get('channelId'),
                    channel_title=snippet.get('channelTitle'),
                    video_id=item['id'],
                    video_title=snippet.get('title'),
                    description=snippet.get('description', ''),
                    published_at=snippet.get('publishedAt'),
                    tags=snippet.get('tags', []),
                    duration=content_details.get('duration'),
                    dimension=content_details.get('dimension'),
                    view_count=statistics.get('viewCount', 0),
                    like_count=statistics.get('likeCount', 0),
                    comment_count=statistics.get('commentCount', 0),
                    topic_categories=topic_details.get('topicCategories', []),
                    has_paid_product_placement=paid_details.get('hasPaidProductPlacement', False)
                )
                lst.append(video_info)

        return VideoResults(
            total_results=len(lst),
            videos=lst
        ).model_dump_json()

    def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50
    ) -> str:
        """
        Returns videos uploaded by a YouTube channel based on the provided channel ID.

        Args:
            channel_id (str): The ID of the YouTube channel.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            str: A list of videos uploaded by the channel.
        """
        # Look up the channel's "uploads" playlist once
        request = self.service.channels().list(
            part='contentDetails',
            id=channel_id
        )
        response = request.execute()

        items = response.get('items')
        if not items:
            return 'Channel not found'

        uploads_playlist_id = items[0]['contentDetails']['relatedPlaylists'].get('uploads')
        if not uploads_playlist_id:
            return 'Channel has no uploads playlist'

        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            current_max = min(50, max_results - len(lst))

            playlist_request = self.service.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=current_max,
                pageToken=next_page_token
            )
            playlist_response = playlist_request.execute()

            for item in playlist_response['items']:
                snippet = item['snippet']

                video_info = VideoInfo(
                    channel_id=snippet.get('channelId'),
                    channel_title=snippet.get('channelTitle'),
                    video_id=snippet['resourceId']['videoId'],
                    video_title=snippet.get('title'),
                    description=snippet.get('description', ''),
                    published_at=snippet.get('publishedAt'),
                )
                lst.append(video_info)

            total_results = playlist_response['pageInfo']['totalResults']
            next_page_token = playlist_response.get('nextPageToken')

            if not next_page_token:
                break

        return VideoResults(
            total_results=total_results,
            videos=lst
        ).model_dump_json()

    def construct_hyperlink(
        self,
        id: str,
        type: str
    ) -> str:
        """
        Construct a hyperlink based on the provided ID and type.

        Args:
            id (str): The ID of the YouTube resource.
            type (str): The type of the YouTube resource.
                Options include 'channel', 'playlist', and 'video'.

        Returns:
            str: The hyperlink to the YouTube resource.
        """
        if type == 'channel':
            link = f'https://www.youtube.com/channel/{id}'
        elif type == 'playlist':
            link = f'https://www.youtube.com/playlist?list={id}'
        elif type == 'video':
            link = f'https://www.youtube.com/watch?v={id}'
        else:
            link = ''

        return link

    def _get_analytics_service(self):
        """
        Create the YouTube Analytics API service the first time it is needed.
        """
        if self.analytics_service is None:
            self.analytics_service = create_service(
                self.client_secret,
                'youtubeAnalytics',
                'v2',
                self.SCOPES
            )
            if not self.analytics_service:
                raise Exception("Failed to create YouTube Analytics service")
        return self.analytics_service

    def get_my_channel_info(self) -> str:
        """
        Get information and public statistics for the signed-in user's own channel.

        Returns:
            str: Channel information (title, subscribers, total views, video count).
        """
        request = self.service.channels().list(
            part='snippet,statistics',
            mine=True
        )
        response = request.execute()

        items = response.get('items')
        if not items:
            return 'No channel found for the signed-in account'

        channel = items[0]
        snippet = channel['snippet']
        statistics = channel.get('statistics', {})

        channel_info = ChannelInfo(
            channel_id=channel.get('id'),
            channel_title=snippet.get('title'),
            description=snippet.get('description'),
            published_at=snippet.get('publishedAt'),
            country=snippet.get('country', ''),
            view_count=statistics.get('viewCount'),
            subscriber_count=statistics.get('subscriberCount'),
            video_count=statistics.get('videoCount'),
        )
        return channel_info.model_dump_json()

    def get_my_channel_analytics(
        self,
        start_date: str,
        end_date: str,
        metrics: str = 'views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,comments',
        dimensions: str = None,
        sort: str = None,
        max_results: int = 50
    ) -> str:
        """
        Get private analytics for the signed-in user's own channel.

        Args:
            start_date (str): First day of the period, formatted YYYY-MM-DD.
            end_date (str): Last day of the period, formatted YYYY-MM-DD.
            metrics (str): Comma-separated metrics. Examples: 'views', 'estimatedMinutesWatched',
                'averageViewDuration', 'averageViewPercentage', 'subscribersGained',
                'subscribersLost', 'likes', 'comments', 'shares'.
            dimensions (str): Optional breakdown. Examples: 'day', 'month', 'video', 'country',
                'insightTrafficSourceType', 'deviceType'. Leave empty for totals.
            sort (str): Optional sort order, e.g. '-views' for most viewed first.
                Required by the API when dimensions is 'video'.
            max_results (int): The maximum number of rows to return. Default is 50.

        Returns:
            str: The analytics rows as JSON.
        """
        request = self._get_analytics_service().reports().query(
            ids='channel==MINE',
            startDate=start_date,
            endDate=end_date,
            metrics=metrics,
            dimensions=dimensions,
            sort=sort,
            maxResults=max_results
        )
        response = request.execute()

        headers = [header['name'] for header in response.get('columnHeaders', [])]
        rows = [dict(zip(headers, row)) for row in response.get('rows', [])]

        return json.dumps({
            'start_date': start_date,
            'end_date': end_date,
            'total_results': len(rows),
            'rows': rows
        })

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str = '',
        tags: list[str] = None,
        category_id: str = '22',
        privacy_status: str = 'private',
        made_for_kids: bool = False
    ) -> str:
        """
        Upload a video file to the signed-in user's channel.

        Args:
            file_path (str): Full path to the video file on this computer.
            title (str): The video title (maximum 100 characters).
            description (str): The video description.
            tags (list[str]): Optional list of tags.
            category_id (str): YouTube category ID. Default is '22' (People & Blogs).
                Others include '28' (Science & Technology), '27' (Education), '24' (Entertainment).
            privacy_status (str): 'private', 'unlisted', or 'public'. Default is 'private'.
            made_for_kids (bool): Whether the video is made for kids. Default is False.

        Returns:
            str: The new video's ID, link, and privacy status as JSON.
        """
        if not os.path.isfile(file_path):
            return f'Error: File not found: {file_path}'

        if privacy_status not in ('private', 'unlisted', 'public'):
            return "Error: privacy_status must be 'private', 'unlisted', or 'public'."

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': made_for_kids
            }
        }

        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        request = self.service.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            _, response = request.next_chunk()
        media.stream().close()

        video_id = response['id']
        return json.dumps({
            'video_id': video_id,
            'url': self.construct_hyperlink(video_id, 'video'),
            'privacy_status': response['status']['privacyStatus']
        })

    # Only videos from this repository can be uploaded by link.
    ALLOWED_URL_PREFIX = 'https://raw.githubusercontent.com/amahrous84/amahrous/'

    def upload_video_from_url(
        self,
        video_url: str,
        title: str,
        description: str = '',
        tags: list[str] = None,
        category_id: str = '28',
        privacy_status: str = 'private',
        made_for_kids: bool = False
    ) -> str:
        """
        Download a video from the amahrous84/amahrous GitHub repository and
        upload it to the signed-in user's channel.

        Args:
            video_url (str): A https://raw.githubusercontent.com/amahrous84/amahrous/... link to an .mp4 file.
            title (str): The video title (maximum 100 characters).
            description (str): The video description.
            tags (list[str]): Optional list of tags.
            category_id (str): YouTube category ID. Default is '28' (Science & Technology).
            privacy_status (str): 'private', 'unlisted', or 'public'. Default is 'private'.
            made_for_kids (bool): Whether the video is made for kids. Default is False.

        Returns:
            str: The new video's ID, link, and privacy status as JSON.
        """
        if not video_url.startswith(self.ALLOWED_URL_PREFIX) or not video_url.endswith('.mp4'):
            return f'Error: video_url must start with {self.ALLOWED_URL_PREFIX} and end with .mp4'

        fd, temp_path = tempfile.mkstemp(suffix='.mp4')
        try:
            with os.fdopen(fd, 'wb') as out, urllib.request.urlopen(video_url, timeout=120) as response:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            return self.upload_video(temp_path, title, description, tags,
                                     category_id, privacy_status, made_for_kids)
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def set_thumbnail_from_url(self, video_id: str, image_url: str) -> str:
        """
        Download a thumbnail image from the amahrous84/amahrous GitHub repository
        and set it as the custom thumbnail of one of the user's videos.

        Args:
            video_id (str): The video ID or URL.
            image_url (str): A https://raw.githubusercontent.com/amahrous84/amahrous/... link
                to a .jpg or .png file (1280x720 recommended, under 2 MB).

        Returns:
            str: The video ID and the new thumbnail's URL as JSON.
        """
        video_id = extract_video_id(video_id)
        if not video_id:
            return 'Error: Invalid video ID or URL.'
        if not image_url.startswith(self.ALLOWED_URL_PREFIX) or not image_url.lower().endswith(('.jpg', '.jpeg', '.png')):
            return f'Error: image_url must start with {self.ALLOWED_URL_PREFIX} and end with .jpg or .png'

        suffix = '.png' if image_url.lower().endswith('.png') else '.jpg'
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, 'wb') as out, urllib.request.urlopen(image_url, timeout=60) as response:
                out.write(response.read())
            media = MediaFileUpload(temp_path, mimetype='image/png' if suffix == '.png' else 'image/jpeg')
            result = self.service.thumbnails().set(videoId=video_id, media_body=media).execute()
            media.stream().close()
            url = result.get('items', [{}])[0].get('default', {}).get('url')
            return json.dumps({'video_id': video_id, 'thumbnail_url': url})
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
