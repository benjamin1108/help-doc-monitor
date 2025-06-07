# 多云平台帮助文档爬虫

🚀 全功能多云平台帮助文档爬虫，支持批量爬取主流云厂商的网络产品帮助文档链接。采用深度优先搜索算法，智能展开所有菜单层级，确保文档爬取的完整性。

## ✨ 支持的云平台

- ✅ **阿里云** - 13个网络产品，包括负载均衡、VPC、NAT网关等
- ✅ **腾讯云** - 18个网络产品，覆盖云上网络和混合云网络
- ✅ **华为云** - 12个网络产品，包括ELB、VPC、专线等
- ✅ **火山引擎** - 13个网络产品，覆盖网络基础和性能优化

## 🎯 功能特性

- 🏗️ **模块化架构**: 按厂商拆分配置，支持独立维护和扩展
- 📁 **有序输出**: 每个厂商和产品的结果保存在独立目录中
- ⚡ **高效爬取**: 使用异步编程和深度优先搜索算法
- 🛡️ **智能识别**: 自动识别已展开菜单，避免重复点击
- 🎯 **灵活选择**: 支持按厂商、产品进行精确爬取
- 🔧 **统一接口**: 通过命令行统一管理所有厂商爬虫
- ⚙️ **配置分离**: 按厂商独立配置，便于维护和定制

## 📁 项目结构

```
.
├── config/                              # 配置文件目录
│   ├── aliyun.yaml                      # 阿里云配置
│   ├── tencentcloud.yaml               # 腾讯云配置
│   ├── huaweicloud.yaml                # 华为云配置
│   └── volcengine.yaml                 # 火山引擎配置
├── src/
│   ├── config_loader.py                # 配置加载器
│   └── help_crawler/
│       ├── __init__.py
│       ├── aliyun/
│       │   ├── __init__.py
│       │   └── aliyun_doc_crawler.py   # 阿里云爬虫
│       ├── tencentcloud/
│       │   ├── __init__.py
│       │   └── tencentcloud_doc_crawler.py  # 腾讯云爬虫
│       ├── huaweicloud/
│       │   ├── __init__.py
│       │   └── huaweicloud_doc_crawler.py   # 华为云爬虫
│       └── volcengine/
│           ├── __init__.py
│           └── volcengine_doc_crawler.py    # 火山引擎爬虫
├── config.yaml                         # 主配置文件（厂商映射）
├── run_crawler.py                      # 统一爬虫运行器
├── requirements.txt                    # 项目依赖
├── .gitignore                          # Git忽略文件
├── README.md                           # 项目说明
└── out/                                # 输出目录
    ├── aliyun/                         # 阿里云输出
    ├── tencentcloud/                   # 腾讯云输出
    ├── huaweicloud/                    # 华为云输出
    └── volcengine/                     # 火山引擎输出
```

## 🛠️ 安装和配置

### 环境要求

- Python 3.8+
- 网络连接

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/benjamin1108/help-doc-monitor.git
cd help-doc-monitor

# 安装Python依赖
pip install playwright pyyaml

# 安装Playwright浏览器
playwright install chromium
```

### 快速开始

```bash
# 查看所有支持的厂商
python run_crawler.py --list-vendors

# 查看指定厂商的产品列表
python run_crawler.py --vendor aliyun --list-products

# 爬取指定厂商的所有产品
python run_crawler.py --vendor aliyun

# 爬取指定厂商的指定产品
python run_crawler.py --vendor aliyun --product vpc
```

## 📋 使用方法

### 命令行接口

```bash
# 基本用法
python run_crawler.py [选项]

# 可用选项
--list-vendors                    # 列出所有厂商
--vendor VENDOR                   # 指定厂商 (aliyun/tencentcloud/huaweicloud/volcengine)
--product PRODUCT                 # 指定产品代码
--list-products                   # 列出指定厂商的所有产品

# 示例
python run_crawler.py --list-vendors
python run_crawler.py --vendor aliyun --list-products
python run_crawler.py --vendor aliyun
python run_crawler.py --vendor aliyun --product vpc
python run_crawler.py --vendor tencentcloud --product clb
```

### 编程接口

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_loader import config_loader
from help_crawler.aliyun.aliyun_doc_crawler import AliyunDocCrawler

# 加载配置
vendor_config = config_loader.get_vendor_config('aliyun')

# 创建爬虫实例
crawler = AliyunDocCrawler(vendor_config)

# 爬取指定产品
crawler.crawl_product('vpc')

# 爬取所有产品
crawler.crawl_all_products()
```

## ⚙️ 配置文件说明

### 主配置文件 (config.yaml)

```yaml
# 厂商配置文件映射
vendors:
  aliyun:
    name: "阿里云"
    config_file: "config/aliyun.yaml"
    description: "阿里云帮助文档爬虫"
  
  tencentcloud:
    name: "腾讯云"
    config_file: "config/tencentcloud.yaml"
    description: "腾讯云帮助文档爬虫"
  
  # ... 其他厂商配置

# 全局默认设置
default_settings:
  crawler_settings:
    headless: true
    wait_timeout: 20000
    click_delay: 0.2
    crawl_delay: 0.5
    debug_mode: false
  
  output_settings:
    base_dir: "out"
    include_content: false
```

