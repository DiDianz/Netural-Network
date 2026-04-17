import pyodbc
print(pyodbc.drivers())

import pyodbc

# 先测试能不能连上 master 库
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=master;"
    "UID=sa;"
    "PWD=Aa123456;"
    "TrustServerCertificate=yes;"
)
try:
    conn = pyodbc.connect(conn_str, timeout=5)
    print("连接成功！")

    # 检查 neural_predict 数据库是否存在
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.databases WHERE name='neural_predict'")
    row = cursor.fetchone()
    if row:
        print("数据库 neural_predict 已存在")
    else:
        print("数据库 neural_predict 不存在，需要先创建")
    conn.close()
except Exception as e:
    print(f"连接失败: {e}")
