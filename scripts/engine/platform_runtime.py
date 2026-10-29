import contextlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading


def browser_path(playwright):
    path = Path(os.environ.get(
        'HUASHU_BROWSER_PATH', playwright.chromium.executable_path
    ))
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f'Preinstalled Chromium is missing or not executable: {path}')
    return str(path)


@contextlib.contextmanager
def chromium(playwright):
    browser = playwright.chromium.launch(
        executable_path=browser_path(playwright),
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    )
    try:
        yield browser
    finally:
        browser.close()


@contextlib.contextmanager
def serving(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@contextlib.contextmanager
def encoder(command):
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors)
        try:
            yield process.stdin
            process.stdin.close()
            code = process.wait()
        except BaseException as exc:
            if process.poll() is None:
                process.kill()
            process.wait()
            errors.seek(0)
            detail = errors.read().decode('utf-8', errors='replace').strip()
            try:
                process.stdin.close()
            except BrokenPipeError as close_error:
                detail += f'; stdin cleanup: {close_error}'
            if isinstance(exc, Exception):
                raise RuntimeError(
                    f'FFmpeg/render failed ({process.returncode}): {exc}; {detail}'
                ) from exc
            raise
        if code:
            errors.seek(0)
            raise RuntimeError(
                f'FFmpeg exited with {code}: '
                + errors.read().decode('utf-8', errors='replace')
            )


def preflight():
    missing = [name for name in ('playwright', 'numpy', 'PIL', 'cv2')
               if importlib.util.find_spec(name) is None]
    missing += [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        raise RuntimeError('Missing preinstalled dependencies: ' + ', '.join(missing))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        executable = browser_path(playwright)
    result = subprocess.run(
        ['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True,
        check=True,
    )
    names = {line.split()[1] for line in result.stdout.splitlines()
             if len(line.split()) >= 2}
    if not {'libx264', 'aac'} <= names:
        raise RuntimeError('FFmpeg requires libx264 and aac encoders')
    return {'status': 'ready', 'chromium': executable,
            'note': 'Dependency check only; render and QA are still required.'}


if __name__ == '__main__':
    try:
        print(json.dumps(preflight()))
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc)) from exc
