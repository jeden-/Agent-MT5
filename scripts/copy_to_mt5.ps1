# Skrypt do kopiowania plików EA do katalogu MT5

# Definiujemy ścieżkę do katalogu MT5
$mt5Path = "C:\Users\win\AppData\Roaming\MetaQuotes\Terminal\47AEB69EDDAD4D73097816C71FB25856\MQL5\Experts"

# Ścieżka źródłowa
$sourcePath = "src\mt5_ea\fixed_AgentMT5_EA.mq5"

# Ścieżka docelowa
$destPath = Join-Path -Path $mt5Path -ChildPath "AgentMT5_EA.mq5"

# Sprawdzamy, czy ścieżka docelowa istnieje
if (!(Test-Path -Path $mt5Path)) {
    Write-Host "Katalog docelowy nie istnieje: $mt5Path"
    exit 1
}

# Kopiujemy plik
try {
    Copy-Item -Path $sourcePath -Destination $destPath -Force
    Write-Host "Plik został skopiowany pomyślnie do: $destPath"
} catch {
    Write-Host "Wystąpił błąd podczas kopiowania pliku: $_"
    exit 1
}

# Informujemy użytkownika o dalszych krokach
Write-Host "Teraz musisz skompilować EA w MetaEditor!"
Write-Host "1. Uruchom MetaEditor (F4 w MT5)"
Write-Host "2. Otwórz plik AgentMT5_EA.mq5"
Write-Host "3. Skompiluj projekt (F7)" 