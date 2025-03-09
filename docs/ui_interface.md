# Interfejs Użytkownika AgentMT5

Interfejs użytkownika AgentMT5 to aplikacja webowa stworzona przy użyciu Streamlit, służąca do monitorowania i zarządzania systemem handlowym AgentMT5. Interfejs jest zaprojektowany zgodnie z nowoczesnym podejściem do dashboardów, zapewniając intuicyjną interakcję i bogatą wizualizację danych.

## Architektura Interfejsu

### Struktura Interfejsu

Interfejs jest podzielony na cztery główne sekcje, które są dostępne jako zakładki:

1. **Live Monitor** - bieżące monitorowanie handlu
2. **Performance Dashboard** - analiza wyników
3. **AI Analytics** - monitorowanie modeli AI
4. **System Status** - monitorowanie stanu systemu

### Komunikacja z Serwerem

Interfejs komunikuje się z serwerem HTTP AgentMT5 poprzez dedykowane API:

- Protokół komunikacji: HTTP
- Format danych: JSON
- Uwierzytelnianie: Podstawowe (w przyszłości planowane token-based)

Główne endpointy wykorzystywane przez interfejs:

- `/monitoring/status` - pobieranie statusu systemu
- `/monitoring/alerts` - pobieranie alertów
- `/monitoring/logs` - pobieranie logów
- `/monitoring/connections` - pobieranie informacji o połączeniach

### Wykorzystane Technologie

- **Streamlit** - framework do tworzenia aplikacji webowych w Pythonie
- **Plotly** - interaktywne wizualizacje danych
- **Pandas** - przetwarzanie i analiza danych
- **Requests** - komunikacja HTTP z serwerem

## Szczegółowy Opis Funkcjonalności

### 1. Live Monitor

Funkcjonalności:
- Wykres equity w czasie rzeczywistym
- Lista aktywnych pozycji
- Statystyki konta (balance, equity, P/L)
- Ostatnie operacje handlowe
- Szybkie akcje (zamykanie pozycji, zatrzymanie awaryjne)

Przykład wykorzystania:
```python
# Pobieranie aktywnych pozycji
positions = api_request("positions", params={"active": "true"})

# Wyświetlanie aktywnych pozycji
st.dataframe(pd.DataFrame(positions))
```

### 2. Performance Dashboard

Funkcjonalności:
- Kluczowe wskaźniki (win rate, profit factor, itp.)
- Wykresy wyników handlowych
- Analiza wydajności instrumentów
- Analiza wydajności strategii

Przykładowe wskaźniki:
- Win Rate: Procent zyskownych transakcji
- Profit Factor: Stosunek zysków do strat
- Sharpe Ratio: Miara efektywności inwestycji
- Maximum Drawdown: Maksymalny spadek kapitału

### 3. AI Analytics

Funkcjonalności:
- Status modeli AI (Claude, Grok, DeepSeek)
- Logi decyzji AI
- Jakość sygnałów AI
- Koszty operacyjne AI

Monitorowane metryki dla modeli AI:
- Czas odpowiedzi
- Dokładność decyzji
- Zużycie zasobów
- Koszt operacyjny

### 4. System Status

Funkcjonalności:
- Ogólny status systemu
- Status komponentów
- Monitoring zasobów systemowych
- Aktywne alerty
- Statystyki zapytań

Monitorowane zasoby:
- Użycie CPU
- Zużycie pamięci
- Aktywne/nieaktywne połączenia
- Liczba i rodzaje alertów

## Możliwości Rozbudowy

### Planowane Funkcjonalności

1. **Zarządzanie Strategiami**:
   - Tworzenie i edycja strategii handlowych
   - Testowanie strategii na danych historycznych
   - Porównywanie wyników strategii

2. **Zaawansowana Analityka**:
   - Szczegółowa analiza dziennych wyników
   - Wykrywanie wzorców w danych handlowych
   - Rekomendacje optymalizacyjne

3. **Mobilna Wersja Interfejsu**:
   - Responsywny design dla urządzeń mobilnych
   - Powiadomienia push o ważnych wydarzeniach
   - Dedykowana aplikacja mobilna

4. **System Użytkowników**:
   - Wielopoziomowe konta użytkowników
   - Zarządzanie uprawnieniami
   - Personalizacja interfejsu

## Instalacja i Uruchamianie

### Wymagania

- Python 3.8+
- Streamlit i zależności z `requirements.txt`
- Działający serwer HTTP AgentMT5

### Instalacja

```bash
# Instalacja zależności
pip install -r src/ui/requirements.txt
```

### Uruchomienie

```bash
# Uruchomienie serwera
python scripts/http_mt5_server.py --host 127.0.0.1 --port 5555

# Uruchomienie interfejsu
cd src/ui
streamlit run app.py
```

## Najlepsze Praktyki

1. **Monitorowanie w Czasie Rzeczywistym**:
   - Utrzymuj aktywne połączenie z systemem podczas handlu
   - Regularnie sprawdzaj zakładkę Live Monitor

2. **Reagowanie na Alerty**:
   - Priorytetyzuj alerty krytyczne i błędy
   - Sprawdzaj szczegóły alertów w zakładce System Status

3. **Analiza Wyników**:
   - Regularnie przeglądaj Performance Dashboard
   - Identyfikuj mocne i słabe strony strategii

4. **Koszty Operacyjne AI**:
   - Monitoruj koszty AI w zakładce AI Analytics
   - Optymalizuj wykorzystanie modeli dla efektywności kosztowej 