# Monkeys 平台约定

本 fork 基于花叔的 [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion), 保留原 MIT 归属、艺术风格、Canvas 引擎、参数化片段、QA 与交付门禁.  平台维护仓库为 [jtianling/huashu-art-motion](https://github.com/jtianling/huashu-art-motion).  历史参考中的供应商接入、uv 安装、宿主私有配置和模型分档不作为平台操作步骤.

## 工作区与依赖

skill 安装目录只读.  在平台当轮任务工作区运行命令, 用 `cp -R <skill>/scripts/engine <项目>/代码工程` 创建可写副本.  素材、spec、QA 和最终文件均放任务目录, 命令路径含空格时加引号.  不使用宿主机目录、环境文件或私人配置.

沙箱需 Python 3.10+, Python Playwright 及匹配 Chromium/系统库, FFmpeg/FFprobe (libx264/AAC), numpy, Pillow, opencv-python-headless.  字体子集另需 fonttools; `scripts/audio/synth_艺术史速通.py` 另需 scipy/soundfile, 按需选用.  正常代码动画不需 Node、Remotion、Hyperframes、外部 Studio、第三方 AI API Key 或硬件 GPU.  3D 使用 Chromium 软件 WebGL, 实际场景仍需渲染验证.

先运行 `python3 <skill>/scripts/engine/platform_runtime.py`.  此命令只检查依赖与编码器, 不等于成片验收.  缺项时交付诊断, 不自动安装或下载浏览器.  默认使用 Playwright 预装 Chromium, 沙箱确有另一个匹配浏览器时可显式设 `HUASHU_BROWSER_PATH`.  `playwright-chromium` 名称本身不能证明 FFmpeg/OpenCV 已具备.

## 媒体工具

图片用当轮实际暴露的 `image_generate`, 配音用 `text_to_speech`.  `music_generate` 仅在实际可用且任务需要配乐时调用; 未提供时沿用已有配乐或交付无配乐版本并说明.  不使用 `audio_generate` 配音, 不改走火山或 Mac 系统声音.  不读取 VOLC 等凭据, 不训练音色、不注册供应商、不通过脚本模拟平台工具.  `capabilities.py`, `koubo.py`, `images.py` 的旧 CLI 已停用; 保留纯函数供素材校验复用.

在对话层按当前工具 schema 调用, 异步任务轮询到真实成功终态.  下载与生成均以平台工具的真实本地结果为准, 不猜本地路径.  将终态结果规范化为任务内 JSON 清单, 例如:

```json
{"status":"success","tool":"text_to_speech","localPath":"/当前任务目录/真实返回的声音.wav"}
```

这只是 agent 整理的接入清单, 不是平台原始响应 schema 或签名认证.  不得将未完成、失败任务或手写假来源标为成功.  `schemas/platform-receipt.schema.json` 校验清单形状, 接入器另外检查真实文件、格式、图像像素或音频解码与时长, 并写入 SHA256 侧车.  来源只记作 `agent_reported_tool_call`, 不冒充平台验证.

从当前任务工作区运行, `--out` 相对项目目录, 输入和项目也必须位于当前工作区, 包括解析软链后的真实路径.  接入器不覆盖、不转码.

```sh
python3 <skill>/scripts/platform_media.py --kind voice --receipt 配音终态.json --project 项目 --out 素材/口播-v1.wav
python3 <skill>/scripts/platform_media.py --kind image --file 用户图片.png --project 项目 --out 素材/原图-v1.png
```

配音和配乐分别用 `--kind voice` / `--kind music`.  支持静态 PNG/JPEG/WEBP 和 WAV/MP3/M4A/OGG/FLAC.  实测时长不是逐词时间戳; 无 ASR 时只做段落时间轴.  需要改图、参考图、透明背景或特定音色时先核对当轮工具能力, 不从工具名推断.

## 渲染与交付

使用 `python3` 直接运行预装依赖.  历史参考中的 `uv run --with ... python` 和 `uv run` 统一换为 `python3`, 其中安装浏览器/依赖的命令不执行.  本地 HTTP 服务仅供 Chromium 访问复制后的工程, 命令结束自动关闭, 不必提供用户可访问的 Studio 端口.  spec 图片先接入本地, 拒绝 HTTP/HTTPS 素材.  内置字体许可保留, 子集缺字时更换有覆盖的本地字体并重新验画面.

```sh
python3 项目/代码工程/render.py --spec 项目/镜01.json --out 项目/镜01.mp4
python3 <skill>/scripts/qa.py --spec 项目/镜01.json --out 项目/qa/镜01
python3 <skill>/scripts/deliver.py 项目/成片.mp4 --root 项目 --qa 项目/qa/镜01 --out 项目/output
```

逐镜检查和最终 film_gate 保留, 红灯先修片再重验.  编码失败返回非零并保留具体 stderr, 不宣称成功.  独立审片必须来自平台实际提供且未参与制作的子代理, 不可用时如实记未审.  检查视频和音轨各自时长、解码后信号、字幕同步、缺字和裁切, 不能仅凭 MP4 存在或包含 AAC 流交付.  最终按当轮 `deliver_file` 的真实 schema, 以工作区相对路径交付成片和交付说明, 不只口述绝对路径.  原始工具素材作为中间文件, 不重复交付, 失败也保留可复核日志与中间文件.
