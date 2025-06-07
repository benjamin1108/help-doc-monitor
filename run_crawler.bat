@echo off
chcp 65001 > nul
REM 多云平台帮助文档爬虫Windows运行脚本

echo ======================================================================
echo 🚀 多云平台帮助文档爬虫运行器 (Windows)
echo ======================================================================

REM 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python，请确保Python已安装并添加到PATH环境变量
    pause
    exit /b 1
)

REM 检查是否在正确的目录
if not exist "run_crawler.py" (
    echo ❌ 错误：未找到run_crawler.py，请确保在项目根目录下运行此脚本
    pause
    exit /b 1
)

REM 如果有参数，直接传递给Python脚本
if not "%~1"=="" (
    python run_crawler.py %*
) else (
    REM 无参数时运行交互式模式
    python run_crawler.py
)

REM 如果需要暂停以查看结果
if errorlevel 1 (
    echo.
    echo 按任意键退出...
    pause > nul
) 