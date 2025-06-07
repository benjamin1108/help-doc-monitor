# 多云平台帮助文档爬虫

通用的云平台帮助文档爬虫，支持批量爬取多个云平台产品的帮助文档链接。

## 支持的云平台

- ✅ **阿里云** - 阿里云帮助文档
- ✅ **腾讯云** - 腾讯云产品文档
- 🚧 **华为云** - 开发中
- 🚧 **火山引擎** - 开发中

## 功能特性

- 🔧 **通用性**: 通过YAML配置文件支持多个阿里云产品
- 📁 **有序输出**: 每个产品的结果保存在独立目录中
- ⚡ **高效爬取**: 使用异步编程和深度优先算法
- 🛡️ **智能识别**: 自动识别已展开菜单，避免重复点击
- 📊 **详细报告**: 生成爬取总结报告
- 🎯 **灵活选择**: 可指定爬取特定产品或全部产品

## 文件结构

```
.
├── src/
│   └── help_crawler/
│       ├── aliyun/
│       │   └── aliyun_doc_crawler.py     # 阿里云爬虫
│       ├── tencentcloud/
│       │   └── tencentcloud_doc_crawler.py  # 腾讯云爬虫
│       ├── huaweicloud/                  # 华为云爬虫（开发中）
│       └── volcengine/                   # 火山引擎爬虫（开发中）
├── config.yaml                          # 多云平台配置文件
├── run_aliyun_crawler.py                # 阿里云爬虫运行脚本
├── run_tencentcloud_crawler.py          # 腾讯云爬虫运行脚本
├── requirements.txt                     # 依赖库
├── README.md                           # 说明文档
└── out/                                # 输出目录
    ├── aliyun/                         # 阿里云输出目录
    │   ├── aliyun_vpc_links_20241201_143128.txt
    │   ├── aliyun_vpc_data_20241201_143128.json
    │   └── aliyun_crawl_summary_20241201_143300.txt
    ├── tencentcloud/                   # 腾讯云输出目录
    │   ├── tencentcloud_clb_links_20241201_143052.txt
    │   ├── tencentcloud_clb_data_20241201_143052.json
    │   └── tencentcloud_crawl_summary_20241201_143300.txt
    └── ...                             # 其他厂商目录
```

## 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

## 配置文件说明

配置文件 `config.yaml` 包含阿里云和腾讯云两个平台的配置：

### 阿里云配置 (顶级配置)
```yaml
base_url: "https://help.aliyun.com"
crawler_settings:
  headless: true
  wait_timeout: 10000
  click_delay: 0.3
  # ... 其他设置
products:
  vpc:
    name: "专有网络"
    url: "https://help.aliyun.com/zh/vpc/"
    description: "专有网络帮助文档"
```

### 腾讯云配置 (tencentcloud节点下)
```yaml
tencentcloud:
  base_url: "https://cloud.tencent.com"
  crawler_settings:
    headless: true
    wait_timeout: 15000  # 腾讯云加载较慢，需要更长时间
    click_delay: 0.5     # 腾讯云需要更长的等待时间
    # ... 其他设置
  products:
    clb:
      name: "负载均衡"
      url: "https://cloud.tencent.com/document/product/214"
      description: "腾讯云负载均衡CLB帮助文档"
```

### 配置参数说明
- `headless`: 是否无头模式运行（true/false）
- `wait_timeout`: 页面加载超时时间（毫秒）
- `click_delay`: 点击间隔时间（秒）
- `crawl_delay`: 文档爬取间隔（秒）
- `max_depth`: 最大展开深度
- `debug_mode`: 是否启用详细调试输出（true/false）

### 输出设置
- `base_dir`: 输出目录名
- `include_content`: 是否包含文档内容（false只保存链接）

### 产品配置
每个产品包含：
- `name`: 产品中文名称
- `url`: 帮助文档起始页URL
- `description`: 产品描述

## 调试输出说明

启用debug_mode后，爬虫会显示详细的菜单展开过程：

```
🔍 开始菜单展开调试模式...
============================================================
✅ 找到菜单容器，开始深度优先展开...
📁 [深度 0] 发现 7 个子元素
├─ [ 1] 产品概述 🔗
│   └─ 🔽可展开 🔗有链接
│   🔄 尝试展开...
│     🔍 元素状态: class='Menu--level1--xxx', aria-expanded='false'
│     🎯 点击图标: [class*="arrow"]
│     ✅ 点击成功: 图标([class*="arrow"])
│     📊 点击后aria-expanded: true
│   ✅ 展开成功，递归处理子元素
  📁 [深度 1] 发现 2 个子元素
  ├─ [ 1] 什么是应用型负载均衡ALB 🔗
  │   └─ 📄叶节点 🔗有链接
  │   🔗 链接: /zh/slb/application-load-balancer/product-overview/what-is-alb
```

符号说明：
- 📁 有子元素的节点  
- 📄 叶子节点
- 🔽 可展开  
- 📂 已展开
- 🔗 有链接
- ✅ 操作成功
- ❌ 操作失败

## 使用方法

### 阿里云爬虫

#### 方法1: 直接运行主程序

