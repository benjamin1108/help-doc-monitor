import asyncio
import os
import re
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urljoin
from io import StringIO
from rich.console import Console

CONSOLE = Console()

class BaseExtractor:
    """
    提取器基类，定义了所有提取器应遵循的接口和默认实现。
    """
    def __init__(self, soup: BeautifulSoup, url: str):
        self.soup = soup
        self.url = url

    def extract(self) -> dict:
        """
        执行提取过程并返回一个包含所有数据的结构化字典。
        """
        title = self._extract_title()
        content_html = self._extract_content_html()
        
        if content_html:
            self._fix_relative_urls(content_html)

        return {
            "title": title,
            "content_html": str(content_html) if content_html else "",
        }

    def _extract_title(self) -> str:
        """提取页面主标题。默认实现是查找第一个h1标签。"""
        title_tag = self.soup.find('h1')
        return title_tag.get_text(strip=True) if title_tag else "Untitled"

    def _extract_content_html(self) -> BeautifulSoup:
        """
        默认的内容提取逻辑。
        它会先移除通用干扰标签，然后返回清理后的 <body>。
        """
        body = self.soup.find('body')
        if not body:
            return self.soup # 如果没有body，返回整个soup

        # 对body进行通用清理
        for tag in body.find_all(['nav', 'footer', 'header', 'script', 'style', 'aside', 'form']):
            tag.decompose()
        return body

    def _fix_relative_urls(self, content_soup: BeautifulSoup):
        """将内容中的相对URL转换为绝对URL。"""
        for tag in content_soup.find_all(['a'], href=True):
            if tag['href'].startswith('/'):
                tag['href'] = urljoin(self.url, tag['href'])
        for tag in content_soup.find_all(['img'], src=True):
            if tag['src'].startswith('/'):
                tag['src'] = urljoin(self.url, tag['src'])


class TencentCloudExtractor(BaseExtractor):
    """腾讯云专属提取器。"""
    def _extract_content_html(self) -> BeautifulSoup:
        return self.soup.select_one('#docArticleContent') or super()._extract_content_html()

class AliyunExtractor(BaseExtractor):
    """阿里云专属提取器。"""
    def _extract_content_html(self) -> BeautifulSoup:
        return self.soup.select_one('.content-body') or super()._extract_content_html()

class HuaweiCloudExtractor(BaseExtractor):
    """华为云专属提取器。"""
    def _extract_content_html(self) -> BeautifulSoup:
        return self.soup.select_one('.content-body') or super()._extract_content_html()

class VolcengineExtractor(BaseExtractor):
    """火山引擎专属提取器。"""
    def _extract_content_html(self) -> BeautifulSoup:
        return self.soup.select_one('.markdown-body') or super()._extract_content_html()

class DefaultExtractor(BaseExtractor):
    """默认提取器，当没有特定厂商的提取器时使用。"""
    pass


def get_extractor(vendor: str, soup: BeautifulSoup, url: str) -> BaseExtractor:
    """
    提取器工厂函数。根据厂商名称返回相应的提取器实例。
    """
    extractors = {
        'tencentcloud': TencentCloudExtractor,
        'aliyun': AliyunExtractor,
        'huaweicloud': HuaweiCloudExtractor,
        'volcengine': VolcengineExtractor,
    }
    
    extractor_class = extractors.get(vendor.lower(), DefaultExtractor)
    return extractor_class(soup, url)


