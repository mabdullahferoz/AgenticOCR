# Ensure the script runs in the evaluation directory
Set-Location -Path $PSScriptRoot

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Running OCR vs PDF Evaluation Script..." -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Run the Python evaluation script to generate metrics.json
& "..\venv\Scripts\python.exe" "evaluate.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Evaluation script failed. Please check the errors above." -ForegroundColor Red
    exit 1
}

Write-Host "Metrics successfully generated!" -ForegroundColor Green
Write-Host ""
Write-Host "Starting Local Web Server for the Dashboard on Port 8080..." -ForegroundColor Yellow

# Start the web server in the background
$serverProcess = Start-Process -PassThru -FilePath "..\venv\Scripts\python.exe" -ArgumentList "-m", "http.server", "8080"

# Give the server a moment to start up
Start-Sleep -Seconds 2

Write-Host "Opening Dashboard in your default web browser..." -ForegroundColor Green
Start-Process "http://localhost:8080/dashboard.html"

Write-Host ""
Write-Host "Press any key to stop the server and exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup the web server process when exiting
Stop-Process -Id $serverProcess.Id -Force
Write-Host "Server stopped." -ForegroundColor Yellow
