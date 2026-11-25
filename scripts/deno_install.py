from pathlib import Path
import os
import subprocess

DENO_URL = 'https://deno.land/install.ps1'
DENO_PATH = Path('vendor/deno')

def deno_exist() -> bool:
    return (DENO_PATH / 'bin' / 'deno.exe').is_file()

def install_deno() -> None:
    if deno_exist():
        return

    env = os.environ.copy()
    env["DENO_INSTALL"] = str(DENO_PATH.resolve())

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            f"irm {DENO_URL} | iex",
        ],
        env=env,
        check=True
    )

    if not deno_exist():
        raise RuntimeError(
            "Deno installation process was executed, but Deno wasn't found"
        )

if __name__ == '__main__':
    install_deno()
