$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "ARIS / MASTEN - Windows installer"
py -3.12 --version
if ($LASTEXITCODE -ne 0) { throw "Instale Python 3.12" }
py -3.12 -m pip install -r aris_masten/requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias" }
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
  $ollamaPath = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
  if (Test-Path $ollamaPath) { $ollama = @{ Source = $ollamaPath } }
}
if (-not $ollama) { throw "Instale Ollama antes de continuar" }
& $ollama.Source pull qwen2.5:3b
if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar o modelo Ollama" }
if (-not (Test-Path "vosk-model/am")) {
  Write-Host "Baixando modelo de reconhecimento portugues..."
  Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip" -OutFile "vosk-pt.zip"
  Expand-Archive "vosk-pt.zip" -DestinationPath "." -Force
  Rename-Item "vosk-model-small-pt-0.3" "vosk-model"
  Remove-Item "vosk-pt.zip"
}
Write-Host "Instalacao concluida. Iniciando..."
py -3.12 -m aris_masten.desktop
