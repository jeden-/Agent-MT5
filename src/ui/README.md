# AgentMT5 - Interfejs Użytkownika

Interfejs użytkownika do monitorowania i zarządzania systemem handlowym AgentMT5.

## Funkcje

- **Live Monitor** - monitorowanie aktywnych pozycji, wykresu equity i ostatnich operacji
- **Performance Dashboard** - analiza wyników handlowych, wydajności instrumentów i strategii
- **AI Analytics** - monitorowanie modeli AI, decyzji i kosztów operacyjnych
- **System Status** - monitorowanie stanu systemu, alertów i statystyk

## Wymagania

- Python 3.8+
- Streamlit i inne zależności z pliku `requirements.txt`
- Działający serwer HTTP AgentMT5

## Instalacja

```bash
# Instalacja zależności
pip install -r requirements.txt
```

## Uruchomienie

1. Upewnij się, że serwer HTTP AgentMT5 jest uruchomiony:
   ```bash
   python scripts/http_mt5_server.py --host 127.0.0.1 --port 5555
   ```

2. Uruchom aplikację Streamlit:
   ```bash
   cd src/ui
   streamlit run app.py
   ```

3. Aplikacja będzie dostępna w przeglądarce pod adresem: [http://localhost:8501](http://localhost:8501)

## Konfiguracja

Podstawowe ustawienia można skonfigurować w panelu bocznym aplikacji:
- URL serwera AgentMT5
- Interwał odświeżania danych

## Uwagi

- Automatyczne odświeżanie jest domyślnie włączone z 5-sekundowym interwałem
- Dane są pobierane z serwera HTTP AgentMT5 w czasie rzeczywistym
- W przypadku braku połączenia z serwerem, wyświetlane są przykładowe dane 