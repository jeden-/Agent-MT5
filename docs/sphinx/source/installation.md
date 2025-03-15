# Instalacja

## Wymagania systemowe

- Python 3.10 lub nowszy
- MetaTrader 5 (zainstalowany lokalnie)
- PostgreSQL 13 lub nowszy
- Konto demo lub rzeczywiste u brokera obsługującego MetaTrader 5

## Instalacja środowiska

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/jeden-/AgentMT5.git
cd AgentMT5
```

### 2. Tworzenie wirtualnego środowiska Python

```bash
python -m venv venv
```

#### Aktywacja środowiska

Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

### 3. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 4. Konfiguracja bazy danych

Utwórz bazę danych PostgreSQL:

```sql
CREATE DATABASE mt5remotetest;
CREATE USER mt5remote WITH PASSWORD 'mt5remote';
GRANT ALL PRIVILEGES ON DATABASE mt5remotetest TO mt5remote;
```

### 5. Konfiguracja pliku .env

Skopiuj plik `.env.example` do `.env` i dostosuj parametry:

```bash
cp .env.example .env
```

Edytuj plik `.env` i ustaw odpowiednie wartości dla:
- Parametrów bazy danych
- Danych logowania do MT5
- Kluczy API dla modeli AI
- Innych parametrów konfiguracyjnych

### 6. Inicjalizacja bazy danych

```bash
python scripts/init_db.py
```

## Konfiguracja MetaTrader 5

1. Zainstaluj MetaTrader 5 z oficjalnej strony
2. Zaloguj się na konto demo lub rzeczywiste
3. Skopiuj pliki EA (Expert Advisor) do katalogu MT5:
   ```bash
   python scripts/deploy_ea.py
   ```
4. Aktywuj EA na wybranym instrumencie w MT5

## Uruchomienie aplikacji

```bash
python main.py
```

Aplikacja będzie dostępna pod adresem: http://127.0.0.1:8502/

## Rozwiązywanie problemów

Jeśli napotkasz problemy podczas instalacji lub uruchamiania:

1. Sprawdź logi w pliku `mt5remoteai.log`
2. Upewnij się, że MetaTrader 5 jest uruchomiony i zalogowany
3. Sprawdź połączenie z bazą danych
4. Zweryfikuj poprawność kluczy API dla modeli AI 