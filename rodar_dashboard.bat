@echo off
echo Iniciando Dashboard Demografico...
echo.

cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado. Instale o Python 3.10+ e tente novamente.
    pause
    exit /b
)

pip install -r requirements.txt --quiet

start http://localhost:8508
streamlit run app.py --server.port 8508
