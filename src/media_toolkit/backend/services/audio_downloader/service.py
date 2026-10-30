import yt_dlp #type:ignore
from yt_dlp.postprocessor.ffmpeg import FFmpegExtractAudioPP #type:ignore
from yt_dlp.postprocessor.embedthumbnail import EmbedThumbnailPP #type:ignore
from yt_dlp.postprocessor.common import PostProcessor #type:ignore

from typing import Any, cast
from copy import deepcopy

from media_toolkit.type import DownloadInfo, FFMPEG_DIR, DENO_EXE
from media_toolkit.backend.services.youtube_base import YoutubeBase
from media_toolkit.backend.services.type import ROUND_ABR_TOLERANCE

class CappedExtractAudioPP(FFmpegExtractAudioPP):
    def __init__(self,
                 downloader: Any = None,
                 preferredcodec: str | None = None,
                 preferredquality: str | None = None,
                 nopostoverwrites: bool = False):
        super().__init__(downloader, preferredcodec, preferredquality, nopostoverwrites)
        self._requested_quality: float | None = self._preferredquality

    def run(self, information: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        abr = information.get('abr')
        request_abr = self._requested_quality

        if request_abr is not None and abr:
            self._preferredquality = min(request_abr, round(abr, 1))
        else:
            self._preferredquality = request_abr

        return super().run(information)


class AudioDownloader(YoutubeBase):
    def __init__(self, download_info: DownloadInfo, id: int):
        super().__init__(download_info, id)
        self.audio_quality = int(download_info.audio_quality[:-5])

        self.options: dict[str, Any] = {
            'format': self._create_format(),
            'ffmpeg_location': str(FFMPEG_DIR),
            'js_runtimes': {'deno': {'path': DENO_EXE}},
            'verbose': False,
            'writethumbnail': True,
            'noplaylist': not download_info.is_playlist,
            'outtmpl': self._create_download_path(),
            'progress_hooks': [self._progress_hook, self._stop_hook],
            'postprocessor_hooks': [self._postprocessor_hook, self._stop_hook],
        }

    def _create_format(self) -> str:
        """create format param to options"""

        return f'ba[abr<={self.audio_quality + ROUND_ABR_TOLERANCE}]/ba'

    def download(self, info: dict[str, Any]) -> None:
        """download audio from url with current settings"""

        with yt_dlp.YoutubeDL(self.options) as ytd: #type:ignore
            ytd.add_post_processor(
                cast(
                    PostProcessor,
                    CappedExtractAudioPP(
                        ytd,
                        preferredcodec=self.format,
                        preferredquality=str(self.audio_quality),
                    )
                ),
                when='post_process',
            )
            ytd.add_post_processor(cast(PostProcessor, EmbedThumbnailPP(ytd)), when='post_process')
            ytd.process_ie_result(deepcopy(info), download=True) #type:ignore
