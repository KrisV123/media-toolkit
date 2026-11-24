import requests
import platform

from zipfile import ZipFile
from pathlib import Path

WINDOWS_ARM_FFMPEG_URL = 'https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-winarm64-gpl-9.0.zip'
WINDOWS_X86_FFMPEG_URL = 'https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-win64-gpl-9.0.zip'
FFMPEG_DIR = Path('vendor/ffmpeg')

def validate() -> str:
    if platform.system() != 'Windows':
        raise SystemError('Windows is required')

    machine = platform.machine().lower()
    if machine in ('amd64', 'x86_64'):
        return WINDOWS_X86_FFMPEG_URL
    elif machine in ('arm64', 'aarch64'):
        return WINDOWS_ARM_FFMPEG_URL
    else:
        raise SystemError('Unsupported architecture: {machine}')

def install_ffmpeg_tools():
    URL = validate()

    with requests.get(URL, stream=True) as response:
        response.raise_for_status()
        FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
        archive_path = Path(FFMPEG_DIR / 'archive.zip')

        with open(archive_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        with ZipFile(archive_path) as archive:
            archive.extractall(FFMPEG_DIR)

        archive_path.unlink()

if __name__ == '__main__':
    install_ffmpeg_tools()
