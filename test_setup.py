#!/usr/bin/env python3
"""
墨心 - 测试脚本
验证所有组件是否正确配置
"""
import sys
import os

def test_backend_imports():
    """测试后端模块导入"""
    print("Testing backend imports...")
    try:
        os.chdir('/Users/loyd/PycharmProjects/joe-ai-writer/backend')
        sys.path.insert(0, '/Users/loyd/PycharmProjects/joe-ai-writer/backend')
        
        from app.main import app
        from app.core.config import get_settings
        from app.core.ai_client import get_ai_client
        from app.models.models import Project, Document, AIMemory, Event
        from app.api import projects, ai, system, events
        
        print("✓ All backend imports successful")
        return True
    except Exception as e:
        print(f"✗ Backend import failed: {e}")
        return False

def test_frontend_structure():
    """测试前端文件结构"""
    print("\nTesting frontend structure...")
    import glob
    
    required_files = [
        'frontend/src/components/AIConfigPanel.vue',
        'frontend/src/components/EventManager.vue',
        'frontend/src/components/ProjectSettingsManager.vue',
        'frontend/src/api/index.ts',
        'frontend/src/stores/project.ts'
    ]
    
    base_path = '/Users/loyd/PycharmProjects/joe-ai-writer'
    all_ok = True
    
    for file in required_files:
        path = os.path.join(base_path, file)
        if os.path.exists(path):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} missing")
            all_ok = False
    
    return all_ok

def test_start_script():
    """测试启动脚本"""
    print("\nTesting start script...")
    path = '/Users/loyd/PycharmProjects/joe-ai-writer/start.py'
    
    if os.path.exists(path):
        print("  ✓ start.py exists")
        # Check if it's executable
        if os.access(path, os.X_OK):
            print("  ✓ start.py is executable")
        return True
    else:
        print("  ✗ start.py missing")
        return False

def test_env_template():
    """测试环境变量模板"""
    print("\nTesting environment template...")
    path = '/Users/loyd/PycharmProjects/joe-ai-writer/.env.example'
    
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
            checks = [
                ('AI_PROVIDER' in content, 'AI_PROVIDER'),
                ('DEEPSEEK_API_KEY' in content, 'DEEPSEEK_API_KEY'),
                ('SILICONFLOW_API_KEY' in content, 'SILICONFLOW_API_KEY'),
            ]
            for check, name in checks:
                if check:
                    print(f"  ✓ {name} found")
                else:
                    print(f"  ✗ {name} missing")
        return True
    else:
        print("  ✗ .env.example missing")
        return False

def main():
    print("="*60)
    print("墨心 - Configuration Test")
    print("="*60)
    
    results = [
        test_backend_imports(),
        test_frontend_structure(),
        test_start_script(),
        test_env_template(),
    ]
    
    print("\n" + "="*60)
    if all(results):
        print("All tests passed! ✓")
        print("\nYou can now start the application with:")
        print("  python3 start.py")
    else:
        print("Some tests failed. Please check the output above.")
        sys.exit(1)
    print("="*60)

if __name__ == "__main__":
    main()
