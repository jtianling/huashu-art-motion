# Monkeys 平台适配与验证

验证日期: 2026-10-30 (UTC+8).  原作者为花叔, 基线提交 `8a0d7d72ca65fcce6f8ba82c4a6c8dfe35b8422c`, 原仓库为 https://github.com/alchaincyf/huashu-art-motion.  本 fork 为 https://github.com/jtianling/huashu-art-motion, 保留原 MIT 与字体许可.  不涉及 Open Design.

## 适配范围

- 统一模型无关流程, 任务工作区可写, 安装目录只读.  取消运行时安装、更新 skill 和私人宿主配置步骤.
- 图片、配音改用平台当轮真实的 `image_generate` / `text_to_speech`, 可选实际提供的 `music_generate`.  不启用 `audio_generate`, 不调用旧火山/系统声音 CLI, 不新增 API Key 或付费调用.
- 复用原图片校验与文件锁, 新素材接入器校验规范化终态清单、工作区真实路径、格式、解码、时长和 SHA256.  清单来源只标记为 agent 报告, 不冒充平台签名认证.
- 复用艺术引擎、逐镜 QA 和 film_gate/deliver.  使用预装 Chromium 与 CPU 软件 WebGL 参数, 编码错误和取消路径回收进程与本地服务, 保留具体 stderr.  辅助压测子进程也改用当前 Python.
- 两个渲染 HTML 加内嵌 favicon, 修复 Chromium 默认图标请求 404 被误判为页面错误的问题.  其他错误检查保留, HTTP 失败记录 URL.

## 运行依赖与边界

需要 Python 3.10+, Python Playwright 和匹配 Chromium/系统库, FFmpeg/FFprobe (libx264/AAC), numpy/Pillow/opencv-python-headless.  字体子集与示例合成配乐的额外依赖见 [平台约定](../../references/platform.md).  不要求 Node、Remotion、Hyperframes 或硬件 GPU.

生产 agent 原有 `playwright-chromium` 预置未迁移.  此次未连接生产 VM 或验证其依赖, 不宣称生产已能完整出片.  本地测试使用现有 pdf-base 镜像补齐 FFmpeg/OpenCV 后的隔离镜像, 并不是生产沙箱交付.  镜像 ID 和源文件指纹见 [verification.json](verification.json).  初次固定旧 OpenCV 与基础镜像实测 Python 3.15.1/NumPy 不兼容, 构建失败; 改用兼容版本的二进制包后构建完成.  宿主依赖未修改.

## 验证结果

断网 Docker, 仓库只读挂载, 仅任务输出目录可写.  9 项定向测试通过, 见 [tests.txt](tests.txt).  覆盖真实 PNG/WAV 接入、规范化平台回执、失败和畸形回执、路径越界/软链、格式不符、禁止覆盖、透明空图、旧 CLI 停用、缺浏览器不下载、远程 spec 拒绝和具体编码错误诊断.

真实管线完成中文财经片段、艺术场景静帧、QA、成片门禁、交付和说明指纹校验, 见 [pipeline.txt](pipeline.txt).  视频 H.264、声音 AAC, 两者约 7 秒; 解码音频约 7.04 秒, 主频约 440.06 Hz.  另用实际 render 入口注入失败编码器, 确认非零退出、保留具体错误且不打印成功.  [静帧总览](contact-sheet.png) 已人工目视检查, 未见中文黑块或明显裁切.

质量结果单独保留: 财经示例交付为黄灯, 包含低运动量、空底与固定页框等原版提示; [qa.json](qa.json) 的冷/热渲染最大像素差为 13, 不满足逐像素确定性.  此次未修原财经语法的质量/确定性问题, 未伪造独立审片.  因此这里只证明基础管线可运行, 不把它记为成片质量全绿.  首次 favicon 失败、一次读取脚本时的 UTF-8 错误及后续匹配哈希/AST/完整重跑证据均保留在本地任务记录中, 未删改成一次成功.

独立干净上下文源码 review 已通过, 最初的异常清理与内部 uv 调用问题均已修复并定向复验.  本轮没有调用真实模型或平台付费媒体工具, 没有验证完整生产 agent E2E 或所有 3D 场景.
