import asyncio
import logging

from yt_convertor.frontend import YtConvertorApp
from yt_convertor.backend import TaskManager

logging.basicConfig(
    filename='debug.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)
LOGGER = logging.getLogger(__name__)

async def main():
    manager = TaskManager()
    manager.start()
    try:
        await YtConvertorApp().run_async()
    finally:
        await manager.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
