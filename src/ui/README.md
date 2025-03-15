# AgentMT5 - Interfejs Użytkownika

Ten katalog zawiera interfejs użytkownika dla systemu AgentMT5, zbudowany przy użyciu Streamlit.

## Funkcje

- **Live Monitor**: 
  - **Status Systemu**: Informacja o statusie połączenia, ostatniej aktywności i liczbie pozycji
  - **Stan Konta**: Aktualne informacje z MT5 o saldzie, kapitale, depozycie i poziomie depozytu
  - **Aktywne Pozycje**: Tabela zawierająca wszystkie otwarte pozycje z MT5
  - **Historia Transakcji**: Historia zamkniętych transakcji
- **Performance Dashboard**: Analiza wyników handlowych
- **AI Analytics**: Analityka związana z modelami AI
- **System Status**: Monitorowanie ogólnego stanu systemu

## Sekcja Stan Konta

Sekcja "Stan Konta" wyświetla następujące metryki z MT5:
- **Saldo**: Aktualne saldo konta bez uwzględnienia otwartych pozycji
- **Kapitał**: Całkowity kapitał konta, uwzględniający zysk/stratę z otwartych pozycji
- **Depozyt**: Aktualna wartość depozytu zajętego przez otwarte pozycje
- **Dostępny Depozyt**: Wartość depozytu dostępnego do wykorzystania
- **Poziom Depozytu**: Procentowy stosunek kapitału do depozytu

## Sekcja Aktywne Pozycje

Tabela aktywnych pozycji wyświetla:
- **Bilet**: Numer biletu transakcji w MT5
- **Instrument**: Symbol instrumentu finansowego
- **Typ**: Kierunek transakcji (BUY/SELL)
- **Czas Otwarcia**: Data i czas otwarcia pozycji
- **Wolumen**: Wielkość pozycji
- **Zysk/Strata**: Aktualny wynik finansowy pozycji

## Lokalizacja

- Interfejs używa polskiego formatu dla:
  - Walut: "10 500,00 zł" (spacja jako separator tysięcy, przecinek jako separator dziesiętny, symbol "zł")
  - Dat: "DD.MM.YYYY HH:MM:SS"
  - Procentów: "10,5%" (przecinek jako separator dziesiętny)

## Wymagania

```
streamlit==1.27.0
plotly==5.17.0
pandas==2.1.0
numpy==1.25.2
requests==2.31.0
```

## Uruchomienie

```bash
# Zainstaluj wymagane pakiety
pip install -r requirements.txt

# Uruchom aplikację Streamlit
cd src/ui
streamlit run app.py
```

## Dostęp

Po uruchomieniu, interfejs będzie dostępny pod adresem:
- http://localhost:8501

## Konfiguracja

Główne ustawienia aplikacji znajdują się w zmiennych na początku pliku `app.py`:

```python
# Stałe
SERVER_URL = "http://127.0.0.1:5555"  # Adres serwera HTTP MT5
REFRESH_INTERVAL = 5  # Interwał odświeżania w sekundach
CURRENCY = "zł"  # Waluta używana w systemie
```

## Autoodświeżanie

Interfejs obsługuje automatyczne odświeżanie danych z ustalonym interwałem. Można to włączyć/wyłączyć za pomocą opcji w panelu bocznym.

## Rozwój

Aby dodać nowe funkcje:

1. Zdefiniuj nową funkcję renderującą w pliku `app.py`
2. Dodaj nową opcję w menu w funkcji `main()`
3. Aktualizuj API zgodnie z potrzebami

## Dostosowanie wyglądu

Styl interfejsu można dostosować za pomocą CSS w zmiennej `st.markdown()` na początku pliku. 