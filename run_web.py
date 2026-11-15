"""Convenience runner to start Hirthick's Vision Studio Web Application."""

import sys
import os
import webbrowser
import uvicorn
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    url = f"http://{host}:{port}"
    print("=" * 65)
    print("  HIRTHICK'S VISION STUDIO — Web Application & Pipeline Runner")
    print("=" * 65)
    print(f"  * Local Web Dashboard: {url}")
    print(f"  * ChatCut MCP Monitor: Live / Simulated Supported")
    print(f"  * Press Ctrl+C to stop the server")
    print("=" * 65)
    print()

    uvicorn.run("app.web.server:app", host=host, port=port, log_level="info")
