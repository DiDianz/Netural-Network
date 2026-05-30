# backend/fix_all.py — 支持 MySQL / SQL Server 双数据库
import sys
import os

# 确保能找到模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
from core.database import engine, SessionLocal, Base, ensure_database_exists
from passlib.hash import bcrypt
from sqlalchemy import text

settings = get_settings()

print("=" * 50)
print("神经网络预测系统 - 数据库修复工具")
print(f"当前数据库类型: {settings.DB_TYPE}")
print("=" * 50)

# 0. 自动创建数据库（如果不存在）
print("\n[0/4] 检查数据库...")
try:
    ensure_database_exists()
except Exception as e:
    print(f"  ✗ 数据库创建失败: {e}")
    exit(1)

# 1. 测试连接
print("\n[1/4] 测试数据库连接...")
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("  ✓ 连接成功")
except Exception as e:
    print(f"  ✗ 连接失败: {e}")
    if settings.is_mysql:
        print(f"\n  请检查 .env 文件中的 MySQL 配置:")
        print(f"  服务器: {settings.MYSQL_SERVER}:{settings.MYSQL_PORT}")
        print(f"  数据库: {settings.MYSQL_DATABASE}")
        print(f"  用户名: {settings.MYSQL_USERNAME}")
    else:
        print(f"\n  请检查 .env 文件中的 SQL Server 配置:")
        print(f"  服务器: {settings.MSSQL_SERVER}:{settings.MSSQL_PORT}")
        print(f"  数据库: {settings.MSSQL_DATABASE}")
        print(f"  用户名: {settings.MSSQL_USERNAME}")
    exit(1)

# 2. 建表
print("\n[2/4] 创建数据表...")
try:
    # 导入模型以注册表
    from models.user import SysUser
    from models.role import SysRole
    from models.menu import SysMenu

    Base.metadata.create_all(bind=engine)
    print("  ✓ 表创建成功")
except Exception as e:
    print(f"  ✗ 建表失败: {e}")
    exit(1)

# 3. 初始化数据
print("\n[3/4] 初始化数据...")
db = SessionLocal()
try:
    # 检查用户是否已存在
    count = db.execute(text("SELECT COUNT(*) FROM sys_user")).scalar()

    if count and count > 0:
        print(f"  已有 {count} 个用户")

        # 重置 admin 密码
        hashed = bcrypt.hash('admin123')
        db.execute(text("UPDATE sys_user SET password = :pwd WHERE user_name = 'admin'"), {"pwd": hashed})
        db.commit()
        print("  ✓ admin 密码已重置为: admin123")
    else:
        from models.role import SysRole
        from models.user import SysUser, sys_user_role
        from models.menu import SysMenu

        # 插入角色
        db.add(SysRole(role_name="超级管理员", role_key="admin", sort=1, status="0", remark="超级管理员"))
        db.add(SysRole(role_name="普通用户", role_key="user", sort=2, status="0", remark="普通用户"))
        db.flush()

        # 插入用户
        hashed = bcrypt.hash('admin123')
        admin = SysUser(
            user_name="admin",
            nick_name="管理员",
            password=hashed,
            email="admin@test.com",
            status="0",
            del_flag="0",
        )
        db.add(admin)
        db.flush()

        # 关联角色
        admin_role = db.query(SysRole).filter_by(role_key="admin").first()
        admin.roles = [admin_role]

        # 插入菜单
        menus = [
            ('系统管理', 0, 1, 'system', '', 'M', 'system'),
            ('神经网络预测', 0, 2, 'prediction', '', 'M', 'chart'),
            ('用户管理', 1, 1, 'user', 'system/user/index', 'C', 'user'),
            ('角色管理', 1, 2, 'role', 'system/role/index', 'C', 'peoples'),
            ('菜单管理', 1, 3, 'menu', 'system/menu/index', 'C', 'tree-table'),
            ('实时预测', 2, 1, 'realtime', 'prediction/realtime/index', 'C', 'monitor'),
            ('历史记录', 2, 2, 'history', 'prediction/history/index', 'C', 'date'),
            ('模型管理', 2, 3, 'models', 'prediction/models/index', 'C', 'code'),
        ]
        for name, parent, order, path, comp, mtype, icon in menus:
            db.add(SysMenu(menu_name=name, parent_id=parent, order_num=order,
                           path=path, component=comp, menu_type=mtype,
                           visible="0", status="0", icon=icon))

        db.commit()
        print("  ✓ 数据初始化成功")

except Exception as e:
    db.rollback()
    print(f"  ✗ 初始化失败: {e}")
finally:
    db.close()

# 4. 验证
print("\n[4/4] 验证...")
db = SessionLocal()
try:
    user = db.execute(text("SELECT user_name, nick_name, status, del_flag FROM sys_user WHERE user_name = 'admin'")).fetchone()
    if user:
        print(f"  用户: {user[0]} ({user[1]})")
        print(f"  状态: {'正常' if user[2] == '0' else '停用'}")
        print(f"  删除: {'否' if user[3] == '0' else '是'}")

        # 验证密码
        pwd = db.execute(text("SELECT password FROM sys_user WHERE user_name = 'admin'")).scalar()
        if bcrypt.verify('admin123', pwd): # type: ignore
            print("  密码: ✓ 验证通过")
        else:
            print("  密码: ✗ 验证失败")

    role_count = db.execute(text("SELECT COUNT(*) FROM sys_role")).scalar()
    menu_count = db.execute(text("SELECT COUNT(*) FROM sys_menu")).scalar()
    print(f"  角色: {role_count} 个")
    print(f"  菜单: {menu_count} 个")
finally:
    db.close()

print("\n" + "=" * 50)
print("修复完成！登录信息:")
print("  用户名: admin")
print("  密码: admin123")
print("=" * 50)
