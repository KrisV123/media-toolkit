import asyncio
import logging

from media_toolkit.frontend import YtConvertorApp
from media_toolkit.backend import TaskManager
from media_toolkit.backend.yt_dlp_patch import install_yt_dlp_patch

logging.basicConfig(
    filename='debug.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)
LOGGER = logging.getLogger(__name__)

async def main():
    install_yt_dlp_patch()
    manager = TaskManager()
    manager.start()
    try:
        await YtConvertorApp().run_async()
    finally:
        await manager.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
