import asyncio
import json
import time
import yaml
import glob
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timedelta

from playwright.async_api import async_playwright


class VolcEngineLinkCollector:
    """火山引擎帮助文档爬虫
    
    针对火山引擎文档侧边栏 DOM 结构进行适配，支持深层级菜单展开。
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
            vc_conf = config
        else:
            # 从文件加载配置
            self.raw_config = self._load_config(config_file)
            vc_conf = self.raw_config.get("volcengine", {})

            if not vc_conf:
                raise ValueError("config.yaml 缺少 volcengine 节点")

        # 基本配置
        self.base_url: str = vc_conf.get("base_url", "https://www.volcengine.com")
        self.crawler_settings: dict = vc_conf.get("crawler_settings", {})
        self.output_settings: dict = vc_conf.get("output_settings", {})
        self.products: dict = vc_conf.get("products", {})
        self.clicked_elements = set()

        # 移除内容提取器，只专注于链接收集

        # 输出目录
        base_output_dir = Path(self.output_settings.get("base_dir", "out"))
        self.output_dir = base_output_dir / "links" / "volcengine"
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

    async def _expand_all_menus_dfs(self, page):
        """
        使用深度优先的方法，通过迭代点击展开所有可折叠的侧边栏菜单。
        火山引擎的菜单是通过 aria-expanded 属性来控制展开/折叠状态的。
        """
        debug = self.crawler_settings.get("debug_mode", False)
        if debug:
            print("🔍 [DFS] 开始展开所有菜单...")

        # 找到侧边栏容器
        sidebar_selector = ".arco-menu-inner" #
        sidebar = await page.query_selector(sidebar_selector)
        if not sidebar:
            print(f"⚠️ [DFS] 未找到 {sidebar_selector} 侧边栏容器。")
            return
            
        while True:
            # 查找所有当前可见的、但未展开的菜单头
            expandable_selector = 'div.arco-menu-inline-header[aria-expanded="false"]'
            
            headers_to_click = await sidebar.query_selector_all(expandable_selector)
            
            # 只处理可见的节点
            visible_headers = []
            for header in headers_to_click:
                if await header.is_visible():
                    visible_headers.append(header)

            if not visible_headers:
                # 如果没有更多可展开的菜单，说明已经全部展开
                if debug:
                    print("✅ [DFS] 没有更多可展开的菜单，展开完成。")
                break

            if debug:
                print(f"  ▶️ [DFS] 发现 {len(visible_headers)} 个新的可展开菜单，正在处理...")

            # 依次点击找到的菜单头以展开子菜单
            for i, header in enumerate(visible_headers):
                try:
                    # 使用 span.label-z77I 获取文本内容
                    text_element = await header.query_selector("span.label-z77I")
                    text = await text_element.text_content() if text_element else "未知菜单"
                    
                    await header.click(timeout=5000)
                    if debug and (i + 1) % 10 == 0:
                        print(f"    🖱️ [DFS] 已点击 ({i+1}/{len(visible_headers)}): {text.strip()}")
                    # 等待一下，让 JS 有时间渲染 DOM
                    await self._wait_dom(page, 50) 
                except Exception as e:
                    if debug:
                        text_element = await header.query_selector("span.label-z77I")
                        text_content = await text_element.text_content() if text_element else "未知元素"
                        print(f"    ❌ [DFS] 点击 '{text_content.strip()}' 失败: {e}")
            
            # 短暂等待，确保所有点击操作的DOM更新都已完成
            await self._wait_dom(page, self.crawler_settings.get("click_delay", 0.2) * 1000)

    async def _collect_all_links_from_sidebar(self, page):
        """
        在所有菜单都展开后，从侧边栏收集所有有效的文档链接。
        火山引擎的链接在 a 标签内，文本在 span.label-z77I 中。
        """
        debug = self.crawler_settings.get("debug_mode", False)
        if debug:
            print("🔗 [Collect] 开始收集所有链接...")

        sidebar_selector = ".arco-menu-inner"
        sidebar = await page.query_selector(sidebar_selector)
        if not sidebar:
            return []

        # 获取所有导航链接
        all_link_elements = await sidebar.query_selector_all("a")
        if debug:
            print(f"  🔍 [Collect] 找到 {len(all_link_elements)} 个 <a> 元素。")

        results = []
        seen_urls = set()

        for link in all_link_elements:
            href = await link.get_attribute("href") or ""
            
            # 从内部的 span 获取标题
            title_element = await link.query_selector("span.label-z77I")
            text = (await title_element.text_content() if title_element else "").strip()

            # 忽略无效条目
            if not text or not href or not href.startswith("/docs/"):
                continue

            # 构建绝对URL
            final_url = urljoin(self.base_url, href)
            
            # 过滤非火山引擎文档链接
            if not final_url.startswith(self.base_url):
                 continue

            # 去重
            if final_url in seen_urls:
                continue
            seen_urls.add(final_url)

            results.append({"url": final_url, "title": text})

        if debug:
            print(f"✅ [Collect] 收集完成，共找到 {len(results)} 个有效文档链接。")
        return results

    async def _crawl_single_doc(self, page, url: str, title: str):
        """如需抓取正文内容，可在 config.yaml 将 include_content 设为 true"""
        if not self.output_settings.get("include_content", False):
            return {"url": url, "title": title, "crawl_time": datetime.now().isoformat()}

        try:
            await page.goto(url, timeout=self.crawler_settings.get("wait_timeout", 20000), wait_until="domcontentloaded")
            await asyncio.sleep(0.3)

            content = ""
            # 火山引擎正文选择器
            selectors = [".markdown-body", ".article-wrap", "main", ".article-content"] 
            for sel in selectors:
                node = await page.query_selector(sel)
                if node:
                    txt = await node.text_content()
                    if txt and len(txt) > 50:
                        content = txt.strip()
                        break

            return {"url": url, "title": title, "content": content, "crawl_time": datetime.now().isoformat()}
        except Exception as e:
            return {"url": url, "title": title, "content": "", "error": str(e), "crawl_time": datetime.now().isoformat()}

    async def _save_product(self, key: str, info: dict, docs: list[dict]):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        links_file = self.output_dir / f"volcengine_{key}_links_{ts}.txt"

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

        if self.output_settings.get("include_content", False):
            json_file = self.output_dir / f"volcengine_{key}_data_{ts}.json"
            with open(json_file, "w", encoding="utf-8") as jf:
                json.dump({"product": info, "docs": docs, "timestamp": ts}, jf, ensure_ascii=False, indent=2)

        return links_file

    def _should_skip_crawl(self, key: str) -> bool:
        """
        根据文件时间戳和配置的间隔，判断是否应该跳过爬取。
        """
        interval_hours = self.output_settings.get("recrawl_interval_hours")
        if not interval_hours or not isinstance(interval_hours, (int, float)) or interval_hours <= 0:
            return False

        # 查找最新的文件
        search_pattern = str(self.output_dir / f"volcengine_{key}_links_*.txt")
        existing_files = glob.glob(search_pattern)
        if not existing_files:
            return False

        latest_file = max(existing_files, key=lambda p: Path(p).stat().st_mtime)
        file_mod_time = datetime.fromtimestamp(Path(latest_file).stat().st_mtime)
        
        # 检查文件是否在有效期间内
        if datetime.now() - file_mod_time < timedelta(hours=interval_hours):
            print(f"✅ 产品 '{key}' 在 {interval_hours} 小时内已有新文件，本次跳过爬取。")
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
                # 1. 打开页面
                print("1️⃣  加载页面...")
                await page.goto(info['url'], timeout=self.crawler_settings.get("wait_timeout", 20000), wait_until="domcontentloaded")
                await self._wait_dom(page, 500)
                print(f"✓ 页面加载完成 ({time.time() - t0:.1f}s)")

                # 2. 保存页面HTML用于调试（如果开启调试模式）
                if self.crawler_settings.get("debug_mode", False):
                    print("🔍 保存页面HTML用于调试...")
                    html_content = await page.content()
                    debug_file = self.output_dir / f"debug_{key}_page.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print(f"📄 页面HTML已保存: {debug_file.name}")

                # 3. 展开侧边栏
                print("2️⃣  深度展开菜单 (DFS)...")
                t1 = time.time()
                await self._expand_all_menus_dfs(page)
                print(f"✓ 菜单展开完成 ({time.time() - t1:.1f}s)")

                # 4. 收集链接
                print("3️⃣  收集文档链接...")
                docs_info = await self._collect_all_links_from_sidebar(page)
                print(f"✓ 共收集到 {len(docs_info)} 条记录")
                if not docs_info:
                    print("⚠️  未找到任何文档链接，跳过该产品")
                    return None

                # 5. 可选抓取正文
                final_docs = []
                if self.output_settings.get("include_content", False):
                    print("4️⃣  抓取正文内容 (这可能需要一些时间)...")
                    for idx, doc_info in enumerate(docs_info, 1):
                        if idx % 20 == 0:
                            print(f"   进度: {idx}/{len(docs_info)}")
                        # Pass url and title from the dict
                        doc_content = await self._crawl_single_doc(page, doc_info['url'], doc_info['title'])
                        final_docs.append(doc_content)
                        if idx < len(docs_info):
                            await asyncio.sleep(self.crawler_settings.get("crawl_delay", 0.5))
                else:
                    # The data is already in the right format, just need to add crawl_time
                    for doc_info in docs_info:
                        doc_info['crawl_time'] = datetime.now().isoformat()
                    final_docs = docs_info

                # 6. 保存
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


# 当直接执行该模块时，默认启动单产品爬取
if __name__ == "__main__":
    async def _self_test():
        crawler = VolcEngineLinkCollector()
        # 指定一个产品进行测试, 例如 eip
        await crawler.crawl_all_products(["eip"])

    asyncio.run(_self_test()) 