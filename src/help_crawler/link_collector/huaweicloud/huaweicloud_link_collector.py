import asyncio
import json
import time
import yaml
import glob
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timedelta

from playwright.async_api import async_playwright


class HuaweiCloudLinkCollector:
    """华为云帮助文档爬虫
    
    针对华为云文档侧边栏 DOM 结构进行适配，支持深层级菜单展开。
    """

    def __init__(self, config=None, config_file: str = "config.yaml") -> None:
        """
        初始化爬虫
        
        Args:
            config: 配置字典（可选，如果提供则直接使用）
            config_file: 配置文件路径（config为None时使用）
        """
        if config is not None:
            # 直接使用传入的配置字典
            hw_conf = config
        else:
            # 从文件加载配置
            self.raw_config = self._load_config(config_file)
            hw_conf = self.raw_config.get("huaweicloud", {})

            if not hw_conf:
                raise ValueError("config.yaml 缺少 huaweicloud 节点")

        # 基本配置
        self.base_url: str = hw_conf.get("base_url", "https://support.huaweicloud.com")
        self.crawler_settings: dict = hw_conf.get("crawler_settings", {})
        self.output_settings: dict = hw_conf.get("output_settings", {})
        self.products: dict = hw_conf.get("products", {})
        self.clicked_elements = set()

        # 输出目录
        base_output_dir = Path(self.output_settings.get("base_dir", "out"))
        self.output_dir = base_output_dir / "links" / "huaweicloud"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load_config(config_file: str):
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    async def _wait_dom(self, page, ms: int | None = None):
        await page.wait_for_load_state("domcontentloaded", timeout=self.crawler_settings.get("wait_timeout", 10000))
        if ms is None:
            ms = int(self.crawler_settings.get("click_delay", 0.2) * 1000)
        await asyncio.sleep(ms / 1000)

    async def _collect_visible_links(self, page, results, seen_urls):
        """收集当前所有可见的链接"""
        # 每次都重新查询sidebar，避免元素失效
        sidebar = await page.query_selector("div.side-nav.sidenav-main")
        if not sidebar:
            return 0
            
        all_link_elements = await sidebar.query_selector_all("a.js-title.ajax-nav")
        new_links_count = 0
        base_url_for_join = self.base_url + "/" if not self.base_url.endswith("/") else self.base_url
        
        for link in all_link_elements:
            try:
                if not await link.is_visible():
                    continue

                href = await link.get_attribute("p-href") or await link.get_attribute("href") or ""
                text = (await link.text_content() or "").strip()

                if not text or not href or href.startswith("javascript:"):
                    continue

                # 使用 urljoin 保证链接正确拼接
                final_url = urljoin(base_url_for_join, href)

                if final_url not in seen_urls:
                    seen_urls.add(final_url)
                    results.append({"url": final_url, "title": text})
                    new_links_count += 1
            except Exception:
                # 忽略单个元素的错误，继续处理其他元素
                continue
                
        return new_links_count

    async def _expand_all_menus_dfs(self, page):
        """
        以深度优先(DFS)的迭代方式，模拟用户点击行为，将所有可展开的菜单项全部展开。
        这个方法只负责展开，不收集链接，以提高效率。
        """
        debug = self.crawler_settings.get("debug_mode", False)
        if debug:
            print("🔍 [Crawl] 开始深度优先展开所有菜单...")

        # 循环直到没有新的可展开项为止
        while True:
            # 每次循环都重新查询所有元素，保证健壮性
            sidebar = await page.query_selector("div.side-nav.sidenav-main")
            if not sidebar:
                if debug:
                    print("⚠️ [Crawl] 侧边栏消失，结束流程。")
                break

            expandable_selector = "li.nav-item:not(.unfold):has(> i.foldIcon) > a.js-title"
            
            link_to_click = None
            try:
                # 找到所有可展开的链接
                potential_links = await sidebar.query_selector_all(expandable_selector)
                
                # 深度优先：只找第一个可见的进行点击
                for link in potential_links:
                    if await link.is_visible():
                        link_to_click = link
                        break
            except Exception as e:
                if debug:
                    print(f"    ❌ [Crawl] 查询可展开菜单时出错: {e}")
                break

            # 如果没有找到可点击的链接，说明全部展开完毕
            if not link_to_click:
                if debug:
                    print("✅ [Crawl] 没有发现新的可展开菜单，展开完成。")
                break
            
            try:
                if debug:
                    text = await link_to_click.text_content() or ""
                    print(f"  ▶️ [Crawl] 点击展开: {text.strip()}")
                
                await link_to_click.click(timeout=5000)
                await page.wait_for_timeout(50) # 轻量级等待，避免过度延迟
            except Exception as e:
                if debug:
                    print(f"    ❌ [Crawl] 点击菜单失败: {e}，尝试进入下一次循环。")
                # 如果点击失败（例如元素在查询后到点击前消失了），就继续下一次循环
                continue
        
        if debug:
            print("✅ [Crawl] 所有菜单展开完毕。")

    async def _collect_all_links_from_sidebar(self, page):
        """
        在所有菜单都展开后，一次性收集侧边栏中所有可见的文档链接。
        """
        debug = self.crawler_settings.get("debug_mode", False)
        if debug:
            print("🔍 [Crawl] 开始收集所有链接...")

        results = []
        seen_urls = set()
        
        # _collect_visible_links 内部会重新查询 sidebar，是安全的
        await self._collect_visible_links(page, results, seen_urls)

        if debug:
            print(f"✅ [Crawl] 收集完成，共找到 {len(results)} 个有效文档链接。")
        
        return results

    def _create_link_record(self, url: str, title: str):
        """创建链接记录，只保存链接信息"""
        return {"url": url, "title": title, "crawl_time": datetime.now().isoformat()}

    async def _save_product(self, key: str, info: dict, docs: list[dict]):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        links_file = self.output_dir / f"huawei_{key}_links_{ts}.txt"

        with open(links_file, "w", encoding="utf-8") as f:
            f.write(f"{info['name']} 帮助文档链接\n")
            f.write("=" * 50 + "\n")
            f.write(f"产品: {info['name']}\n")
            f.write(f"描述: {info['description']}\n")
            f.write(f"起始URL: {info['url']}\n")
            f.write(f"文档数量: {len(docs)}\n")
            f.write(f"生成时间: {ts}\n")
            f.write("=" * 50 + "\n\n")
            for idx, doc in enumerate(docs, 1):
                f.write(f"{idx:3d}. {doc['title']}\n")
                f.write(f"     {doc['url']}\n\n")

        return links_file

    def _should_skip_crawl(self, key: str) -> bool:
        """
        根据文件时间戳和配置的间隔，判断是否应该跳过爬取。
        """
        recrawl_interval_hours = self.output_settings.get('recrawl_interval_hours', 24)

        # 查找最新的文件
        search_pattern = str(self.output_dir / f"huawei_{key}_links_*.txt")
        existing_files = glob.glob(search_pattern)
        if not existing_files:
            return False

        latest_file = max(existing_files, key=lambda p: Path(p).stat().st_mtime)
        file_mod_time = datetime.fromtimestamp(Path(latest_file).stat().st_mtime)
        
        # 检查文件是否在有效期间内
        if datetime.now() - file_mod_time < timedelta(hours=recrawl_interval_hours):
            print(f"✅ 产品 '{key}' 在 {recrawl_interval_hours} 小时内已有新文件，本次跳过爬取。")
            print(f"   📄 文件: {Path(latest_file).name}")
            return True
            
        return False

    async def crawl_product(self, key: str, info: dict):
        if self._should_skip_crawl(key):
            return

        print(f"\n🚀 开始爬取: {info['name']}")
        print(f"📍 URL: {info['url']}")
        print("-" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.crawler_settings.get("headless", True),
                                              args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-images"])
            try:
                context = await browser.new_context()
                page = await context.new_page()

                t0 = time.time()
                print("1️⃣  加载页面...")
                await page.goto(info['url'], timeout=self.crawler_settings.get("wait_timeout", 20000), wait_until="domcontentloaded")
                await page.wait_for_timeout(100)
                print(f"✓ 页面加载完成 ({time.time() - t0:.1f}s)")

                if self.crawler_settings.get("debug_mode", False):
                    print("🔍 保存页面HTML用于调试...")
                    html_content = await page.content()
                    debug_file = self.output_dir / f"debug_{key}_page.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print(f"📄 页面HTML已保存: {debug_file.name}")

                print("2️⃣  动态展开所有菜单...")
                t1 = time.time()
                await self._expand_all_menus_dfs(page)
                print(f"✓ 菜单展开完成 ({time.time() - t1:.1f}s)")
                
                print("3️⃣  收集所有链接...")
                docs_info = await self._collect_all_links_from_sidebar(page)
                
                print(f"✓ 共收集到 {len(docs_info)} 条记录")
                if not docs_info:
                    print("⚠️  未找到任何文档链接，跳过该产品")
                    return None

                # 只保存链接信息，不提取内容
                final_docs = []
                for doc_info in docs_info:
                    final_docs.append(self._create_link_record(doc_info['url'], doc_info['title']))

                print("5️⃣  保存结果...")
                links_path = await self._save_product(key, info, final_docs)
                elapsed = time.time() - t0
                print(f"✅ {info['name']} 爬取完成，耗时 {elapsed:.1f}s，链接文件: {links_path.name}")

                return {"product_key": key, "product_name": info['name'], "total_docs": len(final_docs),
                        "links_file": str(links_path), "duration": elapsed}
            finally:
                await browser.close()

    async def crawl_all_products(self, selected_products: list[str] | None = None):
        products = self.products if not selected_products else {k: v for k, v in self.products.items() if k in selected_products}
        print(f"🎯 计划爬取 {len(products)} 个产品文档")
        print(f"📂 输出目录: {self.output_dir.resolve()}")
        print("=" * 70)

        results = []
        all_start = time.time()
        for idx, (k, info) in enumerate(products.items(), 1):
            print(f"\n[{idx}/{len(products)}] 当前产品: {info['name']} ({k})")
            try:
                res = await self.crawl_product(k, info)
                if res:
                    results.append(res)
            except Exception as exc:
                print(f"❌ 爬取 {info['name']} 失败: {exc}")
                continue

        # 汇总
        print(f"\n🏁 所有产品爬取完成，总耗时: {time.time() - all_start:.1f}s")
        return results


if __name__ == "__main__":
    async def _self_test():
        crawler = HuaweiCloudLinkCollector()
        # 假设在 config.yaml 中已配置了 'vpc' 产品
        await crawler.crawl_all_products(["vpc"])

    asyncio.run(_self_test()) 