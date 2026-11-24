from pathlib import Path
import os
import subprocess

DENO_URL = 'https://deno.land/install.ps1'
DENO_PATH = Path('vendor/deno')

def install_deno() -> None:
    env = os.environ.copy()
    env["DENO_INSTALL"] = str(DENO_PATH.resolve())

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            f"irm {DENO_URL} | iex",
        ],
        env=env,
        check=True
    )

if __name__ == '__main__':
    install_deno()
