# backend/reset_password.py
from core.database import SessionLocal
from passlib.hash import bcrypt
from sqlalchemy import text

db = SessionLocal()

new_password = 'admin123'
hashed = bcrypt.hash(new_password)

db.execute(text("UPDATE sys_user SET password = :pwd WHERE user_name = 'admin'"), {"pwd": hashed})
db.commit()

print(f"密码已重置为: {new_password}")
print(f"新哈希: {hashed}")

# 验证
result = db.execute(text("SELECT password FROM sys_user WHERE user_name = 'admin'")).scalar()
print(f"验证: {bcrypt.verify(new_password, result)}") # type: ignore

db.close()
