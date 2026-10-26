import yt_dlp #type:ignore
from typing import Any, cast
from urllib.parse import urlparse, parse_qs
from abc import ABC, abstractmethod

from yt_convertor.backend.services.type import ServiceError

from yt_convertor.type import DownloadInfo, DOWNLOAD_FOLDER
from yt_convertor.backend.services.type import StoppedService

class YoutubeBase(ABC):
    def __init__(self, download_info: DownloadInfo, id: int):
        self.url = download_info.link
        self.id = id
        self.format = download_info.format
        self.is_playlist = download_info.is_playlist
        self.progress_dict: dict[str, Any] = {}
        self.stop_event = False
        self.output_folder = DOWNLOAD_FOLDER / f'convertor_{self.id}'
        self.options: dict[str, Any] = {}

    def _create_download_path(self) -> str:
        """add download path based on playlist param"""

        if self.is_playlist:
            return str(
                self.output_folder / "%(playlist_title)s" / "%(title)s.%(ext)s"
            )
        else:
            return str(self.output_folder / "%(title)s.%(ext)s")

    def validate(self):
        """validate, if downloading object is in consistant state"""

        query = parse_qs(urlparse(self.url).query)
        has_list = 'list' in query
        has_video = 'v' in query or urlparse(self.url).netloc.endswith('youtu.be')

        if not self.is_playlist and not has_video:
            raise ServiceError('user wants single video but url is only playlist')
        if self.is_playlist and not has_list:
            raise ServiceError('want playlist but url is single video')

    def fetch_data(self) -> dict[str, Any]:
        options = self.options.copy()
        if self.is_playlist:
            options['extract_flat'] = 'in_playlist'
        with yt_dlp.YoutubeDL(options) as ytd: #type:ignore
            info = ytd.extract_info(self.url, download=False)
        return cast(dict[str, Any], info)

    def _progress_hook(self, d: dict[str, Any]) -> Any:
        self.progress_dict = d

    def _stop_hook(self, d: dict[str, Any]) -> Any:
        if self.stop_event:
            raise StoppedService()

    @abstractmethod
    def download(self, info: dict[str, Any]) -> None:
        """download audio from url with current settings"""
