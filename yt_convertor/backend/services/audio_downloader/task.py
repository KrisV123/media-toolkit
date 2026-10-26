from yt_convertor.type import DownloadInfo
from yt_convertor.backend.services.youtube_base import YoutubeBaseTask
from .service import AudioDownloader

class AudioDownloaderTask(YoutubeBaseTask[AudioDownloader]):
    def __init__(self, download_info: DownloadInfo, id: int):
        super().__init__(download_info, id, AudioDownloader)
