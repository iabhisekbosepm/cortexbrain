"""Allow running the MCP server via: python -m cortexbrain.mcp

Transport is controlled by MCP_TRANSPORT env var:
  - "stdio" (default) — for local Claude Code CLI (subprocess)
  - "sse"             — for Docker / remote access over HTTP
"""

import os

from cortexbrain.mcp.server import mcp

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
