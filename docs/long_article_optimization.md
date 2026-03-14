# 长篇文章生成器 - 百万字优化方案

## 概述

本文档描述了"墨心"AI 写作助手如何支持生成 100 万字以上的长篇文章。

## 核心挑战

1. **AI Token 限制**：单次调用无法生成超长内容
2. **上下文连贯性**：长篇文章需要保持前后一致
3. **内存占用**：百万字内容不能全部加载到内存
4. **生成时间**：需要数小时，必须支持断点续写
5. **质量控制**：避免重复、跑题、逻辑混乱

## 解决方案

### 1. 多层级分段生成

#### 章节级拆分
```
100万字文章
├── 第1章 (8000字)
├── 第2章 (8000字)
├── ...
└── 第125章 (8000字)
```

- 根据目标字数自动计算章节数
- 每章 3000-15000 字（可配置）
- 逐章生成，降低单次 AI 调用压力

#### 段落级拆分
```
第1章 (8000字)
├── 第1段 (2000字)
├── 第2段 (2000字)
├── 第3段 (2000字)
└── 第4段 (2000字)
```

- 超过 5000 字的章节自动拆分为段落
- 每段 2000 字左右
- 段落间传递上下文（最后 1000 字）

### 2. 智能上下文管理

#### 多章节上下文窗口
```python
# 生成第10章时，使用第7、8、9章的摘要作为上下文
context_window = 3  # 可配置
```

- 每章生成后自动生成 300 字摘要
- 使用最近 N 章的摘要作为上下文
- 避免上下文过长，保持连贯性

#### 段落间上下文传递
```python
# 生成第2段时，使用第1段的最后1000字作为上下文
section_context_length = 1000  # 可配置
```

### 3. 配置管理系统

所有参数集中在 `LongArticleConfig` 类中：

```python
class LongArticleConfig:
    # 章节字数配置
    MIN_CHAPTER_WORDS = 3000
    MAX_CHAPTER_WORDS = 15000
    DEFAULT_CHAPTER_WORDS = 8000
    
    # 段落生成配置
    SECTION_THRESHOLD = 5000      # 超过此字数拆分为段落
    SECTION_TARGET_WORDS = 2000   # 每段目标字数
    
    # 上下文管理配置
    CONTEXT_WINDOW_SIZE = 3       # 使用最近N章的摘要
    SUMMARY_MAX_LENGTH = 300      # 章节摘要最大长度
    SECTION_CONTEXT_LENGTH = 1000 # 段落生成时的前文长度
    
    # AI 调用配置
    OUTLINE_MAX_TOKENS = 4000
    CHAPTER_MAX_TOKENS = 8000
    SECTION_MAX_TOKENS = 3000
    
    # 错误重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 2
```

### 4. 字数分级策略

根据目标字数自动调整生成策略：

| 目标字数 | 章节数 | 每章字数 | 策略 |
|---------|--------|---------|------|
| 100万+ | 100-150 | 6000-10000 | 段落级拆分 + 多章节上下文 |
| 50万+ | 60-80 | 6000-8000 | 段落级拆分 + 多章节上下文 |
| 10万+ | 15-20 | 5000-7000 | 段落级拆分 |
| 5万+ | 8-10 | 5000-6000 | 章节级生成 |
| 5万以下 | 5-8 | 5000 | 章节级生成 |

### 5. 错误重试机制

```python
async def generate_chapter(self, ..., retry_count: int = 0):
    try:
        # 生成章节
        ...
    except Exception as e:
        if retry_count < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY)
            # 重试
            async for chunk in self.generate_chapter(..., retry_count + 1):
                yield chunk
        else:
            raise Exception(f"章节生成失败，已重试 {retry_count} 次")
```

### 6. 流式生成 + 实时保存

```python
async for chunk in self.ai_client.stream_completion(...):
    full_content += chunk
    yield chunk  # 实时推送到前端

# 章节生成完成后立即保存
self._save_chapter(article_id, chapter_index, chapter_info, full_content)
```

## 性能优化

### 1. 并发生成（未来优化）
- 多章节并行生成（需要更复杂的上下文管理）
- 使用任务队列（Celery/RQ）

### 2. 数据库优化
- 章节内容分表存储
- 使用 TEXT/LONGTEXT 字段
- 添加索引优化查询

### 3. 缓存策略
- 大纲缓存
- 章节摘要缓存
- Redis 存储生成进度

## 使用示例

### 生成 100 万字小说

```python
# 1. 创建文章任务
article = await service.create_article(
    user_id=1,
    title="史诗级奇幻小说",
    target_words=1000000,
    style="奇幻冒险"
)

# 2. 生成大纲（自动计算 125 章）
outline = await service.generate_outline(
    article_id=article.id,
    topic="一个少年的成长与冒险",
    target_words=1000000,
    style="奇幻冒险"
)

# 3. 生成完整文章（流式推送）
async for event in service.generate_full_article(
    article_id=article.id,
    topic="一个少年的成长与冒险",
    target_words=1000000,
    style="奇幻冒险"
):
    if event["type"] == "progress":
        print(f"进度: {event['data']['progress']}%")
    elif event["type"] == "chapter_chunk":
        print(event["data"]["chunk"], end="")
```

### 前端使用

```javascript
// 创建文章
const article = await createArticle({
  title: "史诗级奇幻小说",
  targetWords: 1000000,
  style: "奇幻冒险"
});

// 生成大纲
const outline = await generateOutline(article.id, {
  topic: "一个少年的成长与冒险",
  targetWords: 1000000
});

// 生成文章（SSE 流式接收）
const eventSource = new EventSource(`/api/long-article/${article.id}/generate`);

eventSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  console.log(`进度: ${data.progress}%`);
});

eventSource.addEventListener('chapter_chunk', (e) => {
  const data = JSON.parse(e.data);
  appendContent(data.chunk);
});
```

## 配置调优建议

### 高质量模式（慢但质量高）
```python
SECTION_TARGET_WORDS = 3000      # 每段更长
CONTEXT_WINDOW_SIZE = 5          # 更多上下文
SUMMARY_MAX_LENGTH = 500         # 更详细的摘要
CHAPTER_TEMPERATURE = 0.7        # 更保守的生成
```

### 快速模式（快但质量略低）
```python
SECTION_TARGET_WORDS = 1500      # 每段更短
CONTEXT_WINDOW_SIZE = 2          # 更少上下文
SUMMARY_MAX_LENGTH = 200         # 更简短的摘要
CHAPTER_TEMPERATURE = 0.9        # 更随机的生成
```

### 超长文章模式（200万字+）
```python
MIN_CHAPTER_WORDS = 5000
MAX_CHAPTER_WORDS = 20000
SECTION_THRESHOLD = 8000
CONTEXT_WINDOW_SIZE = 5
```

## 未来优化方向

1. **智能大纲优化**
   - AI 自动检测大纲质量
   - 自动调整章节分配

2. **质量检测**
   - 检测重复内容
   - 检测逻辑矛盾
   - 检测跑题

3. **并行生成**
   - 多章节并行生成
   - 智能上下文合并

4. **断点续写优化**
   - 更智能的续写策略
   - 自动检测中断点

5. **用户交互**
   - 实时修改大纲
   - 手动调整章节内容
   - 插入自定义内容

## 总结

通过多层级分段生成、智能上下文管理、配置化参数、错误重试机制等技术，"墨心"AI 写作助手能够稳定生成 100 万字以上的长篇文章，同时保持内容的连贯性和质量。
