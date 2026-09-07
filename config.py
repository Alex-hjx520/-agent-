"""
应用配置模块
============
基于 pydantic-settings 加载环境变量（底层使用 python-dotenv）。

用法：
    from config import settings

    settings.deepseek_api_key   # 你的 DeepSeek API Key
    settings.deepseek_base_url  # https://api.deepseek.com/v1
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从 .env / 环境变量读取的应用配置。"""

    # DeepSeek API 配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # MySQL 数据库配置（数据库直查模式：不用大模型时按条件查设备型号）
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_db: str = "equipment"

    model_config = SettingsConfigDict(
        env_file=".env",          # 从项目根目录的 .env 读取
        env_file_encoding="utf-8",
        case_sensitive=False,     # 字段名大小写不敏感（deepseek_api_key ↔ DEEPSEEK_API_KEY）
        extra="ignore",           # 忽略 .env 中未声明的其它变量
    )

    @property
    def has_api_key(self) -> bool:
        """是否已配置有效的 API Key（非空且非占位符）。"""
        return bool(self.deepseek_api_key) and not self.deepseek_api_key.startswith("sk-your-")

    @property
    def has_mysql_config(self) -> bool:
        """是否已配置 MySQL 连接（库名非空）。"""
        return bool(self.mysql_db) and bool(self.mysql_user)


@lru_cache
def get_settings() -> Settings:
    """返回配置单例（进程内只加载一次）。"""
    return Settings()


# 模块级单例，其它模块直接 `from config import settings`
settings = get_settings()
