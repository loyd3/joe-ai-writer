"""
TrendRadar 适配器 - 将 TrendRadar 集成到热点写作服务中
"""
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# 添加 TrendRadar 到路径
TRENDRADAR_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'trendradar')
if TRENDRADAR_PATH not in sys.path:
    sys.path.insert(0, TRENDRADAR_PATH)

from trendradar.context import AppContext
from trendradar.core import load_config
from trendradar.crawler import DataFetcher
from trendradar.storage import convert_crawl_results_to_news_data
from trendradar.utils.time import DEFAULT_TIMEZONE


class TrendRadarAdapter:
    """TrendRadar 适配器 - 为热点写作提供数据"""
    
    def __init__(self):
        self.config = None
        self.ctx = None
        self.data_fetcher = None
        self._init_config()
    
    def _init_config(self):
        """初始化配置"""
        try:
            # 加载 TrendRadar 配置
            original_cwd = os.getcwd()
            os.chdir(TRENDRADAR_PATH)
            
            self.config = load_config()
            self.ctx = AppContext(self.config)
            
            # 设置数据获取器
            self.data_fetcher = DataFetcher(proxy_url=None)
            
            os.chdir(original_cwd)
        except Exception as e:
            print(f"[TrendRadarAdapter] 初始化失败: {e}")
            self.config = None
    
    async def fetch_all_hot_topics(self) -> Dict[str, Any]:
        """
        抓取所有平台的热点数据
        
        Returns:
            {
                "topics": [...],
                "total": int,
                "sources": {...},
                "updated_at": str
            }
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(TRENDRADAR_PATH)
            
            # 获取平台列表
            platforms = []
            for platform in self.ctx.platforms:
                if "name" in platform:
                    platforms.append((platform["id"], platform["name"]))
                else:
                    platforms.append(platform["id"])
            
            # 爬取数据
            results, id_to_name, failed_ids = self.data_fetcher.crawl_websites(
                platforms, self.ctx.config["REQUEST_INTERVAL"]
            )
            
            # 转换为标准格式
            topics = []
            sources_status = {}
            
            for source_id, titles_data in results.items():
                platform_name = id_to_name.get(source_id, source_id)
                sources_status[source_id] = {
                    "status": "ok",
                    "count": len(titles_data),
                    "name": platform_name
                }
                
                for title, data in titles_data.items():
                    ranks = data.get("ranks", [])
                    heat = ranks[0] if ranks else 0  # 使用排名作为热度（越小越热）
                    
                    topics.append({
                        "title": title,
                        "heat": self._calculate_heat(heat),
                        "url": data.get("url", ""),
                        "source": platform_name,
                        "rank": heat,
                        "mobile_url": data.get("mobileUrl", ""),
                        "platform_id": source_id
                    })
            
            # 记录失败的源
            for failed_id in failed_ids:
                sources_status[failed_id] = {"status": "error", "error": "抓取失败"}
            
            # 按热度排序
            topics.sort(key=lambda x: x["heat"], reverse=True)
            
            os.chdir(original_cwd)
            
            return {
                "topics": topics[:50],  # 返回前50条
                "total": len(topics),
                "sources": sources_status,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[TrendRadarAdapter] 抓取失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "topics": [],
                "total": 0,
                "sources": {},
                "error": str(e),
                "updated_at": datetime.now().isoformat()
            }
    
    def _calculate_heat(self, rank: int) -> int:
        """
        将排名转换为热度值（排名越小热度越高）
        """
        if rank <= 0:
            return 5000000
        # 排名1 = 1000万热度，排名50 = 100万热度
        heat = int(10000000 / rank)
        return min(heat, 99999999)
    
    async def fetch_topic_detail(self, title: str, platform_id: str = None) -> Optional[Dict[str, Any]]:
        """
        获取话题详细信息
        
        Args:
            title: 话题标题
            platform_id: 平台ID（可选）
            
        Returns:
            话题详情字典
        """
        try:
            return {
                "title": title,
                "source": platform_id or "trendradar",
                "summary": f"关于「{title}」的热门话题讨论...",
                "related_keywords": [title[:5], title[:3] + "热点", title + "最新进展"],
                "url": f"https://www.bing.com/search?q={title}"
            }
        except Exception as e:
            print(f"[TrendRadarAdapter] 获取详情失败: {e}")
            return None
    
    def get_available_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表"""
        if not self.ctx:
            return []
        
        return [
            {
                "id": p["id"],
                "name": p.get("name", p["id"]),
                "enabled": p.get("enabled", True)
            }
            for p in self.ctx.platforms
        ]
    
    async def search_topics(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索热点话题
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的话题列表
        """
        try:
            # 先获取所有热点
            result = await self.fetch_all_hot_topics()
            all_topics = result.get("topics", [])
            
            # 过滤匹配关键词的
            keyword_lower = keyword.lower()
            matched = [
                topic for topic in all_topics
                if keyword_lower in topic.get("title", "").lower()
            ]
            
            return matched[:limit]
            
        except Exception as e:
            print(f"[TrendRadarAdapter] 搜索失败: {e}")
            return []


# 单例实例
trendradar_adapter = TrendRadarAdapter()
