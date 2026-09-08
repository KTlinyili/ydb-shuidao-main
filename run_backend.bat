@echo off
chcp 65001 >nul
title 稻影知微 - 后端服务

echo ========================================
echo   稻影知微 RiceGuard - 后端服务
echo ========================================
echo.

cd /d "%~dp0"

REM 检查虚拟环境
if exist ".venv\Scripts\python.exe" (
    echo [1/2] 使用虚拟环境 .venv
    set PYTHON=.venv\Scripts\python.exe
) else (
    echo [1/2] 使用系统 Python
    set PYTHON=python
)

echo [2/2] 启动 FastAPI 服务 (端口 8000)
echo.
echo 接口文档: http://127.0.0.1:8000/docs
echo 健康检查: http://127.0.0.1:8000/health
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

%PYTHON% -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

pause
