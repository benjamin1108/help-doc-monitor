@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

rem --- 配置 ---
set "ENV_NAME=help-doc-monitor"
set "VENV_DIR=venv"
set "PYTHON_CMD=python"

rem --- 脚本标题 ---
echo ======================================================================
echo 🚀 多云平台帮助文档爬虫运行器 (Windows)
echo ======================================================================

rem --- 检查项目根目录 ---
if not exist "run_crawler.py" (
    echo ❌ 错误：未找到run_crawler.py，请确保在项目根目录下运行此脚本
    pause
    exit /b 1
)

rem --- 环境设置 ---
set "USE_CONDA=false"
where conda >nul 2>nul
if %errorlevel% == 0 (
    set "USE_CONDA=true"
)

if "%USE_CONDA%"=="true" (
    call :setup_conda_env
) else (
    call :setup_venv
)

if %errorlevel% neq 0 (
    echo ❌ 环境设置失败，请检查错误信息。
    pause
    exit /b 1
)

rem --- 运行主程序 ---
echo ----------------------------------------------------------------------
echo 🚀 环境准备就绪，开始运行主程序...
echo ----------------------------------------------------------------------

if "%USE_CONDA%"=="true" (
    rem For interactive mode, we need to activate the environment. `conda run` may not handle TTY correctly.
    if "%~1"=="" (
        echo 🔧 激活conda环境以进入交互式模式...
        call conda activate %ENV_NAME%
        call python run_crawler.py %*
        call conda deactivate
    ) else (
        call conda run -n %ENV_NAME% python run_crawler.py %*
    )
) else (
    call .\%VENV_DIR%\Scripts\activate.bat
    call python run_crawler.py %*
    call .\%VENV_DIR%\Scripts\deactivate.bat
)

exit /b %errorlevel%


rem ======================================================================
rem 子程序
rem ======================================================================

:setup_conda_env
    echo 📦 使用conda管理环境...
    
    rem 检查conda环境是否存在
    call conda env list | findstr /B /C:"%ENV_NAME% " >nul
    if %errorlevel% neq 0 (
        echo ⚠️ conda环境 '%ENV_NAME%' 不存在，正在创建...
        call conda create -n %ENV_NAME% python=3.12 -y
        if %errorlevel% neq 0 (
            echo ❌ conda环境创建失败
            exit /b 1
        )
        echo ✅ conda环境创建完成
    ) else (
        echo ✅ 检测到现有conda环境: %ENV_NAME%
    )

    echo 📥 在conda环境中安装/更新依赖...
    call conda run -n %ENV_NAME% pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        exit /b 1
    )
    echo ✅ 依赖安装完成
    exit /b 0

:setup_venv
    echo 📦 使用Python虚拟环境...
    
    rem 检查Python
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo ❌ 错误：未找到Python，请确保Python 3.7+已安装并添加到PATH
        exit /b 1
    )

    rem 检查Python版本
    for /f "tokens=1,2 delims=. " %%a in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do (
        set "MAJOR_VERSION=%%a"
        set "MINOR_VERSION=%%b"
    )
    
    if !MAJOR_VERSION! lss 3 (
        echo ❌ 错误：需要Python 3.7或更高版本
        exit /b 1
    )
    if !MAJOR_VERSION! equ 3 (
        if !MINOR_VERSION! lss 7 (
            echo ❌ 错误：需要Python 3.7或更高版本
            exit /b 1
        )
    )

    rem 创建虚拟环境
    if not exist "%VENV_DIR%\" (
        echo ⚠️ 虚拟环境 '%VENV_DIR%' 不存在，正在创建...
        call %PYTHON_CMD% -m venv %VENV_DIR%
        if %errorlevel% neq 0 (
            echo ❌ 虚拟环境创建失败
            exit /b 1
        )
        echo ✅ 虚拟环境创建完成
    ) else (
        echo ✅ 检测到现有虚拟环境: %VENV_DIR%
    )
    
    echo 📥 安装/更新依赖...
    call .\%VENV_DIR%\Scripts\activate.bat
    call pip install -r requirements.txt
    call .\%VENV_DIR%\Scripts\deactivate.bat
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        exit /b 1
    )
    echo ✅ 依赖安装完成
    exit /b 0 