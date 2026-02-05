"""
智能文本分块模块
用于处理超过token限制的大文件
支持代码文件、Markdown文档和普通文本的智能分块
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """文本块数据类"""
    content: str
    start_line: int
    end_line: int
    chunk_index: int
    total_chunks: int
    metadata: Dict[str, Any]


class TextChunker:
    """文本分块器基类"""
    
    def __init__(self, max_tokens: int = 8192, overlap_tokens: int = 200):
        """
        初始化分块器
        
        Args:
            max_tokens: 每个块的最大token数
            overlap_tokens: 块之间的重叠token数（保持上下文连续性）
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
    
    def chunk_text(self, text: str, count_tokens_fn, metadata: Optional[Dict] = None) -> List[TextChunk]:
        """
        通用文本分块方法（子类可重写）
        
        Args:
            text: 要分块的文本
            count_tokens_fn: token计数函数
            metadata: 元数据
            
        Returns:
            文本块列表
        """
        raise NotImplementedError("Subclasses must implement chunk_text method")
    
    def _create_chunk(self, content: str, start_line: int, end_line: int, 
                     chunk_index: int, total_chunks: int, metadata: Dict) -> TextChunk:
        """创建文本块"""
        return TextChunk(
            content=content,
            start_line=start_line,
            end_line=end_line,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            metadata=metadata
        )


class CodeChunker(TextChunker):
    """代码文件分块器 - 按函数/类定义分块"""
    
    def chunk_text(self, text: str, count_tokens_fn, metadata: Optional[Dict] = None) -> List[TextChunk]:
        """
        按代码结构智能分块
        - 识别函数和类定义
        - 保持代码块完整性
        - 保留imports和顶层注释
        """
        if metadata is None:
            metadata = {}
        
        lines = text.splitlines(keepends=True)
        chunks = []
        
        # 提取文件头部（imports, 注释, 常量定义等）
        header_lines, code_start = self._extract_header(lines)
        header_text = ''.join(header_lines)
        header_tokens = count_tokens_fn(header_text)
        
        # 识别代码块（函数、类）
        code_blocks = self._identify_code_blocks(lines, code_start)
        
        # 构建分块
        current_chunk_lines = header_lines.copy()
        current_start_line = 1
        chunk_index = 0
        
        for block_start, block_end, block_type in code_blocks:
            block_lines = lines[block_start:block_end]
            block_text = ''.join(block_lines)
            block_tokens = count_tokens_fn(block_text)
            
            # 检查当前块加上新代码块是否超过限制
            current_text = ''.join(current_chunk_lines) + block_text
            current_tokens = count_tokens_fn(current_text)
            
            if current_tokens > self.max_tokens and len(current_chunk_lines) > len(header_lines):
                # 当前块已满，保存并开始新块
                chunk_content = ''.join(current_chunk_lines)
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_line=current_start_line,
                    end_line=block_start,
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will update later
                    metadata={**metadata, 'block_type': 'code', 'has_header': True}
                ))
                
                # 开始新块（包含header和当前代码块）
                current_chunk_lines = header_lines.copy() + block_lines
                current_start_line = block_start + 1
                chunk_index += 1
            else:
                # 添加到当前块
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
    
    def _extract_header(self, lines: List[str]) -> Tuple[List[str], int]:
        """
        提取文件头部（imports, 顶层注释等）
        
        Returns:
            (header_lines, code_start_index)
        """
        header_lines = []
        code_start = 0
        
        in_multiline_comment = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 检测多行注释
            if '"""' in line or "'''" in line:
                in_multiline_comment = not in_multiline_comment
                header_lines.append(line)
                continue
            
            if in_multiline_comment:
                header_lines.append(line)
                continue
            
            # 单行注释、imports、空行
            if (stripped.startswith('#') or 
                stripped.startswith('//') or
                stripped.startswith('import ') or
                stripped.startswith('from ') or
                stripped.startswith('package ') or
                stripped.startswith('using ') or
                stripped == '' or
                self._is_constant_definition(stripped)):
                header_lines.append(line)
            else:
                # 遇到第一个非头部行
                code_start = i
                break
        
        return header_lines, code_start
    
    def _is_constant_definition(self, line: str) -> bool:
        """判断是否为常量定义"""
        # Python常量（全大写变量）
        if re.match(r'^[A-Z_][A-Z0-9_]*\s*=', line):
            return True
        # Go const
        if line.startswith('const '):
            return True
        # Java static final
        if 'static final' in line:
            return True
        return False
    
    def _identify_code_blocks(self, lines: List[str], start_index: int) -> List[Tuple[int, int, str]]:
        """
        识别代码块（函数、类定义）
        
        Returns:
            List of (start_line, end_line, block_type)
        """
        blocks = []
        i = start_index
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Python: def, class, async def
            if re.match(r'^(async\s+)?def\s+\w+|^class\s+\w+', line):
                block_start = i
                block_end = self._find_python_block_end(lines, i)
                blocks.append((block_start, block_end, 'python_block'))
                i = block_end
            # Java/C++/Go: function, method, class
            elif re.match(r'(public|private|protected|static|func)\s+', line) or 'class ' in line:
                block_start = i
                block_end = self._find_brace_block_end(lines, i)
                blocks.append((block_start, block_end, 'brace_block'))
                i = block_end
            else:
                i += 1
        
        return blocks
    
    def _find_python_block_end(self, lines: List[str], start: int) -> int:
        """找到Python代码块的结束（基于缩进）"""
        if start >= len(lines):
            return len(lines)
        
        # 获取定义行的缩进
        def_line = lines[start]
        base_indent = len(def_line) - len(def_line.lstrip())
        
        i = start + 1
        while i < len(lines):
            line = lines[i]
            if line.strip() == '':
                i += 1
                continue
            
            current_indent = len(line) - len(line.lstrip())
            
            # 如果缩进回到基准或更少，块结束
            if current_indent <= base_indent:
                return i
            
            i += 1
        
        return len(lines)
    
    def _find_brace_block_end(self, lines: List[str], start: int) -> int:
        """找到使用花括号的代码块结束"""
        brace_count = 0
        found_opening = False
        
        for i in range(start, len(lines)):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening = True
                elif char == '}':
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        return i + 1
        
        return len(lines)


