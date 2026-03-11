@echo off
setlocal

cd /d "%~dp0"

set "APP_FILE=.\streamlit_app.py"
set "VENV_PY=.venv\Scripts\python.exe"
set "PY_CMD="

if not exist "%APP_FILE%" (
  echo [ERRO] Arquivo %APP_FILE% nao encontrado.
  pause
  exit /b 1
)

if exist "%VENV_PY%" (
  set "PY_CMD=%VENV_PY%"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "PY_CMD=py -3"
  ) else (
    where python >nul 2>nul
    if not errorlevel 1 (
      set "PY_CMD=python"
    )
  )
)

if "%PY_CMD%"=="" (
  echo [ERRO] Python nao encontrado.
  echo - Crie o ambiente virtual com: py -3 -m venv .venv
  echo - Instale dependencias com: .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo [INFO] Usando interpretador: %PY_CMD%

%PY_CMD% -m streamlit --version >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Streamlit nao esta instalado neste interpretador.
  echo Execute: %PY_CMD% -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo [INFO] Iniciando Streamlit...
%PY_CMD% -m streamlit run "%APP_FILE%"

if errorlevel 1 (
  echo.
  echo [ERRO] O app encerrou com falha. Verifique as mensagens acima.
  pause
  exit /b 1
)

endlocal
