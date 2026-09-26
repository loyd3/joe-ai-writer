"""
网络热点服务 - 抓取各大平台的热门话题和新闻（增强版）

注意：不要跨多个 ClientSession 共享同一个 TCPConnector。
aiohttp 在 Session 关闭时默认会关掉其所拥有的 connector，
并行 gather 时一个平台先结束就会把其它请求打成 「Connector is closed」。
本文件改为：一次抓取共用一个 Session；或每个请求自建独立 Session。
"""
import aiohttp
import asyncio
import ssl
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
import random


def _get_ssl_context():
    """开发环境放宽证书校验，避免部分站点证书链问题。"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context


# 静态保底（所有网络源都失败时）
FALLBACK_TOPICS = [
    {"title": "AI技术发展：大语言模型改变内容创作方式", "source": "保底热点", "heat": 9999999, "category": "科技"},
    {"title": "数字化转型：企业如何应对AI时代的挑战", "source": "保底热点", "heat": 8888888, "category": "商业"},
    {"title": "新能源汽车市场竞争加剧，谁是最后赢家", "source": "保底热点", "heat": 7777777, "category": "汽车"},
    {"title": "健康生活：如何在高压力环境中保持身心平衡", "source": "保底热点", "heat": 6666666, "category": "生活"},
    {"title": "教育改革：AI辅助教学的未来发展趋势", "source": "保底热点", "heat": 5555555, "category": "教育"},
    {"title": "人工智能伦理：技术发展与社会责任的平衡", "source": "保底热点", "heat": 4444444, "category": "科技"},
    {"title": "消费升级：新一代年轻人的消费观念变化", "source": "保底热点", "heat": 3333333, "category": "商业"},
    {"title": "环境保护：碳中和目标下的产业转型", "source": "保底热点", "heat": 2222222, "category": "环保"},
    {"title": "短视频内容创作：算法推荐时代的流量密码", "source": "保底热点", "heat": 2111111, "category": "互联网"},
    {"title": "远程办公常态化：工作方式的永久改变", "source": "保底热点", "heat": 1999999, "category": "职场"},
    {"title": "元宇宙概念降温：从炒作到实际应用", "source": "保底热点", "heat": 1888888, "category": "科技"},
    {"title": "跨境电商新机遇：全球化与本土化的平衡", "source": "保底热点", "heat": 1777777, "category": "商业"},
    {"title": "老龄化社会：养老产业的挑战与机遇", "source": "保底热点", "heat": 1666666, "category": "社会"},
    {"title": "心理健康：当代年轻人的焦虑与解压", "source": "保底热点", "heat": 1555555, "category": "健康"},
    {"title": "乡村振兴：数字农业与农村电商发展", "source": "保底热点", "heat": 1444444, "category": "农业"},
]

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


class HotTopicsCache:
    """热点数据缓存"""

    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._last_update: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=5)

    def get(self) -> Optional[Dict[str, Any]]:
        if self._cache is None or self._last_update is None:
            return None
        if datetime.now() - self._last_update > self._cache_duration:
            return None
        return self._cache

    def set(self, data: Dict[str, Any]):
        self._cache = data
        self._last_update = datetime.now()

    def clear(self):
        self._cache = None
        self._last_update = None


class HotTopicsService:
    """网络热点抓取服务"""

    _cache = HotTopicsCache()

    @staticmethod
    def _new_session() -> aiohttp.ClientSession:
        """每次创建自有 connector 的 Session（关闭时一并释放，互不干扰）。"""
        connector = aiohttp.TCPConnector(
            ssl=_get_ssl_context(),
            limit=20,
            limit_per_host=6,
            enable_cleanup_closed=True,
            force_close=True,
            ttl_dns_cache=300,
        )
        return aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=12, connect=6),
            headers={"User-Agent": _BROWSER_UA, "Accept-Language": "zh-CN,zh;q=0.9"},
        )

    @staticmethod
    async def _get(
        session: aiohttp.ClientSession,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10,
    ) -> aiohttp.ClientResponse:
        return await session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
        )

    # ---------- 各平台 ----------

    @staticmethod
    async def fetch_weibo_hot(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """抓取微博热搜"""
        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            headers = {
                "Referer": "https://weibo.com/",
                "Accept": "application/json, text/plain, */*",
            }
            async with await HotTopicsService._get(session, url, headers=headers) as resp:
                if resp.status != 200:
                    print(f"[HotTopics] 微博热搜返回状态码: {resp.status}")
                    return []
                data = await resp.json(content_type=None)
                topics = []
                for item in (data.get("data") or {}).get("realtime") or []:
                    title = (item.get("note") or "").strip()
                    if not title:
                        continue
                    topics.append({
                        "title": title,
                        "heat": item.get("num", 0),
                        "url": f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                        "source": "微博热搜",
                        "category": item.get("category") or "",
                        "rank": len(topics) + 1,
                    })
                    if len(topics) >= 20:
                        break
                print(f"[HotTopics] 微博热搜获取成功: {len(topics)} 条")
                return topics
        except asyncio.TimeoutError:
            print("[HotTopics] 微博热搜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取微博热搜失败: {e}")
        return []

    @staticmethod
    async def fetch_zhihu_hot(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """抓取知乎热榜（官方接口常 401，失败时由聚合源兜底）。"""
        try:
            url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20&desktop=true"
            headers = {
                "Referer": "https://www.zhihu.com/hot",
                "Accept": "application/json, text/plain, */*",
                "x-requested-with": "fetch",
                "x-api-version": "3.0.76",
            }
            async with await HotTopicsService._get(session, url, headers=headers) as resp:
                if resp.status != 200:
                    print(f"[HotTopics] 知乎热榜返回状态码: {resp.status}")
                    return []
                data = await resp.json(content_type=None)
                topics = []
                for item in data.get("data") or []:
                    detail = item.get("target") or {}
                    title = (detail.get("title") or "").strip()
                    if not title:
                        continue
                    heat_text = item.get("detail_text") or ""
                    heat_num = 0
                    if "万" in heat_text:
                        try:
                            heat_num = int(float(heat_text.replace("万热度", "").replace("万", "")) * 10000)
                        except Exception:
                            pass
                    topics.append({
                        "title": title,
                        "heat": heat_num or detail.get("heat") or 0,
                        "url": detail.get("url") or "",
                        "source": "知乎热榜",
                        "excerpt": (detail.get("excerpt") or "")[:200],
                        "rank": len(topics) + 1,
                    })
                    if len(topics) >= 20:
                        break
                print(f"[HotTopics] 知乎热榜获取成功: {len(topics)} 条")
                return topics
        except asyncio.TimeoutError:
            print("[HotTopics] 知乎热榜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取知乎热榜失败: {e}")
        return []

    @staticmethod
    async def fetch_baidu_hot(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """抓取百度热搜"""
        try:
            url = "https://top.baidu.com/board?tab=realtime"
            headers = {
                "Referer": "https://www.baidu.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            async with await HotTopicsService._get(session, url, headers=headers) as resp:
                if resp.status != 200:
                    print(f"[HotTopics] 百度热搜返回状态码: {resp.status}")
                    return []
                html = await resp.text()
                topics = []
                pattern1 = r'"word":\s*"([^"]+)"[^}]*"hotScore":\s*"?([^",}]+)"?'
                for title, heat in re.findall(pattern1, html)[:20]:
                    title = title.strip()
                    if not title:
                        continue
                    topics.append({
                        "title": title,
                        "heat": str(heat).replace('"', "").strip(),
                        "url": f"https://www.baidu.com/s?wd={title}",
                        "source": "百度热搜",
                        "rank": len(topics) + 1,
                    })
                if not topics:
                    pattern2 = (
                        r'<div[^>]*class="[^"]*c-single-text-ellipsis[^"]*"[^>]*>([^<]+)</div>'
                    )
                    for idx, title in enumerate(re.findall(pattern2, html)[:20]):
                        title = title.strip()
                        if not title:
                            continue
                        topics.append({
                            "title": title,
                            "heat": (20 - idx) * 100000,
                            "url": f"https://www.baidu.com/s?wd={title}",
                            "source": "百度热搜",
                            "rank": idx + 1,
                        })
                if topics:
                    print(f"[HotTopics] 百度热搜获取成功: {len(topics)} 条")
                return topics
        except asyncio.TimeoutError:
            print("[HotTopics] 百度热搜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取百度热搜失败: {e}")
        return []

    @staticmethod
    async def fetch_toutiao_hot(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """抓取头条热榜"""
        urls = [
            "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
            "https://www.toutiao.com/api/pc/hot_gallery/",
        ]
        headers = {
            "Referer": "https://www.toutiao.com/",
            "Accept": "application/json, text/plain, */*",
        }
        for url in urls:
            try:
                async with await HotTopicsService._get(
                    session, url, headers=headers, timeout=8
                ) as resp:
                    if resp.status != 200:
                        continue
                    content_type = resp.headers.get("content-type", "")
                    if "application/json" not in content_type and "json" not in content_type:
                        # 仍尝试按 JSON 解析
                        pass
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        continue
                    topics = []
                    for item in data.get("data") or []:
                        title = (item.get("Title") or item.get("title") or "").strip()
                        if not title:
                            continue
                        topics.append({
                            "title": title,
                            "heat": item.get("HotValue") or item.get("hot_value") or 0,
                            "url": item.get("Url") or item.get("url") or "",
                            "source": "头条热榜",
                            "label": item.get("Label") or "",
                            "rank": len(topics) + 1,
                        })
                        if len(topics) >= 20:
                            break
                    if topics:
                        print(f"[HotTopics] 头条热榜获取成功: {len(topics)} 条")
                        return topics
            except Exception as e:
                print(f"[HotTopics] 头条API {url} 失败: {e}")
        return []

    @staticmethod
    async def fetch_bilibili_hot(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """抓取 B 站热门"""
        try:
            url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
            headers = {"Referer": "https://www.bilibili.com/"}
            async with await HotTopicsService._get(session, url, headers=headers) as resp:
                if resp.status != 200:
                    print(f"[HotTopics] B站热门返回状态码: {resp.status}")
                    return []
                data = await resp.json(content_type=None)
                topics = []
                if data.get("code") == 0:
                    for item in (data.get("data") or {}).get("list") or []:
                        title = (item.get("title") or "").strip()
                        if not title:
                            continue
                        topics.append({
                            "title": title,
                            "heat": (item.get("stat") or {}).get("view", 0),
                            "url": item.get("short_link") or item.get("bvid") or "",
                            "source": "B站热门",
                            "category": item.get("tname") or "",
                            "rank": len(topics) + 1,
                        })
                        if len(topics) >= 15:
                            break
                if topics:
                    print(f"[HotTopics] B站热门获取成功: {len(topics)} 条")
                return topics
        except asyncio.TimeoutError:
            print("[HotTopics] B站热门请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取B站热门失败: {e}")
        return []

    @staticmethod
    async def fetch_douyin_hot(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """抓取抖音热榜（官方常需签名，失败由聚合源兜底）。"""
        try:
            url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
            headers = {"Referer": "https://www.douyin.com/"}
            async with await HotTopicsService._get(session, url, headers=headers) as resp:
                if resp.status != 200:
                    print(f"[HotTopics] 抖音热榜返回状态码: {resp.status}")
                    return []
                data = await resp.json(content_type=None)
                topics = []
                for item in (data.get("data") or {}).get("word_list") or []:
                    title = (item.get("word") or "").strip()
                    if not title:
                        continue
                    topics.append({
                        "title": title,
                        "heat": item.get("hot_value") or 0,
                        "url": f"https://www.douyin.com/search/{title}",
                        "source": "抖音热榜",
                        "rank": len(topics) + 1,
                    })
                    if len(topics) >= 20:
                        break
                if topics:
                    print(f"[HotTopics] 抖音热榜获取成功: {len(topics)} 条")
                return topics
        except asyncio.TimeoutError:
            print("[HotTopics] 抖音热榜请求超时")
        except Exception as e:
            print(f"[HotTopics] 抓取抖音热榜失败: {e}")
        return []

    @staticmethod
    async def fetch_vvhan_board(
        session: aiohttp.ClientSession,
        board: str,
        source_name: str,
    ) -> List[Dict[str, Any]]:
        """
        公开聚合热榜（官方接口被拦时的补充源）。
        https://api.vvhan.com/api/hotlist/{board}
        """
        try:
            url = f"https://api.vvhan.com/api/hotlist/{board}"
            async with await HotTopicsService._get(session, url, timeout=10) as resp:
                if resp.status != 200:
                    print(f"[HotTopics] vvhan/{board} 状态码: {resp.status}")
                    return []
                data = await resp.json(content_type=None)
                if not data.get("success") and data.get("code") not in (None, 200, "200"):
                    # 兼容不同响应字段
                    if not (data.get("data") or data.get("list")):
                        return []
                items = data.get("data") or data.get("list") or []
                topics = []
                for item in items[:20]:
                    title = (
                        item.get("title")
                        or item.get("name")
                        or item.get("word")
                        or ""
                    ).strip()
                    if not title:
                        continue
                    heat = item.get("hot") or item.get("hotValue") or item.get("index") or 0
                    topics.append({
                        "title": title,
                        "heat": heat,
                        "url": item.get("url") or item.get("mobilUrl") or "",
                        "source": source_name,
                        "rank": len(topics) + 1,
                    })
                if topics:
                    print(f"[HotTopics] vvhan/{board} 获取成功: {len(topics)} 条")
                return topics
        except Exception as e:
            print(f"[HotTopics] vvhan/{board} 失败: {e}")
        return []

    # ---------- 汇总 ----------

    @staticmethod
    async def fetch_all_hot_topics(use_cache: bool = True) -> Dict[str, Any]:
        """
        并行抓取各平台热点。同一轮请求共用一个 ClientSession，避免 Connector is closed。
        """
        if use_cache:
            cached = HotTopicsService._cache.get()
            if cached:
                print("[HotTopics] 返回缓存数据")
                return cached

        print("[HotTopics] 开始抓取热点数据...")
        all_topics: List[Dict[str, Any]] = []
        sources_status: Dict[str, Any] = {}
        success_count = 0

        session = HotTopicsService._new_session()
        fetch_tasks = [
            ("weibo", HotTopicsService.fetch_weibo_hot(session)),
            ("zhihu", HotTopicsService.fetch_zhihu_hot(session)),
            ("baidu", HotTopicsService.fetch_baidu_hot(session)),
            ("toutiao", HotTopicsService.fetch_toutiao_hot(session)),
            ("bilibili", HotTopicsService.fetch_bilibili_hot(session)),
            ("douyin", HotTopicsService.fetch_douyin_hot(session)),
            # 聚合源：官方 401/签名失败时仍可能拿到实时榜
            ("vvhan_weibo", HotTopicsService.fetch_vvhan_board(session, "wbHot", "微博热搜")),
            ("vvhan_zhihu", HotTopicsService.fetch_vvhan_board(session, "zhihuHot", "知乎热榜")),
            ("vvhan_baidu", HotTopicsService.fetch_vvhan_board(session, "baiduRD", "百度热搜")),
            ("vvhan_douyin", HotTopicsService.fetch_vvhan_board(session, "douyinHot", "抖音热榜")),
            ("vvhan_bili", HotTopicsService.fetch_vvhan_board(session, "bili", "B站热门")),
        ]
        try:
            results = await asyncio.gather(
                *[task for _, task in fetch_tasks],
                return_exceptions=True,
            )
        finally:
            await session.close()

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

        use_fallback = len(all_topics) == 0
        if use_fallback:
            all_topics = FALLBACK_TOPICS.copy()
            sources_status["fallback"] = {
                "status": "ok",
                "count": len(FALLBACK_TOPICS),
                "note": "使用备用数据",
            }
            print(f"[HotTopics] 所有平台抓取失败，使用备用数据: {len(FALLBACK_TOPICS)} 条")

        unique_topics = HotTopicsService._deduplicate_topics(all_topics)
        unique_topics.sort(
            key=lambda x: HotTopicsService._parse_heat(x.get("heat", 0)),
            reverse=True,
        )

        result = {
            "topics": unique_topics[:50],
            "total": len(unique_topics),
            "sources": sources_status,
            "updated_at": datetime.now().isoformat(),
            "data_source": "fallback" if use_fallback else "api",
            "success_rate": f"{success_count}/{len(fetch_tasks)}",
        }
        HotTopicsService._cache.set(result)
        print(
            f"[HotTopics] 抓取完成，共 {len(unique_topics)} 条热点"
            f"（去重前 {len(all_topics)} 条）"
        )
        return result

    @staticmethod
    def _deduplicate_topics(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique = []
        seen_titles = set()
        for topic in topics:
            title = (topic.get("title") or "").strip()
            if not title:
                continue
            normalized = HotTopicsService._normalize_title(title)
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
        title = re.sub(r"[^\w\u4e00-\u9fff]", "", title)
        return title.lower().strip()

    @staticmethod
    def _title_similarity(a: str, b: str) -> float:
        if a == b:
            return 1.0
        if len(a) == 0 or len(b) == 0:
            return 0.0
        shorter, longer = (a, b) if len(a) < len(b) else (b, a)
        if shorter in longer:
            return len(shorter) / len(longer) * 0.9
        set_a, set_b = set(a), set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _parse_heat(heat: Any) -> int:
        if isinstance(heat, (int, float)):
            return int(heat)
        if isinstance(heat, str):
            heat = heat.replace(",", "").replace(" ", "")
            if "万" in heat:
                try:
                    return int(float(heat.replace("万", "")) * 10000)
                except Exception:
                    pass
            if "亿" in heat:
                try:
                    return int(float(heat.replace("亿", "")) * 100000000)
                except Exception:
                    pass
            try:
                return int(float(heat))
            except Exception:
                pass
        return 0

    @staticmethod
    async def fetch_topic_detail(title: str, source: str = "zhihu") -> Optional[Dict[str, Any]]:
        return {
            "title": title,
            "source": source,
            "summary": f"关于「{title}」的相关讨论和新闻...",
            "related_keywords": [title[:5], title[:3] + "事件", title + "最新"],
            "url": f"https://www.bing.com/search?q={title}",
        }

    @staticmethod
    def clear_cache():
        HotTopicsService._cache.clear()
        print("[HotTopics] 缓存已清除")
