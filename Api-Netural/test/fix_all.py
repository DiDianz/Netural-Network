# backend/fix_all.py
import sys
import os

# 确保能找到模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import get_settings
from core.database import engine, SessionLocal, Base
from passlib.hash import bcrypt
from sqlalchemy import text

settings = get_settings()

print("=" * 50)
print("神经网络预测系统 - 数据库修复工具")
print("=" * 50)

# 1. 测试连接
print("\n[1/4] 测试数据库连接...")
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("  ✓ 连接成功")
except Exception as e:
    print(f"  ✗ 连接失败: {e}")
    print(f"\n  请检查 .env 文件中的数据库配置:")
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
        # 插入角色
        db.execute(text("""
            IF NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key = 'admin')
            INSERT INTO sys_role (role_name, role_key, sort, status, remark)
            VALUES (N'超级管理员', 'admin', 1, '0', N'超级管理员')
        """))
        db.execute(text("""
            IF NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key = 'user')
            INSERT INTO sys_role (role_name, role_key, sort, status, remark)
            VALUES (N'普通用户', 'user', 2, '0', N'普通用户')
        """))

        # 插入用户
        hashed = bcrypt.hash('admin123')
        db.execute(text("""
            INSERT INTO sys_user (user_name, nick_name, password, email, status, del_flag)
            VALUES ('admin', N'管理员', :password, 'admin@test.com', '0', '0')
        """), {"password": hashed})

        # 关联角色
        db.execute(text("""
            INSERT INTO sys_user_role (user_id, role_id)
            SELECT u.user_id, r.role_id
            FROM sys_user u, sys_role r
            WHERE u.user_name = 'admin' AND r.role_key = 'admin'
        """))

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
            db.execute(text("""
                INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, menu_type, visible, status, icon)
                VALUES (:name, :parent, :order, :path, :comp, :mtype, '0', '0', :icon)
            """), {"name": name, "parent": parent, "order": order, "path": path, "comp": comp, "mtype": mtype, "icon": icon})

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
