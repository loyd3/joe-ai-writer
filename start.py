#!/usr/bin/env python3
"""
墨心（AI 辅助写作）- 一键启动脚本
同时启动后端 (FastAPI) 和前端 (Vue3)
"""
import subprocess
import sys
import os
import signal
import time
import argparse
from pathlib import Path

# On Windows, "npm" is npm.cmd; Popen with shell=False cannot run .cmd files.
_WIN = sys.platform == "win32"

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    END = '\033[0m'

def log(msg, color=Colors.GREEN):
    print(f"{color}[墨心]{Colors.END} {msg}")

def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent.absolute()

def check_backend_deps(backend_path):
    """检查后端依赖"""
    req_file = backend_path / "requirements.txt"
    if not req_file.exists():
        log("未找到 requirements.txt", Colors.YELLOW)
        return True
    
    log("检查后端依赖...")
    try:
        # 设置 UTF-8 编码环境变量，解决 Windows 编码问题
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            log("安装依赖失败:", Colors.RED)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return False
        log("后端依赖已就绪")
        return True
    except Exception as e:
        log(f"安装依赖失败: {e}", Colors.RED)
        return False

def check_frontend_deps(frontend_path):
    """检查前端依赖"""
    node_modules = frontend_path / "node_modules"
    if node_modules.exists():
        log("前端依赖已安装")
        return True
    
    log("安装前端依赖...")
    try:
        if _WIN:
            subprocess.run("npm install", cwd=str(frontend_path), check=True, shell=True)
        else:
            subprocess.run(
                ["npm", "install"],
                cwd=str(frontend_path),
                check=True
            )
        log("前端依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        log(f"安装前端依赖失败: {e}", Colors.RED)
        return False
    except FileNotFoundError:
        log("未找到 npm，请安装 Node.js", Colors.RED)
        return False

def ensure_docker_mysql(root: Path, timeout: int = 90) -> bool:
    """确保 Docker MySQL 已启动并健康（供本地 start.py 连接 localhost:3307）。"""
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
    except Exception:
        log("未检测到 Docker，请自行保证 DATABASE_URL 指向可用数据库", Colors.YELLOW)
        return False

    log("检查 / 启动 Docker MySQL...")
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", "mysql"],
            cwd=str(root),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        log(f"启动 MySQL 容器失败: {e.stderr or e}", Colors.RED)
        return False

    start = time.time()
    while time.time() - start < timeout:
        try:
            result = subprocess.run(
                [
                    "docker", "inspect",
                    "-f", "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                    "joe-writer-mysql",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            status = (result.stdout or "").strip().lower()
            if status == "healthy":
                log("Docker MySQL 已就绪 (localhost:3307)", Colors.GREEN)
                return True
            # 无 healthcheck 时 State.Status 可能是 running
            if status == "running":
                log("Docker MySQL 已运行 (localhost:3307)", Colors.GREEN)
                return True
        except Exception:
            pass
        time.sleep(2)

    log("MySQL 启动超时，后端可能暂时连不上库", Colors.YELLOW)
    return False


def start_backend(backend_path, port=8000, reload=True):
    """启动后端服务（默认开启 --reload 热重载）"""
    log(f"启动后端服务 (端口: {port}){' · 热重载已开启' if reload else ''}...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_path.parent)
    env["PYTHONUNBUFFERED"] = "1"
    # Windows 下原生文件监听偶发失效，强制轮询更稳
    if _WIN and reload:
        env["WATCHFILES_FORCE_POLLING"] = "true"
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
    ]
    if reload:
        app_dir = backend_path / "app"
        cmd.extend([
            "--reload",
            f"--reload-dir={app_dir}",
            "--reload-include=*.py",
            "--reload-exclude=*.pyc",
            "--reload-exclude=__pycache__",
        ])
    
    return subprocess.Popen(
        cmd,
        cwd=str(backend_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

def start_frontend(frontend_path, port=5173):
    """启动前端 Vite 开发服务（自带 HMR 热更新）"""
    log(f"启动前端服务 (端口: {port}) · HMR 热更新已开启...")
    
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = "http://localhost:8000"
    env["VITE_API_URL"] = "http://localhost:8000"
    # 保证 Vite 控制台立即输出 HMR 日志
    env["FORCE_COLOR"] = "1"
    
    if _WIN:
        cmd = f"npm run dev -- --host 127.0.0.1 --port {port}"
        return subprocess.Popen(
            cmd,
            cwd=str(frontend_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=True,
            encoding="utf-8",
            errors="replace",
        )
    return subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(frontend_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

def print_output(process, prefix, color):
    """打印进程输出"""
    try:
        for line in process.stdout:
            print(f"{color}[{prefix}]{Colors.END} {line.rstrip()}")
    except Exception:
        pass

def wait_for_service(url, timeout=30):
    """等待服务启动"""
    import urllib.request
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except:
            time.sleep(0.5)
    return False

def main():
    parser = argparse.ArgumentParser(description="墨心 AI 辅助写作 启动脚本")
    parser.add_argument("--backend-port", type=int, default=8000, help="后端端口 (默认: 8000)")
    parser.add_argument("--frontend-port", type=int, default=5173, help="前端端口 (默认: 5173)")
    parser.add_argument("--no-reload", action="store_true", help="禁用后端热重载")
    parser.add_argument("--backend-only", action="store_true", help="只启动后端")
    parser.add_argument("--frontend-only", action="store_true", help="只启动前端")
    args = parser.parse_args()
    
    root = get_project_root()
    backend_path = root / "backend"
    frontend_path = root / "frontend"
    
    # 检查路径
    if not backend_path.exists():
        log(f"后端目录不存在: {backend_path}", Colors.RED)
        sys.exit(1)
    
    if not args.backend_only and not frontend_path.exists():
        log(f"前端目录不存在: {frontend_path}", Colors.RED)
        sys.exit(1)
    
    processes = []
    
    try:
        # 启动后端
        if not args.frontend_only:
            # 本地开发默认依赖 Docker MySQL（.env 中 localhost:3307）
            ensure_docker_mysql(root)

            if not check_backend_deps(backend_path):
                sys.exit(1)
            
            backend_proc = start_backend(
                backend_path, 
                port=args.backend_port,
                reload=not args.no_reload
            )
            processes.append(("Backend", backend_proc, Colors.BLUE))
            
            # 等待后端启动（含数据库建表重试，适当加长）
            log("等待后端启动...")
            if wait_for_service(f"http://localhost:{args.backend_port}/health", timeout=60):
                log(f"后端已就绪: http://localhost:{args.backend_port}", Colors.GREEN)
            else:
                log("后端启动超时，继续尝试启动前端...", Colors.YELLOW)
        
        # 启动前端
        if not args.backend_only:
            if not check_frontend_deps(frontend_path):
                sys.exit(1)
            
            frontend_proc = start_frontend(frontend_path, port=args.frontend_port)
            processes.append(("Frontend", frontend_proc, Colors.CYAN))
            
            # 等待前端启动
            log("等待前端启动...")
            time.sleep(3)  # 给 Vite 一些启动时间
            log(f"前端地址: http://localhost:{args.frontend_port}", Colors.GREEN)
        
        # 打印访问信息
        print("\n" + "="*60)
        print(f"  {Colors.GREEN}墨心 · AI 辅助写作 已启动!{Colors.END}")
        print("="*60)
        if not args.frontend_only:
            print(f"  后端 API: {Colors.BLUE}http://localhost:{args.backend_port}{Colors.END}")
            print(f"  API 文档: {Colors.BLUE}http://localhost:{args.backend_port}/docs{Colors.END}")
            if not args.no_reload:
                print(f"  后端热重载: {Colors.GREEN}已开启{Colors.END}（改 .py 自动重启）")
        if not args.backend_only:
            print(f"  前端界面: {Colors.CYAN}http://localhost:{args.frontend_port}{Colors.END}")
            print(f"  前端热更新: {Colors.GREEN}已开启{Colors.END}（改 .vue/.ts 浏览器自动刷新）")
        print("="*60)
        print(f"\n按 Ctrl+C 停止服务\n")
        
        # 实时监控输出
        import threading
        threads = []
        for name, proc, color in processes:
            t = threading.Thread(target=print_output, args=(proc, name, color))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 等待进程结束
        while processes:
            for i, (name, proc, _) in enumerate(processes):
                ret = proc.poll()
                if ret is not None:
                    log(f"{name} 进程已退出 (代码: {ret})", Colors.RED if ret != 0 else Colors.YELLOW)
                    processes.pop(i)
                    break
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        log("\n正在停止服务...")
    finally:
        # 清理进程
        for name, proc, _ in processes:
            log(f"停止 {name}...")
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        
        log("所有服务已停止")

if __name__ == "__main__":
    main()
