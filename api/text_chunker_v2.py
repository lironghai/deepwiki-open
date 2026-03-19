"""
文本分块器 V2 - 增强版
支持处理超大函数的边缘情况
"""
try:
    from api.text_chunker import (
        TextChunker, CodeChunker, MarkdownChunker, PlainTextChunker,
        TextChunk, get_chunker
    )
except Exception:
    # Backward-compatible import for direct script execution from api/ directory
    from text_chunker import (
        TextChunker, CodeChunker, MarkdownChunker, PlainTextChunker,
        TextChunk, get_chunker
    )
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class EnhancedCodeChunker(CodeChunker):
    """
    增强的代码分块器
    能处理超大函数的特殊情况
    """
    
    def __init__(self, max_tokens: int = 8192, overlap_tokens: int = 200, 
                 force_split_threshold: float = 1.5):
        """
        Args:
            max_tokens: 每个块的最大token数
            overlap_tokens: 块之间的重叠token数
            force_split_threshold: 当单个函数超过 max_tokens * force_split_threshold 时强制分割
        """
        super().__init__(max_tokens, overlap_tokens)
        self.force_split_threshold = force_split_threshold
        self.force_split_max = int(max_tokens * force_split_threshold)
    
    def chunk_text(self, text: str, count_tokens_fn, metadata: Optional[Dict] = None) -> List[TextChunk]:
        """增强的分块逻辑，处理超大函数"""
        if metadata is None:
            metadata = {}
        
        lines = text.splitlines(keepends=True)
        chunks = []
        
        # 提取文件头部
        header_lines, code_start = self._extract_header(lines)
        
        # 识别代码块
        code_blocks = self._identify_code_blocks(lines, code_start)
        
        # 构建分块
        current_chunk_lines = header_lines.copy()
        current_start_line = 1
        chunk_index = 0
        
        for block_start, block_end, block_type in code_blocks:
            block_lines = lines[block_start:block_end]
            block_text = ''.join(block_lines)
            block_tokens = count_tokens_fn(block_text)
            
            # 检查单个代码块是否过大
            if block_tokens > self.force_split_max:
                logger.warning(f"Large code block detected ({block_tokens} tokens), applying sub-chunking")
                
                # 保存当前块（如果有内容）
                if len(current_chunk_lines) > len(header_lines):
                    chunk_content = ''.join(current_chunk_lines)
                    chunks.append(self._create_chunk(
                        content=chunk_content,
                        start_line=current_start_line,
                        end_line=block_start,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        metadata={**metadata, 'block_type': 'code', 'has_header': True}
                    ))
                    chunk_index += 1
                
                # 对超大函数进行二次分块
                sub_chunks = self._split_large_block(
                    block_lines, block_start, block_type, 
                    header_lines, count_tokens_fn, chunk_index, metadata
                )
                
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                
                # 重置当前块
                current_chunk_lines = header_lines.copy()
                current_start_line = block_end + 1
                
            else:
                # 正常大小的代码块
                current_text = ''.join(current_chunk_lines) + block_text
                current_tokens = count_tokens_fn(current_text)
                
                if current_tokens > self.max_tokens and len(current_chunk_lines) > len(header_lines):
                    # 保存当前块
                    chunk_content = ''.join(current_chunk_lines)
                    chunks.append(self._create_chunk(
                        content=chunk_content,
                        start_line=current_start_line,
                        end_line=block_start,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        metadata={**metadata, 'block_type': 'code', 'has_header': True}
                    ))
                    
                    # 开始新块
                    current_chunk_lines = header_lines.copy() + block_lines
                    current_start_line = block_start + 1
                    chunk_index += 1
                else:
                    current_chunk_lines.extend(block_lines)
        
        # 保存最后一个块
        if len(current_chunk_lines) > len(header_lines):
            chunk_content = ''.join(current_chunk_lines)
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_line=current_start_line,
                end_line=len(lines),
                chunk_index=chunk_index,
                total_chunks=0,
                metadata={**metadata, 'block_type': 'code', 'has_header': True}
            ))
        
        # 更新total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        return chunks if chunks else [self._create_chunk(
            content=text,
            start_line=1,
            end_line=len(lines),
            chunk_index=0,
            total_chunks=1,
            metadata={**metadata, 'block_type': 'code'}
        )]
    
    def _split_large_block(self, block_lines: List[str], block_start: int, 
                          block_type: str, header_lines: List[str], 
                          count_tokens_fn, start_chunk_index: int,
                          metadata: Dict) -> List[TextChunk]:
        """
        对超大函数/类进行二次分块
        策略：按段落（空行分隔）或固定行数分割
        """
        chunks = []
        chunk_index = start_chunk_index
        
        # 提取函数签名（第一行）
        signature_line = block_lines[0] if block_lines else ""
        body_lines = block_lines[1:] if len(block_lines) > 1 else []
        
        # 按段落分割（连续的非空行为一段）
        paragraphs = self._split_into_paragraphs(body_lines)
        
        current_chunk_lines = header_lines.copy() + [signature_line]
        current_start = block_start
        
        for para_lines in paragraphs:
            # 对超大段落做固定长度兜底分割，避免单段本身超过限制
            paragraph_slices = self._split_paragraph_safely(
                para_lines, header_lines, signature_line, count_tokens_fn
            )

            for para_slice in paragraph_slices:
                test_lines = current_chunk_lines + para_slice
                test_text = ''.join(test_lines)
                test_tokens = count_tokens_fn(test_text)
            
                if test_tokens > self.max_tokens and len(current_chunk_lines) > len(header_lines) + 1:
                    # 保存当前块
                    chunk_content = ''.join(current_chunk_lines)
                    chunks.append(self._create_chunk(
                        content=chunk_content,
                        start_line=current_start,
                        end_line=current_start + len(current_chunk_lines),
                        chunk_index=chunk_index,
                        total_chunks=0,
                        metadata={
                            **metadata, 
                            'block_type': 'code_fragment',
                            'has_header': True,
                            'is_partial_function': True
                        }
                    ))
                    
                    # 开始新块（带函数签名和当前段落切片）
                    current_chunk_lines = header_lines.copy() + [signature_line, '\n'] + para_slice
                    current_start += len(chunk_content.splitlines())
                    chunk_index += 1
                else:
                    current_chunk_lines.extend(para_slice)
        
        # 保存最后一个块
        if len(current_chunk_lines) > len(header_lines) + 1:
            chunk_content = ''.join(current_chunk_lines)
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_line=current_start,
                end_line=block_start + len(block_lines),
                chunk_index=chunk_index,
                total_chunks=0,
                metadata={
                    **metadata, 
                    'block_type': 'code_fragment',
                    'has_header': True,
                    'is_partial_function': True
                }
            ))
        
        return chunks
    
    def _split_into_paragraphs(self, lines: List[str]) -> List[List[str]]:
        """将代码行按段落分组（以空行分隔）"""
        paragraphs = []
        current_para = []
        
        for line in lines:
            if line.strip() == '':
                if current_para:
                    paragraphs.append(current_para)
                    current_para = []
                paragraphs.append([line])  # 保留空行
            else:
                current_para.append(line)
        
        if current_para:
            paragraphs.append(current_para)
        
        return paragraphs

    def _split_paragraph_safely(
        self,
        paragraph_lines: List[str],
        header_lines: List[str],
        signature_line: str,
        count_tokens_fn
    ) -> List[List[str]]:
        """
        当单段过大时，按固定行窗口进一步切分。
        这样即便遇到超长方法中的超长单段，也能保证不超过max_tokens。
        """
        if not paragraph_lines:
            return [[]]

        base_prefix = ''.join(header_lines + [signature_line, '\n'])
        paragraph_text = ''.join(paragraph_lines)
        if count_tokens_fn(base_prefix + paragraph_text) <= self.max_tokens:
            return [paragraph_lines]

        slices: List[List[str]] = []
        current_slice: List[str] = []
        fixed_line_cap = 80

        for line in paragraph_lines:
            test_slice = current_slice + [line]
            test_text = base_prefix + ''.join(test_slice)

            # 双重条件：token和固定行数，任何一个触发都切
            should_flush = (
                current_slice
                and (
                    count_tokens_fn(test_text) > self.max_tokens
                    or len(test_slice) > fixed_line_cap
                )
            )
            if should_flush:
                slices.append(current_slice)
                current_slice = [line]
            else:
                current_slice = test_slice

        if current_slice:
            slices.append(current_slice)

        return slices


