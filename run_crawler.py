#!/usr/bin/env python3
"""
多云平台帮助文档爬虫主程序

支持爬取阿里云、腾讯云、华为云、火山引擎的帮助文档
配置文件已按厂商拆分到 config/ 目录下
"""

import sys
import argparse
import asyncio
import inspect
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from config_loader import config_loader
from help_crawler.aliyun.aliyun_doc_crawler import AliyunDocCrawler
from help_crawler.tencentcloud.tencentcloud_doc_crawler import TencentCloudDocCrawler
from help_crawler.huaweicloud.huaweicloud_doc_crawler import HuaweiCloudDocCrawler
from help_crawler.volcengine.volcengine_doc_crawler import VolcEngineDocCrawler

# 导入新库
try:
    import questionary
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    IS_INTERACTIVE_ENHANCED = True
except ImportError:
    IS_INTERACTIVE_ENHANCED = False

console = Console()


def get_crawler_class(vendor: str):
    """
    根据厂商名称获取对应的爬虫类
    
    Args:
        vendor: 厂商名称
        
    Returns:
        爬虫类
    """
    crawler_classes = {
        'aliyun': AliyunDocCrawler,
        'tencentcloud': TencentCloudDocCrawler,
        'huaweicloud': HuaweiCloudDocCrawler,
        'volcengine': VolcEngineDocCrawler
    }
    return crawler_classes.get(vendor)


async def run_vendor_crawler(vendor: str, product: str = None):
    """
    运行指定厂商的爬虫
    
    Args:
        vendor: 厂商名称
        product: 产品名称（可选，如果不指定则爬取所有产品）
    """
    print(f"\n开始运行 {vendor} 爬虫...")
    
    # 获取厂商配置
    vendor_config = config_loader.get_vendor_config(vendor)
    if not vendor_config:
        print(f"无法加载厂商配置: {vendor}")
        return
    
    # 获取爬虫类
    crawler_class = get_crawler_class(vendor)
    if not crawler_class:
        print(f"不支持的厂商: {vendor}")
        return
    
    # 创建爬虫实例，直接传入配置字典
    try:
        crawler = crawler_class(vendor_config)
    except Exception as e:
        console.print(f"[red]创建爬虫实例失败: {e}[/red]")
        return
    
    # 运行爬虫
    try:
        if product:
            # 爬取指定产品
            products = vendor_config.get('products', {})
            if product not in products:
                console.print(f"[red]产品 {product} 不存在于 {vendor} 配置中[/red]")
                return
            
            product_info = products[product]
            console.print(f"爬取产品: [bold cyan]{product_info['name']}[/bold cyan]")
            
            # 检查 crawl_product 方法签名
            sig = inspect.signature(crawler.crawl_product)
            if 'info' in sig.parameters:
                await crawler.crawl_product(product, product_info)
            else:
                await crawler.crawl_product(product)
        else:
            # 爬取所有产品
            await crawler.crawl_all_products()
            
        console.print(f"[green]{vendor} 爬虫运行完成[/green]")
        
    except Exception as e:
        console.print(f"[red]爬虫运行失败: {e}[/red]")
        import traceback
        traceback.print_exc()


def list_vendors():
    """列出所有可用的厂商"""
    vendors = config_loader.get_available_vendors()
    
    if IS_INTERACTIVE_ENHANCED:
        table = Table(title="所有支持的厂商", title_style="bold magenta", show_header=True, header_style="bold blue")
        table.add_column("厂商代码", style="cyan")
        table.add_column("厂商名称", style="green")
        for vendor, description in vendors.items():
            table.add_row(vendor, description)
        console.print(table)
    else:
        print("\n可用的厂商:")
        for vendor, description in vendors.items():
            print(f"  {vendor}: {description}")
            
    return vendors


def list_products(vendor: str):
    """列出指定厂商的所有产品"""
    products = config_loader.get_vendor_products(vendor)
    if not products:
        console.print(f"[yellow]厂商 {vendor} 没有配置产品[/yellow]")
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
        console.print(table)
    else:
        print(f"\n{vendor} 可用的产品:")
        for product_id, product_info in products.items():
            name = product_info.get('name', product_id)
            description = product_info.get('description', '')
            print(f"  {product_id}: {name}")
            if description:
                print(f"    {description}")
                
    return products


async def interactive_mode_enhanced():
    """增强版交互式模式"""
    console.print(Panel("[bold yellow]🚀 多云平台帮助文档爬虫 - 交互式模式[/bold yellow]", 
                        title="[bold green]Welcome[/bold green]", 
                        expand=False, 
                        border_style="blue"))

    while True:
        try:
            action = await questionary.select(
                "请选择您要执行的操作:",
                choices=[
                    questionary.Choice("1. 查看所有支持的厂商", value='list_vendors'),
                    questionary.Choice("2. 爬取指定厂商的所有产品", value='crawl_vendor'),
                    questionary.Choice("3. 爬取指定厂商的指定产品", value='crawl_product'),
                    questionary.Separator(),
                    questionary.Choice("4. 退出程序", value='exit')
                ],
                use_indicator=True
            ).ask_async()

            if action is None or action == 'exit':
                console.print("\n[bold yellow]👋 感谢使用多云平台帮助文档爬虫！[/bold yellow]\n")
                break

            if action == 'list_vendors':
                list_vendors()

            elif action in ['crawl_vendor', 'crawl_product']:
                vendors = config_loader.get_available_vendors()
                vendor = await questionary.select(
                    "请选择一个厂商:",
                    choices=[questionary.Choice(f"{v} ({d})", value=v) for v, d in vendors.items()]
                ).ask_async()

                if vendor is None: continue

                if action == 'crawl_product':
                    products = config_loader.get_vendor_products(vendor)
                    if not products:
                        console.print(f"[yellow]厂商 {vendor} 没有配置产品[/yellow]")
                        continue
                    
                    product = await questionary.select(
                        "请选择要爬取的产品:",
                        choices=[questionary.Choice(f"{p_info.get('name', p_id)} ({p_id})", value=p_id) for p_id, p_info in products.items()]
                    ).ask_async()

                    if product is None: continue
                    
                    product_name = products[product]['name']
                    console.print(f"\n🚀 即将爬取 [bold blue]{vendors[vendor]}[/bold blue] - [bold green]{product_name}[/bold green]")
                    if await questionary.confirm("确认开始爬取吗?", default=True).ask_async():
                        await run_vendor_crawler(vendor, product)

                else: # crawl_vendor
                    console.print(f"\n🚀 即将爬取 [bold blue]{vendors[vendor]}[/bold blue] 的所有产品")
                    if await questionary.confirm("确认开始爬取吗?", default=True).ask_async():
                        await run_vendor_crawler(vendor)
        
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]👋 程序已取消，感谢使用！[/bold yellow]\n")
            break
        except Exception as e:
            console.print(f"[bold red]❌ 发生意外错误: {e}[/bold red]")


