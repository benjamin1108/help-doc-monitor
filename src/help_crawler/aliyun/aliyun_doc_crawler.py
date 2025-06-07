import asyncio
import json
import time
import yaml
import os
from pathlib import Path
from playwright.async_api import async_playwright
from urllib.parse import urljoin
from datetime import datetime

class AliyunDocCrawler:
    def __init__(self, config=None, config_file="config.yaml"):
        """
        初始化爬虫
        
        Args:
            config: 配置字典（可选，如果提供则直接使用）
            config_file: 配置文件路径（config为None时使用）
        """
        if config is not None:
            self.config = config
        else:
            self.config = self.load_config(config_file)
            
        self.base_url = self.config['base_url']
        self.crawler_settings = self.config['crawler_settings']
        self.output_settings = self.config['output_settings']
        self.products = self.config['products']
        self.clicked_elements = set()
        
        # 确保阿里云专用输出目录存在
        base_output_dir = Path(self.output_settings['base_dir'])
        self.output_dir = base_output_dir / "aliyun"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_config(self, config_file):
        """加载YAML配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"❌ 配置文件 {config_file} 未找到")
            raise
        except yaml.YAMLError as e:
            print(f"❌ 配置文件格式错误: {e}")
            raise
    
    async def wait_for_update(self, page, ms=None):
        """等待DOM更新"""
        if ms is None:
            ms = self.crawler_settings['click_delay'] * 1000
        await page.wait_for_load_state('domcontentloaded', timeout=self.crawler_settings['wait_timeout'])
        await asyncio.sleep(ms / 1000)
    
    async def _expand_all_menus_dfs(self, page):
        """
        使用迭代点击的方式，高效地展开所有可折叠的侧边栏菜单。
        该方法取代了旧的、复杂的递归展开逻辑。
        """
        debug = self.crawler_settings.get("debug_mode", False)
        if debug:
            print("🔍 [DFS-Expand] 开始使用新的DFS方法展开所有菜单...")

        sidebar = await page.query_selector("#common-menu-container")
        if not sidebar:
            print("⚠️ [DFS-Expand] 未找到 #common-menu-container 侧边栏容器。")
            return

        while True:
            # 新的选择器策略:
            # 查找所有表示"关闭"状态的可展开菜单的箭头图标。
            expandable_icon_selector = 'i.help-icon-close-arrow'
            
            icons_to_click = await sidebar.query_selector_all(expandable_icon_selector)
            
            visible_icons_to_click = []
            for icon in icons_to_click:
                if await icon.is_visible():
                    visible_icons_to_click.append(icon)

            if not visible_icons_to_click:
                if debug:
                    print("✅ [DFS-Expand] 没有更多可见的 '关闭' 状态菜单，展开完成。")
                break

            if debug:
                print(f"  ▶️ [DFS-Expand] 发现 {len(visible_icons_to_click)} 个新的可展开菜单，正在处理...")

            # 依次点击图标以展开子菜单
            for icon in visible_icons_to_click:
                click_target = None # define here for except block
                try:
                    # 定位到父级<a>标签，这是更可靠的点击目标
                    click_target = await icon.query_selector("xpath=./parent::a")
                    if not click_target:
                        if debug: print("    ⚠️ [DFS-Expand] 未找到图标的父级<a>，跳过")
                        continue

                    # 点击前，确保元素在可视区域内
                    await click_target.scroll_into_view_if_needed()
                    await page.wait_for_timeout(100) # 等待滚动稳定

                    text = await click_target.text_content() or "未知菜单"
                    await click_target.click(timeout=5000)
                    
                    if debug:
                        print(f"    🖱️ [DFS-Expand] 点击展开: {text.strip()}")

                    # 每次点击后给予短暂延时，等待JS渲染
                    await self.wait_for_update(page, 50)

                except Exception as e:
                    if debug:
                        failed_text = "未知菜单"
                        try:
                            if click_target:
                                failed_text = await click_target.text_content() or failed_text
                        except:
                            pass # 获取文本失败就算了
                        print(f"    ❌ [DFS-Expand] 点击 '{failed_text.strip()}' 失败: {str(e)}")
            
            # 一轮点击完成后，等待一个完整的周期，确保DOM更新完毕
            await self.wait_for_update(page, self.crawler_settings.get("click_delay", 0.2) * 1000)
    
    async def _collect_all_links_from_sidebar(self, page):
        """
        在所有菜单都展开后，一次性从侧边栏收集所有有效的文档链接。
        """
        debug = self.crawler_settings.get("debug_mode", False)
        if debug:
            print("🔗 [Collect] 开始从侧边栏收集所有链接...")

        sidebar = await page.query_selector("#common-menu-container")
        if not sidebar:
            print("⚠️ [Collect] 未找到 #common-menu-container 容器。")
            return []

        # 选择所有包含href的<a>标签
        all_link_elements = await sidebar.query_selector_all("a[href]")
        if debug:
            print(f"  🔍 [Collect] 找到 {len(all_link_elements)} 个带 href 的 <a> 元素。")

        results = []
        seen_urls = set()

        for link in all_link_elements:
            try:
                href = await link.get_attribute("href")
                text = (await link.text_content() or "").strip()

                # 过滤无效链接
                if not text or not href or href.strip() == '#':
                    continue
                
                absolute_url = urljoin(self.base_url, href)
                
                # 必须是阿里云帮助文档的链接
                if 'help.aliyun.com' not in absolute_url:
                    continue

                # 清理URL用于去重（移除查询参数和片段）
                clean_url = absolute_url.split('?')[0].split('#')[0]

                if clean_url in seen_urls:
                    continue
                
                seen_urls.add(clean_url)
                # 保存原始URL，因为它可能包含必要信息
                results.append({"url": absolute_url, "title": text})
            except Exception as e:
                if debug:
                    print(f"  ⚠️ [Collect] 处理链接 '{href}' 时出错: {e}")

        if debug:
            print(f"✅ [Collect] 收集完成，共找到 {len(results)} 个有效文档链接。")
        return results
    
    async def crawl_document(self, page, url, title):
        """爬取单个文档"""
        if not self.output_settings['include_content']:
            # 只返回链接信息，不爬取内容
            return {
                'url': url,
                'title': title,
                'crawl_time': datetime.now().isoformat()
            }
        
        try:
            await page.goto(url, timeout=self.crawler_settings['wait_timeout'], wait_until='domcontentloaded')
            await asyncio.sleep(0.2)
            
            # 并行获取内容
            content_selectors = ['.content-body', '.doc-content', '.article-content', 'main']
            content = ""
            
            for selector in content_selectors:
                content_element = await page.query_selector(selector)
                if content_element:
                    content = await content_element.text_content()
                    if content and len(content.strip()) > 50:
                        break
            
            page_title = await page.title()
            
            return {
                'url': url,
                'title': title or page_title,
                'content': content.strip() if content else "",
                'crawl_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'url': url,
                'title': title,
                'content': "",
                'error': str(e),
                'crawl_time': datetime.now().isoformat()
            }
    
    async def save_product_results(self, product_key, product_info, documents):
        """保存单个产品的结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        product_name = product_info['name']
        
        # 保存在阿里云专用目录下
        # 保存链接列表
        links_file = self.output_dir / f"aliyun_{product_key}_links_{timestamp}.txt"
        with open(links_file, 'w', encoding='utf-8') as f:
            f.write(f"{product_name}帮助文档链接\n")
            f.write("=" * 50 + "\n")
            f.write(f"产品: {product_name}\n")
            f.write(f"描述: {product_info['description']}\n")
            f.write(f"起始URL: {product_info['url']}\n")
            f.write(f"爬取时间: {timestamp}\n")
            f.write(f"文档数量: {len(documents)}\n")
            f.write("=" * 50 + "\n\n")
            
            for i, doc in enumerate(documents, 1):
                f.write(f"{i:3d}. {doc['title']}\n")
                f.write(f"     {doc['url']}\n\n")
        
        # 如果包含内容，保存JSON文件
        if self.output_settings['include_content']:
            json_file = self.output_dir / f"aliyun_{product_key}_data_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'product': product_info,
                    'crawl_info': {
                        'timestamp': timestamp,
                        'total_docs': len(documents)
                    },
                    'documents': documents
                }, f, ensure_ascii=False, indent=2)
        
        return links_file, self.output_dir
    
    async def crawl_product(self, product_key, product_info):
        """爬取单个产品的文档"""
        print(f"\n🚀 开始爬取: {product_info['name']}")
        print(f"📍 URL: {product_info['url']}")
        print("-" * 60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.crawler_settings['headless'],
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-images']
            )
            
            try:
                context = await browser.new_context()
                page = await context.new_page()
                
                start_time = time.time()
                
                # 1. 加载页面
                print("1️⃣ 加载页面...")
                await page.goto(product_info['url'], timeout=self.crawler_settings['wait_timeout'], wait_until='domcontentloaded')
                await self.wait_for_update(page, 500)
                print(f"✓ 页面加载完成 ({time.time() - start_time:.1f}s)")
                
                # 2. 展开菜单 (NEW EFFICIENT LOGIC)
                print("2️⃣ 高效展开菜单...")
                if self.crawler_settings.get('debug_mode', False):
                    print(f"🔧 调试模式已启用，将显示详细展开过程")
                expand_start = time.time()
                await self._expand_all_menus_dfs(page)
                print(f"✓ 菜单展开完成 ({time.time() - expand_start:.1f}s)")
                
                # 3. 收集链接 (NEW EFFICIENT LOGIC)
                print("3️⃣ 收集文档链接...")
                docs_info = await self._collect_all_links_from_sidebar(page)
                print(f"✓ 收集到 {len(docs_info)} 个文档链接")
                
                if not docs_info:
                    print("❌ 未找到文档链接")
                    return None
                
                # 4. 爬取文档
                documents = []
                if self.output_settings['include_content']:
                    print(f"4️⃣ 爬取 {len(docs_info)} 个文档内容...")
                    crawl_start = time.time()
                    
                    for i, doc_info in enumerate(docs_info, 1):
                        if i % 20 == 0:
                            print(f"  进度: {i}/{len(docs_info)} ({i/len(docs_info)*100:.1f}%)")
                        
                        doc_data = await self.crawl_document(page, doc_info['url'], doc_info['title'])
                        documents.append(doc_data)
                        
                        if i < len(docs_info):
                            await asyncio.sleep(self.crawler_settings['crawl_delay'])
                    
                    print(f"✓ 文档爬取完成 ({time.time() - crawl_start:.1f}s)")
                else:
                    # 只保存链接信息
                    for doc_info in docs_info:
                        documents.append({
                            'url': doc_info['url'],
                            'title': doc_info['title'],
                            'crawl_time': datetime.now().isoformat()
                        })
                
                # 5. 保存结果
                print("5️⃣ 保存结果...")
                links_file, output_dir = await self.save_product_results(product_key, product_info, documents)
                
                total_time = time.time() - start_time
                print(f"✅ {product_info['name']} 爬取完成！")
                print(f"📄 文件保存至: {output_dir}")
                print(f"🔗 链接文件: {links_file.name}")
                print(f"⏱️  总耗时: {total_time:.1f}s")
                
                return {
                    'product_key': product_key,
                    'product_name': product_info['name'],
                    'total_docs': len(documents),
                    'output_dir': str(output_dir),
                    'links_file': str(links_file),
                    'duration': total_time
                }
                
            finally:
                await browser.close()
    
    async def crawl_all_products(self, selected_products=None):
        """爬取所有产品或指定产品的文档"""
        if selected_products:
            products_to_crawl = {k: v for k, v in self.products.items() if k in selected_products}
        else:
            products_to_crawl = self.products
        
        print(f"🎯 准备爬取 {len(products_to_crawl)} 个产品的帮助文档")
        print(f"📁 输出目录: {self.output_dir.absolute()}")
        print("-" * 70)

        results = []
        total_start_time = time.time()
        
        # 运行选定的爬虫
        for i, (key, info) in enumerate(products_to_crawl.items(), 1):
            print(f"[{i}/{len(products_to_crawl)}] 正在处理: {info['name']} ({key})")
            try:
                res = await self.crawl_product(key, info)
                if res:
                    results.append(res)
            except Exception as e:
                print(f"❌ 爬取 '{info['name']}' 失败: {e}")
                import traceback
                traceback.print_exc()

        total_elapsed_time = time.time() - total_start_time
        print("\n" + "=" * 70)
        print(f"✅ 所有产品爬取完成，总耗时: {total_elapsed_time:.2f}秒")
        
        # # 生成总结报告
        # await self.generate_summary_report(results, total_elapsed_time)
        
        return results

    # async def generate_summary_report(self, results, total_time):
    #     """生成总结报告"""
    #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     report_file = self.output_dir / f"aliyun_crawl_summary_{timestamp}.txt"
    #     
    #     total_docs = sum(r['doc_count'] for r in results)
    #     
    #     with open(report_file, 'w', encoding='utf-8') as f:
    #         f.write("阿里云文档爬取总结报告\n")
    #         f.write("=" * 50 + "\n")
    #         f.write(f"报告生成时间: {timestamp}\n")
    #         f.write(f"总耗时: {total_time:.2f} 秒\n")
    #         f.write(f"爬取产品数: {len(results)}\n")
    #         f.write(f"总文档数: {total_docs}\n")
    #         f.write("=" * 50 + "\n\n")
    #         
    #         for res in results:
    #             f.write(f"产品: {res['product_name']} ({res['product_key']})\n")
    #             f.write(f"  - 文档数量: {res['doc_count']}\n")
    #             f.write(f"  - 耗时: {res['duration']:.2f} 秒\n")
    #             f.write(f"  - 链接文件: {res['links_file']}\n\n")
    #             
    #     print(f"📊 总结报告已生成: {report_file}")

async def main():
    """主函数"""
    crawler = AliyunDocCrawler()
    
    # 可以指定要爬取的产品，如果不指定则爬取所有产品
    # selected_products = ['alb', 'nlb', 'ecs']  # 示例：只爬取这几个产品
    selected_products = None  # 爬取所有产品
    
    results = await crawler.crawl_all_products(selected_products)
    
    print(f"\n🎉 所有任务完成！共处理 {len(results)} 个产品")

if __name__ == "__main__":
    asyncio.run(main()) 