整体架构
┌──────────────────────────────────────────────────────────────────┐
│                         Vue 3 前端                                │
│  ┌──────────┐  ┌───────────────────────────────────────────────┐ │
│  │ 登录页面  │  │  若依风格主布局                                │ │
│  │ /login   │  │  ┌──────┬──────────────────────────────────┐  │ │
│  └──────────┘  │  │ 侧栏  │ 顶部导航 + 标签页 + 内容区       │  │ │
│                │  │ ┌────┐│ ┌──────────────────────────────┐ │  │ │
│                │  │ │预测││ │  神经网络预测页面             │ │  │ │
│                │  │ │系统││ │  (SSE + ECharts)             │ │  │ │
│                │  │ └────┘│ └──────────────────────────────┘ │  │ │
│                │  └──────┴──────────────────────────────────┘  │ │
│                └───────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────┘
                               │ JWT Token
┌──────────────────────────────┼───────────────────────────────────┐
│                        FastAPI 后端                               │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐ │
│  │ Auth API  │  │User API   │  │Predict API│  │ Menu API      │ │
│  │ 登录/登出  │  │用户管理   │  │SSE预测流  │  │ 动态菜单      │ │
│  └─────┬─────┘  └─────┬─────┘  └───────────┘  └───────────────┘ │
│        │              │                                          │
│  ┌─────┴──────────────┴──────────────────────────────────────┐   │
│  │              SQLAlchemy ORM + JWT Auth                     │   │
│  └─────────────────────────┬─────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │  MySQL / SQL Server     │
                │  (通过 .env DB_TYPE 切换) │
                │                         │
                │  ┌───────────┐          │
                │  │ sys_user  │          │
                │  │ sys_role  │          │
                │  │ sys_menu  │          │
                │  └───────────┘          │
                └─────────────────────────┘


# ========== 数据库切换 ==========
# 在 .env 文件中修改 DB_TYPE 即可切换数据库:
#   DB_TYPE=mysql   → 使用 MySQL (pymysql 驱动)
#   DB_TYPE=mssql   → 使用 SQL Server (pyodbc 驱动)

# 1. 创建数据库
# MySQL:
#    CREATE DATABASE neural_predict CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
# SQL Server:
#    CREATE DATABASE neural_predict;

# 2. 后端
cd Api-Netural
pip install -r requirements.txt

# 编辑 .env 文件，配置数据库连接信息
# MySQL 示例:
#   DB_TYPE=mysql
#   MYSQL_SERVER=localhost
#   MYSQL_PORT=3306
#   MYSQL_DATABASE=neural_predict
#   MYSQL_USERNAME=root
#   MYSQL_PASSWORD=YourPassword
#
# SQL Server 示例:
#   DB_TYPE=mssql
#   MSSQL_SERVER=localhost
#   MSSQL_DATABASE=neural_predict
#   MSSQL_USERNAME=sa
#   MSSQL_PASSWORD=YourPassword

python main.py
# → http://localhost:8000  (首次启动自动建表+初始化数据)

# 3. 前端
cd Vue-Netural
npm install
npm install element-plus @element-plus/icons-vue path-browserify
npm run dev
# → http://localhost:5173

