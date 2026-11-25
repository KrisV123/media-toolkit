import requests
import platform

from zipfile import ZipFile
from pathlib import Path

WINDOWS_ARM_FFMPEG_URL = 'https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-winarm64-gpl-9.0.zip'
WINDOWS_X86_FFMPEG_URL = 'https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-win64-gpl-9.0.zip'
FFMPEG_DIR = Path('vendor/ffmpeg')

def validate_platform() -> str:
    if platform.system() != 'Windows':
        raise RuntimeError('Windows is required')

    machine = platform.machine().lower()
    if machine in ('amd64', 'x86_64'):
        return WINDOWS_X86_FFMPEG_URL
    elif machine in ('arm64', 'aarch64'):
        return WINDOWS_ARM_FFMPEG_URL
    else:
        raise RuntimeError(f'Unsupported architecture: {machine}')

def ffmpeg_exist() -> bool:
    if not FFMPEG_DIR.is_dir():
        return False

    for directory in FFMPEG_DIR.iterdir():
        bin = directory / 'bin'
        if bin.is_dir():
            tools = ('ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe')
            if all((bin / tool).is_file() for tool in tools):
                return True

    return False

def safe_unzip(destination: Path, archive_path: Path) -> None:
    destination = destination.resolve()

    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()

            if not target.is_relative_to(destination):
                raise RuntimeError(f'Unsafe path in zipfile: {member.filename}')

        archive.extractall(destination)

def install_ffmpeg_tools() -> None:
    URL = validate_platform()
    if ffmpeg_exist():
        return

    with requests.get(URL, stream=True, timeout=(10, 60)) as response:
        response.raise_for_status()
        FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
        archive_path = Path(FFMPEG_DIR / 'archive.zip')

        with open(archive_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        try:
            safe_unzip(FFMPEG_DIR, archive_path)
        finally:
            archive_path.unlink(missing_ok=True)

    if not ffmpeg_exist():
        raise RuntimeError(
            "ffmpeg installation process was executed, but ffmpeg tools weren't found"
        )

if __name__ == '__main__':
    install_ffmpeg_tools()
