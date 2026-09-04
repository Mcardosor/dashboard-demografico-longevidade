@echo off
REM Sobe o painel localmente, sem Docker.
REM
REM Desde a atualizacao (pandas 2.2.3 / pyarrow 25) isto funciona em Python
REM 3.13. Antes o lock so instalava em 3.11, e o Docker era obrigatorio.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.lock.txt
)

echo.
echo Painel em http://localhost:8508/cenarios/demografico-longevidade
echo.
start http://localhost:8508/cenarios/demografico-longevidade
.venv\Scripts\python.exe -m streamlit run app.py --server.port 8508
