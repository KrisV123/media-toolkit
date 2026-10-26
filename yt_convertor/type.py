from pathlib import Path
from dataclasses import dataclass
from platform import system

import win32com.shell.shell as shell #type:ignore
import win32com.shell.shellcon as shellcon #type:ignore

OS = system()

def get_downloads_folder() -> Path:
    match OS:
        case "Windows":
            downloads_dir = shell.SHGetKnownFolderPath(shellcon.FOLDERID_Downloads)
        case _:
            raise NotImplementedError(
                f'finding download folder on {OS} is not implemented'
            )

    return Path(downloads_dir)

DOWNLOAD_FOLDER = get_downloads_folder()

AUDIO_FORMATS = {'mp3', 'flac'}
VIDEO_FORMATS = {'mp4'}

FFMPEG_DIR = 'vendor/ffmpeg'
DENO_EXE = 'vendor/deno/deno-x86_64-pc-windows-msvc/deno.exe'

@dataclass
class DownloadInfo:
    link: str
    widget_name: str
    format: str
    is_playlist: bool
    audio_quality: str
    video_quality: str
