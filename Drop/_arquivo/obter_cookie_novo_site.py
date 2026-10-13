"""Compatibility entry point; authentication and scraping now run together."""

import asyncio

from wedrop_monitor_sistema import main


if __name__ == "__main__":
    asyncio.run(main())
