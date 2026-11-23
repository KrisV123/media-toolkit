from yt_dlp.utils import Popen as YtPopen #type:ignore

from contextvars import ContextVar
from .services.youtube_base import YoutubeBase

_CURRENT_DOWNLOAD: ContextVar[YoutubeBase | None] = ContextVar('process_inst', default=None)
_DEFAULT_INIT = YtPopen.__init__

def _ctm_ytpopen_init(self: YtPopen, *args, **kwargs) -> None:
    """
    wrapper around yt_dlp custom popen, that saves
    running processes into downloader instance
    """

    _DEFAULT_INIT(self, *args, **kwargs)
    owner = _CURRENT_DOWNLOAD.get()
    if owner:
        _register_process(owner, self)

def _register_process(owner: YoutubeBase, process: YtPopen) -> None:
    with owner.lock:
        if owner:
            owner.ffmpeg_processes.add(process)
    if owner.stop_event:
        process.kill()

def install_yt_dlp_patch() -> None:
    """
    changes defaulit yt_dlp Popen __init__ function with custom,
    that saves references of running tasks into current running downloader.
    This operation atomicity is on thread level.
    """

    YtPopen.__init__ = _ctm_ytpopen_init

def uninstall_yt_dlp_patch() -> None:
    """sets default yt_dlp popen operation"""

    YtPopen.__init__ = _DEFAULT_INIT
