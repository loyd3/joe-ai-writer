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
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True,
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

def start_backend(backend_path, port=8000, reload=True):
    """启动后端服务"""
    log(f"启动后端服务 (端口: {port})...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_path.parent)
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
    ]
    if reload:
        cmd.append("--reload")
    
    return subprocess.Popen(
        cmd,
        cwd=str(backend_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

def start_frontend(frontend_path, port=5173):
    """启动前端服务"""
    log(f"启动前端服务 (端口: {port})...")
    
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = f"http://localhost:8000"
    
    if _WIN:
        cmd = f"npm run dev -- --port {port}"
        return subprocess.Popen(
            cmd,
            cwd=str(frontend_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=True,
        )
    return subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(port)],
        cwd=str(frontend_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
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
            if not check_backend_deps(backend_path):
                sys.exit(1)
            
            backend_proc = start_backend(
                backend_path, 
                port=args.backend_port,
                reload=not args.no_reload
            )
            processes.append(("Backend", backend_proc, Colors.BLUE))
            
            # 等待后端启动
            log("等待后端启动...")
            if wait_for_service(f"http://localhost:{args.backend_port}/health", timeout=30):
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
        if not args.backend_only:
            print(f"  前端界面: {Colors.CYAN}http://localhost:{args.frontend_port}{Colors.END}")
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
