import asyncio
import argparse
import re
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from config_loader import config_loader
from src.help_crawler.content_extractor import (
    crawl_and_extract,
    save_content,
    parse_link_file
)

# 导入交互式库
try:
    import questionary
    IS_INTERACTIVE_ENHANCED = True
except ImportError:
    IS_INTERACTIVE_ENHANCED = False

# --- 配置 ---
OUTPUT_FORMATS = ['md']
# -----------

CONSOLE = Console()

def list_vendors():
    """列出所有可用的厂商"""
    vendors = config_loader.get_available_vendors()
    
    if IS_INTERACTIVE_ENHANCED:
        table = Table(title="所有支持的厂商", title_style="bold magenta", show_header=True, header_style="bold blue")
        table.add_column("厂商代码", style="cyan")
        table.add_column("厂商名称", style="green")
        for vendor, description in vendors.items():
            table.add_row(vendor, description)
        CONSOLE.print(table)
    else:
        print("\n可用的厂商:")
        for vendor, description in vendors.items():
            print(f"  {vendor}: {description}")
            
    return vendors


def list_products(vendor: str):
    """列出指定厂商的所有产品"""
    products = config_loader.get_vendor_products(vendor)
    if not products:
        CONSOLE.print(f"[yellow]厂商 {vendor} 没有配置产品[/yellow]")
        return None

    if IS_INTERACTIVE_ENHANCED:
        table = Table(title=f"{vendor} 平台可用产品", title_style="bold magenta", show_header=True, header_style="bold blue")
        table.add_column("产品代码", style="cyan", max_width=20)
        table.add_column("产品名称", style="green")
        table.add_column("描述", style="dim")
        for product_id, product_info in products.items():
            name = product_info.get('name', product_id)
            description = product_info.get('description', '')
            table.add_row(product_id, name, description)
        CONSOLE.print(table)
    else:
        print(f"\n{vendor} 可用的产品:")
        for product_id, product_info in products.items():
            name = product_info.get('name', product_id)
            description = product_info.get('description', '')
            print(f"  {product_id}: {name}")
            if description:
                print(f"    {description}")
                
    return products


def find_link_files(vendor: str, product: str = None):
    """查找指定厂商和产品的链接文件"""
    links_base_dir = Path("out/links")
    if not links_base_dir.exists():
        return []
    
    vendor_dir = links_base_dir / vendor
    if not vendor_dir.exists():
        return []
    
    if product:
        # 查找特定产品的链接文件，尝试多种命名模式
        patterns = [
            f"{vendor}_{product}_links_*.txt",  # 完整厂商名
            f"{vendor[:6]}_{product}_links_*.txt",  # 厂商名前6个字符（如 huawei）
            f"*_{product}_links_*.txt",  # 任意前缀
        ]
        
        link_files = []
        for pattern in patterns:
            files = list(vendor_dir.glob(pattern))
            link_files.extend(files)
            if files:  # 如果找到文件，使用第一个成功的模式
                break
    else:
        # 查找该厂商所有产品的链接文件
        link_files = list(vendor_dir.glob("*_links_*.txt"))
    
    return link_files


