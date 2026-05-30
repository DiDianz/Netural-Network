# backend/test_db.py — 支持 MySQL / SQL Server 双数据库
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
from core.database import engine, SessionLocal, ensure_database_exists
from sqlalchemy import text

settings = get_settings()

print("=" * 50)
print("数据库连接测试")
print(f"数据库类型: {settings.DB_TYPE}")
print("=" * 50)

# 0. 自动创建数据库
print("\n[0] 检查/创建数据库...")
try:
    ensure_database_exists()
except Exception as e:
    print(f"✗ 数据库创建失败: {e}")
    exit(1)

# 1. 打印连接信息（隐藏密码）
if settings.is_mysql:
    print(f"服务器: {settings.MYSQL_SERVER}:{settings.MYSQL_PORT}")
    print(f"数据库: {settings.MYSQL_DATABASE}")
    print(f"用户名: {settings.MYSQL_USERNAME}")
    uri_display = settings.SQLALCHEMY_DATABASE_URI.replace(settings.MYSQL_PASSWORD, '****')
else:
    print(f"服务器: {settings.MSSQL_SERVER}:{settings.MSSQL_PORT}")
    print(f"数据库: {settings.MSSQL_DATABASE}")
    print(f"用户名: {settings.MSSQL_USERNAME}")
    uri_display = settings.SQLALCHEMY_DATABASE_URI.replace(settings.MSSQL_PASSWORD, '****')

print(f"连接串: {uri_display}")
print()

# 2. 测试连接
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✓ 数据库连接成功")
except Exception as e:
    print(f"✗ 数据库连接失败: {e}")
    exit(1)

# 3. 检查表是否存在
try:
    with engine.connect() as conn:
        if settings.is_mysql:
            tables = conn.execute(text(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = :db AND TABLE_TYPE = 'BASE TABLE'"
            ), {"db": settings.MYSQL_DATABASE}).fetchall()
        else:
            tables = conn.execute(text(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
            )).fetchall()
        print(f"\n现有表: {[t[0] for t in tables]}")
except Exception as e:
    print(f"✗ 查询表失败: {e}")

# 4. 检查用户数据
try:
    db = SessionLocal()
    from models.user import SysUser
    users = db.query(SysUser).all()
    print(f"\n用户数量: {len(users)}")
    for u in users:
        print(f"  - ID={u.user_id}, 用户名={u.user_name}, 状态={u.status}, 删除={u.del_flag}")
    db.close()
except Exception as e:
    print(f"✗ 查询用户失败: {e}")

print()
print("=" * 50)
