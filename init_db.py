#!/usr/bin/env python3
"""
数据库初始化脚本 - 支持 MySQL 和 SQLite
自动读取 .env 文件中的配置
"""
import subprocess
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# 尝试加载 .env 文件
def load_env_file():
    """加载 .env 文件中的环境变量"""
    env_paths = [
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
        Path(__file__).parent / "backend" / ".env",
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            print(f"[DB Setup]: {env_path}")
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key, value)
            return True
    return False

# 先加载环境变量
load_env_file()

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    END = '\033[0m'

def log(msg, color=Colors.GREEN):
    print(f"{color}[DB Setup]{Colors.END} {msg}")

def parse_mysql_url(url):
    """解析 MySQL URL 返回连接参数"""
    try:
        # mysql+pymysql://user:password@host:port/dbname?params
        parsed = urlparse(url.replace('mysql+pymysql://', 'mysql://'))
        
        user = parsed.username or 'root'
        password = parsed.password or ''
        host = parsed.hostname or 'localhost'
        port = parsed.port or 3306
        
        # 获取数据库名（去掉查询参数）
        db_name = parsed.path.lstrip('/').split('?')[0] if parsed.path else 'aiwriter'
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'db_name': db_name
        }
    except Exception as e:
        log(f"解析 URL 失败: {e}", Colors.RED)
        return None