def get_enhanced_chunker(file_type: str, max_tokens: int = 8192, 
                        overlap_tokens: int = 200) -> TextChunker:
    """
    获取增强版分块器
    
    Args:
        file_type: 文件类型
        max_tokens: 最大token数
        overlap_tokens: 重叠token数
    
    Returns:
        增强版分块器
    """
    code_extensions = {'py', 'java', 'go', 'js', 'ts', 'jsx', 'tsx', 'cpp', 'c', 'h', 'rs', 'rb', 'php'}
    markdown_extensions = {'md', 'markdown', 'rst'}
    
    if file_type in code_extensions:
        return EnhancedCodeChunker(max_tokens, overlap_tokens)
    elif file_type in markdown_extensions:
        return MarkdownChunker(max_tokens, overlap_tokens)
    else:
        return PlainTextChunker(max_tokens, overlap_tokens)


# 便捷函数
def chunk_large_file_v2(content: str, file_path: str, count_tokens_fn, 
                       max_tokens: int = 8192, overlap_tokens: int = 200) -> List[TextChunk]:
    """
    增强版大文件分块函数
    能处理超大函数的边缘情况
    """
    import os
    file_ext = os.path.splitext(file_path)[1][1:]
    
    chunker = get_enhanced_chunker(file_ext, max_tokens, overlap_tokens)
    
    metadata = {
        'file_path': file_path,
        'file_type': file_ext,
        'original_length': len(content),
        'original_token_count': count_tokens_fn(content)
    }
    
    try:
        chunks = chunker.chunk_text(content, count_tokens_fn, metadata)
        logger.info(f"Enhanced chunking: {file_path} → {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error in enhanced chunking for {file_path}: {e}")
        # 降级到普通文本分块
        fallback_chunker = PlainTextChunker(max_tokens, overlap_tokens)
        return fallback_chunker.chunk_text(content, count_tokens_fn, metadata)