async def interactive_mode_enhanced():
    """增强版交互式模式"""
    CONSOLE.print(Panel("[bold yellow]🚀 内容提取爬虫 - 交互式模式[/bold yellow]", 
                        title="[bold green]Content Crawler[/bold green]", 
                        expand=False, 
                        border_style="blue"))

    while True:
        try:
            action = await questionary.select(
                "请选择您要执行的操作:",
                choices=[
                    questionary.Choice("1. 查看所有支持的厂商", value='list_vendors'),
                    questionary.Choice("2. 处理指定厂商的所有产品", value='crawl_vendor'),
                    questionary.Choice("3. 处理指定厂商的指定产品", value='crawl_product'),
                    questionary.Choice("4. 处理所有厂商的所有产品", value='crawl_all'),
                    questionary.Separator(),
                    questionary.Choice("5. 退出程序", value='exit')
                ],
                use_indicator=True
            ).ask_async()

            if action is None or action == 'exit':
                CONSOLE.print("\n[bold yellow]👋 感谢使用内容提取爬虫！[/bold yellow]\n")
                break

            if action == 'list_vendors':
                list_vendors()

            elif action == 'crawl_all':
                CONSOLE.print(f"\n🚀 即将处理所有厂商的所有产品...")
                await process_all_vendors()

            elif action in ['crawl_vendor', 'crawl_product']:
                vendors = config_loader.get_available_vendors()
                vendor = await questionary.select(
                    "请选择一个厂商:",
                    choices=[questionary.Choice(f"{v} ({d})", value=v) for v, d in vendors.items()]
                ).ask_async()

                if vendor is None: 
                    continue

                if action == 'crawl_product':
                    products = config_loader.get_vendor_products(vendor)
                    if not products:
                        CONSOLE.print(f"[yellow]厂商 {vendor} 没有配置产品[/yellow]")
                        continue
                    
                    product = await questionary.select(
                        "请选择要处理的产品:",
                        choices=[questionary.Choice(f"{p_info.get('name', p_id)} ({p_id})", value=p_id) for p_id, p_info in products.items()]
                    ).ask_async()

                    if product is None: 
                        continue
                    
                    product_name = products[product]['name']
                    CONSOLE.print(f"\n🚀 即将处理 [bold blue]{vendors[vendor]}[/bold blue] - [bold green]{product_name}[/bold green]")
                    await process_vendor_product(vendor, product)

                else: # crawl_vendor
                    CONSOLE.print(f"\n🚀 即将处理 [bold blue]{vendors[vendor]}[/bold blue] 的所有产品")
                    await process_vendor_product(vendor)
        
        except KeyboardInterrupt:
            CONSOLE.print("\n\n[bold yellow]👋 程序已取消，感谢使用！[/bold yellow]\n")
            break
        except Exception as e:
            CONSOLE.print(f"[bold red]❌ 发生意外错误: {e}[/bold red]")


async def interactive_mode():
    """原始交互式模式（作为备用）"""
    print("\n" + "="*60)
    print("🚀 内容提取爬虫 - 交互式模式")
    print("="*60)
    
    while True:
        print("\n📋 请选择操作:")
        print("  1. 查看所有支持的厂商")
        print("  2. 处理指定厂商的所有产品")
        print("  3. 处理指定厂商的指定产品")
        print("  4. 处理所有厂商的所有产品")
        print("  5. 退出程序")
        
        try:
            choice = input("\n请输入选项 (1-5): ").strip()
            
            if choice == '1':
                list_vendors()
                
            elif choice == '2':
                # 处理指定厂商的所有产品
                list_vendors()
                vendor = input("\n请输入厂商代码: ").strip().lower()
                
                vendors = config_loader.get_available_vendors()
                if vendor not in vendors:
                    print(f"❌ 无效的厂商代码: {vendor}")
                    continue
                
                print(f"\n🚀 开始处理 {vendors[vendor]} 的所有产品...")
                await process_vendor_product(vendor)
                
            elif choice == '3':
                # 处理指定厂商的指定产品
                list_vendors()
                vendor = input("\n请输入厂商代码: ").strip().lower()
                
                vendors = config_loader.get_available_vendors()
                if vendor not in vendors:
                    print(f"❌ 无效的厂商代码: {vendor}")
                    continue
                
                list_products(vendor)
                product = input("\n请输入产品代码: ").strip().lower()
                
                products = config_loader.get_vendor_products(vendor)
                if product not in products:
                    print(f"❌ 无效的产品代码: {product}")
                    continue
                
                product_name = products[product]['name']
                print(f"\n🚀 开始处理 {vendors[vendor]} - {product_name}")
                await process_vendor_product(vendor, product)
                
            elif choice == '4':
                print("\n🚀 开始处理所有厂商的所有产品...")
                await process_all_vendors()

            elif choice == '5':
                print("\n👋 感谢使用内容提取爬虫！")
                break
                
            else:
                print("❌ 无效的选项，请输入 1-5")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序已取消，感谢使用！")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")


