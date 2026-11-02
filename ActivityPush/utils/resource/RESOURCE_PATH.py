"""插件运行时资源路径约定（集中管理，业务代码统一引用）"""
from gsuid_core.data_store import get_res_path

# 插件运行时根目录：data/ActivityPush/
MAIN_PATH = get_res_path() / "ActivityPush"
# 配置文件（StringConfig 用）
CONFIG_PATH = MAIN_PATH / "config.json"
# 图片/临时缓存
CACHE_PATH = MAIN_PATH / "cache"
# 活动数据磁盘快照（跨重启持久化）
DATA_PATH = MAIN_PATH / "data"

for _p in (CACHE_PATH, DATA_PATH):
    _p.mkdir(parents=True, exist_ok=True)