```bash
python src/help_crawler/aliyun/aliyun_doc_crawler.py
```

#### 方法2: 使用示例程序

```bash
python example_usage.py
```

#### 方法3: 调试模式 (推荐用于问题排查)

```bash
python debug_crawler.py
```

### 腾讯云爬虫

#### 运行腾讯云爬虫

```bash
python run_tencentcloud_crawler.py
```

#### 腾讯云爬虫特色功能

- **深层级菜单支持**：支持5层以上的深度菜单结构
- **目录节点输出**：除了文档链接，还输出目录节点信息
- **智能展开等待**：根据菜单深度自动调整等待时间
- **精确元素识别**：适配腾讯云特有的DOM结构

#### 输出格式说明

多云平台爬虫的输出文件包含两种类型的项目：

1. **实际文档链接**：可直接访问的文档页面
2. **目录节点**：标记为 `[目录]` 的菜单节点，用于构建完整的文档结构

#### 输出目录结构

每个云厂商有独立的输出目录：
- 阿里云：`out/aliyun/`
- 腾讯云：`out/tencentcloud/`
- 华为云：`out/huaweicloud/`（开发中）
- 火山引擎：`out/volcengine/`（开发中）

#### 在代码中使用腾讯云爬虫

```python
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from help_crawler.tencentcloud.tencentcloud_doc_crawler import TencentCloudDocCrawler

async def main():
    crawler = TencentCloudDocCrawler()
    
    # 爬取指定产品
    selected_products = ['clb']  # 只爬取负载均衡
    results = await crawler.crawl_all_products(selected_products)
    
    # 或爬取所有产品
    # results = await crawler.crawl_all_products()

if __name__ == "__main__":
    asyncio.run(main())
```

调试模式特性：
- 🐛 详细的菜单展开过程输出
- 🌳 树状显示文档层级结构  
- 🎯 可选择特定产品进行调试
- 👁️ 可视化浏览器操作过程
- 📊 实时状态检查和错误信息

### 方法4: 在代码中使用

```python
import asyncio
from aliyun_doc_crawler import AliyunDocCrawler

async def main():
    crawler = AliyunDocCrawler()
    
    # 爬取指定产品
    selected_products = ['alb', 'nlb', 'ecs']
    results = await crawler.crawl_all_products(selected_products)
    
    # 或爬取所有产品
    # results = await crawler.crawl_all_products()

if __name__ == "__main__":
    asyncio.run(main())
```

## 输出文件

### out目录包含:

#### 阿里云输出文件
- `aliyun_{产品}_links_{时间戳}.txt` - 阿里云产品文档链接列表
- `aliyun_{产品}_data_{时间戳}.json` - 详细文档数据（如果启用内容爬取）
- `aliyun_crawl_summary_{时间戳}.txt` - 阿里云爬取总结报告

#### 腾讯云输出文件
- `tencentcloud_{产品}_links_{时间戳}.txt` - 腾讯云产品文档链接列表
- `tencentcloud_{产品}_data_{时间戳}.json` - 详细文档数据（如果启用内容爬取）
- `tencentcloud_crawl_summary_{时间戳}.txt` - 腾讯云爬取总结报告

## 输出示例

```
out/
├── aliyun/
│   ├── aliyun_vpc_links_20241201_143128.txt
│   ├── aliyun_vpc_data_20241201_143128.json
│   └── aliyun_crawl_summary_20241201_143300.txt
├── tencentcloud/
│   ├── tencentcloud_clb_links_20241201_143052.txt
│   ├── tencentcloud_clb_data_20241201_143052.json
│   └── tencentcloud_crawl_summary_20241201_143300.txt
└── ...
```

## 添加新产品

### 添加阿里云产品

在 `config.yaml` 的 `products` 部分添加新产品：

```yaml
products:
  新产品代码:
    name: "新产品名称"
    url: "https://help.aliyun.com/zh/新产品路径"
    description: "新产品描述"
```

### 添加腾讯云产品

在 `config.yaml` 的 `tencentcloud.products` 部分添加新产品：

```yaml
tencentcloud:
  products:
    新产品代码:
      name: "新产品名称"
      url: "https://cloud.tencent.com/document/product/产品ID"
      description: "腾讯云新产品描述"
```

## 注意事项

1. 首次运行需要安装Playwright浏览器：`playwright install chromium`
2. 建议设置适当的延迟时间，避免请求过于频繁
3. 大量产品爬取可能需要较长时间，建议分批执行
4. 网络异常时爬虫会自动跳过失败的产品继续执行

## 故障排除

### 常见问题

1. **浏览器启动失败**
   ```bash
   playwright install chromium
   ```

2. **YAML配置错误**
   - 检查缩进是否正确（使用空格，不要使用Tab）
   - 确保字符串包含在引号内

3. **网络超时**
   - 增加 `wait_timeout` 值
   - 检查网络连接

4. **找不到菜单容器**
   - 可能是页面结构发生变化
   - 需要更新选择器

5. **"The object has been collected" 错误**
   - 这是DOM元素引用失效的问题
   - 爬虫已内置重试和刷新机制
   - 如果频繁出现，可以增加 `click_delay` 值

## 许可证

MIT License 