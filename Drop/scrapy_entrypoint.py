"""Legacy entry point redirected to the integrated login-and-scrape flow."""

import asyncio

from wedrop_monitor_sistema import main


if __name__ == "__main__":
    asyncio.run(main())
