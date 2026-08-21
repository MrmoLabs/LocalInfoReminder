# Enter a project-local Python session without inheriting global PYTHONPATH.
$env:PYTHONPATH = ""
& "$PSScriptRoot\venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 'Python 3.12 is required; recreate the project venv with Python 3.12.')"
if ($LASTEXITCODE -ne 0) {
    throw "The project venv must use Python 3.12."
}
& "$PSScriptRoot\venv\Scripts\Activate.ps1"
Write-Host "Project virtualenv activated with PYTHONPATH cleared." -ForegroundColor Green
Write-Host "Python: $(& "$PSScriptRoot\venv\Scripts\python.exe" -c 'import sys; print(sys.executable)')" -ForegroundColor Green
