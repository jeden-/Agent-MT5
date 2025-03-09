# Skrypt do uruchamiania aplikacji z poprawnie ustawionym PYTHONPATH

Write-Host "Uruchamianie aplikacji z poprawnie skonfigurowanym środowiskiem..."

# Ustaw PYTHONPATH na katalog główny projektu
$env:PYTHONPATH = $PWD.Path

# Aktywuj środowisko wirtualne, jeśli jeszcze nie jest aktywne
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Aktywuję środowisko wirtualne..."
    .\venv\Scripts\Activate.ps1
}

# Uruchom aplikację
Write-Host "Uruchamianie aplikacji..."
python src/main.py 