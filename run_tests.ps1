# Skrypt do uruchamiania testów z poprawnie ustawionym PYTHONPATH
# Użycie: .\run_tests.ps1 [ścieżka_do_testu]
# Przykład: .\run_tests.ps1 src.tests.unit.analysis.test_feedback_loop

param (
    [Parameter(Mandatory=$false)]
    [string]$TestPath = "discover"
)

Write-Host "Uruchamianie testów z poprawnie skonfigurowanym środowiskiem..."

# Ustaw PYTHONPATH na katalog główny projektu
$env:PYTHONPATH = $PWD.Path

# Aktywuj środowisko wirtualne, jeśli jeszcze nie jest aktywne
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Aktywuję środowisko wirtualne..."
    .\venv\Scripts\Activate.ps1
}

# Utwórz tymczasowy skrypt do uruchamiania testów z modyfikacją sys.path
$tempScript = @"
# Zaimportuj nasz moduł naprawiający importy
import src_path_fix

# Importuj unittest
import unittest

if __name__ == '__main__':
    # Uruchom testy
    if '$TestPath' == 'discover':
        unittest.main(module=None, argv=['unittest', 'discover', '-s', 'src/tests'])
    else:
        __import__('$TestPath')
        unittest.main(module='$TestPath')
"@

# Zapisz skrypt tymczasowy
$tempScriptPath = ".\run_tests_temp.py"
$tempScript | Out-File -FilePath $tempScriptPath -Encoding utf8

try {
    # Uruchom skrypt tymczasowy
    python $tempScriptPath
}
finally {
    # Usuń skrypt tymczasowy
    Remove-Item -Path $tempScriptPath -ErrorAction SilentlyContinue
} 