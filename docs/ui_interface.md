# Dokumentacja Interfejsu Użytkownika AgentMT5

## Wprowadzenie

Interfejs użytkownika AgentMT5 to aplikacja webowa zbudowana przy użyciu Streamlit, która umożliwia monitorowanie i kontrolowanie systemu tradingowego AgentMT5. Interfejs zapewnia dostęp do danych handlowych w czasie rzeczywistym, analiz AI oraz kontroli nad agentem.

## Funkcje

Interfejs użytkownika AgentMT5 oferuje następujące funkcje:

1. **Live Monitor** - monitorowanie aktualnych pozycji, stanu konta i ostatnich transakcji w czasie rzeczywistym
2. **Performance Dashboard** - analiza wyników handlowych, statystyki i wykresy
3. **AI Analytics** - analiza wydajności modeli AI i ich sygnałów
4. **System Status** - monitorowanie stanu systemu, zasobów i alertów
5. **Control Panel** - sterowanie agentem, konfiguracja parametrów i ustawień

## Architektura

Interfejs użytkownika jest zbudowany w oparciu o następujące komponenty:

- **Streamlit** - framework do tworzenia aplikacji webowych w Pythonie
- **Plotly** - biblioteka do tworzenia interaktywnych wykresów
- **Pandas** - biblioteka do analizy danych
- **MT5ApiClient** - klient API do komunikacji z serwerem MT5

## Struktura kodu

Główny plik aplikacji to `src/ui/app.py`, który zawiera następujące komponenty:

- **Funkcje pomocnicze** - formatowanie danych, obsługa API, itp.
- **Funkcje renderujące** - odpowiedzialne za wyświetlanie poszczególnych zakładek
- **Funkcja główna** - inicjalizacja aplikacji i obsługa nawigacji

## Komunikacja z MT5

Interfejs komunikuje się z serwerem MT5 za pomocą klienta API (`MT5ApiClient`), który wysyła żądania HTTP do serwera MT5. Klient API obsługuje następujące endpointy:

- `/monitoring/connections` - informacje o połączeniach z MT5
- `/monitoring/positions` - informacje o aktywnych pozycjach
- `/monitoring/transactions` - historia transakcji
- `/monitoring/performance` - statystyki wydajności
- `/monitoring/status` - status systemu
- `/monitoring/resources` - informacje o zasobach systemowych
- `/monitoring/alerts` - aktywne alerty
- `/mt5/account` - informacje o koncie MT5
- `/ai/models` - informacje o modelach AI
- `/ai/signals` - sygnały handlowe generowane przez modele AI
- `/ai/signals/latest` - najnowsze sygnały handlowe
- `/ai/costs` - informacje o kosztach wykorzystania API modeli AI
- `/agent/status` - status agenta
- `/agent/start` - uruchomienie agenta
- `/agent/stop` - zatrzymanie agenta
- `/agent/restart` - restart agenta
- `/agent/config` - konfiguracja agenta

## Funkcje interfejsu

### Live Monitor

Zakładka Live Monitor wyświetla:

- Status systemu i połączenia z MT5
- Saldo konta i equity
- Bieżący zysk/stratę
- Informacje o ostatniej transakcji
- Listę aktywnych pozycji z możliwością zarządzania nimi

### Performance Dashboard

Zakładka Performance Dashboard wyświetla:

- Kluczowe wskaźniki wydajności (win rate, profit factor, itp.)
- Wykres skumulowanego P/L
- Wykres wyników per instrument
- Pełną historię transakcji

### AI Analytics

Zakładka AI Analytics wyświetla:

- Aktualne sygnały handlowe generowane przez modele AI
- Wydajność poszczególnych modeli AI
- Analizę sygnałów AI
- Korelację między sygnałami AI a wynikami handlowymi
- Informacje o kosztach wykorzystania API modeli AI

#### System statusów danych w AI Analytics

W zakładce AI Analytics, dane wyświetlane są z odpowiednim oznaczeniem ich statusu:

- **ok** - rzeczywiste dane pobrane z systemu
- **demo** - przykładowe dane demonstracyjne (używane gdy rzeczywiste dane nie są dostępne)
- **no_data** - brak danych (np. gdy system jeszcze nie wygenerował sygnałów)
- **error** - błąd podczas pobierania danych

Każdy status jest wyświetlany z odpowiednim komunikatem wyjaśniającym aktualny stan danych oraz instrukcją, jak rozpocząć zbieranie rzeczywistych danych. Komunikaty są oznaczone kolorami dla łatwiejszej identyfikacji:
- Dane demonstracyjne: pomarańczowy
- Brak danych: niebieski
- Błąd: czerwony
- Rzeczywiste dane: zielony