def advanced_html_to_markdown(html_content: str) -> str:
    """
    一个增强版的HTML到Markdown转换器，能够更好地处理复杂表格。
    它使用pandas来解析表格，从而正确处理rowspan和colspan。
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')

    for table_idx, table in enumerate(soup.find_all('table')):
        try:
            # 检查表格是否有真正的表头（th标签）
            has_real_header = bool(table.find('th'))
            
            # 使用pandas读取HTML表格
            # 如果没有真正的表头，告诉pandas不要把第一行当作header
            if has_real_header:
                df_list = pd.read_html(StringIO(str(table)), flavor='bs4')
            else:
                df_list = pd.read_html(StringIO(str(table)), flavor='bs4', header=None)
            
            if not df_list:
                continue
            
            # 一个<table>标签通常只包含一个表格
            df = df_list[0]
            
            # 数据清理：
            # 1. 删除全空的行
            df = df.dropna(how='all')
            
            # 2. 删除全空的列
            df = df.dropna(axis=1, how='all')
            
            # 3. 将NaN替换为空字符串
            df = df.fillna('')
            
            # 4. 删除所有列都是空字符串的行
            df = df[~(df == '').all(axis=1)]
            
            # 5. 特殊处理：如果第一行是空的（可能是pandas生成的空表头），删除它
            if not df.empty and (df.iloc[0] == '').all():
                df = df.iloc[1:].reset_index(drop=True)
            
            # 6. 如果DataFrame为空，跳过这个表格
            if df.empty:
                continue
            
            # 将DataFrame转换为一个简单的、没有合并单元格的HTML表格
            # header=False 确保不输出pandas自动生成的列名
            if has_real_header:
                simple_table_html = df.to_html(index=False, border=0, escape=False)
            else:
                simple_table_html = df.to_html(index=False, border=0, header=False, escape=False)
            
            simple_table_soup = BeautifulSoup(simple_table_html, 'html.parser')
            new_table = simple_table_soup.find('table')
            
            # 关键修复：将第一行的td转换为th，这样markdownify就能正确识别表头
            first_row = new_table.find('tr')
            if first_row:
                for td in first_row.find_all('td'):
                    # 创建新的th标签，复制td的内容和属性
                    th = simple_table_soup.new_tag('th')
                    th.string = td.get_text()
                    # 复制所有属性
                    for attr, value in td.attrs.items():
                        th[attr] = value
                    # 替换td为th
                    td.replace_with(th)
            
            # 替换旧的复杂表格
            table.replace_with(new_table)

        except Exception as e:
            # 如果pandas处理失败（例如，表格格式非常不规范），
            # 打印一个警告并保持原样，让markdownify尝试处理
            CONSOLE.log(f"[yellow]警告: 处理表格时出错: {e}。将回退到默认转换。[/yellow]")
            continue

    # 将整个HTML（现在只包含简单表格）转换为Markdown
    md_content = md(str(soup), heading_style="ATX", bullets='-')

    return md_content


def parse_link_file(file_path: Path):
    """从链接文件中解析URL和标题。"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    docs = []
    current_title = None
    item_pattern = re.compile(r"^\s*\d+\.\s*(.*)")

    try:
        start_index = lines.index("=" * 50 + "\n") + 2
    except ValueError:
        start_index = 0

    for i in range(start_index, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        
        match = item_pattern.match(line)
        if match:
            current_title = match.group(1).strip()
        elif (line.startswith("https://") or line.startswith("http://")) and current_title:
            docs.append({"title": current_title, "url": line})
            current_title = None
        elif current_title: # 处理多行标题
             current_title += " " + line
                
    return docs


def create_metadata_header(metadata: dict) -> str:
    """创建YAML Front Matter格式的元数据块。"""
    # 过滤掉内容字段，只保留元数据
    header_data = {k: v for k, v in metadata.items() if k not in ['md_content', 'txt_content']}
    return f"---\n{yaml.dump(header_data, allow_unicode=True)}---\n\n"


async def crawl_and_extract(page, url: str, vendor: str):
    """
    获取页面HTML，并使用适合该厂商的提取器来处理它。
    """
    try:
        response = await page.goto(url, timeout=60000, wait_until='domcontentloaded')
        html_bytes = await response.body()
        soup = BeautifulSoup(html_bytes, 'lxml')

        # 使用工厂函数获取合适的提取器
        extractor = get_extractor(vendor, soup, url)
        extracted_data = extractor.extract()

        # 将HTML内容转换为Markdown和TXT
        content_html = extracted_data.get('content_html', '')

        # 使用我们新的、更强大的HTML到Markdown转换函数
        md_content = advanced_html_to_markdown(content_html)
        
        txt_content = BeautifulSoup(content_html, 'html.parser').get_text(separator='\\n', strip=True)
        
        # 清理不需要的Unicode字符（例如：零宽非中断空格 U+FEFF）
        if md_content:
            md_content = md_content.replace('\ufeff', '')
        if txt_content:
            txt_content = txt_content.replace('\ufeff', '')
        
        return {
            "title": extracted_data.get('title'),
            "md_content": md_content,
            "txt_content": txt_content,
        }
    except Exception as e:
        CONSOLE.log(f"[red]❌ 爬取 {url} 时出错: {e}[/red]")
        return None


def save_content(output_dir: Path, metadata: dict, output_formats: list = ['md']):
    """将提取的内容和元数据保存为文件。"""
    vendor = metadata.get('vendor', 'unknown')
    product = metadata.get('product', 'unknown')
    
    safe_title = re.sub(r'[\\/*?:"<>|]', "", metadata['title'])
    safe_filename = safe_title.replace(" ", "_")[:100]

    metadata_header = create_metadata_header(metadata)
    
    content_map = {
        'md': metadata.get('md_content', ''),
        'txt': metadata.get('txt_content', '')
    }

    target_dir = output_dir / vendor / product
    target_dir.mkdir(parents=True, exist_ok=True)
        
    for format_type in output_formats:
        content_to_save = content_map.get(format_type)
        if content_to_save:
            file_path = target_dir / f"{safe_filename}.{format_type}"
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(metadata_header + content_to_save)
            except Exception as e:
                CONSOLE.log(f"[red]❌ 保存文件 {file_path} 时出错: {e}[/red]") 