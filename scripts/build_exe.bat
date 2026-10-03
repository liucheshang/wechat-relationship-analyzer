@echo off
chcp 65001 >nul
REM ============================================================
REM  把 analyze.py 打包成单文件 exe（双击运行，不需要装 Python）
REM  前提：本机有 Python 3.8+，且装过 PyInstaller
REM         pip install pyinstaller
REM ============================================================
cd /d "%~dp0"

echo [1/2] 检查 PyInstaller ...
python -m PyInstaller --version
if errorlevel 1 (
  echo.
  echo 没装 PyInstaller。请先执行：pip install pyinstaller
  pause
  exit /b 1
)

echo.
echo [2/2] 开始打包 ...
python -m PyInstaller --noconfirm --onefile --console ^
  --name "WeChatRelationAnalyzer" ^
  --add-data "%~dp0report_template.html;." ^
  --add-data "%~dp0echarts.min.js;." ^
  --distpath "%~dp0..\dist" ^
  --workpath "%~dp0..\_build" ^
  --specpath "%~dp0..\_build" ^
  "%~dp0analyze.py"

if errorlevel 1 (
  echo.
  echo 打包失败，请把上面的报错发给开发者。
  pause
  exit /b 1
)

echo.
echo 打包完成。exe 在：%~dp0..\dist\WeChatRelationAnalyzer.exe
echo （可以把它改名为中文，例如「聊天记录深度分析器.exe」，功能不受影响）
pause
