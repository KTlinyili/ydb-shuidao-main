@echo off
chcp 65001 >nul
title 稻影知微 - 一键启动（前后端）

echo ========================================
echo   稻影知微 RiceGuard - 一键启动
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 启动后端服务 (端口 8000)...
start "稻影知微 - 后端" cmd /k run_backend.bat

timeout /t 3 /nobreak >nul

echo [2/2] 启动前端服务 (端口 5173)...
start "稻影知微 - 前端" cmd /k run_frontend.bat

echo.
echo ========================================
echo   启动完成！
echo   前端: http://localhost:5173
echo   后端: http://127.0.0.1:8000/docs
echo ========================================
echo.
pause
