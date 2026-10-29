import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
OUT = Path.cwd() / 'evidence'


def run(name, command, expected=0, env=None):
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=360, env=env)
    (OUT / (name + '.txt')).write_text(result.stdout + result.stderr)
    if result.returncode != expected:
        raise RuntimeError(f'{name}: exit {result.returncode}; see {name}.txt')
    return result


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format',
        '-of', 'json', str(path),
    ], text=True))


def main():
    OUT.mkdir()
    engine = OUT / 'engine'
    shutil.copytree(REPO / 'scripts/engine', engine)
    data = json.loads((engine / 'examples/t3_finance_chart.json').read_text())
    data.update(width=960, height=540, fps=12)
    data['data']['title'] = '平台动画中文测试'
    data['data']['source'] = '测试数据, 不构成财务资料'
    spec = OUT / 'clip.json'
    spec.write_text(json.dumps(data, ensure_ascii=False))
    run('preflight', [sys.executable, str(engine / 'platform_runtime.py')])
    audio = OUT / 'tone.wav'
    run('tone', ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                 'sine=frequency=440:sample_rate=24000:duration=7', str(audio)])
    video = OUT / 'clip.mp4'
    run('render', [sys.executable, str(engine / 'render.py'), '--spec', str(spec),
                   '--out', str(video), '--audio', str(audio)])
    run('stills', [sys.executable, str(engine / 'render.py'), '--spec', str(spec),
                   '--stills', '1,3,5', '--out', str(OUT / 'frames')])
    run('scene', [sys.executable, str(engine / 'render.py'), '--solo', '09_postimp',
                  '--stills', '0.3', '--out', str(OUT / 'scene')])
    run('qa', [sys.executable, str(REPO / 'scripts/qa.py'), '--spec', str(spec),
               '--fps', '12', '--out', str(OUT / 'qa')])
    run('deliver', [sys.executable, str(REPO / 'scripts/deliver.py'), str(video),
                    '--root', str(OUT), '--qa', str(OUT / 'qa'),
                    '--out', str(OUT / 'output')])
    summary = probe(video)
    streams = {stream['codec_type']: stream for stream in summary['streams']}
    assert streams['video']['codec_name'] == 'h264'
    assert streams['audio']['codec_name'] == 'aac'
    for kind in ('video', 'audio'):
        assert abs(float(streams[kind]['duration']) - 7) < .1, streams[kind]
    signal = run('audio-signal', [
        'ffmpeg', '-hide_banner', '-i', str(video), '-vn',
        '-af', 'astats=metadata=0:reset=0', '-f', 'null', '-',
    ])
    assert 'RMS level dB: -inf' not in signal.stderr
    assert 'RMS level dB:' in signal.stderr
    run('extract-pcm', ['ffmpeg', '-v', 'error', '-i', str(video), '-vn',
                        '-ar', '24000', '-ac', '1', '-f', 's16le',
                        str(OUT / 'signal.pcm')])
    import numpy as np
    samples = np.frombuffer((OUT / 'signal.pcm').read_bytes(), dtype='<i2')
    assert abs(len(samples) / 24000 - 7) < .1
    frequency = np.argmax(abs(np.fft.rfft(samples))) * 24000 / len(samples)
    assert abs(frequency - 440) < 1, frequency
    run('verify-delivery', [sys.executable, str(REPO / 'scripts/deliver.py'),
                            '--verify', str(OUT / 'output/交付说明.md')])
    fakebin = OUT / 'fakebin'
    fakebin.mkdir()
    fake = fakebin / 'ffmpeg'
    fake.write_text(f'#!{sys.executable}\nimport sys\n'
                    'sys.stdin.buffer.read()\n'
                    'sys.stderr.write("fixture encoder exit 17")\nsys.exit(17)\n')
    fake.chmod(0o755)
    failure = run('encoder-failure', [
        sys.executable, str(engine / 'render.py'), '--spec', str(spec),
        '--out', str(OUT / 'must-not-succeed.mp4'),
    ], expected=1, env={**os.environ, 'PATH': str(fakebin) + ':' + os.environ['PATH']})
    assert 'fixture encoder exit 17' in failure.stderr
    assert 'done ->' not in failure.stdout
    (OUT / 'verification.json').write_text(json.dumps({
        'scope': 'Local offline render/QA/delivery; no platform model or media call',
        'video': summary, 'decoded_audio_seconds': len(samples) / 24000,
        'dominant_frequency_hz': frequency,
        'video_sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
        'independent_film_review': False,
    }, ensure_ascii=False, indent=2))
    print('PASS: render, scene, QA, delivery, H264/AAC duration and decoded signal')


if __name__ == '__main__':
    main()
