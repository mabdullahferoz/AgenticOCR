Write-Host "Installing Backend Dependencies..."
pip install -r requirements.txt

Write-Host "Installing Frontend Dependencies..."
Set-Location -Path "frontend"
npm install
Set-Location -Path ".."

Write-Host "Installation Complete!"
