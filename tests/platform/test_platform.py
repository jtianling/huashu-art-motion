import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import wave

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / 'scripts'
spec = importlib.util.spec_from_file_location(
    'platform_runtime', SCRIPTS / 'engine/platform_runtime.py'
)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        Image.new('RGB', (64, 64), '#b64b32').save(self.work / 'input.png')
        with wave.open(str(self.work / 'input.wav'), 'wb') as audio:
            audio.setparams((1, 2, 24000, 0, 'NONE', 'NONE'))
            audio.writeframes(b''.join(
                struct.pack('<h', round(5000 * math.sin(2 * math.pi * 440 * i / 24000)))
                for i in range(48000)
            ))

    def run_script(self, script, *args, code=0, env=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *map(str, args)],
            cwd=self.work, env=env, capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def ingest(self, kind, source, out, code=0):
        return self.run_script(
            'platform_media.py', '--kind', kind, '--file', source,
            '--project', 'project', '--out', out, code=code,
        )

    def test_real_image_and_audio(self):
        self.ingest('image', 'input.png', 'image.png')
        self.ingest('voice', 'input.wav', 'voice.wav')
        meta = json.loads((self.work / 'project/voice.wav.json').read_text())
        self.assertEqual(meta['duration'], 2)
        self.assertFalse(meta['generated'])
        self.assertEqual((self.work / 'project/voice.wav').read_bytes(),
                         (self.work / 'input.wav').read_bytes())
        self.ingest('voice', 'input.wav', 'voice.wav', code=2)

    def test_normalized_tool_receipt(self):
        receipt = self.work / 'receipt.json'
        receipt.write_text(json.dumps({
            'status': 'success', 'tool': 'text_to_speech', 'localPath': 'input.wav',
        }))
        self.run_script(
            'platform_media.py', '--kind', 'voice', '--receipt', receipt,
            '--project', 'project', '--out', 'voice.wav',
        )
        meta = json.loads((self.work / 'project/voice.wav.json').read_text())
        self.assertEqual(meta['provenance'], 'agent_reported_tool_call')
        self.assertTrue(meta['generated'])

    def test_bad_receipts(self):
        for patch in ({'status': 'pending'}, {'tool': 'audio_generate'},
                      {'localPath': ''}, {'unexpected': True},
                      {'tool': 'image_generate'}):
            receipt = self.work / 'receipt.json'
            receipt.write_text(json.dumps({
                'status': 'success', 'tool': 'text_to_speech',
                'localPath': 'input.wav', **patch,
            }))
            self.run_script(
                'platform_media.py', '--kind', 'voice', '--receipt', receipt,
                '--project', 'project', '--out', 'bad.wav', code=2,
            )
        self.assertFalse((self.work / 'project/bad.wav').exists())

    def test_workspace_and_formats(self):
        self.ingest('image', 'input.png', '../../escape.png', code=2)
        self.ingest('image', 'input.png', 'wrong.jpg', code=2)
        self.ingest('voice', 'input.wav', 'wrong.mp3', code=2)
        self.ingest('voice', 'input.png', 'wrong.png', code=2)
        self.ingest('image', '.env', 'environment.png', code=2)
        (self.work / 'outside.png').symlink_to(self.work.parent / 'nonexistent')
        self.ingest('image', 'outside.png', 'escape.png', code=2)
        Image.new('RGBA', (4, 4), (0, 0, 0, 0)).save(self.work / 'clear.png')
        self.ingest('image', 'clear.png', 'clear.png', code=2)

    def test_legacy_cli_does_not_read_configuration(self):
        for script in ('capabilities.py', 'koubo.py', 'images.py'):
            result = self.run_script(script, '--help', code=1)
            self.assertIn('Legacy media CLI is disabled', result.stderr)

    def test_missing_browser_does_not_download(self):
        result = self.run_script(
            'engine/platform_runtime.py', code=1,
            env={**os.environ, 'HUASHU_BROWSER_PATH': '/nonexistent/chromium'},
        )
        self.assertIn('Preinstalled Chromium is missing', result.stderr)
        self.assertNotIn('Downloading', result.stdout + result.stderr)

    def test_encoder_failure_contains_stderr(self):
        command = [sys.executable, '-c',
                   'import sys; sys.stdin.buffer.read(); '
                   'sys.stderr.write("fixture encoder failure"); sys.exit(19)']
        with self.assertRaisesRegex(RuntimeError, 'fixture encoder failure'):
            with runtime.encoder(command) as pipe:
                pipe.write(b'frame')

    def test_render_error_preserves_encoder_stderr(self):
        command = [sys.executable, '-c',
                   'import sys; sys.stderr.write("early encoder failure"); '
                   'sys.exit(19)']
        with self.assertRaisesRegex(RuntimeError, 'early encoder failure'):
            with runtime.encoder(command) as pipe:
                pipe.write(b'frame')
                time.sleep(.3)
                raise ValueError('fixture render failure')

    def test_remote_spec_is_rejected(self):
        spec_path = self.work / 'remote.json'
        spec_path.write_text(json.dumps({'cues': [{'image': 'https://example.com/x'}]}))
        result = self.run_script(
            'engine/render.py', '--spec', spec_path, '--out', 'bad.mp4', code=1,
        )
        self.assertIn('Remote media is disabled', result.stderr)
        self.assertFalse((self.work / 'bad.mp4').exists())


if __name__ == '__main__':
    unittest.main()