def check_mysql_installed():
    """检查 MySQL 是否安装"""
    try:
        result = subprocess.run(
            ["mysql", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            log(f"MySQL 已安装: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    log("未检测到 MySQL 客户端", Colors.YELLOW)
    return False

def test_mysql_connection(user, password, host, port):
    """测试 MySQL 连接"""
    try:
        cmd = ["mysql", f"-h{host}", f"-P{port}", f"-u{user}"]
        if password:
            cmd.append(f"-p{password}")
        cmd.extend(["-e", "SELECT 1"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

def create_mysql_database(user, password, host, port, db_name):
    """创建 MySQL 数据库"""
    log(f"正在创建 MySQL 数据库: {db_name}")
    log(f"连接信息: {user}@{host}:{port}")
    
    # 创建数据库的 SQL
    sql = f"""
    CREATE DATABASE IF NOT EXISTS {db_name} 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;
    
    SHOW DATABASES LIKE '{db_name}';
    """
    
    try:
        cmd = ["mysql", f"-h{host}", f"-P{port}", f"-u{user}"]
        if password:
            cmd.append(f"-p{password}")
        
        result = subprocess.run(
            cmd,
            input=sql,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log(f"数据库 '{db_name}' 创建/确认成功！", Colors.GREEN)
            return True
        else:
            log(f"创建失败: {result.stderr}", Colors.RED)
            return False
            
    except FileNotFoundError:
        log("mysql 命令未找到", Colors.RED)
        return False

def execute_sql_file(user, password, host, port, db_name):
    """执行 SQL 文件创建表"""
    log("正在执行建表 SQL...")
    
    # 查找 SQL 文件
    sql_paths = [
        Path(__file__).parent / "backend" / "database" / "init.sql",
        Path(__file__).parent / "database" / "init.sql",
        Path.cwd() / "backend" / "database" / "init.sql",
        Path.cwd() / "database" / "init.sql",
    ]
    
    sql_file = None
    for path in sql_paths:
        if path.exists():
            sql_file = path
            break
    
    if not sql_file:
        log("未找到 init.sql 文件，将使用 SQLAlchemy 自动创建表", Colors.YELLOW)
        return init_tables_with_sqlalchemy()
    
    log(f"找到 SQL 文件: {sql_file}")
    
    try:
        cmd = ["mysql", f"-h{host}", f"-P{port}", f"-u{user}", f"-D{db_name}"]
        if password:
            cmd.append(f"-p{password}")
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        result = subprocess.run(
            cmd,
            input=sql_content,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log("数据表创建成功！", Colors.GREEN)
            if result.stdout:
                print(result.stdout)
            return True
        else:
            log(f"执行 SQL 失败: {result.stderr}", Colors.RED)
            log("尝试使用 SQLAlchemy 创建表...", Colors.YELLOW)
            return init_tables_with_sqlalchemy()
            
    except Exception as e:
        log(f"执行 SQL 文件失败: {e}", Colors.RED)
        return init_tables_with_sqlalchemy()

def init_tables_with_sqlalchemy():
    """使用 SQLAlchemy 初始化表结构"""
    log("使用 SQLAlchemy 创建表...")
    
    try:
        # 切换到 backend 目录
        backend_path = os.path.join(os.path.dirname(__file__), "backend")
        if not os.path.exists(backend_path):
            backend_path = os.path.join(os.getcwd(), "backend")
        
        os.chdir(backend_path)
        
        # 安装依赖
        log("检查并安装依赖...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "pymysql", "cryptography"],
            capture_output=True
        )
        
        # 运行 Python 脚本创建表
        py_code = "from app.database import engine, Base; Base.metadata.create_all(bind=engine); print('Tables created successfully!')"
        result = subprocess.run(
            [sys.executable, "-c", py_code],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": backend_path}
        )
        
        if result.returncode == 0:
            log("数据库表创建成功！", Colors.GREEN)
            return True
        else:
            log(f"创建表失败: {result.stderr}", Colors.RED)
            return False
            
    except Exception as e:
        log(f"初始化失败: {e}", Colors.RED)
        return False

def print_manual_guide(db_name):
    """打印手动操作指南"""
    print(f"""
{Colors.CYAN}═══════════════════════════════════════════════════════════════{Colors.END}
{Colors.YELLOW}MySQL 连接失败，请尝试以下方法手动创建：{Colors.END}

{Colors.GREEN}方法 1：使用 mysql 命令行（无密码）{Colors.END}
mysql -u root

CREATE DATABASE IF NOT EXISTS {db_name} 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE {db_name};
SOURCE backend/database/init.sql;

{Colors.GREEN}方法 2：使用 mysql 命令行（有密码）{Colors.END}
mysql -u root -p

CREATE DATABASE IF NOT EXISTS {db_name} 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE {db_name};
SOURCE backend/database/init.sql;

{Colors.GREEN}方法 3：使用 MySQL Workbench / Sequel Ace{Colors.END}
1. 打开图形化客户端
2. 连接 localhost
3. 执行上述 SQL 命令

{Colors.YELLOW}提示：{Colors.END}
- macOS Homebrew 安装的 MySQL 默认 root 无密码，或密码为你设置的密码
- 如果忘记密码，可以重置：
  brew services stop mysql
  mysqld_safe --skip-grant-tables
  # 在另一个终端
  mysql -u root
  ALTER USER 'root'@'localhost' IDENTIFIED BY '新密码';
{Colors.CYAN}═══════════════════════════════════════════════════════════════{Colors.END}
""")

def main():
    print("="*60)
    print("墨心 - 数据库初始化")
    print("="*60)
    
    # 读取环境变量
    db_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost:3306/aiwriter?charset=utf8mb4")
    log(f"数据库 URL: {db_url.replace('://', '://***:***@') if '://' in db_url else db_url}")
    
    if "sqlite" in db_url.lower():
        log("使用 SQLite 数据库")
        init_tables_with_sqlalchemy()
    elif "mysql" in db_url.lower():
        log("使用 MySQL 数据库")
        
        # 解析数据库 URL
        params = parse_mysql_url(db_url)
        if not params:
            log("无法解析数据库 URL", Colors.RED)
            return
        
        log(f"目标数据库: {params['db_name']}")
        
        # 检查 MySQL
        if not check_mysql_installed():
            log("请确保 MySQL 已安装: brew install mysql", Colors.RED)
            print_manual_guide(params['db_name'])
            return
        
        # 测试连接
        log("测试 MySQL 连接...")
        if test_mysql_connection(
            params['user'], 
            params['password'], 
            params['host'], 
            params['port']
        ):
            log("连接成功！")
        else:
            log("连接失败！可能是密码错误或权限问题", Colors.RED)
            print_manual_guide(params['db_name'])
            return
        
        # 创建数据库
        if create_mysql_database(
            params['user'],
            params['password'],
            params['host'],
            params['port'],
            params['db_name']
        ):
            # 执行 SQL 创建表
            execute_sql_file(
                params['user'],
                params['password'],
                params['host'],
                params['port'],
                params['db_name']
            )
    else:
        log(f"不支持的数据库类型: {db_url}", Colors.RED)
    
    print("="*60)

if __name__ == "__main__":
    main()
