Api/
├── main.py
├── core/
│   ├── __init__.py
│   ├── config.py              # 新增: 全局配置
│   ├── database.py            # 新增: SQL Server 连接
│   ├── security.py            # 新增: JWT 认证
│   ├── model.py
│   ├── inference.py
│   └── stream_manager.py
├── models/                    # 新增: SQLAlchemy 模型
│   ├── __init__.py
│   ├── user.py
│   ├── role.py
│   └── menu.py
├── schemas/                   # 新增: Pydantic 数据模型
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   └── menu.py
├── api/
│   ├── __init__.py
│   ├── auth.py                # 新增: 登录接口
│   ├── user.py                # 新增: 用户信息接口
│   ├── menu.py                # 新增: 菜单接口
│   ├── predict.py
│   └── websocket.py
├── deps.py                    # 新增: 依赖注入
├── requirements.txt
└── .env                       # 新增: 环境变量
