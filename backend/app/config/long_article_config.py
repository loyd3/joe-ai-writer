"""
长篇文章生成配置
用于管理百万字级别文章生成的各项参数
"""

class LongArticleConfig:
    """长篇文章生成配置类"""
    
    # 章节字数配置
    MIN_CHAPTER_WORDS = 3000      # 最小章节字数
    MAX_CHAPTER_WORDS = 15000     # 最大章节字数
    DEFAULT_CHAPTER_WORDS = 8000  # 默认章节字数
    
    # 段落生成配置
    SECTION_THRESHOLD = 5000      # 超过此字数的章节将拆分为段落生成
    SECTION_TARGET_WORDS = 2000   # 每个段落目标字数
    MIN_SECTIONS_PER_CHAPTER = 3  # 每章最少段落数
    
    # 上下文管理配置
    CONTEXT_WINDOW_SIZE = 3       # 上下文窗口：使用最近N章的摘要
    SUMMARY_MAX_LENGTH = 300      # 章节摘要最大长度
    SECTION_CONTEXT_LENGTH = 1000 # 段落生成时使用的前文长度
    
    # AI 调用配置
    OUTLINE_MAX_TOKENS = 4000     # 大纲生成最大 tokens
    CHAPTER_MAX_TOKENS = 8000     # 章节生成最大 tokens
    SECTION_MAX_TOKENS = 3000     # 段落生成最大 tokens
    SUMMARY_MAX_TOKENS = 1000     # 摘要生成最大 tokens
    
    # 温度参数
    OUTLINE_TEMPERATURE = 0.7     # 大纲生成温度
    CHAPTER_TEMPERATURE = 0.8     # 章节生成温度
    SUMMARY_TEMPERATURE = 0.3     # 摘要生成温度
    
    # 字数分级配置（根据目标字数自动调整章节数）
    WORD_TIERS = [
        {"min": 1000000, "avg_chapter": 8000, "min_chapters": 100},  # 100万字+
        {"min": 500000, "avg_chapter": 8000, "min_chapters": 60},    # 50万字+
        {"min": 100000, "avg_chapter": 7000, "min_chapters": 15},    # 10万字+
        {"min": 50000, "avg_chapter": 6000, "min_chapters": 8},      # 5万字+
        {"min": 0, "avg_chapter": 5000, "min_chapters": 5},          # 默认
    ]
    
    # 数据库批量操作配置
    BATCH_SAVE_SIZE = 10          # 每N章保存一次到数据库
    
    # 错误重试配置
    MAX_RETRIES = 3               # 生成失败最大重试次数
    RETRY_DELAY = 2               # 重试延迟（秒）
    
    @classmethod
    def get_chapter_count(cls, target_words: int) -> int:
        """
        根据目标字数计算建议章节数
        :param target_words: 目标总字数
        :return: 建议章节数
        """
        for tier in cls.WORD_TIERS:
            if target_words >= tier["min"]:
                chapter_count = max(
                    tier["min_chapters"],
                    target_words // tier["avg_chapter"]
                )
                return chapter_count
        return 10
    
    @classmethod
    def should_split_to_sections(cls, chapter_words: int) -> bool:
        """
        判断章节是否需要拆分为段落生成
        :param chapter_words: 章节目标字数
        :return: 是否需要拆分
        """
        return chapter_words > cls.SECTION_THRESHOLD
    
    @classmethod
    def calculate_section_count(cls, chapter_words: int) -> int:
        """
        计算章节应拆分的段落数
        :param chapter_words: 章节目标字数
        :return: 段落数
        """
        if not cls.should_split_to_sections(chapter_words):
            return 1
        
        section_count = max(
            cls.MIN_SECTIONS_PER_CHAPTER,
            chapter_words // cls.SECTION_TARGET_WORDS
        )
        return section_count
