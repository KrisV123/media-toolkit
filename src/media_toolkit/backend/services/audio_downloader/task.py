from media_toolkit.type import DownloadInfo
from media_toolkit.backend.services.youtube_base import YoutubeBaseTask
from media_toolkit.backend.services.type import FALLBACK_ABR_TOLERANCE

from .service import AudioDownloader

class AudioDownloaderTask(YoutubeBaseTask[AudioDownloader]):
    def __init__(self, download_info: DownloadInfo, id: int):
        super().__init__(download_info, id, AudioDownloader)

    def check_fallback(self, pos: int | None) -> list[str] | None:
        service = self._service
        audio_quality = service.audio_quality
        video_data = service.params_by_pos.get(pos)
        if video_data is None:
            return None

        misses = []
        if video_data.abr is not None:
            abr_over_range = abs(video_data.abr - audio_quality) > FALLBACK_ABR_TOLERANCE
            if abr_over_range:
                misses.append(f'{round(video_data.abr, 1)} kbps')

        return None if len(misses) == 0 else misses
