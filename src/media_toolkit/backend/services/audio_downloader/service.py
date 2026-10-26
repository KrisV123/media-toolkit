import yt_dlp #type:ignore
from typing import Any
from copy import deepcopy

from media_toolkit.type import DownloadInfo, FFMPEG_DIR, DENO_EXE
from media_toolkit.backend.services.youtube_base.service import YoutubeBase

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
            'postprocessor_hooks': [self._progress_hook, self._stop_hook],
        }

    def _create_format(self) -> str:
        """create format param to options"""

        return f'ba[abr<={self.audio_quality}]/ba'

    def _add_postprocessing(self, info: dict[str, Any]) -> None:
        """update postprocessing options, if format or audio_quality does not match"""

        extract_audio = {
            "key": 'FFmpegExtractAudio',
            "preferredcodec": self.format,
            "preferredquality": str(self.audio_quality),
        }

        self.options['postprocessors'] = []
        if self.is_playlist:
            self.options['postprocessors'].append(extract_audio)
        else:
            abr = info.get('abr')
            ext = info.get('ext')
            if abr is None or abr > self.audio_quality or ext != self.format:
                self.options['postprocessors'].append(extract_audio)

        self.options['postprocessors'].append({'key': 'EmbedThumbnail'})

    def download(self, info: dict[str, Any]) -> None:
        """download audio from url with current settings"""

        self._add_postprocessing(info)

        with yt_dlp.YoutubeDL(self.options) as ytd: #type:ignore
            ytd.process_ie_result(deepcopy(info), download=True) #type:ignore
