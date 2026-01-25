# Sovereign-Mind 3.0 Launcher
# Automation for the "One-Click" Experience

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   SOVEREIGN-MIND 3.0 - LAUNCHER        " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Environment Checks
$BinDir = ".\bin"
$LlamaFile = "$BinDir\llamafile.exe"
$ModelUrl = "https://huggingface.co/jartine/TinyLlama-1.1B-Chat-v1.0-llamafile/resolve/main/TinyLlama-1.1B-Chat-v1.0.Q5_K_M.llamafile?download=true" # Using TinyLlama (~700MB) as efficient small model

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
}

# 2. Check for Llamafile
if (-not (Test-Path $LlamaFile)) {
    Write-Host "[!] Llamafile not found. Downloading bundled inference engine..." -ForegroundColor Yellow
    Write-Host "    Model: TinyLlama-1.1B (closest reliable single-file to 0.5B)" -ForegroundColor Gray
    Write-Host "    Size: ~760 MB" -ForegroundColor Gray
    
    # Use Python for reliable download (bypasses PS auth issues)
    python scripts/download_model.py
    
    if (-not (Test-Path $LlamaFile)) {
         Write-Host "[!] Download failed. Please download manually." -ForegroundColor Red
         exit
    }
} else {
    Write-Host "[*] Inference Engine found." -ForegroundColor Green
}

# 3. Start Backend
Write-Host "[*] Starting Sovereign-Mind Backend..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -NoNewWindow
# Note: In production we wouldn't use --reload

# 4. Start Frontend
Write-Host "[*] Starting Dashboard UI..." -ForegroundColor Green
Set-Location ".\ui"
if (-not (Test-Path "node_modules")) {
    Write-Host "[!] Initializes UI dependencies..." -ForegroundColor Yellow
    npm install
}
Write-Host "[*] Starting Dashboard UI..." -ForegroundColor Green
Start-Process -FilePath "cmd" -ArgumentList "/c npm run dev" -NoNewWindow
Set-Location ".."

Write-Host "[*] Systems Nominal." -ForegroundColor Cyan
Write-Host "    > Backend: http://localhost:8000/docs"
Write-Host "    > Frontend: http://localhost:3000"
Write-Host "    > Press Ctrl+C to stop."
