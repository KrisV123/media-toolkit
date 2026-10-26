from functools import cached_property

from yt_convertor.type import DownloadInfo
from .service import VideoDownloader
from yt_convertor.backend.services.youtube_base import YoutubeBaseTask

class VideoDownloaderTask(YoutubeBaseTask[VideoDownloader]):
    def __init__(self, download_info: DownloadInfo, id: int):
        super().__init__(download_info, id, VideoDownloader)

    @cached_property
    def fallback(self) -> bool:
        return self._service.check_fallback
