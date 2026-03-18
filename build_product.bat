@echo off
chcp 65001 >nul
title 打包 OpenClaw 安装助手 (Windows) - 产品级
echo ========================================
echo   OpenClaw 安装助手 - Windows 产品打包
echo ========================================
echo.

cd /d "%~dp0"
if errorlevel 1 (
    echo [错误] 无法进入脚本所在目录
    goto :end
)

REM 检查 Python（优先 python，其次 py）
set PYCMD=python
python --version >nul 2>&1 || set PYCMD=py
%PYCMD% -c "import sys; print(sys.executable)" 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python
    echo 请先安装 Python 3.8+ 并勾选「Add Python to PATH」
    goto :end
)

echo [1/5] 检查打包依赖...
%PYCMD% -m pip install -q pyinstaller
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败
    goto :end
)

echo [2/5] 清理旧构建...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo [3/5] 运行测试...
%PYCMD% -c "from skills_manager import SkillManager; m = SkillManager(); s = m.get_skills(); print(f'测试通过: 加载了 {len(s)} 个技能')"
if errorlevel 1 (
    echo [警告] 技能管理器测试失败，继续打包...
)

echo [4/5] 开始打包（产品级配置）...
%PYCMD% -m PyInstaller --noconfirm "OpenClaw安装助手.spec"
if errorlevel 1 (
    echo [错误] 打包失败
    goto :end
)

echo [5/5] 创建产品文档...
(
echo OpenClaw 安装助手
echo ===================
echo.
echo 使用说明：
echo 1. 双击运行 "OpenClaw安装助手.exe"
echo 2. 首次使用需要安装 OpenClaw
echo 3. 技能管理功能可直接使用，无需额外配置
echo.
echo 系统要求：
echo - Windows 10/11
echo - 已安装 OpenClaw（用于安装/卸载技能）
echo.
echo 注意事项：
echo - 本程序内置常用技能数据，无需联网即可查看
echo - 安装/卸载技能需要系统中已安装 OpenClaw
echo - 如 OpenClaw 不在 PATH 中，请使用 npx openclaw
echo.
echo 版本：v2.0
echo 构建时间：%date% %time%
) > "dist\README.txt"

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 输出目录: dist\
echo 可执行文件: dist\OpenClaw安装助手.exe
echo 产品文档: dist\README.txt
echo.
echo 发布前检查清单：
echo [ ] 在干净环境测试 exe 能否正常运行
echo [ ] 检查技能列表是否正确显示
echo [ ] 测试安装/卸载功能（需要 OpenClaw）
echo [ ] 检查翻译功能是否正常
echo.

:end
echo.
pause
