import asyncio
import os
import re
from dotenv import load_dotenv
from typing import TypeVar, TypedDict, Any, Awaitable, List, Dict

from fastmcp import FastMCP  # type: ignore
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
from youtube_transcript_api import YouTubeTranscriptApi

# ...
import os
from dotenv import load_dotenv

# Ensure .env is loaded from the directory of this file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
T = TypeVar("T")
E = TypeVar("E", bound=Exception)


def extract_video_id(input_str: str) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, input_str)
        if match:
            return match.group(1)
    if re.match(r"^[a-zA-Z0-9_-]{11}$", input_str):
        return input_str
    return None


class Success(TypedDict):
    data: T
    error: None


class Failure(TypedDict):
    data: None
    error: E


Result = Success | Failure


async def tryCatch(promise: Awaitable[T]) -> Result:
    try:
        data = await promise
        return {"data": data, "error": None}
    except Exception as error:
        return {"data": None, "error": error}


youtube_mcp = FastMCP("youtube-mcp")


def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing YOUTUBE_API_KEY environment variable required for YouTube Data API"
        )
    # The discovery client is not async-friendly; keep usage in threads.
    return build("youtube", "v3", developerKey=api_key)


def list_channel_videos_sync(channel_name: str, max_results: int = 200):
    client = get_youtube_client()

    search_response = (
        client.search()
        .list(q=channel_name, type="channel", part="id,snippet", maxResults=1)
        .execute()
    )

    items = search_response.get("items", [])
    if not items:
        return []

    channel_id = items[0]["id"]["channelId"]

    channel_info = (
        client.channels().list(id=channel_id, part="contentDetails,snippet").execute()
    )

    uploads_playlist = (
        channel_info.get("items", [])[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )

    if not uploads_playlist:
        return []

    videos: List[Dict[str, str]] = []
    next_page_token: str | None = None

    while True:
        playlist_response = (
            client.playlistItems()
            .list(
                playlistId=uploads_playlist,
                part="snippet,contentDetails",
                maxResults=50,
                pageToken=next_page_token,
            )
            .execute()
        )

        for item in playlist_response.get("items", []):
            snippet = item.get("snippet", {})
            video_id = snippet.get("resourceId", {}).get("videoId")
            if not video_id:
                continue
            videos.append(
                {
                    "title": snippet.get("title", "Untitled"),
                    "videoId": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "publishedAt": snippet.get("publishedAt", ""),
                }
            )

        next_page_token = playlist_response.get("nextPageToken")
        if not next_page_token or len(videos) >= max_results:
            break

    return videos[:max_results]


@youtube_mcp.tool()
async def list_channel_videos(channel_name: str, max_results: int = 200) -> str:
    """
    Lists recent videos on a YouTube channel by channel display name.

    Example:
    - \"Kurzgesagt – In a Nutshell\"
    - \"Marques Brownlee\"
    """

    async def runner():
        return await asyncio.to_thread(
            list_channel_videos_sync, channel_name, max_results
        )

    result = await tryCatch(runner())

    if result["error"] is not None:
        err = result["error"]
        if isinstance(err, RuntimeError) and "YOUTUBE_API_KEY" in str(err):
            return (
                "Set the YOUTUBE_API_KEY environment variable with a YouTube Data API v3 key "
                "and try again."
            )
        if isinstance(err, HttpError):
            status = getattr(err.resp, "status", "unknown")
            return f"Failed to fetch channel videos (HTTP {status}): {err}"
        return f"Failed to fetch channel videos: {err}"

    videos = result["data"]
    if not videos:
        return f"No videos found for channel '{channel_name}'."

    lines = [
        f"{idx + 1}. {video['title']} ({video['publishedAt']}) - {video['url']}"
        for idx, video in enumerate(videos)
    ]
    return "\n".join(lines)


def fetch_transcript_sync(video_id: str) -> List[Dict[str, Any]]:
    transcript = YouTubeTranscriptApi().fetch(video_id)
    return [{"start": entry.start, "text": entry.text} for entry in transcript]


@youtube_mcp.tool()
async def get_full_transcript(video_id_or_url: str) -> str:
    """
    Retrieves the complete transcript for a YouTube video.
    Ideal for summarizing long dev tutorials or tech keynotes.

    Accepts a video ID, watch URL, or share URL (youtu.be).
    Examples:
    - "dQw4w9WgXcQ"
    - "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    - "https://youtu.be/dQw4w9WgXcQ"
    """
    video_id = extract_video_id(video_id_or_url)
    if not video_id:
        return f"Invalid YouTube URL or video ID: {video_id_or_url}"

    promise = asyncio.to_thread(fetch_transcript_sync, video_id)
    result = await tryCatch(promise)

    if result["error"] is not None:
        return f"Failed to retrieve transcript: {str(result['error'])}"

    transcript_data = result["data"]

    formatted_text = []
    for entry in transcript_data:  # type: ignore
        start_time = round(entry["start"], 2)
        formatted_text.append(f"[{start_time}s]: {entry['text']}")

    return "\n".join(formatted_text)


@youtube_mcp.tool()
async def search_transcript(video_id_or_url: str, keyword: str) -> str:
    """
    Searches a YouTube video's transcript for a specific keyword or phrase.
    Returns the exact quotes and their timestamps for specific data extraction.

    Accepts a video ID, watch URL, or share URL (youtu.be).
    Examples:
    - "dQw4w9WgXcQ"
    - "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    - "https://youtu.be/dQw4w9WgXcQ"
    """
    video_id = extract_video_id(video_id_or_url)
    if not video_id:
        return f"Invalid YouTube URL or video ID: {video_id_or_url}"

    promise = asyncio.to_thread(fetch_transcript_sync, video_id)
    result = await tryCatch(promise)

    if result["error"] is not None:
        return f"Failed to retrieve transcript: {str(result['error'])}"

    transcript_data = result["data"]
    matches = []

    for entry in transcript_data:  # type: ignore
        if keyword.lower() in entry["text"].lower():
            start_time = round(entry["start"], 2)
            matches.append(f"[{start_time}s]: {entry['text']}")

    if not matches:
        return f"No results found for '{keyword}' in this video."

    return "\n".join(matches)


def main():
    youtube_mcp.run()


if __name__ == "__main__":
    main()
