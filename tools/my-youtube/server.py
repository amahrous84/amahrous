"""
MCP server that lets Claude use the YouTube tools in tools/google/youtube_tools.py.

Claude starts this file itself (see the "my-youtube" entry in
claude_desktop_config.json). You do not need to run it by hand.
"""
import contextlib
import os
import sys

# The server class was renamed in version 2 of the mcp library.
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET = os.path.join(BASE_DIR, 'client_secret.json')

# Make "tools" importable no matter which folder Claude starts this from.
sys.path.insert(0, BASE_DIR)

from tools.google.youtube_tools import YouTubeTool  # noqa: E402

mcp = MCPServer('my-youtube')

# An MCP server talks to Claude over standard output, so anything else
# printed there breaks the connection. Send it to stderr while signing in.
with contextlib.redirect_stdout(sys.stderr):
    youtube = YouTubeTool(CLIENT_SECRET)

# Each function becomes a tool. Claude reads the function's docstring
# to learn what it does and which arguments it takes.
for function in (
    youtube.search_videos,
    youtube.search_channel,
    youtube.search_playlist,
    youtube.get_channel_info,
    youtube.get_video_info,
    youtube.get_channel_videos,
    youtube.get_my_channel_info,
    youtube.get_my_channel_analytics,
    youtube.upload_video,
    youtube.upload_video_from_url,
    youtube.set_thumbnail_from_url,
):
    mcp.add_tool(function)


if __name__ == '__main__':
    mcp.run()