### 厂商独立配置文件

每个厂商有独立的配置文件，例如 `config/aliyun.yaml`：

```yaml
# 阿里云帮助文档爬虫配置
base_url: "https://help.aliyun.com"

# 爬虫设置
crawler_settings:
  headless: true                  # 无头模式
  wait_timeout: 10000            # 页面加载超时(毫秒)
  click_delay: 0.2               # 点击间隔(秒)
  crawl_delay: 0.5               # 文档爬取间隔(秒)
  max_depth: 10                  # 最大展开深度
  debug_mode: false              # 调试模式

# 输出设置
output_settings:
  base_dir: "out"                # 输出目录
  include_content: false         # 是否包含文档内容

# 产品配置
products:
  vpc:
    name: "专有网络VPC"
    url: "https://help.aliyun.com/zh/vpc/"
    description: "专有网络VPC帮助文档"
  
  # ... 更多产品
```

### 配置参数详解

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `headless` | boolean | 是否无头模式运行 | true |
| `wait_timeout` | int | 页面加载超时时间(毫秒) | 20000 |
| `click_delay` | float | 点击间隔时间(秒) | 0.2 |
| `crawl_delay` | float | 文档爬取间隔(秒) | 0.5 |
| `max_depth` | int | 最大菜单展开深度 | 10 |
| `debug_mode` | boolean | 是否启用调试输出 | false |
| `include_content` | boolean | 是否爬取文档内容 | false |

## 📊 产品覆盖详情

### 阿里云 (13个网络产品)

| 类别 | 产品 | 产品代码 |
|------|------|----------|
| 负载均衡 | 应用型负载均衡ALB | `alb` |
| | 网络型负载均衡NLB | `nlb` |
| | 传统型负载均衡CLB | `clb` |
| 网络基础 | 专有网络VPC | `vpc` |
| | 弹性公网IP | `eip` |
| | NAT网关 | `nat` |
| 网络连接 | VPN网关 | `vpn` |
| | 高速通道 | `expressconnect` |
| | 私网连接 | `privatelink` |
| 跨地域网络 | 云企业网CEN | `cen` |
| | 转发路由器TR | `tr` |
| 性能优化 | 全球加速GA | `ga` |
| | 共享带宽 | `cbwp` |

### 腾讯云 (18个网络产品)

| 类别 | 产品 | 产品代码 |
|------|------|----------|
| 云上网络-负载均衡 | 负载均衡 | `clb` |
| | 网关负载均衡 | `gwlb` |
| 云上网络-基础网络 | 私有网络 | `vpc` |
| | 弹性网卡 | `eni` |
| | NAT网关 | `nat` |
| | 网络流日志 | `fl` |
| 云上网络-公网产品 | 共享带宽包 | `bwp` |
| | 共享流量包 | `sts` |
| | 弹性公网IPv6 | `eipv6` |
| | 弹性公网IP | `eip` |
| 云上网络-性能优化 | 智能高性能网络 | `hsn` |
| | 私有连接 | `privatelink` |
| | Anycast公网加速 | `anycast` |
| 混合云网络-连接 | 专线接入 | `dc` |
| | 云联网 | `ccn` |
| | 对等连接 | `pc` |
| | VPN连接 | `vpn` |
| 混合云网络-加速 | 全球应用加速 | `gaap` |

### 华为云 (12个网络产品)

| 类别 | 产品 | 产品代码 |
|------|------|----------|
| 负载均衡 | 弹性负载均衡ELB | `elb` |
| 网络基础 | 虚拟私有云VPC | `vpc` |
| | 弹性公网IP | `eip` |
| | NAT网关 | `nat` |
| 网络连接 | VPN网关 | `vpn` |
| | 云专线 | `dc` |
| | 终端节点 | `vpcep` |
| 跨地域网络 | 云连接CC | `cc` |
| | 企业路由器 | `er` |
| 性能优化 | 全球加速 | `ga` |
| | 共享带宽 | `cbw` |

### 火山引擎 (13个网络产品)

| 类别 | 产品 | 产品代码 |
|------|------|----------|
| 负载均衡 | 负载均衡CLB | `clb` |
| 网络基础 | 私有网络VPC | `vpc` |
| | 公网IP | `eip` |
| | NAT网关 | `nat` |
| 网络连接 | VPN连接 | `vpn` |
| | 专线连接 | `dc` |
| | 私网连接 | `privatelink` |
| 跨地域网络 | 云企业网CEN | `cen` |
| | 转发路由器TR | `tr` |
| 性能优化 | 全球加速GA | `ga` |
| | 共享带宽包 | `bwp` |

## 📤 输出文件说明

### 输出目录结构

