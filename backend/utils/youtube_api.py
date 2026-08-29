import os
import urllib.parse
import urllib.request
import json
import logging

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')


def search_youtube_videos(query, max_results=3):
    """
    Searches for YouTube videos matching the given query.
    If API key is unavailable or fails, returns curated search query results.
    """
    clean_query = urllib.parse.quote(query)
    fallback_url = f"https://www.youtube.com/results?search_query={clean_query}"

    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == 'your_youtube_api_key_here':
        return [
            {
                'title': f'{query} Crash Course & Tutorial',
                'url': fallback_url,
                'channel': 'YouTube Educational Search',
                'thumbnail': 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=300&auto=format&fit=crop&q=60'
            }
        ]

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults={max_results}&q={clean_query}&type=video&key={YOUTUBE_API_KEY}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SkillBridge-App'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode('utf-8'))
            items = data.get('items', [])
            results = []
            for item in items:
                video_id = item['id'].get('videoId')
                snippet = item.get('snippet', {})
                results.append({
                    'title': snippet.get('title', query),
                    'url': f"https://www.youtube.com/watch?v={video_id}" if video_id else fallback_url,
                    'channel': snippet.get('channelTitle', 'YouTube Tutorial'),
                    'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', '')
                })
            return results if results else [{'title': query, 'url': fallback_url, 'channel': 'YouTube', 'thumbnail': ''}]
    except Exception as e:
        logging.warning(f"YouTube API call failed: {e}")
        return [{
            'title': f'{query} Full Tutorial',
            'url': fallback_url,
            'channel': 'YouTube Search',
            'thumbnail': ''
        }]
