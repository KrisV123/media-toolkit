import yt_dlp #type:ignore
from typing import Any, cast
from urllib.parse import urlparse, parse_qs
from abc import ABC, abstractmethod
from dataclasses import dataclass

from media_toolkit.backend.services.type import StoppedService, ServiceError
from media_toolkit.type import DownloadInfo, DOWNLOAD_FOLDER

@dataclass(slots=True)
class DownloadParams:
    abr: float | None = None
    height: int | None = None


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

        self.params_by_pos: dict[int | None, DownloadParams] = {}
        "None for single video"

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

    def _collect_video_params(self, info: dict[str, Any]) -> None:
        """
        hook method to yt_dlp downloading,
        that takes update dict and setup current video metadata
        """

        abr, height = info.get('abr'), info.get('height')
        pos = info.get('playlist_autonumber') or None
        params = self.params_by_pos.setdefault(pos, DownloadParams())
        if abr:
            params.abr = abr
        if height:
            params.height = height

    def _progress_hook(self, d: dict[str, Any]) -> None:
        self.progress_dict = d
        info = d.get('info_dict') or {}
        self._collect_video_params(info)

    def _postprocessor_hook(self, d: dict[str, Any]) -> None:
        self.progress_dict = d

    def _stop_hook(self, d: dict[str, Any]) -> Any:
        if self.stop_event:
            raise StoppedService()

    @abstractmethod
    def download(self, info: dict[str, Any]) -> None:
        """download audio from url with current settings"""