```
out/
├── aliyun/
│   ├── aliyun_vpc_links_20241215_143128.txt     # VPC产品链接列表
│   └── aliyun_eip_links_20241215_144052.txt     # EIP产品链接列表
├── tencentcloud/
│   ├── tencent_clb_links_20241215_143052.txt    # CLB产品链接列表
│   └── tencent_vpc_links_20241215_144123.txt    # VPC产品链接列表
├── huaweicloud/
│   └── huawei_elb_links_20241215_145032.txt     # ELB产品链接列表
└── volcengine/
    └── volcengine_clb_links_20241215_150112.txt # CLB产品链接列表
```

### 输出文件格式

```
专有网络VPC 帮助文档链接
==================================================
产品: 专有网络VPC
描述: 专有网络VPC帮助文档
起始URL: https://help.aliyun.com/zh/vpc/
文档数量: 156
生成时间: 20241215_143128
==================================================

  1. VPC概述
     https://help.aliyun.com/zh/vpc/product-overview/

  2. 什么是专有网络
     https://help.aliyun.com/zh/vpc/product-overview/what-is-a-vpc

  3. 专有网络使用限制
     https://help.aliyun.com/zh/vpc/product-overview/limits

  ... (更多链接)
```

## 🔧 高级配置

### 添加新产品

1. **在对应厂商的配置文件中添加产品配置**

```yaml
# 例如在 config/aliyun.yaml 中添加新产品
products:
  new_product:
    name: "新产品名称"
    url: "https://help.aliyun.com/zh/new-product/"
    description: "新产品帮助文档"
```

2. **运行爬虫验证**

```bash
python run_crawler.py --vendor aliyun --product new_product
```

### 调试模式

启用调试模式可以查看详细的爬取过程：

```yaml
crawler_settings:
  debug_mode: true
```

调试输出示例：
```
🔍 [DFS] 开始展开所有菜单...
  ▶️ [DFS] 发现 5 个新的可展开菜单，正在处理...
    🖱️ [DFS] 点击展开: 产品概述
    🖱️ [DFS] 点击展开: 快速入门
✅ [DFS] 没有更多可展开的菜单，展开完成。
🔗 [Collect] 开始收集所有链接...
✅ [Collect] 收集完成，共找到 156 个有效文档链接。
```

### 性能优化

1. **调整并发和延迟参数**
```yaml
crawler_settings:
  click_delay: 0.1      # 减少点击延迟
  crawl_delay: 0.3      # 减少爬取延迟
  wait_timeout: 15000   # 调整超时时间
```

2. **禁用图片和CSS加载**（在代码中实现）
3. **使用无头模式**（默认开启）

## 🐛 故障排除

### 常见问题

1. **浏览器启动失败**
   ```bash
   playwright install chromium
   ```

2. **模块导入错误**
   ```bash
   # 确保所有__init__.py文件存在
   find src/ -name "__init__.py"
   ```

3. **配置文件解析错误**
   - 检查YAML语法（缩进、引号）
   - 使用在线YAML验证器

4. **网络超时**
   - 增加 `wait_timeout` 值
   - 检查网络连接稳定性

5. **华为云不显示在厂商列表**
   - 确保 `src/help_crawler/__init__.py` 文件存在
   - 检查模块导入路径

### 错误代码说明

| 错误类型 | 可能原因 | 解决方案 |
|----------|----------|----------|
| `ModuleNotFoundError` | 缺少__init__.py | 添加空的__init__.py文件 |
| `yaml.YAMLError` | 配置文件格式错误 | 检查YAML语法 |
| `TimeoutError` | 网络或页面加载超时 | 增加wait_timeout值 |
| `ElementNotFound` | 页面结构变化 | 更新CSS选择器 |

## 🚀 扩展开发

### 添加新厂商

1. **创建厂商目录和爬虫类**
```bash
mkdir src/help_crawler/new_vendor/
touch src/help_crawler/new_vendor/__init__.py
```

2. **实现爬虫类**
```python
# src/help_crawler/new_vendor/new_vendor_doc_crawler.py
class NewVendorDocCrawler:
    def __init__(self, config=None, config_file="config.yaml"):
        # 初始化逻辑
        pass
    
    async def crawl_product(self, product_key):
        # 爬取逻辑
        pass
```

3. **添加配置文件**
```yaml
# config/new_vendor.yaml
base_url: "https://docs.newvendor.com"
# ... 其他配置
```

4. **更新主配置**
```yaml
# config.yaml
vendors:
  new_vendor:
    name: "新厂商"
    config_file: "config/new_vendor.yaml"
    description: "新厂商文档爬虫"
```

### 自定义选择器

不同厂商的页面结构不同，需要适配相应的CSS选择器：

```python
# 示例：适配新的侧边栏结构
sidebar_selector = ".new-sidebar-container"
expandable_selector = ".new-expandable-item:not(.expanded)"
link_selector = "a.new-doc-link"
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📞 联系方式

- 项目地址：[https://github.com/benjamin1108/help-doc-monitor](https://github.com/benjamin1108/help-doc-monitor)
- 问题反馈：[Issues](https://github.com/benjamin1108/help-doc-monitor/issues)

---

⭐ 如果这个项目对您有帮助，请给个 Star 支持一下！ 