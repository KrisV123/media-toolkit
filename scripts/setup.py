import subprocess

from .deno_install import install_deno
from .fmmpeg_install import install_ffmpeg_tools

def setup() -> None:
    print('INSTALLING DENO')
    install_deno()
    print('DENO INSTALLED')

    print('INSTALLING FFMPEG TOOLS')
    install_ffmpeg_tools()
    print('FFMPED TOOLS INSTALLED')

    print('INSTALLING EXTERNAL PACKAGES')
    subprocess.run(['uv', 'sync'], check=True)
    print('PACKAGES INSTALLED')

if __name__ == '__main__':
    setup()
