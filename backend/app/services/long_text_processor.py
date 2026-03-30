"""
长文本处理器 - 智能分段处理超长文本

解决 AI 模型上下文限制问题，将长文本分段处理后再合并结果。
"""
import asyncio
from typing import AsyncGenerator, List, Callable, Optional
from dataclasses import dataclass
import re


@dataclass
class TextSegment:
    """文本段落"""
    index: int
    content: str
    context_before: str = ""  # 前文上下文（用于保持连贯性）
    context_after: str = ""   # 后文上下文（用于保持连贯性）
    is_overlap: bool = False  # 是否是重叠段落


class LongTextProcessor:
    """长文本处理器"""
    
    # 默认配置
    DEFAULT_MAX_CHUNK_SIZE = 8000  # 每个段落的最大字符数
    DEFAULT_OVERLAP_SIZE = 500     # 段落间重叠字符数（保持连贯性）
    DEFAULT_CONTEXT_SIZE = 200     # 上下文保留字符数
    
    def __init__(
        self,
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
        overlap_size: int = DEFAULT_OVERLAP_SIZE,
        context_size: int = DEFAULT_CONTEXT_SIZE
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.context_size = context_size
    
    def split_text(self, text: str) -> List[TextSegment]:
        """
        将长文本智能分段
        
        分段策略：
        1. 优先按段落（空行）分割
        2. 如果段落过长，按句子分割
        3. 如果句子过长，按固定长度强制分割
        4. 段落间保留重叠区域保持连贯性
        """
        if len(text) <= self.max_chunk_size:
            return [TextSegment(index=0, content=text)]
        
        segments = []
        
        # 首先尝试按段落分割
        paragraphs = self._split_by_paragraphs(text)
        
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_len = len(para)
            
            # 如果单个段落就超过限制，需要进一步分割
            if para_len > self.max_chunk_size:
                # 先保存当前累积的段落
                if current_chunk:
                    segment = self._create_segment(chunk_index, current_chunk, text)
                    segments.append(segment)
                    chunk_index += 1
                    current_chunk = []
                    current_size = 0
                
                # 分割长段落
                sub_segments = self._split_long_paragraph(para, chunk_index, text)
                segments.extend(sub_segments)
                chunk_index += len(sub_segments)
            
            # 如果加入当前段落后会超过限制，先保存当前累积的段落
            elif current_size + para_len > self.max_chunk_size:
                if current_chunk:
                    segment = self._create_segment(chunk_index, current_chunk, text)
                    segments.append(segment)
                    chunk_index += 1
                
                current_chunk = [para]
                current_size = para_len
            
            # 否则累积段落
            else:
                current_chunk.append(para)
                current_size += para_len
        
        # 保存最后一个段落
        if current_chunk:
            segment = self._create_segment(chunk_index, current_chunk, text)
            segments.append(segment)
        
        return segments
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本"""
        # 按一个或多个空行分割
        paragraphs = re.split(r'\n\s*\n', text.strip())
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_long_paragraph(self, paragraph: str, start_index: int, full_text: str) -> List[TextSegment]:
        """分割长段落为句子"""
        segments = []
        
        # 按句子分割（支持中英文标点）
        sentences = re.split(r'([。！？.!?]\s*)', paragraph)
        # 重新组合句子和标点
        sentences = [''.join(sentences[i:i+2]) for i in range(0, len(sentences)-1, 2)]
        
        current_chunk = []
        current_size = 0
        chunk_index = start_index
        
        for sent in sentences:
            sent_len = len(sent)
            
            if current_size + sent_len > self.max_chunk_size:
                if current_chunk:
                    segment = self._create_segment(chunk_index, current_chunk, full_text)
                    segments.append(segment)
                    chunk_index += 1
                
                # 如果单个句子就超过限制，强制分割
                if sent_len > self.max_chunk_size:
                    for i in range(0, sent_len, self.max_chunk_size):
                        chunk = sent[i:i + self.max_chunk_size]
                        chunk_global_pos = full_text.find(chunk)
                        if chunk_global_pos < 0:
                            chunk_global_pos = 0
                        segment = TextSegment(
                            index=chunk_index,
                            content=chunk,
                            context_before=self._get_context_before(full_text, chunk_global_pos),
                            context_after=self._get_context_after(full_text, chunk_global_pos + len(chunk))
                        )
                        segments.append(segment)
                        chunk_index += 1
                    current_chunk = []
                    current_size = 0
                else:
                    current_chunk = [sent]
                    current_size = sent_len
            else:
                current_chunk.append(sent)
                current_size += sent_len
        
        if current_chunk:
            segment = self._create_segment(chunk_index, current_chunk, full_text)
            segments.append(segment)
        
        return segments
    
    def _create_segment(self, index: int, paragraphs: List[str], full_text: str) -> TextSegment:
        """创建文本段落，添加上下文信息"""
        content = '\n\n'.join(paragraphs)
        
        # 计算在原文中的位置
        pos = full_text.find(content)
        if pos == -1:
            pos = full_text.find(paragraphs[0]) if paragraphs else 0
        
        return TextSegment(
            index=index,
            content=content,
            context_before=self._get_context_before(full_text, pos),
            context_after=self._get_context_after(full_text, pos + len(content))
        )
    
    def _get_context_before(self, text: str, position: int) -> str:
        """获取指定位置前的上下文"""
        start = max(0, position - self.context_size)
        context = text[start:position]
        # 确保从段落边界开始
        if start > 0 and '\n' in context:
            context = context[context.find('\n') + 1:]
        return context.strip()
    
    def _get_context_after(self, text: str, position: int) -> str:
        """获取指定位置后的上下文"""
        end = min(len(text), position + self.context_size)
        context = text[position:end]
        # 确保在段落边界结束
        if end < len(text) and '\n' in context:
            context = context[:context.rfind('\n')]
        return context.strip()
    
    def build_segment_prompt(
        self,
        segment: TextSegment,
        action: str,
        instruction: Optional[str] = None
    ) -> str:
        """
        构建段落处理提示词
        
        包含上下文信息，确保处理结果连贯
        """
        action_names = {
            'polish': '润色',
            'revise': '修改',
            'expand': '扩展',
            'continue': '续写'
        }
        action_name = action_names.get(action, '处理')
        
        parts = []
        
        # 添加系统指令
        parts.append(f"你是一位专业的写作助手。请对以下文本进行{action_name}。")
        
        # 添加上下文信息
        if segment.context_before:
            parts.append(f"\n【前文参考（仅用于保持连贯性，不需要{action_name}）】\n{segment.context_before}")
        
        # 添加主要处理内容
        parts.append(f"\n【需要{action_name}的文本】\n{segment.content}")
        
        if segment.context_after:
            parts.append(f"\n【后文参考（仅用于保持连贯性，不需要{action_name}）】\n{segment.context_after}")
        
        # 添加格式要求
        parts.append(f"\n【{action_name}要求】")
        if instruction:
            parts.append(instruction)
        
        parts.append(f"""
请直接输出{action_name}后的正文，不要添加任何说明、理由或前缀。
注意：
1. 保持与前后文的连贯性
2. 保持原文的风格和语气
3. 只输出这段文本的{action_name}结果，不要包含上下文内容
4. 编辑器格式约定（用于自动排版）：
   - 大标题用单独一行以 `##` 开头
   - 小标题用单独一行以 `###` 开头
   - 引用/对话用单独一行以 `>` 开头
   - 列表用单独一行以 `- ` 开头
   - 分割线用单独一行使用 `---`
   - 段落之间空一行
   - 不要使用 Markdown 标题 `#`
   - 不要使用 `**`/`*` 加粗斜体
   - 不要输出 ``` 代码块
""")
        
        return '\n'.join(parts)
    
    async def process_long_text(
        self,
        text: str,
        process_func: Callable[[str], AsyncGenerator[str, None]],
        action: str = 'polish',
        instruction: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> AsyncGenerator[str, None]:
        """
        处理长文本
        
        Args:
            text: 原始文本
            process_func: 处理函数，接收提示词，返回流式结果
            action: 操作类型
            instruction: 额外指令
            progress_callback: 进度回调函数 (current, total)
        
        Yields:
            处理后的文本片段
        """
        # 如果文本不长，直接处理
        if len(text) <= self.max_chunk_size:
            async for chunk in process_func(text):
                yield chunk
            return
        
        # 分段处理
        segments = self.split_text(text)
        total_segments = len(segments)
        
        # 发送开始标记
        yield f"[长文本处理中，共 {total_segments} 段...]\n\n"
        
        for i, segment in enumerate(segments):
            # 更新进度
            if progress_callback:
                progress_callback(i + 1, total_segments)
            
            # 发送段落标记
            if total_segments > 1:
                yield f"\n<!-- segment {i+1}/{total_segments} -->\n"
            
            # 构建提示词
            prompt = self.build_segment_prompt(segment, action, instruction)
            
            # 处理段落
            segment_result = []
            async for chunk in process_func(prompt):
                segment_result.append(chunk)
                yield chunk
            
            # 段落间添加适当分隔
            if i < total_segments - 1:
                # 检查最后是否有空行
                result_text = ''.join(segment_result)
                if not result_text.endswith('\n'):
                    yield '\n'
        
        # 发送完成标记
        yield f"\n\n[长文本处理完成]"
    
    def merge_results(self, results: List[str], remove_markers: bool = True) -> str:
        """
        合并处理结果
        
        Args:
            results: 各段落的处理结果
            remove_markers: 是否移除段落标记
        
        Returns:
            合并后的完整文本
        """
        if remove_markers:
            # 移除段落标记
            cleaned_results = []
            for result in results:
                # 移除 HTML 注释标记
                result = re.sub(r'\n?<!-- segment \d+/\d+ -->\n?', '\n', result)
                # 移除处理状态标记
                result = re.sub(r'\[长文本处理[^\]]*\]\n?', '', result)
                cleaned_results.append(result.strip())
            
            # 合并，确保段落间有空行
            merged = '\n\n'.join(cleaned_results)
            # 清理多余空行
            merged = re.sub(r'\n{3,}', '\n\n', merged)
            return merged.strip()
        else:
            return '\n\n'.join(results)


# 便捷函数
async def process_long_text_stream(
    text: str,
    process_func: Callable[[str], AsyncGenerator[str, None]],
    action: str = 'polish',
    instruction: Optional[str] = None,
    max_chunk_size: int = 8000,
    overlap_size: int = 500
) -> AsyncGenerator[str, None]:
    """
    流式处理长文本的便捷函数
    
    使用示例：
        async def process_with_ai(prompt: str):
            async for chunk in ai_client.stream_completion([{"role": "user", "content": prompt}]):
                yield chunk
        
        async for chunk in process_long_text_stream(long_text, process_with_ai, action='polish'):
            print(chunk, end='')
    """
    processor = LongTextProcessor(max_chunk_size=max_chunk_size, overlap_size=overlap_size)
    async for chunk in processor.process_long_text(text, process_func, action, instruction):
        yield chunk
