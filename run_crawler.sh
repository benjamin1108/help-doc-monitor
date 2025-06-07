#!/bin/bash
# 多云平台帮助文档爬虫Unix/Linux运行脚本

echo "======================================================================"
echo "🚀 多云平台帮助文档爬虫运行器 (Unix/Linux)"
echo "======================================================================"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ 错误：未找到Python，请确保Python 3.7+已安装"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# 检查Python版本
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+')
if [[ $(echo "$PYTHON_VERSION >= 3.7" | bc -l) -eq 0 ]]; then
    echo "❌ 错误：需要Python 3.7或更高版本，当前版本：$PYTHON_VERSION"
    exit 1
fi

# 检查是否在正确的目录
if [ ! -f "run_crawler.py" ]; then
    echo "❌ 错误：未找到run_crawler.py，请确保在项目根目录下运行此脚本"
    exit 1
fi

# 检查依赖是否安装
if [ ! -d "venv" ] && [ ! -f ".venv_created" ]; then
    echo "⚠️  建议创建虚拟环境，是否现在创建？(y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "📦 创建虚拟环境..."
        $PYTHON_CMD -m venv venv
        source venv/bin/activate
        echo "📥 安装依赖..."
        pip install -r requirements.txt
        touch .venv_created
        echo "✅ 虚拟环境创建完成"
    fi
fi

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "🔧 激活虚拟环境..."
    source venv/bin/activate
fi

# 运行Python脚本
if [ $# -eq 0 ]; then
    # 无参数时运行交互式模式
    $PYTHON_CMD run_crawler.py
else
    # 有参数时传递所有参数
    $PYTHON_CMD run_crawler.py "$@"
fi

# 记录退出状态
exit_code=$?

# 如果在虚拟环境中，deactivate
if [[ "$VIRTUAL_ENV" != "" ]]; then
    deactivate
fi

exit $exit_code 