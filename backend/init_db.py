#!/usr/bin/env python3
"""
数据库初始化脚本 - 后端专用
用于 Docker 容器启动时自动初始化数据库
"""

import sys
import os

# 确保导入路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_database():
    """初始化数据库表"""
    print("🔄 正在初始化数据库...")
    
    try:
        from app.database import init_database as db_init
        db_init()
        
        print("✅ 数据库初始化完成！")
        print("📋 已创建表:")
        print("   • projects - 项目表")
        print("   • documents - 文档表")
        print("   • settings - 设定表")
        print("   • ai_memory - AI 记忆表")
        print("   • events - 事件表")
        print("   • users - 用户表")
        return True
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
