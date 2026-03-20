import asyncio
import re
from typing import TypeVar, TypedDict, Any, Awaitable, List, Dict

from fastmcp import FastMCP  # type: ignore
from youtube_transcript_api import YouTubeTranscriptApi

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
