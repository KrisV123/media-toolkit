import yt_dlp #type:ignore
from yt_dlp.postprocessor.embedthumbnail import EmbedThumbnailPP #type:ignore
from yt_dlp.postprocessor.common import PostProcessor #type:ignore
from yt_dlp.postprocessor.ffmpeg import FFmpegVideoConvertorPP #type:ignore

from typing import Any, cast
from collections.abc import Generator
from copy import deepcopy

from media_toolkit.type import DownloadInfo, FFMPEG_DIR, DENO_EXE
from media_toolkit.backend.services.youtube_base import YoutubeBase
from media_toolkit.backend.services.type import ROUND_ABR_TOLERANCE, YT_DLP_TUMBNAIL_SUPPORT
from media_toolkit.backend.yt_dlp_patch import _CURRENT_DOWNLOAD

class CappedVideoConvertorPP(FFmpegVideoConvertorPP):
    def __init__(self,
                 downloader=None,
                 preferedformat=None,
                 requested_abr: float | None = None):
        super().__init__(downloader, preferedformat)
        self._requested_abr = requested_abr
        self._abr_cap: float | None = requested_abr

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        abr = info.get('abr')
        if self._requested_abr is not None and abr:
            self._abr_cap = min(self._requested_abr, round(abr, 1))
        else:
            self._abr_cap = self._requested_abr
        return super().run(info)

    def _options(self, target_ext) -> Generator: #type:ignore
        yield from FFmpegVideoConvertorPP._options(False)
        if self._abr_cap is not None:
            yield from ('-b:a', f'{self._abr_cap}k')


class VideoDownloader(YoutubeBase):
    def __init__(self, download_info: DownloadInfo, id: int):
        super().__init__(download_info, id)
        self.audio_quality = int(download_info.audio_quality[:-5])
        self.video_quality = int(download_info.video_quality[:-1])
        self.options = {
            'format': self._create_format(),
            'ffmpeg_location': str(FFMPEG_DIR),
            'js_runtimes': {'deno': {'path': DENO_EXE}},
            'verbose': False,
            'writethumbnail': True,
            'noplaylist': not download_info.is_playlist,
            'outtmpl': self._create_download_path(),
            'progress_hooks': [self._progress_hook, self._stop_hook],
            'postprocessor_hooks': [self._stop_hook],
        }

    def _create_format(self):
        return f'bv[height<={self.video_quality}]+ba[abr<={self.audio_quality + ROUND_ABR_TOLERANCE}]/best'

    def download(self, info: dict[str, Any]) -> None:
        tok = _CURRENT_DOWNLOAD.set(self)
        try:
            with yt_dlp.YoutubeDL(self.options) as ytd: #type:ignore
                ytd.add_post_processor(
                    cast(PostProcessor, CappedVideoConvertorPP(ytd, self.format, self.audio_quality)),
                    when='post_process'
                )
                if self.format in YT_DLP_TUMBNAIL_SUPPORT:
                    ytd.add_post_processor(cast(PostProcessor, EmbedThumbnailPP(ytd)), when='post_process')
                ytd.process_ie_result(deepcopy(info), download=True) #type:ignore
        finally:
            _CURRENT_DOWNLOAD.reset(tok)
