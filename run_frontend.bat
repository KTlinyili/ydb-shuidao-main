@echo off
chcp 65001 >nul
title 稻影知微 - 前端开发服务

echo ========================================
echo   稻影知微 RiceGuard - 前端开发服务
echo ========================================
echo.

cd /d "%~dp0web"

echo [1/1] 启动 Vite 开发服务 (端口 5173)
echo.
echo 访问地址: http://localhost:5173
echo 后端代理: /api -^> http://127.0.0.1:8000
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

call npm run dev

pause
