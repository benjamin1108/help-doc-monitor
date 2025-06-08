import asyncio
import argparse
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from rich.console import Console
from rich.progress import Progress
from src.help_crawler.content_extractor import (
    crawl_and_extract,
    save_content,
    parse_link_file
)

# --- 配置 ---
OUTPUT_FORMATS = ['md']
# -----------

CONSOLE = Console()

async def main():
    parser = argparse.ArgumentParser(description="Crawl content from URLs found in link files or a specific URL.")
    parser.add_argument("--url", type=str, help="A single URL to crawl and extract content from.")
    parser.add_argument("--vendor", type=str, help="Specify a vendor for single URL crawling. Required if --url is used.")
    args = parser.parse_args()

    content_base_dir = Path("out/content")

    # 当使用 --url 时，--vendor 必须提供
    if args.url and not args.vendor:
        CONSOLE.log("[bold red]错误：使用 --url 时，必须通过 --vendor 指定厂商。[/bold red]")
        parser.print_help()
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        if args.url:
            CONSOLE.log(f"[bold cyan]Processing single URL: {args.url}[/bold cyan]")
            extracted_data = await crawl_and_extract(page, args.url, args.vendor)
            if extracted_data:
                full_metadata = {
                    "url": args.url,
                    "vendor": args.vendor,
                    "product": "single_url",
                    "crawl_time": datetime.now().isoformat(),
                    **extracted_data
                }
                save_content(content_base_dir, full_metadata, OUTPUT_FORMATS)
                CONSOLE.log(f"[bold green]✔ Saved output to out/content/{args.vendor}/single_url/[/bold green]")
            
            await browser.close()
            return

        # 批量处理逻辑
        links_base_dir = Path("out/links")
        if not links_base_dir.exists():
            CONSOLE.log("[bold red]错误: 'out/links' 目录未找到。[/bold red]")
            await browser.close()
            return

        link_files = list(links_base_dir.glob("*/*_links_*.txt"))
        if not link_files:
            CONSOLE.log("[bold yellow]在 'out/links' 目录中未找到链接文件。[/bold yellow]")
            await browser.close()
            return

        CONSOLE.log(f"[bold green]找到 {len(link_files)} 个链接文件待处理。[/bold green]")

        for link_file in link_files:
            CONSOLE.log(f"\n[cyan]处理文件: {link_file}[/cyan]")
            
            vendor = link_file.parent.name
            product_match = re.search(r"(\w+)_links_", link_file.name.replace(f"{vendor}_", ""))
            product_key = product_match.group(1) if product_match else "unknown"

            documents_to_crawl = parse_link_file(link_file)
            if not documents_to_crawl:
                CONSOLE.log(f"[yellow]在 {link_file} 中未找到文档。跳过。[/yellow]")
                continue

            with Progress(*Progress.get_default_columns(), console=CONSOLE) as progress:
                task = progress.add_task(f"[green]爬取 {vendor}/{product_key}", total=len(documents_to_crawl))

                for doc in documents_to_crawl:
                    extracted_data = await crawl_and_extract(page, doc['url'], vendor)
                    if extracted_data:
                        full_metadata = {
                            "url": doc['url'],
                            "vendor": vendor,
                            "product": product_key,
                            "crawl_time": datetime.now().isoformat(),
                            "title": doc['title'], # Use title from link file as primary
                            **extracted_data
                        }
                        # 如果提取器没能获取标题，使用链接文件中的标题
                        if not full_metadata["title"] or full_metadata["title"] == "Untitled":
                            full_metadata["title"] = doc['title']

                        save_content(content_base_dir, full_metadata, OUTPUT_FORMATS)
                    
                    progress.update(task, advance=1)

            CONSOLE.log(f"[bold green]✔ 完成 {vendor}/{product_key} 的内容提取。[/bold green]")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 