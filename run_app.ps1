$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$activateScript = Join-Path $projectRoot '.venv\Scripts\Activate.ps1'
if (-not (Test-Path $activateScript)) {
    Write-Error "Ambiente virtual não encontrado em .venv\Scripts\Activate.ps1"
}

& $activateScript
python -m streamlit run .\streamlit_app.py
