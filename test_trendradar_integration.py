#!/usr/bin/env python3
"""
TrendRadar 集成测试脚本
测试 TrendRadar 是否正确集成到 joe-ai-writer 项目中
"""
import asyncio
import sys
import os

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.trendradar_adapter import trendradar_adapter
from app.services.hot_topics_service import HotTopicsService


async def test_trendradar_adapter():
    """测试 TrendRadar 适配器"""
    print("=" * 60)
    print("测试 TrendRadar 适配器")
    print("=" * 60)
    
    # 测试获取平台列表
    print("\n1. 获取平台列表...")
    platforms = trendradar_adapter.get_available_platforms()
    print(f"   可用平台数量: {len(platforms)}")
    for p in platforms[:5]:
        print(f"   - {p['name']} ({p['id']})")
    if len(platforms) > 5:
        print(f"   ... 还有 {len(platforms) - 5} 个平台")
    
    # 测试获取热点
    print("\n2. 获取热点数据...")
    result = await trendradar_adapter.fetch_all_hot_topics()
    print(f"   获取结果:")
    print(f"   - 总条数: {result.get('total', 0)}")
    print(f"   - 数据源: {result.get('data_source', 'unknown')}")
    print(f"   - 更新时间: {result.get('updated_at', 'unknown')}")
    
    if result.get('topics'):
        print(f"\n   前5条热点:")
        for i, topic in enumerate(result['topics'][:5], 1):
            print(f"   {i}. [{topic['source']}] {topic['title'][:40]}... (热度: {topic['heat']})")
    
    # 测试搜索
    print("\n3. 测试搜索功能...")
    search_results = await trendradar_adapter.search_topics("AI", limit=5)
    print(f"   搜索 'AI' 结果: {len(search_results)} 条")
    for topic in search_results[:3]:
        print(f"   - {topic['title'][:50]}...")
    
    return result


async def test_hot_topics_service():
    """测试热点服务（已集成 TrendRadar）"""
    print("\n" + "=" * 60)
    print("测试热点服务（TrendRadar 集成）")
    print("=" * 60)
    
    result = await HotTopicsService.fetch_all_hot_topics()
    print(f"\n获取结果:")
    print(f"- 总条数: {result.get('total', 0)}")
    print(f"- 数据源: {result.get('data_source', 'unknown')}")
    print(f"- 平台状态:")
    for source, status in result.get('sources', {}).items():
        if isinstance(status, dict):
            print(f"  * {source}: {status.get('status', 'unknown')} ({status.get('count', 0)} 条)")
    
    if result.get('topics'):
        print(f"\n前5条热点:")
        for i, topic in enumerate(result['topics'][:5], 1):
            heat = topic.get('heat', 0)
            source = topic.get('source', 'unknown')
            title = topic.get('title', '')[:40]
            print(f"{i}. [{source}] {title}... (热度: {heat})")
    
    return result


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("TrendRadar 集成测试")
    print("项目: joe-ai-writer")
    print("=" * 60 + "\n")
    
    try:
        # 测试适配器
        adapter_result = await test_trendradar_adapter()
        
        # 测试热点服务
        service_result = await test_hot_topics_service()
        
        # 总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        
        adapter_total = adapter_result.get('total', 0)
        service_total = service_result.get('total', 0)
        
        if adapter_total > 0:
            print(f"✅ TrendRadar 适配器工作正常 ({adapter_total} 条热点)")
        else:
            print("❌ TrendRadar 适配器未能获取数据")
        
        if service_total > 0:
            print(f"✅ 热点服务集成成功 ({service_total} 条热点)")
        else:
            print("❌ 热点服务未能获取数据")
        
        if adapter_total > 0 or service_total > 0:
            print("\n✅ 集成测试通过！TrendRadar 已成功集成到项目中。")
        else:
            print("\n⚠️ 未能获取热点数据，请检查网络连接或配置。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
