#!/bin/bash
# 多云平台帮助文档爬虫Unix/Linux运行脚本

# 函数：打印带有颜色的消息
print_message() {
    color_code=$1
    shift
    message=$@
    echo -e "\e[${color_code}m${message}\e[0m"
}

print_message "1;34" "======================================================================"
print_message "1;34" "🚀 多云平台帮助文档爬虫运行器 (Unix/Linux)"
print_message "1;34" "======================================================================"

# --- 环境配置 ---
ENV_NAME="help-doc-monitor"
VENV_DIR="venv"
PYTHON_CMD="python3"
USE_CONDA=false

# --- Conda 环境检测与设置 ---
setup_conda_env() {
    print_message "32" "📦 使用conda管理环境..."
    
    # 检查conda环境是否存在
    if ! conda env list | grep -q "^${ENV_NAME}\s"; then
        print_message "33" " conda环境 '${ENV_NAME}' 不存在，正在创建..."
        conda create -n "$ENV_NAME" python=3.12 -y
        if [ $? -ne 0 ]; then
            print_message "1;31" "❌ conda环境创建失败"
            exit 1
        fi
        print_message "32" "✅ conda环境创建完成"
    else
        print_message "32" "✅ 检测到现有conda环境: $ENV_NAME"
    fi

    print_message "32" "📥 在conda环境中安装/更新依赖..."
    conda run -n "$ENV_NAME" pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        print_message "1;31" "❌ 依赖安装失败"
        exit 1
    fi
    print_message "32" "✅ 依赖安装完成"
}

# --- Python 虚拟环境检测与设置 ---
setup_venv() {
    print_message "32" "📦 使用Python虚拟环境..."
    
    # 检查Python版本
    if ! command -v $PYTHON_CMD &> /dev/null; then
        PYTHON_CMD="python"
        if ! command -v $PYTHON_CMD &> /dev/null; then
            print_message "1;31" "❌ 错误：未找到Python，请确保Python 3.7+已安装"
            exit 1
        fi
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
    if [ -z "$PYTHON_VERSION" ]; then
        print_message "1;31" "❌ 无法获取Python版本，请检查您的Python安装"
        exit 1
    fi

    MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR_VERSION" -lt 3 ] || { [ "$MAJOR_VERSION" -eq 3 ] && [ "$MINOR_VERSION" -lt 7 ]; }; then
        print_message "1;31" "❌ 错误：需要Python 3.7或更高版本，当前版本：$PYTHON_VERSION"
        exit 1
    fi

    # 创建虚拟环境
    if [ ! -d "$VENV_DIR" ]; then
        print_message "33" " 虚拟环境 '${VENV_DIR}' 不存在，正在创建..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            print_message "1;31" "❌ 虚拟环境创建失败"
            exit 1
        fi
        print_message "32" "✅ 虚拟环境创建完成"
    else
        print_message "32" "✅ 检测到现有虚拟环境: $VENV_DIR"
    fi
    
    print_message "32" "📥 安装/更新依赖..."
    # 激活并安装
    source "${VENV_DIR}/bin/activate"
    pip install -r requirements.txt
    deactivate
    if [ $? -ne 0 ]; then
        print_message "1;31" "❌ 依赖安装失败"
        exit 1
    fi
    print_message "32" "✅ 依赖安装完成"
}

# --- 主逻辑 ---
# 检查是否在正确的目录
if [ ! -f "run_crawler.py" ]; then
    print_message "1;31" "❌ 错误：未找到run_crawler.py，请确保在项目根目录下运行此脚本"
    exit 1
fi

# 决定使用Conda还是Venv
if command -v conda &> /dev/null; then
    USE_CONDA=true
    setup_conda_env
else
    setup_venv
fi

print_message "1;34" "----------------------------------------------------------------------"
print_message "1;32" "🚀 环境准备就绪，开始运行主程序..."
print_message "1;34" "----------------------------------------------------------------------"

# 运行Python脚本
if [ "$USE_CONDA" = true ]; then
    # 对于交互式模式（无参数），必须激活环境，因为 `conda run` 在某些系统上无法正确处理TTY
    if [ $# -eq 0 ]; then
        print_message "32" "🔧 激活conda环境以进入交互式模式..."
        # sourcing conda.sh is crucial for `conda activate` to work in scripts
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate "$ENV_NAME"
        python run_crawler.py
        conda deactivate
    else
        # 对于非交互式模式（有参数），可以直接使用 conda run
        conda run -n "$ENV_NAME" python run_crawler.py "$@"
    fi
else
    # venv 激活对于两种模式都适用
    source "${VENV_DIR}/bin/activate"
    python run_crawler.py "$@"
    deactivate
fi

exit $? 