async def process_vendor_product(vendor: str, product: str = None):
    """处理指定厂商和产品的内容提取"""
    content_base_dir = Path("out/content")
    
    # 查找对应的链接文件
    link_files = find_link_files(vendor, product)
    
    if not link_files:
        if product:
            CONSOLE.print(f"[yellow]未找到 {vendor}/{product} 的链接文件[/yellow]")
        else:
            CONSOLE.print(f"[yellow]未找到 {vendor} 的任何链接文件[/yellow]")
        return
    
    CONSOLE.print(f"[bold green]找到 {len(link_files)} 个链接文件待处理。[/bold green]")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for link_file in link_files:
            CONSOLE.log(f"\n[cyan]处理文件: {link_file}[/cyan]")
            
            vendor_name = link_file.parent.name
            product_match = re.search(r"(\w+)_links_", link_file.name.replace(f"{vendor_name}_", ""))
            product_key = product_match.group(1) if product_match else "unknown"

            documents_to_crawl = parse_link_file(link_file)
            if not documents_to_crawl:
                CONSOLE.log(f"[yellow]在 {link_file} 中未找到文档。跳过。[/yellow]")
                continue

            with Progress(*Progress.get_default_columns(), console=CONSOLE) as progress:
                task = progress.add_task(f"[green]爬取 {vendor_name}/{product_key}", total=len(documents_to_crawl))

                for doc in documents_to_crawl:
                    extracted_data = await crawl_and_extract(page, doc['url'], vendor_name)
                    if extracted_data:
                        full_metadata = {
                            "url": doc['url'],
                            "vendor": vendor_name,
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

            CONSOLE.log(f"[bold green]✔ 完成 {vendor_name}/{product_key} 的内容提取。[/bold green]")
        
        await browser.close()


async def process_all_vendors():
    """处理所有厂商的所有产品"""
    vendors = config_loader.get_available_vendors()
    for vendor in vendors:
        await process_vendor_product(vendor)


async def main():
    parser = argparse.ArgumentParser(
        description="从链接文件中爬取内容或处理单个URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s                                          # 启动交互式模式
  %(prog)s --url https://example.com --vendor aliyun # 爬取单个URL
  %(prog)s --vendor aliyun                          # 处理阿里云所有产品的链接文件
  %(prog)s --vendor aliyun --product vpc            # 处理阿里云VPC产品的链接文件
  %(prog)s --list-vendors                           # 列出所有厂商
  %(prog)s --vendor aliyun --list-products          # 列出阿里云所有产品
        """
    )
    
    parser.add_argument("--url", type=str, help="A single URL to crawl and extract content from.")
    parser.add_argument("--vendor", type=str, help="Specify a vendor for single URL crawling or batch processing.")
    parser.add_argument("--product", type=str, help="Specify a product for batch processing (requires --vendor).")
    parser.add_argument("--list-vendors", action='store_true', help='列出所有可用的厂商')
    parser.add_argument("--list-products", action='store_true', help='列出指定厂商的所有产品（需要配合--vendor使用）')
    
    args = parser.parse_args()

    # 如果没有提供任何参数，启动交互式模式
    if len(sys.argv) == 1:
        if IS_INTERACTIVE_ENHANCED:
            await interactive_mode_enhanced()
        else:
            CONSOLE.print("[yellow]提示：为了获得更好的交互体验，建议安装 `questionary` 库。[/yellow]")
            CONSOLE.print("[yellow]运行 `pip install questionary` 进行安装。[/yellow]")
            await interactive_mode()
        return

    # 列出厂商
    if args.list_vendors:
        list_vendors()
        return

    # 列出产品
    if args.list_products:
        if not args.vendor:
            CONSOLE.print("[red]使用 --list-products 时必须指定 --vendor[/red]")
            return
        list_products(args.vendor)
        return

    content_base_dir = Path("out/content")

    # 单个URL处理逻辑
    if args.url:
        # 当使用 --url 时，--vendor 必须提供
        if not args.vendor:
            CONSOLE.log("[bold red]错误：使用 --url 时，必须通过 --vendor 指定厂商。[/bold red]")
            parser.print_help()
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

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
    if args.vendor:
        # 处理指定厂商（和可选的产品）
        await process_vendor_product(args.vendor, args.product)
        return

    # 如果没有指定厂商，则处理所有链接文件（原有逻辑）
    links_base_dir = Path("out/links")
    if not links_base_dir.exists():
        CONSOLE.log("[bold red]错误: 'out/links' 目录未找到。[/bold red]")
        return

    link_files = list(links_base_dir.glob("*/*_links_*.txt"))
    if not link_files:
        CONSOLE.log("[bold yellow]在 'out/links' 目录中未找到链接文件。[/bold yellow]")
        return

    CONSOLE.log(f"[bold green]找到 {len(link_files)} 个链接文件待处理。[/bold green]")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

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