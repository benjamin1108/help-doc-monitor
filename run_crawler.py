#!/usr/bin/env python3
"""
多云平台帮助文档爬虫主程序

支持爬取阿里云、腾讯云、华为云、火山引擎的帮助文档
配置文件已按厂商拆分到 config/ 目录下
"""

import sys
import argparse
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from config_loader import config_loader
from help_crawler.aliyun.aliyun_doc_crawler import AliyunDocCrawler
from help_crawler.tencentcloud.tencentcloud_doc_crawler import TencentCloudDocCrawler
from help_crawler.huaweicloud.huaweicloud_doc_crawler import HuaweiCloudDocCrawler
from help_crawler.volcengine.volcengine_doc_crawler import VolcEngineDocCrawler


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


def run_vendor_crawler(vendor: str, product: str = None):
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
        print(f"创建爬虫实例失败: {e}")
        return
    
    # 运行爬虫
    try:
        if product:
            # 爬取指定产品
            products = vendor_config.get('products', {})
            if product not in products:
                print(f"产品 {product} 不存在于 {vendor} 配置中")
                return
            
            print(f"爬取产品: {products[product]['name']}")
            crawler.crawl_product(product)
        else:
            # 爬取所有产品
            crawler.crawl_all_products()
            
        print(f"{vendor} 爬虫运行完成")
        
    except Exception as e:
        print(f"爬虫运行失败: {e}")
        import traceback
        traceback.print_exc()


def list_vendors():
    """列出所有可用的厂商"""
    vendors = config_loader.get_available_vendors()
    print("\n可用的厂商:")
    for vendor, description in vendors.items():
        print(f"  {vendor}: {description}")


def list_products(vendor: str):
    """列出指定厂商的所有产品"""
    products = config_loader.get_vendor_products(vendor)
    if not products:
        print(f"厂商 {vendor} 没有配置产品")
        return
    
    print(f"\n{vendor} 可用的产品:")
    for product_id, product_info in products.items():
        name = product_info.get('name', product_id)
        description = product_info.get('description', '')
        print(f"  {product_id}: {name}")
        if description:
            print(f"    {description}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="多云平台帮助文档爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
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
    
    # 如果没有提供任何参数，显示帮助信息
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # 列出厂商
    if args.list_vendors:
        list_vendors()
        return
    
    # 列出产品
    if args.list_products:
        if not args.vendor:
            print("使用 --list-products 时必须指定 --vendor")
            return
        list_products(args.vendor)
        return
    
    # 运行爬虫
    if args.vendor:
        run_vendor_crawler(args.vendor, args.product)
    else:
        print("请指定要运行的厂商爬虫，使用 --vendor 参数")
        parser.print_help()


if __name__ == "__main__":
    main() 