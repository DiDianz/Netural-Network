# backend/manual_init_user.py
from core.database import SessionLocal, engine, Base
from passlib.hash import bcrypt
from sqlalchemy import text

# 先建表
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # 检查是否已有数据
    count = db.execute(text("SELECT COUNT(*) FROM sys_user")).scalar()
    if count and count > 0:
        print(f"已有 {count} 个用户，跳过")
    else:
        # 插入角色
        db.execute(text("""
            INSERT INTO sys_role (role_name, role_key, sort, status, remark)
            VALUES ('超级管理员', 'admin', 1, '0', '超级管理员')
        """))
        db.execute(text("""
            INSERT INTO sys_role (role_name, role_key, sort, status, remark)
            VALUES ('普通用户', 'user', 2, '0', '普通用户')
        """))

        # 插入用户（密码: admin123）
        hashed = bcrypt.hash('admin123')
        db.execute(text("""
            INSERT INTO sys_user (user_name, nick_name, password, email, status, del_flag)
            VALUES ('admin', '管理员', :password, 'admin@test.com', '0', '0')
        """), {"password": hashed})

        # 关联用户和角色
        db.execute(text("INSERT INTO sys_user_role (user_id, role_id) VALUES (1, 1)"))

        # 插入菜单
        db.execute(text("""
            INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, menu_type, visible, status, icon) VALUES
            ('系统管理', 0, 1, 'system', '', 'M', '0', '0', 'system')
        """))
        db.execute(text("""
            INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, menu_type, visible, status, icon) VALUES
            ('神经网络预测', 0, 2, 'prediction', '', 'M', '0', '0', 'chart')
        """))
        db.execute(text("""
            INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, menu_type, visible, status, icon) VALUES
            ('用户管理', 1, 1, 'user', 'system/user/index', 'C', '0', '0', 'user')
        """))
        db.execute(text("""
            INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, menu_type, visible, status, icon) VALUES
            ('实时预测', 2, 1, 'realtime', 'prediction/realtime/index', 'C', '0', '0', 'monitor')
        """))
        db.execute(text("""
            INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, menu_type, visible, status, icon) VALUES
            ('历史记录', 2, 2, 'history', 'prediction/history/index', 'C', '0', '0', 'date')
        """))
        db.execute(text("""
            INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, menu_type, visible, status, icon) VALUES
            ('模型管理', 2, 3, 'models', 'prediction/models/index', 'C', '0', '0', 'code')
        """))

        db.commit()
        print("初始化完成！")
        print("用户名: admin")
        print("密码: admin123")

except Exception as e:
    db.rollback()
    print(f"初始化失败: {e}")
finally:
    db.close()
