@echo off
chcp 65001 >nul
REM 电化学检测 GUI 启动脚本

echo ========================================
echo   电化学检测系统 GUI
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo 正在启动 GUI 应用程序...
echo.

REM 运行主程序
python electrochemical_gui.py

if errorlevel 1 (
    echo.
    echo 程序运行出错，请检查错误信息
    pause
)