class MarkdownChunker(TextChunker):
    """Markdown文档分块器 - 按标题层级分块"""
    
    def chunk_text(self, text: str, count_tokens_fn, metadata: Optional[Dict] = None) -> List[TextChunk]:
        """
        按Markdown标题层级分块
        - 保持标题和内容一起
        - 优先在标题处分块
        - 保持语义完整性
        """
        if metadata is None:
            metadata = {}
        
        lines = text.splitlines(keepends=True)
        chunks = []
        
        # 识别标题位置
        heading_positions = self._find_headings(lines)
        
        if not heading_positions:
            # 没有标题，使用段落分块
            return self._chunk_by_paragraphs(text, lines, count_tokens_fn, metadata)
        
        # 按标题分块
        current_chunk_lines = []
        current_start_line = 1
        chunk_index = 0
        
        for i, (line_num, level, title) in enumerate(heading_positions):
            # 从上一个标题到当前标题之间的内容
            if i > 0:
                prev_line_num = heading_positions[i-1][0]
                section_lines = lines[prev_line_num:line_num]
            else:
                section_lines = lines[:line_num]
            
            # 检查是否需要开始新块
            test_text = ''.join(current_chunk_lines + section_lines)
            test_tokens = count_tokens_fn(test_text)
            
            if test_tokens > self.max_tokens and current_chunk_lines:
                # 保存当前块
                chunk_content = ''.join(current_chunk_lines)
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_line=current_start_line,
                    end_line=line_num,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    metadata={**metadata, 'block_type': 'markdown'}
                ))
                
                # 开始新块
                current_chunk_lines = section_lines
                current_start_line = prev_line_num + 1 if i > 0 else 1
                chunk_index += 1
            else:
                current_chunk_lines.extend(section_lines)
        
        # 处理最后一个标题之后的内容
        if heading_positions:
            last_heading_line = heading_positions[-1][0]
            remaining_lines = lines[last_heading_line:]
            current_chunk_lines.extend(remaining_lines)
        
        # 保存最后一个块
        if current_chunk_lines:
            chunk_content = ''.join(current_chunk_lines)
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_line=current_start_line,
                end_line=len(lines),
                chunk_index=chunk_index,
                total_chunks=0,
                metadata={**metadata, 'block_type': 'markdown'}
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
            metadata={**metadata, 'block_type': 'markdown'}
        )]
    
    def _find_headings(self, lines: List[str]) -> List[Tuple[int, int, str]]:
        """
        查找Markdown标题
        
        Returns:
            List of (line_number, level, title)
        """
        headings = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            # ATX风格标题: # Title
            match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if match:
                level = len(match.group(1))
                title = match.group(2)
                headings.append((i, level, title))
        
        return headings
    
    def _chunk_by_paragraphs(self, text: str, lines: List[str], count_tokens_fn, metadata: Dict) -> List[TextChunk]:
        """按段落分块（当没有标题时）"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_start = 1
        chunk_index = 0
        
        for para in paragraphs:
            test_text = '\n\n'.join(current_chunk + [para])
            test_tokens = count_tokens_fn(test_text)
            
            if test_tokens > self.max_tokens and current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_line=current_start,
                    end_line=current_start + len(chunk_content.splitlines()),
                    chunk_index=chunk_index,
                    total_chunks=0,
                    metadata={**metadata, 'block_type': 'paragraph'}
                ))
                
                current_chunk = [para]
                current_start += len(chunk_content.splitlines())
                chunk_index += 1
            else:
                current_chunk.append(para)
        
        # 保存最后一个块
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_line=current_start,
                end_line=len(lines),
                chunk_index=chunk_index,
                total_chunks=0,
                metadata={**metadata, 'block_type': 'paragraph'}
            ))
        
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        return chunks if chunks else [self._create_chunk(
            content=text,
            start_line=1,
            end_line=len(lines),
            chunk_index=0,
            total_chunks=1,
            metadata=metadata
        )]


class PlainTextChunker(TextChunker):
    """普通文本分块器 - 按句子/段落分块，带重叠"""
    
    def chunk_text(self, text: str, count_tokens_fn, metadata: Optional[Dict] = None) -> List[TextChunk]:
        """
        按句子分块，带重叠以保持上下文连续性
        """
        if metadata is None:
            metadata = {}
        
        # 按句子分割
        sentences = self._split_sentences(text)
        
        chunks = []
        current_sentences = []
        chunk_index = 0
        
        for sentence in sentences:
            test_text = ' '.join(current_sentences + [sentence])
            test_tokens = count_tokens_fn(test_text)
            
            if test_tokens > self.max_tokens and current_sentences:
                # 保存当前块
                chunk_content = ' '.join(current_sentences)
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_line=chunk_index * 10,  # 估算
                    end_line=(chunk_index + 1) * 10,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    metadata={**metadata, 'block_type': 'text', 'has_overlap': True}
                ))
                
                # 计算重叠部分
                overlap_text = chunk_content
                overlap_tokens = count_tokens_fn(overlap_text)
                
                # 保留最后几句作为重叠
                overlap_sentences = []
                for sent in reversed(current_sentences):
                    overlap_test = ' '.join([sent] + overlap_sentences)
                    if count_tokens_fn(overlap_test) > self.overlap_tokens:
                        break
                    overlap_sentences.insert(0, sent)
                
                # 开始新块（包含重叠）
                current_sentences = overlap_sentences + [sentence]
                chunk_index += 1
            else:
                current_sentences.append(sentence)
        
        # 保存最后一个块
        if current_sentences:
            chunk_content = ' '.join(current_sentences)
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_line=chunk_index * 10,
                end_line=(chunk_index + 1) * 10,
                chunk_index=chunk_index,
                total_chunks=0,
                metadata={**metadata, 'block_type': 'text'}
            ))
        
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        return chunks if chunks else [self._create_chunk(
            content=text,
            start_line=1,
            end_line=len(text.splitlines()),
            chunk_index=0,
            total_chunks=1,
            metadata=metadata
        )]
    
    def _split_sentences(self, text: str) -> List[str]:
        """简单的句子分割"""
        # 按句号、问号、感叹号分割
        sentences = re.split(r'([.!?]+\s+)', text)
        
        # 重新组合
        result = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i+1])
            else:
                result.append(sentences[i])
        
        return [s.strip() for s in result if s.strip()]


def get_chunker(file_type: str, max_tokens: int = 8192, overlap_tokens: int = 200) -> TextChunker:
    """
    根据文件类型获取合适的分块器
    
    Args:
        file_type: 文件类型 ('py', 'java', 'go', 'md', 'txt'等)
        max_tokens: 最大token数
        overlap_tokens: 重叠token数
        
    Returns:
        对应的分块器实例
    """
    code_extensions = {'py', 'java', 'go', 'js', 'ts', 'jsx', 'tsx', 'cpp', 'c', 'h', 'rs', 'rb', 'php'}
    markdown_extensions = {'md', 'markdown', 'rst'}
    
    if file_type in code_extensions:
        return CodeChunker(max_tokens, overlap_tokens)
    elif file_type in markdown_extensions:
        return MarkdownChunker(max_tokens, overlap_tokens)
    else:
        return PlainTextChunker(max_tokens, overlap_tokens)


def chunk_large_file(content: str, file_path: str, count_tokens_fn, 
                     max_tokens: int = 8192, overlap_tokens: int = 200) -> List[TextChunk]:
    """
    智能分块大文件的便捷函数
    
    Args:
        content: 文件内容
        file_path: 文件路径
        count_tokens_fn: token计数函数
        max_tokens: 最大token数
        overlap_tokens: 重叠token数
        
    Returns:
        文本块列表
    """
    import os
    file_ext = os.path.splitext(file_path)[1][1:]  # 去掉点号
    
    chunker = get_chunker(file_ext, max_tokens, overlap_tokens)
    
    metadata = {
        'file_path': file_path,
        'file_type': file_ext,
        'original_length': len(content),
        'original_token_count': count_tokens_fn(content)
    }
    
    try:
        chunks = chunker.chunk_text(content, count_tokens_fn, metadata)
        logger.info(f"Chunked {file_path} into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error chunking {file_path}: {e}")
        # 降级为普通文本分块
        fallback_chunker = PlainTextChunker(max_tokens, overlap_tokens)
        return fallback_chunker.chunk_text(content, count_tokens_fn, metadata)





