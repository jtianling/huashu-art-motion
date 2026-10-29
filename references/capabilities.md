# 平台配音

已有录音优先沿用, 新配音通过当轮实际提供的 `text_to_speech` 调用.  不读取全局配置、VOLC 凭据或私人音色, 不使用 Mac `say` 或供应商训练接口.  `capabilities.py` 和 `koubo.py` 的旧 CLI 已停用.  素材接入与实测时长见 [Monkeys 平台约定](platform.md).