async def interactive_mode():
    """原始交互式模式（作为备用）"""
    import sys
    
    print("\n" + "="*60)
    print("🚀 多云平台帮助文档爬虫 - 交互式模式")
    print("="*60)
    sys.stdout.flush()
    
    while True:
        print("\n📋 请选择操作:")
        print("  1. 查看所有支持的厂商")
        print("  2. 爬取指定厂商的所有产品")
        print("  3. 爬取指定厂商的指定产品")
        print("  4. 退出程序")
        sys.stdout.flush()
        
        try:
            choice = input("\n请输入选项 (1-4): ").strip()
            
            if choice == '1':
                list_vendors()
                
            elif choice == '2':
                # 爬取指定厂商的所有产品
                list_vendors()
                sys.stdout.flush()
                vendor = input("\n请输入厂商代码: ").strip().lower()
                
                vendors = config_loader.get_available_vendors()
                if vendor not in vendors:
                    print(f"❌ 无效的厂商代码: {vendor}")
                    continue
                
                print(f"\n🚀 开始爬取 {vendors[vendor]} 的所有产品...")
                sys.stdout.flush()
                confirm = input("确认开始？(y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    await run_vendor_crawler(vendor)
                
            elif choice == '3':
                # 爬取指定厂商的指定产品
                list_vendors()
                sys.stdout.flush()
                vendor = input("\n请输入厂商代码: ").strip().lower()
                
                vendors = config_loader.get_available_vendors()
                if vendor not in vendors:
                    print(f"❌ 无效的厂商代码: {vendor}")
                    continue
                
                list_products(vendor)
                sys.stdout.flush()
                product = input("\n请输入产品代码: ").strip().lower()
                
                products = config_loader.get_vendor_products(vendor)
                if product not in products:
                    print(f"❌ 无效的产品代码: {product}")
                    continue
                
                product_name = products[product]['name']
                print(f"\n🚀 开始爬取 {vendors[vendor]} - {product_name}")
                sys.stdout.flush()
                confirm = input("确认开始？(y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    await run_vendor_crawler(vendor, product)
                
            elif choice == '4':
                print("\n👋 感谢使用多云平台帮助文档爬虫！")
                break
                
            else:
                print("❌ 无效的选项，请输入 1-4")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序已取消，感谢使用！")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="多云平台帮助文档爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s                                   # 启动交互式模式
  %(prog)s --list-vendors                    # 列出所有厂商
  %(prog)s --vendor aliyun --list-products   # 列出阿里云所有产品
  %(prog)s --vendor aliyun                   # 爬取阿里云所有产品
  %(prog)s --vendor aliyun --product vpc     # 爬取阿里云VPC产品
  %(prog)s --vendor tencentcloud             # 爬取腾讯云所有产品
        """
    )
    
    parser.add_argument(
        '--vendor', 
        choices=['aliyun', 'tencentcloud', 'huaweicloud', 'volcengine'],
        help='指定要爬取的厂商'
    )
    
    parser.add_argument(
        '--product',
        help='指定要爬取的产品（仅在指定vendor时有效）'
    )
    
    parser.add_argument(
        '--list-vendors',
        action='store_true',
        help='列出所有可用的厂商'
    )
    
    parser.add_argument(
        '--list-products',
        action='store_true',
        help='列出指定厂商的所有产品（需要配合--vendor使用）'
    )
    
    args = parser.parse_args()
    
    # 如果没有提供任何参数，启动交互式模式
    if len(sys.argv) == 1:
        if IS_INTERACTIVE_ENHANCED:
            await interactive_mode_enhanced()
        else:
            console.print("[yellow]提示：为了获得更好的交互体验，建议安装 `rich` 和 `questionary` 库。[/yellow]")
            console.print("[yellow]运行 `pip install -r requirements.txt` 进行安装。[/yellow]")
            await interactive_mode()
        return
    
    # 列出厂商
    if args.list_vendors:
        list_vendors()
        return
    
    # 列出产品
    if args.list_products:
        if not args.vendor:
            console.print("[red]使用 --list-products 时必须指定 --vendor[/red]")
            return
        list_products(args.vendor)
        return
    
    # 运行爬虫
    if args.vendor:
        await run_vendor_crawler(args.vendor, args.product)
    else:
        console.print("[red]请指定要运行的厂商爬虫，使用 --vendor 参数[/red]")
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main()) 