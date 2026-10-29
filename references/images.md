# 平台图片

已有图片优先导入, 新图片通过当轮实际提供的 `image_generate` 调用.  工具不可用时说明缺项, 不自行切换供应商.  参考图、透明背景与改图能力按当前工具 schema 核对.  结果成功后用 `scripts/platform_media.py --kind image` 接入真实本地文件; 旧 `images.py` CLI 已停用.  接入清单并非平台签名来源证明, 细节见 [Monkeys 平台约定](platform.md).
