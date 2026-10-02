@echo off
chcp 65001 >nul
echo ============================================
echo   微信关系分析器 · 一键打包脚本
echo ============================================
echo.
echo [1/3] 安装打包工具...
pip install pyinstaller gradio -q
echo.
echo [2/3] 开始打包（约 2-3 分钟）...
pyinstaller --noconfirm --clean --onefile ^
  --name "wx-relation-analyzer" ^
  --add-data "analyzer;analyzer" ^
  --hidden-import analyzer.rules ^
  --hidden-import analyzer.io_loader ^
  --collect-submodules analyzer ^
  app.py
echo.
echo [3/3] 完成！
echo 生成的文件在 dist\wx-relation-analyzer.exe
echo 双击就能用，会自动打开浏览器
echo.
pause
