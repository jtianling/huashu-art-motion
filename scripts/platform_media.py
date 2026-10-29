import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import capabilities as c
import images

ROOT = Path(__file__).resolve().parent.parent
TOOLS = {'image': 'image_generate', 'voice': 'text_to_speech',
         'music': 'music_generate'}
AUDIO = {'.wav': 'wav', '.mp3': 'mp3', '.m4a': 'mov,mp4,m4a,3gp,3g2,mj2',
         '.ogg': 'ogg', '.flac': 'flac'}


def workspace_path(value, base):
    path = (base / value).resolve()
    if not path.is_relative_to(base.resolve()):
        raise c.ConfigError('Path must stay inside the current task workspace')
    if any(part.startswith('.env') for part in path.parts):
        raise c.ConfigError('Environment files are not media inputs')
    return path


def inspect_audio(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_streams', '-show_format',
         '-of', 'json', str(path)], capture_output=True, text=True,
    )
    if result.returncode:
        raise c.ConfigError('FFprobe failed: ' + result.stderr.strip())
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    if not streams or any(s.get('codec_type') != 'audio' for s in streams):
        raise c.ConfigError('Input must contain audio streams only')
    info = data.get('format', {})
    duration = float(info.get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise c.ConfigError('Audio duration must be finite and positive')
    if AUDIO.get(path.suffix.lower()) != info.get('format_name'):
        raise c.ConfigError('Audio extension must match the actual container')
    decoded = subprocess.run(
        ['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-map', '0:a',
         '-f', 'null', '-'], capture_output=True, text=True,
    )
    if decoded.returncode:
        raise c.ConfigError('Audio decode failed: ' + decoded.stderr.strip())
    return {'duration': duration, 'format': info['format_name']}


def ingest(args):
    workspace = Path.cwd().resolve()
    project = workspace_path(args.project, workspace)
    source = args.file
    provenance = 'provided_file'
    if args.receipt:
        receipt = c.read_json(workspace_path(args.receipt, workspace))
        c.validate(receipt, c.read_json(ROOT / 'schemas/platform-receipt.schema.json'))
        if receipt['tool'] != TOOLS[args.kind]:
            raise c.ConfigError('Receipt tool does not match the media kind')
        source, provenance = receipt['localPath'], 'agent_reported_tool_call'
    source = workspace_path(source, workspace)
    if not source.is_file():
        raise c.ConfigError('Media file does not exist: ' + str(source))
    out = workspace_path(args.out, project)
    meta = {'kind': args.kind, 'provenance': provenance,
            'generated': bool(args.receipt)}
    if args.kind == 'image':
        meta.update(images.inspect_image(source))
        if not meta['has_visible_pixels']:
            raise c.ConfigError('Image contains no visible pixels')
        return images.import_artifact(source, out, meta)
    payload = source.read_bytes()
    meta.update(inspect_audio(source), sha256=hashlib.sha256(payload).hexdigest())
    if out.suffix.lower() != source.suffix.lower():
        raise c.ConfigError('This importer does not transcode audio')
    sidecar = out.with_name(out.name + '.json')
    with c.locked(out):
        if out.exists() or sidecar.exists():
            raise c.ConfigError('Output or metadata already exists; use a new version')
        if source.read_bytes() != payload:
            raise c.ConfigError('Audio changed during validation')
        images.no_overwrite(out, payload)
        images.no_overwrite(sidecar, (json.dumps(meta, indent=2) + '\n').encode())
    return {'status': 'complete', 'output': str(out), 'metadata': str(sidecar),
            'sha256': meta['sha256']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=tuple(TOOLS), required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--file')
    source.add_argument('--receipt')
    parser.add_argument('--project', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(ingest(args), ensure_ascii=False))
    except (c.ConfigError, OSError, ValueError, TypeError,
            subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == '__main__':
    main()
