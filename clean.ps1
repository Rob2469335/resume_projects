# 1. Tell Git to forget everything it's currently tracking
Write-Host "Cleaning the 'Pending' bucket..." -ForegroundColor Cyan
git rm -r --cached .

# 2. Re-scan the files using your new .gitignore rules
Write-Host "Re-applying your .gitignore rules..." -ForegroundColor Cyan
git add .

# 3. Check the status
Write-Host "Done! Here is your new, clean list:" -ForegroundColor Green
git status