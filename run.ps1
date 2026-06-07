Write-Host "Starting Backend Server..."
# Using Start-Process to run the backend in a separate window so both can run simultaneously
Start-Process -FilePath "python" -ArgumentList "-m uvicorn server:app --host 127.0.0.1 --port 8000" -WindowStyle Normal

Write-Host "Starting Frontend Server..."
Set-Location -Path "frontend"
npm run dev
