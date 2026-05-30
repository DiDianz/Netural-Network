# core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ========== 数据库类型切换 ==========
    DB_TYPE: str = "mysql"  # "mysql" 或 "mssql"

    # ========== MySQL 配置 ==========
    MYSQL_SERVER: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "neural_predict"
    MYSQL_USERNAME: str = "root"
    MYSQL_PASSWORD: str = "Aa123456"
    MYSQL_CHARSET: str = "utf8mb4"

    # ========== SQL Server 配置 ==========
    MSSQL_SERVER: str = "localhost"
    MSSQL_PORT: int = 1433
    MSSQL_DATABASE: str = "neural_predict"
    MSSQL_USERNAME: str = "sa"
    MSSQL_PASSWORD: str = "Aa123456"
    MSSQL_DRIVER: str = "ODBC Driver 17 for SQL Server"

    # ========== JWT ==========
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ========== App ==========
    APP_DEBUG: bool = True
    APP_TITLE: str = "神经网络预测系统"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        db_type = self.DB_TYPE.lower().strip()
        if db_type == "mysql":
            return (
                f"mysql+pymysql://{self.MYSQL_USERNAME}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
                f"?charset={self.MYSQL_CHARSET}"
            )
        elif db_type in ("mssql", "sqlserver"):
            import urllib.parse
            params = urllib.parse.quote_plus(
                f"DRIVER={{{self.MSSQL_DRIVER}}};"
                f"SERVER={self.MSSQL_SERVER},{self.MSSQL_PORT};"
                f"DATABASE={self.MSSQL_DATABASE};"
                f"UID={self.MSSQL_USERNAME};"
                f"PWD={self.MSSQL_PASSWORD};"
                f"TrustServerCertificate=yes;"
            )
            return f"mssql+pyodbc:///?odbc_connect={params}"
        else:
            raise ValueError(f"不支持的数据库类型: {self.DB_TYPE}，请使用 mysql 或 mssql")

    @property
    def is_mysql(self) -> bool:
        return self.DB_TYPE.lower().strip() == "mysql"

    @property
    def is_mssql(self) -> bool:
        return self.DB_TYPE.lower().strip() in ("mssql", "sqlserver")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
