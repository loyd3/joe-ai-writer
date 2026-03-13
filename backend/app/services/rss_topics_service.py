"""
RSS 热点源 - 通过 RSS 订阅获取热点新闻
作为 Firecrawl 的免费替代方案
"""
import aiohttp
import ssl
import feedparser
from typing import List, Dict, Any
from datetime import datetime


def _get_ssl_context():
    """获取 SSL 上下文"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context


# RSS 源配置
RSS_SOURCES = {
    "知乎": {
        "url": "https://www.zhihu.com/rss",
        "source_name": "知乎精选"
    },
    "澎湃新闻": {
        "url": "https://www.thepaper.cn/rss.xml",
        "source_name": "澎湃新闻"
    },
    "财新": {
        "url": "http://www.caixin.com/rss.xml",
        "source_name": "财新网"
    },
    "36氪": {
        "url": "https://36kr.com/feed",
        "source_name": "36氪"
    },
    "虎嗅": {
        "url": "https://www.huxiu.com/rss.xml",
        "source_name": "虎嗅"
    },
    "Solidot": {
        "url": "https://www.solidot.org/index.rss",
        "source_name": "Solidot"
    }
}


class RSSTopicsService:
    """通过 RSS 获取热点"""
    
    @staticmethod
    async def fetch_rss_feed(url: str, timeout: int = 15) -> str:
        """获取 RSS 内容"""
        try:
            ssl_context = _get_ssl_context()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    ssl=ssl_context,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                ) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        print(f"RSS 请求失败: {url}, 状态码: {resp.status}")
                        return None
        except Exception as e:
            print(f"获取 RSS 失败 {url}: {e}")
            return None
    
    @staticmethod
    def parse_rss_content(xml_content: str, source_name: str) -> List[Dict[str, Any]]:
        """解析 RSS 内容"""
        if not xml_content:
            return []
        
        try:
            feed = feedparser.parse(xml_content)
            topics = []
            
            for entry in feed.entries[:15]:  # 取前15条
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))[:200]
                published = entry.get("published", "")
                
                if title:
                    topics.append({
                        "title": title,
                        "source": source_name,
                        "url": link,
                        "excerpt": summary,
                        "heat": 1000000,  # RSS 没有热度，给个默认值
                        "published": published
                    })
            
            return topics
        except Exception as e:
            print(f"解析 RSS 失败: {e}")
            return []
    
    @staticmethod
    async def fetch_all_rss_topics() -> Dict[str, Any]:
        """获取所有 RSS 源的热点"""
        import asyncio
        
        tasks = []
        source_names = []
        
        for name, config in RSS_SOURCES.items():
            tasks.append(RSSTopicsService.fetch_rss_feed(config["url"]))
            source_names.append((name, config["source_name"]))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_topics = []
        sources_status = {}
        
        for idx, result in enumerate(results):
            source_key, source_name = source_names[idx]
            
            if isinstance(result, Exception):
                sources_status[source_key] = {"status": "error", "error": str(result)}
            elif result:
                topics = RSSTopicsService.parse_rss_content(result, source_name)
                sources_status[source_key] = {"status": "ok", "count": len(topics)}
                all_topics.extend(topics)
            else:
                sources_status[source_key] = {"status": "error", "error": "无数据返回"}
        
        return {
            "topics": all_topics,
            "total": len(all_topics),
            "sources": sources_status,
            "updated_at": datetime.now().isoformat(),
            "type": "rss"
        }


# 兼容层：保持与 HotTopicsService 相同的接口
class HotTopicsServiceRSS(RSSTopicsService):
    """兼容旧接口的 RSS 热点服务"""
    pass
