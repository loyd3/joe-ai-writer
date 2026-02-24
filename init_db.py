#!/usr/bin/env python3
"""
数据库初始化脚本 - 支持 MySQL 和 SQLite
"""
import subprocess
import sys
import os

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

def create_mysql_database(db_name="joe_writer", user="root", password="password", host="localhost"):
    """创建 MySQL 数据库"""
    log(f"正在创建 MySQL 数据库: {db_name}")
    
    # 创建数据库的 SQL
    sql = f"""
    CREATE DATABASE IF NOT EXISTS {db_name} 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;
    
    SHOW DATABASES LIKE '{db_name}';
    """
    
    try:
        # 使用 mysql 命令行创建数据库
        cmd = [
            "mysql",
            f"-h{host}",
            f"-u{user}"
        ]
        
        if password:
            cmd.append(f"-p{password}")
        
        result = subprocess.run(
            cmd,
            input=sql,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log(f"数据库 '{db_name}' 创建成功！", Colors.GREEN)
            return True
        else:
            log(f"创建失败: {result.stderr}", Colors.RED)
            return False
            
    except FileNotFoundError:
        log("mysql 命令未找到，请手动创建数据库:", Colors.YELLOW)
        print(f"""
{Colors.CYAN}请执行以下 SQL 命令：{Colors.END}

CREATE DATABASE IF NOT EXISTS {db_name} 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

{Colors.YELLOW}或者使用 .env 文件中的配置：{Colors.END}
mysql -u root -p

CREATE DATABASE IF NOT EXISTS joe_writer 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;
        """)
        return False

def init_tables():
    """初始化数据库表结构"""
    log("正在初始化数据库表...")
    
    try:
        # 切换到 backend 目录
        backend_path = os.path.join(os.path.dirname(__file__), "backend")
        if not os.path.exists(backend_path):
            backend_path = os.path.join(os.getcwd(), "backend")
        
        os.chdir(backend_path)
        
        # 运行 Python 脚本创建表
        result = subprocess.run(
            [sys.executable, "-c", "from app.database import engine, Base; Base.metadata.create_all(bind=engine); print('Tables created!')"],
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

def main():
    print("="*60)
    print("Joe AI Writer - 数据库初始化")
    print("="*60)
    
    # 读取环境变量
    db_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/joe_writer?charset=utf8mb4")
    
    if "sqlite" in db_url.lower():
        log("使用 SQLite 数据库")
        log("数据库文件将自动创建")
        init_tables()
    elif "mysql" in db_url.lower():
        log("使用 MySQL 数据库")
        
        # 解析数据库 URL
        # mysql+pymysql://user:password@host:port/dbname
        try:
            # 简单解析 URL
            parts = db_url.replace("mysql+pymysql://", "").split("/")[0]
            auth_host = parts.split("@")
            if len(auth_host) == 2:
                user_pass = auth_host[0].split(":")
                user = user_pass[0]
                password = user_pass[1] if len(user_pass) > 1 else ""
                
                host_port_db = auth_host[1].split("/")
                host_port = host_port_db[0].split(":")
                host = host_port[0]
                port = host_port[1] if len(host_port) > 1 else "3306"
                
                db_name = host_port_db[1].split("?")[0] if len(host_port_db) > 1 else "joe_writer"
                
                log(f"数据库配置: {user}@{host}:{port}/{db_name}")
                
                if check_mysql_installed():
                    if create_mysql_database(db_name, user, password, host):
                        init_tables()
                else:
                    log("请确保 MySQL 已安装并运行")
                    log("然后手动创建数据库并运行: python init_db.py --tables-only")
            else:
                log("无法解析数据库 URL，请检查配置", Colors.RED)
        except Exception as e:
            log(f"解析数据库 URL 失败: {e}", Colors.RED)
    else:
        log(f"不支持的数据库类型: {db_url}", Colors.RED)
    
    print("="*60)

if __name__ == "__main__":
    main()
