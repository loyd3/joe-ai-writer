"""
网络热点服务 - 抓取各大平台的热门话题和新闻（增强版）
"""
import aiohttp
import asyncio
import ssl
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import re
import random

# 创建 SSL 上下文（用于解决证书问题）
def _get_ssl_context():
    """获取 SSL 上下文，在开发环境中禁用证书验证"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context


# 备用热点数据（当所有抓取都失败时使用）
FALLBACK_TOPICS = [
    {"title": "AI技术发展：大语言模型改变内容创作方式", "source": "科技热点", "heat": 9999999, "category": "科技"},
    {"title": "数字化转型：企业如何应对AI时代的挑战", "source": "商业热点", "heat": 8888888, "category": "商业"},
    {"title": "新能源汽车市场竞争加剧，谁是最后赢家", "source": "汽车热点", "heat": 7777777, "category": "汽车"},
    {"title": "健康生活：如何在高压力环境中保持身心平衡", "source": "生活热点", "heat": 6666666, "category": "生活"},
    {"title": "教育改革：AI辅助教学的未来发展趋势", "source": "教育热点", "heat": 5555555, "category": "教育"},
    {"title": "人工智能伦理：技术发展与社会责任的平衡", "source": "科技热点", "heat": 4444444, "category": "科技"},
    {"title": "消费升级：新一代年轻人的消费观念变化", "source": "商业热点", "heat": 3333333, "category": "商业"},
    {"title": "环境保护：碳中和目标下的产业转型", "source": "环保热点", "heat": 2222222, "category": "环保"},
    {"title": "短视频内容创作：算法推荐时代的流量密码", "source": "互联网热点", "heat": 2111111, "category": "互联网"},
    {"title": "远程办公常态化：工作方式的永久改变", "source": "职场热点", "heat": 1999999, "category": "职场"},
    {"title": "元宇宙概念降温：从炒作到实际应用", "source": "科技热点", "heat": 1888888, "category": "科技"},
    {"title": "跨境电商新机遇：全球化与本土化的平衡", "source": "商业热点", "heat": 1777777, "category": "商业"},
    {"title": "老龄化社会：养老产业的挑战与机遇", "source": "社会热点", "heat": 1666666, "category": "社会"},
    {"title": "心理健康：当代年轻人的焦虑与解压", "source": "健康热点", "heat": 1555555, "category": "健康"},
    {"title": "乡村振兴：数字农业与农村电商发展", "source": "农业热点", "heat": 1444444, "category": "农业"},
]


class HotTopicsCache:
    """热点数据缓存"""
    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._last_update: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=5)  # 缓存5分钟
    
    def get(self) -> Optional[Dict[str, Any]]:
        """获取缓存数据（如果未过期）"""
        if self._cache is None or self._last_update is None:
            return None
        if datetime.now() - self._last_update > self._cache_duration:
            return None
        return self._cache
    
    def set(self, data: Dict[str, Any]):
        """设置缓存数据"""
        self._cache = data
        self._last_update = datetime.now()
    
    def clear(self):
        """清除缓存"""
        self._cache = None
        self._last_update = None


class HotTopicsService:
    """网络热点抓取服务（增强版）"""
    
    # 共享 connector 避免连接池问题
    _connector = None
    _cache = HotTopicsCache()
    
    @classmethod
    def _get_connector(cls):
        """获取共享的 TCP connector"""
        if cls._connector is None or cls._connector.closed:
            cls._connector = aiohttp.TCPConnector(
                ssl=_get_ssl_context(),
                limit=20,
                limit_per_host=5,
                enable_cleanup_closed=True,
                force_close=True,
                ttl_dns_cache=300,
            )
        return cls._connector
    
    @staticmethod
    async def fetch_weibo_hot() -> List[Dict[str, Any]]:
        """抓取微博热搜"""
        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://weibo.com/",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            connector = HotTopicsService._get_connector()
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        topics = []
                        realtime_list = data.get("data", {}).get("realtime", [])
                        for item in realtime_list[:20]:
                            title = item.get("note", "").strip()
                            if title:
                                topics.append({
                                    "title": title,
                                    "heat": item.get("num", 0),
                                    "url": f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                                    "source": "微博热搜",
                                    "category": item.get("category", ""),
                                    "rank": len(topics) + 1
                                })
                        print(f"[HotTopics] 微博热搜获取成功: {len(topics)} 条")
                        return topics
                    else:
                        print(f"[HotTopics] 微博热搜返回状态码: {resp.status}")
        except asyncio.TimeoutError:
            print(f"[HotTopics] 微博热搜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取微博热搜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_zhihu_hot() -> List[Dict[str, Any]]:
        """抓取知乎热榜"""
        try:
            url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.zhihu.com/",
                "Accept": "application/json",
                "x-requested-with": "fetch",
            }
            connector = HotTopicsService._get_connector()
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        topics = []
                        for item in data.get("data", [])[:20]:
                            detail = item.get("target", {})
                            title = detail.get("title", "").strip()
                            if title:
                                heat_text = item.get("detail_text", "")
                                heat_num = 0
                                if "万" in heat_text:
                                    try:
                                        heat_num = int(float(heat_text.replace("万", "")) * 10000)
                                    except:
                                        pass
                                topics.append({
                                    "title": title,
                                    "heat": heat_num or detail.get("heat", 0),
                                    "url": detail.get("url", ""),
                                    "source": "知乎热榜",
                                    "excerpt": detail.get("excerpt", "")[:200],
                                    "rank": len(topics) + 1
                                })
                        print(f"[HotTopics] 知乎热榜获取成功: {len(topics)} 条")
                        return topics
                    else:
                        print(f"[HotTopics] 知乎热榜返回状态码: {resp.status}")
        except asyncio.TimeoutError:
            print(f"[HotTopics] 知乎热榜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取知乎热榜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_baidu_hot() -> List[Dict[str, Any]]:
        """抓取百度热搜"""
        try:
            url = "https://top.baidu.com/board?tab=realtime"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            connector = HotTopicsService._get_connector()
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        topics = []
                        
                        # 尝试多种解析方式
                        # 方式1: JSON 数据嵌入
                        pattern1 = r'"word":\s*"([^"]+)"[^}]*"hotScore":\s*"?([^",}]+)"?'
                        matches = re.findall(pattern1, html)
                        for title, heat in matches[:20]:
                            title = title.strip()
                            if title:
                                topics.append({
                                    "title": title,
                                    "heat": heat.replace('"', '').strip(),
                                    "url": f"https://www.baidu.com/s?wd={title}",
                                    "source": "百度热搜",
                                    "rank": len(topics) + 1
                                })
                        
                        # 方式2: HTML 解析（备用）
                        if not topics:
                            pattern2 = r'<div[^>]*class="[^"]*content_1YWBm[^"]*"[^>]*>.*?<div[^>]*class="[^"]*c-single-text-ellipsis[^"]*"[^>]*>([^<]+)</div>'
                            titles = re.findall(pattern2, html, re.DOTALL)
                            for idx, title in enumerate(titles[:20]):
                                title = title.strip()
                                if title:
                                    topics.append({
                                        "title": title,
                                        "heat": (20 - idx) * 100000,
                                        "url": f"https://www.baidu.com/s?wd={title}",
                                        "source": "百度热搜",
                                        "rank": idx + 1
                                    })
                        
                        if topics:
                            print(f"[HotTopics] 百度热搜获取成功: {len(topics)} 条")
                            return topics
                    else:
                        print(f"[HotTopics] 百度热搜返回状态码: {resp.status}")
        except asyncio.TimeoutError:
            print(f"[HotTopics] 百度热搜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取百度热搜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_toutiao_hot() -> List[Dict[str, Any]]:
        """抓取头条热搜"""
        try:
            # 尝试多个可能的API端点
            urls = [
                "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
                "https://www.toutiao.com/api/pc/hot_gallery/",
            ]
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.toutiao.com/",
                "Accept": "application/json, text/plain, */*",
            }
            connector = HotTopicsService._get_connector()
            
            for url in urls:
                try:
                    async with aiohttp.ClientSession(connector=connector) as session:
                        async with session.get(
                            url, 
                            headers=headers, 
                            timeout=aiohttp.ClientTimeout(total=8)
                        ) as resp:
                            if resp.status == 200:
                                content_type = resp.headers.get('content-type', '')
                                if 'application/json' in content_type:
                                    data = await resp.json()
                                    topics = []
                                    for item in data.get("data", [])[:20]:
                                        title = item.get("Title", "").strip()
                                        if title:
                                            topics.append({
                                                "title": title,
                                                "heat": item.get("HotValue", 0),
                                                "url": item.get("Url", ""),
                                                "source": "头条热榜",
                                                "label": item.get("Label", ""),
                                                "rank": len(topics) + 1
                                            })
                                    if topics:
                                        print(f"[HotTopics] 头条热榜获取成功: {len(topics)} 条")
                                        return topics
                except Exception as e:
                    print(f"[HotTopics] 头条API {url} 失败: {e}")
                    continue
        except asyncio.TimeoutError:
            print(f"[HotTopics] 头条热榜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取头条热搜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_bilibili_hot() -> List[Dict[str, Any]]:
        """抓取B站热门"""
        try:
            url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
            }
            connector = HotTopicsService._get_connector()
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        topics = []
                        if data.get("code") == 0:
                            for item in data.get("data", {}).get("list", [])[:15]:
                                title = item.get("title", "").strip()
                                if title:
                                    topics.append({
                                        "title": title,
                                        "heat": item.get("stat", {}).get("view", 0),
                                        "url": item.get("short_link", item.get("bvid", "")),
                                        "source": "B站热门",
                                        "category": item.get("tname", ""),
                                        "rank": len(topics) + 1
                                    })
                        if topics:
                            print(f"[HotTopics] B站热门获取成功: {len(topics)} 条")
                            return topics
                    else:
                        print(f"[HotTopics] B站热门返回状态码: {resp.status}")
        except asyncio.TimeoutError:
            print(f"[HotTopics] B站热门请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取B站热门失败: {e}")
        return []
    
    @staticmethod
    async def fetch_douyin_hot() -> List[Dict[str, Any]]:
        """抓取抖音热榜"""
        try:
            url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.douyin.com/",
            }
            connector = HotTopicsService._get_connector()
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        topics = []
                        word_list = data.get("data", {}).get("word_list", [])
                        for item in word_list[:20]:
                            title = item.get("word", "").strip()
                            if title:
                                topics.append({
                                    "title": title,
                                    "heat": item.get("hot_value", 0),
                                    "url": f"https://www.douyin.com/search/{title}",
                                    "source": "抖音热榜",
                                    "rank": len(topics) + 1
                                })
                        if topics:
                            print(f"[HotTopics] 抖音热榜获取成功: {len(topics)} 条")
                            return topics
                    else:
                        print(f"[HotTopics] 抖音热榜返回状态码: {resp.status}")
        except asyncio.TimeoutError:
            print(f"[HotTopics] 抖音热榜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取抖音热榜失败: {e}")
        return []
    
    @staticmethod
    async def fetch_all_hot_topics(use_cache: bool = True) -> Dict[str, Any]:
        """
        抓取所有平台的热点（微博、知乎、百度、头条、B站、抖音）
        
        Args:
            use_cache: 是否使用缓存（默认True，5分钟内重复请求返回缓存）
        """
        # 检查缓存
        if use_cache:
            cached = HotTopicsService._cache.get()
            if cached:
                print("[HotTopics] 返回缓存数据")
                return cached
        
        print("[HotTopics] 开始抓取热点数据...")
        
        # 所有抓取任务
        fetch_tasks = [
            ("weibo", HotTopicsService.fetch_weibo_hot()),
            ("zhihu", HotTopicsService.fetch_zhihu_hot()),
            ("baidu", HotTopicsService.fetch_baidu_hot()),
            ("toutiao", HotTopicsService.fetch_toutiao_hot()),
            ("bilibili", HotTopicsService.fetch_bilibili_hot()),
            ("douyin", HotTopicsService.fetch_douyin_hot()),
        ]
        
        # 使用 gather 并行执行所有任务
        results = await asyncio.gather(
            *[task for _, task in fetch_tasks],
            return_exceptions=True
        )
        
        all_topics = []
        sources_status = {}
        success_count = 0
        
        for idx, (source_name, _) in enumerate(fetch_tasks):
            result = results[idx]
            if isinstance(result, Exception):
                sources_status[source_name] = {"status": "error", "error": str(result)[:100]}
                print(f"[HotTopics] {source_name} 抓取异常: {result}")
            elif result and len(result) > 0:
                sources_status[source_name] = {"status": "ok", "count": len(result)}
                all_topics.extend(result)
                success_count += 1
                print(f"[HotTopics] {source_name} 成功获取 {len(result)} 条")
            else:
                sources_status[source_name] = {"status": "empty", "count": 0}
                print(f"[HotTopics] {source_name} 返回空数据")
        
        # 如果没有抓取到任何数据，使用备用数据
        use_fallback = len(all_topics) == 0
        if use_fallback:
            all_topics = FALLBACK_TOPICS.copy()
            sources_status["fallback"] = {"status": "ok", "count": len(FALLBACK_TOPICS), "note": "使用备用数据"}
            print(f"[HotTopics] 所有平台抓取失败，使用备用数据: {len(FALLBACK_TOPICS)} 条")
        
        # 去重：基于标题相似度去重
        unique_topics = HotTopicsService._deduplicate_topics(all_topics)
        
        # 按热度排序
        unique_topics.sort(key=lambda x: HotTopicsService._parse_heat(x.get("heat", 0)), reverse=True)
        
        result = {
            "topics": unique_topics[:50],
            "total": len(unique_topics),
            "sources": sources_status,
            "updated_at": datetime.now().isoformat(),
            "data_source": "fallback" if use_fallback else "api",
            "success_rate": f"{success_count}/{len(fetch_tasks)}"
        }
        
        # 更新缓存
        HotTopicsService._cache.set(result)
        
        print(f"[HotTopics] 抓取完成，共 {len(unique_topics)} 条热点（去重前 {len(all_topics)} 条）")
        return result
    
    @staticmethod
    def _deduplicate_topics(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于标题相似度去重"""
        unique = []
        seen_titles = set()
        
        for topic in topics:
            title = topic.get("title", "").strip()
            if not title:
                continue
            
            # 标准化标题用于比较
            normalized = HotTopicsService._normalize_title(title)
            
            # 检查是否已存在相似标题
            is_duplicate = False
            for seen in seen_titles:
                if HotTopicsService._title_similarity(normalized, seen) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_titles.add(normalized)
                unique.append(topic)
        
        return unique
    
    @staticmethod
    def _normalize_title(title: str) -> str:
        """标准化标题用于比较"""
        # 移除标点、空格，转为小写
        title = re.sub(r'[^\w\u4e00-\u9fff]', '', title)
        return title.lower().strip()
    
    @staticmethod
    def _title_similarity(a: str, b: str) -> float:
        """计算两个标题的相似度（简单版本）"""
        if a == b:
            return 1.0
        if len(a) == 0 or len(b) == 0:
            return 0.0
        
        # 使用最长公共子串的简单近似
        shorter, longer = (a, b) if len(a) < len(b) else (b, a)
        if len(longer) == 0:
            return 0.0
        
        # 检查是否包含
        if shorter in longer:
            return len(shorter) / len(longer) * 0.9
        
        # 计算字符重叠率
        set_a = set(a)
        set_b = set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def _parse_heat(heat: Any) -> int:
        """解析热度值为数字"""
        if isinstance(heat, (int, float)):
            return int(heat)
        if isinstance(heat, str):
            # 处理 "12.3万" 这样的格式
            heat = heat.replace(",", "").replace(" ", "")
            if "万" in heat:
                try:
                    return int(float(heat.replace("万", "")) * 10000)
                except:
                    pass
            if "亿" in heat:
                try:
                    return int(float(heat.replace("亿", "")) * 100000000)
                except:
                    pass
            try:
                return int(heat)
            except:
                pass
        return random.randint(100000, 999999)  # 默认随机热度
    
    @staticmethod
    async def fetch_topic_detail(title: str, source: str = "zhihu") -> Optional[Dict[str, Any]]:
        """
        获取话题详细信息（通过搜索获取内容摘要）
        """
        return {
            "title": title,
            "source": source,
            "summary": f"关于「{title}」的相关讨论和新闻...",
            "related_keywords": [title[:5], title[:3] + "事件", title + "最新"],
            "url": f"https://www.bing.com/search?q={title}"
        }
    
    @staticmethod
    def clear_cache():
        """清除缓存"""
        HotTopicsService._cache.clear()
        print("[HotTopics] 缓存已清除")
