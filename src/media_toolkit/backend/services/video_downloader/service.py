import yt_dlp #type:ignore
from typing import Any
from copy import deepcopy

from media_toolkit.type import DownloadInfo, FFMPEG_DIR, DENO_EXE
from media_toolkit.backend.services.youtube_base.service import YoutubeBase

class VideoDownloader(YoutubeBase):
    compatible_audio: dict[str, list[str]] = {
        'mp4': ['m4a']
    }

    def __init__(self, download_info: DownloadInfo, id: int):
        super().__init__(download_info, id)
        self.audio_quality = int(download_info.audio_quality[:-5])
        self.video_quality = int(download_info.video_quality[:-1])

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
            'merge_output_format': self.format,
            'postprocessors': [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": self.format,
                },
                {'key': 'EmbedThumbnail'}
            ]
        }

    def _create_format(self) -> str:
        """create format param to options"""

        video_format = f'bv[height<={self.video_quality}][ext={self.format}]'
        audio_formats = [f'ba[abr<={self.audio_quality}][ext={ext}]' for ext in self.compatible_audio[self.format]]
        audio_format = '(' + '/'.join(audio_formats) + ')'
        final_format = ''.join((video_format, '+', audio_format, '/best'))
        return final_format

    # treba napravit ziskavanie infa
    @property
    def check_fallback(self) -> bool:
        info = self.get_download_info() #type:ignore
        tracks = info.get('requested_formats') or [info]

        video_over, audio_over = False, False
        for t in tracks:
            height = t.get('height')
            abr = t.get('abr')
            if height is not None and height > self.video_quality:
                video_over = True
            if abr is not None and abr > self.audio_quality:
                audio_over = True

        return video_over or audio_over

    def download(self, info: dict[str, Any]) -> None:
        """download video from url with current settings"""

        with yt_dlp.YoutubeDL(self.options) as ytd: #type:ignore
            ytd.process_ie_result(deepcopy(info), download=True) #type:ignore