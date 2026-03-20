# YouTube MCP Server

MCP server for retrieving YouTube video transcripts with timestamps.

## Features

- **Full Transcripts** - Get complete video transcripts with timestamps
- **Keyword Search** - Search transcripts for specific terms with timestamp references
- **URL Support** - Accepts video IDs, watch URLs, or share URLs (youtu.be)

## Tools

### `get_full_transcript`

Retrieves the complete transcript for a YouTube video.

```python
get_full_transcript(video_id_or_url: str) -> str
```

**Parameters:**
- `video_id_or_url` - Video ID, watch URL, or share URL

**Examples:**
- `dQw4w9WgXcQ`
- `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- `https://youtu.be/dQw4w9WgXcQ`

**Output format:**
```
[0.0s]: Welcome to this tutorial
[5.32s]: Today we'll be covering...
[12.1s]: Let me show you how to...
```

### `search_transcript`

Searches a video's transcript for a keyword or phrase.

```python
search_transcript(video_id_or_url: str, keyword: str) -> str
```

**Parameters:**
- `video_id_or_url` - Video ID, watch URL, or share URL
- `keyword` - Search term (case-insensitive)

## Installation

```bash
cd youtube-mcp
uv sync
```

## Usage

### Run directly

```bash
uv run python main.py
```

### Configure in OpenCode

Add to your OpenCode config (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "youtube-mcp": {
      "type": "local",
      "command": ["uv", "run", "/path/to/youtube-mcp/main.py"],
      "enabled": true
    }
  }
}
```

### Configure in Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `~/.config/Claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "youtube-mcp": {
      "command": "uv",
      "args": ["run", "/path/to/youtube-mcp/main.py"]
    }
  }
}
```

## Use Cases

- **Summarize** long dev tutorials or tech talks
- **Extract** specific data points with timestamps
- **Cross-reference** topics across multiple videos
- **Chat with videos** by providing full context to an LLM
