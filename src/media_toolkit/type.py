from pathlib import Path
from dataclasses import dataclass
from platform import system

import win32com.shell.shell as shell #type:ignore
import win32com.shell.shellcon as shellcon #type:ignore

def get_downloads_folder() -> Path:
    match OS:
        case "Windows":
            downloads_dir = shell.SHGetKnownFolderPath(shellcon.FOLDERID_Downloads)
        case _:
            raise NotImplementedError(
                f'finding download folder on {OS} is not implemented'
            )

    return Path(downloads_dir)

def find_ffmpeg_dir() -> Path:
    """returns first found folder, that contains every ffmpeg tool"""

    for directory in Path('vendor/ffmpeg').iterdir():
        bin = directory / 'bin'
        if bin.is_dir():
            tools = ('ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe')
            if all((bin / tool).is_file() for tool in tools):
                return bin

    raise SystemError('ffmpeg dir with all tools not found')

OS = system()
DOWNLOAD_FOLDER = get_downloads_folder()

AUDIO_FORMATS = frozenset(('mp3', 'flac', 'opus', 'wav', 'm4a'))
VIDEO_FORMATS = frozenset(('mp4', 'mkv', 'webm', 'mov'))

FFMPEG_DIR = str(find_ffmpeg_dir())
DENO_EXE = 'vendor/deno/bin/deno.exe'

@dataclass
class DownloadInfo:
    link: str
    widget_name: str
    format: str
    is_playlist: bool
    audio_quality: int
    video_quality: int
