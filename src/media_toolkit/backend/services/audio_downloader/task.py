from media_toolkit.type import DownloadInfo
from media_toolkit.backend.services.youtube_base import YoutubeBaseTask
from .service import AudioDownloader

class AudioDownloaderTask(YoutubeBaseTask[AudioDownloader]):
    def __init__(self, download_info: DownloadInfo, id: int):
        super().__init__(download_info, id, AudioDownloader)
