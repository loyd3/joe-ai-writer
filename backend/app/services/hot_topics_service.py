"""
网络热点服务 - 抓取各大平台的热门话题和新闻
集成 TrendRadar 增强热点获取能力
"""
import aiohttp
import asyncio
import ssl
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re

# 导入 TrendRadar 适配器
from app.services.trendradar_adapter import trendradar_adapter

# 创建 SSL 上下文（用于解决证书问题）
def _get_ssl_context():
    """获取 SSL 上下文，在开发环境中禁用证书验证"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context


# 备用热点数据（当所有抓取都失败时使用）
FALLBACK_TOPICS = [
    {"title": "AI技术发展：大语言模型改变内容创作方式", "source": "科技热点", "heat": 9999999},
    {"title": "数字化转型：企业如何应对AI时代的挑战", "source": "商业热点", "heat": 8888888},
    {"title": "新能源汽车市场竞争加剧，谁是最后赢家", "source": "汽车热点", "heat": 7777777},
    {"title": "健康生活：如何在高压力环境中保持身心平衡", "source": "生活热点", "heat": 6666666},
    {"title": "教育改革：AI辅助教学的未来发展趋势", "source": "教育热点", "heat": 5555555},
    {"title": "人工智能伦理：技术发展与社会责任的平衡", "source": "科技热点", "heat": 4444444},
    {"title": "消费升级：新一代年轻人的消费观念变化", "source": "商业热点", "heat": 3333333},
    {"title": "环境保护：碳中和目标下的产业转型", "source": "环保热点", "heat": 2222222},
]


class HotTopicsService:
    """网络热点抓取服务"""
    
    @staticmethod
    async def fetch_weibo_hot() -> List[Dict[str, Any]]:
        """抓取微博热搜"""
        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            ssl_context = _get_ssl_context()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), ssl=ssl_context) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        topics = []
                        realtime_list = data.get("data", {}).get("realtime", [])
                        for item in realtime_list[:20]:  # 取前20条
                            topics.append({
                                "title": item.get("note", ""),
                                "heat": item.get("num", 0),
                                "url": f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                                "source": "微博热搜",
                                "category": item.get("category", "")
                            })
                        return topics
        except Exception as e:
            print(f"抓取微博热搜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_zhihu_hot() -> List[Dict[str, Any]]:
        """抓取知乎热榜"""
        try:
            url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"
            }
            ssl_context = _get_ssl_context()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=ssl_context) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        topics = []
                        for item in data.get("data", [])[:20]:
                            detail = item.get("target", {})
                            topics.append({
                                "title": detail.get("title", ""),
                                "heat": detail.get("heat", 0) or item.get("detail_text", ""),
                                "url": detail.get("url", ""),
                                "source": "知乎热榜",
                                "excerpt": detail.get("excerpt", "")[:200]
                            })
                        return topics
        except Exception as e:
            print(f"抓取知乎热榜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_baidu_hot() -> List[Dict[str, Any]]:
        """抓取百度热搜"""
        try:
            url = "https://top.baidu.com/board?tab=realtime"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"
            }
            ssl_context = _get_ssl_context()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=ssl_context) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        # 解析百度热搜数据
                        topics = []
                        # 简单的正则提取
                        pattern = r'"word":\s*"([^"]+)"[^}]*"hotScore":\s*"([^"]+)"'
                        matches = re.findall(pattern, html)
                        for title, heat in matches[:20]:
                            topics.append({
                                "title": title,
                                "heat": heat,
                                "url": f"https://www.baidu.com/s?wd={title}",
                                "source": "百度热搜"
                            })
                        return topics
        except Exception as e:
            print(f"抓取百度热搜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_toutiao_hot() -> List[Dict[str, Any]]:
        """抓取头条热搜"""
        try:
            url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
                "Referer": "https://www.toutiao.com/"
            }
            ssl_context = _get_ssl_context()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=ssl_context) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        topics = []
                        for item in data.get("data", [])[:20]:
                            topics.append({
                                "title": item.get("Title", ""),
                                "heat": item.get("HotValue", 0),
                                "url": item.get("Url", ""),
                                "source": "头条热榜",
                                "label": item.get("Label", "")
                            })
                        return topics
        except Exception as e:
            print(f"抓取头条热搜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_all_hot_topics() -> Dict[str, Any]:
        """
        抓取所有平台的热点
        优先使用 TrendRadar，失败时回退到传统抓取方式
        """
        # 首先尝试使用 TrendRadar 获取热点
        try:
            print("[HotTopicsService] 使用 TrendRadar 获取热点...")
            trendradar_result = await trendradar_adapter.fetch_all_hot_topics()
            
            if trendradar_result.get("total", 0) > 0:
                print(f"[HotTopicsService] TrendRadar 成功获取 {trendar_result['total']} 条热点")
                # 添加数据来源标记
                trendradar_result["data_source"] = "trendradar"
                return trendradar_result
            else:
                print("[HotTopicsService] TrendRadar 未返回数据，回退到传统抓取")
        except Exception as e:
            print(f"[HotTopicsService] TrendRadar 失败: {e}，回退到传统抓取")
        
        # 回退到传统抓取方式
        tasks = [
            HotTopicsService.fetch_weibo_hot(),
            HotTopicsService.fetch_zhihu_hot(),
            HotTopicsService.fetch_baidu_hot(),
            HotTopicsService.fetch_toutiao_hot(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_topics = []
        sources_status = {}
        
        source_names = ["weibo", "zhihu", "baidu", "toutiao"]
        
        for idx, result in enumerate(results):
            source = source_names[idx]
            if isinstance(result, Exception):
                sources_status[source] = {"status": "error", "error": str(result)}
            else:
                sources_status[source] = {"status": "ok", "count": len(result)}
                all_topics.extend(result)
        
        # 如果没有抓取到任何数据，使用备用数据
        use_fallback = len(all_topics) == 0
        if use_fallback:
            all_topics = FALLBACK_TOPICS.copy()
            sources_status["fallback"] = {"status": "ok", "count": len(FALLBACK_TOPICS), "note": "使用备用数据"}
        
        # 按热度排序
        all_topics.sort(key=lambda x: HotTopicsService._parse_heat(x.get("heat", 0)), reverse=True)
        
        return {
            "topics": all_topics[:50],  # 返回前50条
            "total": len(all_topics),
            "sources": sources_status,
            "updated_at": datetime.now().isoformat(),
            "data_source": "legacy"
        }
    
    @staticmethod
    def _parse_heat(heat: Any) -> int:
        """解析热度值为数字"""
        if isinstance(heat, (int, float)):
            return int(heat)
        if isinstance(heat, str):
            # 处理 "12.3万" 这样的格式
            heat = heat.replace(",", "")
            if "万" in heat:
                try:
                    return int(float(heat.replace("万", "")) * 10000)
                except:
                    pass
            try:
                return int(heat)
            except:
                pass
        return 0
    
    @staticmethod
    async def fetch_topic_detail(title: str, source: str = "zhihu") -> Optional[Dict[str, Any]]:
        """
        获取话题详细信息（通过搜索获取内容摘要）
        这是一个简化版本，实际可以接入搜索引擎API
        """
        # 模拟返回话题的相关信息
        # 实际项目中可以接入 Bing/Google 搜索API
        return {
            "title": title,
            "source": source,
            "summary": f"关于「{title}」的相关讨论和新闻...",
            "related_keywords": [title[:5], title[:3] + "事件", title + "最新"],
            "url": f"https://www.bing.com/search?q={title}"
        }
