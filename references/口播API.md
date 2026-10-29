# 平台口播接口

平台托管工具在对话层调用, 沙箱 Python 不直接请求第三方语音 API.  不保留原版 HTTP 请求、鉴权头或 VOLC Key 操作作为本 fork 的步骤.  使用 `text_to_speech` 的真实工具 schema 与终态本地文件, 接入方式见 [Monkeys 平台约定](platform.md).
