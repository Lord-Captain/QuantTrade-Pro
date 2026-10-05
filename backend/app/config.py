import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取当前文件 (config.py) 的绝对路径
BASE_DIR = Path(__file__).resolve().parent
# 获取项目根目录 (backend 的上一级)
PROJECT_ROOT = BASE_DIR.parent
# 确保 data 目录存在
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 构建绝对的数据库文件路径
DB_PATH = DATA_DIR / "quant_trade.db"
# 转换为 SQLite 需要的 URL 格式 (注意斜杠处理)
DATABASE_URL_STR = f"sqlite:///{DB_PATH.as_posix()}"

class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "QuantTrade Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 强制使用计算好的绝对路径，忽略 .env 中的相对路径写法，防止歧义
    DATABASE_URL: str = DATABASE_URL_STR
    
    # 数据源配置
    DATA_SOURCE: str = "akshare"
    
    # 交易核心配置
    INITIAL_CAPITAL: float = 1000000.0
    COMMISSION_RATE: float = 0.0003
    SLIPPAGE: float = 0.001
    
    # API 配置
    API_PREFIX: str = "/api/v1"

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

settings = Settings()

# 打印调试信息，方便确认路径
if __name__ == "__main__":
    print(f"📂 项目根目录: {PROJECT_ROOT}")
    print(f"📂 数据目录: {DATA_DIR}")
    print(f"💾 数据库绝对路径: {DB_PATH}")
    print(f"🔗 数据库 URL: {settings.DATABASE_URL}")