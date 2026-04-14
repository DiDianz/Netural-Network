# core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # SQL Server
    MSSQL_SERVER: str = "localhost"
    MSSQL_PORT: int = 1433
    MSSQL_DATABASE: str = "neural_predict"
    MSSQL_USERNAME: str = "sa"
    MSSQL_PASSWORD: str = "Aa123456"
    MSSQL_DRIVER: str = "ODBC Driver 18 for SQL Server"

    # JWT
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # App
    APP_DEBUG: bool = True
    APP_TITLE: str = "神经网络预测系统"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # 使用 pymssql 驱动（推荐，无需安装 ODBC）
        return (
            f"mssql+pymssql://{self.MSSQL_USERNAME}:{self.MSSQL_PASSWORD}"
            f"@{self.MSSQL_SERVER}:{self.MSSQL_PORT}/{self.MSSQL_DATABASE}"
            f"?charset=utf8"
        )

    # 如果用 pyodbc 驱动，替换为:
    # @property
    # def SQLALCHEMY_DATABASE_URI(self) -> str:
    #     import urllib.parse
    #     params = urllib.parse.quote_plus(
    #         f"DRIVER={{{self.MSSQL_DRIVER}}};"
    #         f"SERVER={self.MSSQL_SERVER},{self.MSSQL_PORT};"
    #         f"DATABASE={self.MSSQL_DATABASE};"
    #         f"UID={self.MSSQL_USERNAME};"
    #         f"PWD={self.MSSQL_PASSWORD};"
    #         f"TrustServerCertificate=yes;"
    #     )
    #     return f"mssql+pyodbc:///?odbc_connect={params}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