```
```
Netural-Network
├─ Api-Netural
│  ├─ .env
│  ├─ api
│  │  ├─ auth.py
│  │  ├─ menu.py
│  │  ├─ model.py
│  │  ├─ predict.py
│  │  ├─ upload.py
│  │  ├─ user.py
│  │  ├─ websocket.py
│  │  ├─ __init__.py
│  │  └─ __pycache__
│  │     ├─ auth.cpython-312.pyc
│  │     ├─ menu.cpython-312.pyc
│  │     ├─ model.cpython-312.pyc
│  │     ├─ predict.cpython-312.pyc
│  │     ├─ upload.cpython-312.pyc
│  │     ├─ user.cpython-312.pyc
│  │     ├─ websocket.cpython-312.pyc
│  │     └─ __init__.cpython-312.pyc
│  ├─ core
│  │  ├─ config.py
│  │  ├─ database.py
│  │  ├─ data_manager.py
│  │  ├─ inference.py
│  │  ├─ model.py
│  │  ├─ model_gru.py
│  │  ├─ model_manager.py
│  │  ├─ model_transformer.py
│  │  ├─ security.py
│  │  ├─ __init__.py
│  │  └─ __pycache__
│  │     ├─ config.cpython-312.pyc
│  │     ├─ database.cpython-312.pyc
│  │     ├─ data_manager.cpython-312.pyc
│  │     ├─ inference.cpython-312.pyc
│  │     ├─ model.cpython-312.pyc
│  │     ├─ model_gru.cpython-312.pyc
│  │     ├─ model_manager.cpython-312.pyc
│  │     ├─ model_transformer.cpython-312.pyc
│  │     ├─ security.cpython-312.pyc
│  │     └─ __init__.cpython-312.pyc
│  ├─ deps.py
│  ├─ main.py
│  ├─ models
│  │  ├─ menu.py
│  │  ├─ predict_history.py
│  │  ├─ role.py
│  │  ├─ train_log.py
│  │  ├─ train_trend.py
│  │  ├─ user.py
│  │  ├─ __init__.py
│  │  └─ __pycache__
│  │     ├─ menu.cpython-312.pyc
│  │     ├─ predict_history.cpython-312.pyc
│  │     ├─ role.cpython-312.pyc
│  │     ├─ train_log.cpython-312.pyc
│  │     ├─ train_trend.cpython-312.pyc
│  │     ├─ user.cpython-312.pyc
│  │     └─ __init__.cpython-312.pyc
│  ├─ README.MD
│  ├─ requirements.txt
│  ├─ saved_models
│  │  ├─ lstm_best.pth
│  │  └─ transformer_best.pth
│  ├─ schemas
│  │  ├─ auth.py
│  │  ├─ model.py
│  │  ├─ user.py
│  │  ├─ __init__.py
│  │  └─ __pycache__
│  │     ├─ auth.cpython-312.pyc
│  │     ├─ model.cpython-312.pyc
│  │     ├─ user.cpython-312.pyc
│  │     └─ __init__.cpython-312.pyc
│  ├─ test
│  │  ├─ fix_all.py
│  │  ├─ manual_init_user.py
│  │  ├─ reset_password.py
│  │  └─ test_db.py
│  └─ __pycache__
│     ├─ deps.cpython-312.pyc
│     └─ main.cpython-312.pyc
├─ README.MD
└─ Vue-Netural
   ├─ index.html
   ├─ package-lock.json
   ├─ package.json
   ├─ public
   │  └─ favicon.ico
   ├─ README.md
   ├─ src
   │  ├─ api
   │  │  ├─ auth.js
   │  │  ├─ menu.js
   │  │  ├─ model.js
   │  │  ├─ request.js
   │  │  └─ user.js
   │  ├─ App.vue
   │  ├─ assets
   │  │  ├─ base.css
   │  │  ├─ logo.svg
   │  │  └─ main.css
   │  ├─ components
   │  │  ├─ ControlPanel.vue
   │  │  ├─ PredictionChart.vue
   │  │  ├─ RealtimePanel.vue
   │  │  └─ ThemeSwitcher.vue
   │  ├─ composables
   │  │  ├─ usePredictionStore.js
   │  │  └─ useSSE.js
   │  ├─ layout
   │  │  ├─ components
   │  │  │  ├─ AppMain.vue
   │  │  │  ├─ Navbar.vue
   │  │  │  ├─ Sidebar.vue
   │  │  │  ├─ SidebarItem.vue
   │  │  │  └─ TagsView.vue
   │  │  └─ index.vue
   │  ├─ main.js
   │  ├─ router
   │  │  └─ index.js
   │  ├─ stores
   │  │  ├─ index.js
   │  │  ├─ permission.js
   │  │  ├─ theme.js
   │  │  └─ user.js
   │  ├─ styles
   │  │  ├─ index.css
   │  │  └─ themes.css
   │  ├─ utils
   │  │  ├─ auth.js
   │  │  └─ sse-client.js
   │  └─ views
   │     ├─ 404.vue
   │     ├─ index.vue
   │     ├─ login
   │     │  └─ index.vue
   │     ├─ prediction
   │     │  ├─ history
   │     │  │  └─ index.vue
   │     │  ├─ models
   │     │  │  └─ index.vue
   │     │  ├─ realtime
   │     │  │  └─ index.vue
   │     │  └─ training
   │     │     └─ index.vue
   │     └─ system
   │        ├─ menu
   │        │  └─ index.vue
   │        ├─ role
   │        │  └─ index.vue
   │        └─ user
   │           └─ index.vue
   └─ vite.config.ts

```