# backend/manual_init_user.py — 支持 MySQL / SQL Server 双数据库
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, engine, Base, ensure_database_exists
from passlib.hash import bcrypt
from sqlalchemy import text

# 自动创建数据库（如果不存在）+ 建表
ensure_database_exists()
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # 检查是否已有数据
    count = db.execute(text("SELECT COUNT(*) FROM sys_user")).scalar()
    if count and count > 0:
        print(f"已有 {count} 个用户，跳过")
    else:
        from models.role import SysRole
        from models.user import SysUser
        from models.menu import SysMenu

        # 插入角色
        db.add(SysRole(role_name="超级管理员", role_key="admin", sort=1, status="0", remark="超级管理员"))
        db.add(SysRole(role_name="普通用户", role_key="user", sort=2, status="0", remark="普通用户"))
        db.flush()

        # 插入用户（密码: admin123）
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

        # 关联用户和角色
        admin_role = db.query(SysRole).filter_by(role_key="admin").first()
        admin.roles = [admin_role]

        # 插入菜单
        menus = [
            ('系统管理', 0, 1, 'system', '', 'M', 'system'),
            ('神经网络预测', 0, 2, 'prediction', '', 'M', 'chart'),
            ('用户管理', 1, 1, 'user', 'system/user/index', 'C', 'user'),
            ('实时预测', 2, 1, 'realtime', 'prediction/realtime/index', 'C', 'monitor'),
            ('历史记录', 2, 2, 'history', 'prediction/history/index', 'C', 'date'),
            ('模型管理', 2, 3, 'models', 'prediction/models/index', 'C', 'code'),
        ]
        for name, parent, order, path, comp, mtype, icon in menus:
            db.add(SysMenu(menu_name=name, parent_id=parent, order_num=order,
                           path=path, component=comp, menu_type=mtype,
                           visible="0", status="0", icon=icon))

        db.commit()
        print("初始化完成！")
        print("用户名: admin")
        print("密码: admin123")

except Exception as e:
    db.rollback()
    print(f"初始化失败: {e}")
finally:
    db.close()
