"""Compatibility entry point for the integrated WeDrop monitor."""

import asyncio

from wedrop_monitor_sistema import main


if __name__ == "__main__":
    asyncio.run(main())