#### Monitoring kosztów API

W sekcji AI Analytics wyświetlane są również informacje o kosztach wykorzystania API modeli AI:

- Całkowity koszt API w bieżącym miesiącu
- Koszty w podziale na poszczególne modele AI
- Wykres kosztów w czasie
- Prognoza kosztów na koniec miesiąca

Dane te pozwalają na monitorowanie wydatków związanych z wykorzystaniem zewnętrznych API modeli AI i optymalizację strategii ich wykorzystania.

### System Status

Zakładka System Status wyświetla:

- Ogólny status systemu
- Status poszczególnych komponentów
- Informacje o zasobach systemowych (CPU, pamięć, dysk)
- Aktywne alerty

### Control Panel

Zakładka Control Panel umożliwia:

- Uruchamianie, zatrzymywanie i restartowanie agenta
- Wybór trybu pracy agenta (obserwacyjny, półautomatyczny, automatyczny)
- Konfigurację limitów ryzyka
- Konfigurację parametrów dla poszczególnych instrumentów

## Funkcje automatycznego odświeżania

Interfejs obsługuje automatyczne odświeżanie danych:

- Domyślny interwał odświeżania wynosi 10 sekund
- Użytkownik może dostosować interwał odświeżania w zakresie 5-60 sekund
- Pasek postępu pokazuje czas do następnego odświeżenia
- Każda zakładka ma również przycisk do ręcznego odświeżenia danych

## Obsługa błędów

Interfejs obsługuje różne scenariusze błędów:

- Brak połączenia z serwerem MT5
- Brak danych z serwera
- Błędy API

W przypadku błędów, interfejs wyświetla odpowiednie komunikaty i instrukcje dla użytkownika.

### Komunikaty o statusie danych

Interfejs wyświetla szczegółowe komunikaty o statusie danych, które pomagają użytkownikowi zrozumieć:
- Czy wyświetlane dane są rzeczywiste czy demonstracyjne
- Jakie są możliwe przyczyny braku danych
- Jakie kroki należy podjąć, aby rozpocząć zbieranie rzeczywistych danych
- Jak rozwiązać problemy z połączeniem lub błędami

## Uruchamianie interfejsu

Aby uruchomić interfejs, należy wykonać następujące kroki:

1. Upewnić się, że serwer MT5 jest uruchomiony
2. Uruchomić skrypt `scripts/run_interface.py`
3. Otworzyć przeglądarkę i przejść do adresu `http://localhost:8501`

## Konfiguracja

Interfejs można skonfigurować za pomocą zmiennych środowiskowych:

- `SERVER_URL` - adres serwera MT5 (domyślnie: `http://127.0.0.1:5555`)
- `REFRESH_INTERVAL` - interwał odświeżania w sekundach (domyślnie: `10`)
- `CURRENCY` - waluta używana w systemie (domyślnie: `zł`)

## Zmiany wprowadzone w wersji 1.1.0

1. Dodano system statusów danych w AI Analytics (ok, demo, no_data, error)
2. Dodano informacje o kosztach wykorzystania API modeli AI
3. Ulepszono komunikaty o błędach i braku danych
4. Dodano szczegółowe instrukcje dla użytkownika jak rozpocząć zbieranie rzeczywistych danych
5. Dodano funkcje renderujące dla wszystkich widoków interfejsu
6. Naprawiono strukturę aplikacji (dodano funkcje `main()`, `check_mt5_connection()` i inne)
7. Zmodyfikowano endpoint `/ai/models` o obsługę różnych statusów danych
8. Dodano mechanizm sprawdzania połączenia z MT5 w menu bocznym

## Zmiany wprowadzone w wersji 1.0.0

1. Usunięto przykładowe dane we wszystkich modułach i zastąpiono je rzeczywistymi danymi z MT5
2. Dodano przyciski odświeżania dla każdego panelu
3. Poprawiono wyświetlanie danych w Live Monitor
4. Zaktualizowano wykresy w Performance Dashboard
5. Ulepszono wizualizację danych w AI Analytics
6. Rozbudowano monitoring zasobów systemowych
7. Dodano lepsze formatowanie alertów
8. Zwiększono interwał odświeżania do 10 sekund dla zmniejszenia obciążenia serwera
9. Dodano wskaźnik stanu połączenia z MT5 w pasku bocznym
10. Dodano możliwość dostosowania interwału odświeżania przez użytkownika
11. Dodano pasek postępu pokazujący czas do następnego odświeżenia
12. Dodano sekcję z aktualnymi pozycjami w zakładce Live Monitor
13. Dodano sekcję z aktualnymi sygnałami AI w zakładce AI Analytics
14. Dodano stopkę z informacjami o wersji i autorze 