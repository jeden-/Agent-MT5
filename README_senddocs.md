# SendDocs - Skrypt do wysyłania dokumentacji na serwer FTP

## Opis

Skrypt `senddocs.py` służy do automatycznego wysyłania dokumentacji projektu AgentMT5 na serwer FTP. 
Umożliwia szybkie i wygodne aktualizowanie dokumentacji online bez konieczności ręcznego przesyłania plików.

## Wymagania

- Python 3.6 lub nowszy
- Dostęp do serwera FTP
- Wygenerowana dokumentacja w katalogu `C:\Users\win\Documents\AgentMT5\docs\sphinx\build\html`

## Konfiguracja

Skrypt używa następujących parametrów, które można edytować w kodzie:

```python
# Konfiguracja FTP
DEFAULT_FTP_HOST = "mainpress.ftp.dhosting.pl"
DEFAULT_FTP_USER = "faih4e_wawrzenp"
DEFAULT_FTP_PASS = "AgentMT%@!2025"
DEFAULT_FTP_DIR = "/wawrzen.pl/public_html"

# Lokalizacja dokumentacji
LOCAL_DOCS_DIR = r"C:\Users\win\Documents\AgentMT5\docs\sphinx\build\html"
```

## Użycie

Aby uruchomić skrypt, wykonaj poniższą komendę w terminalu:

```
python senddocs.py
```

Możliwe opcje wiersza poleceń:

```
python senddocs.py --test     # Testuje tylko połączenie FTP bez wysyłania plików
python senddocs.py -i         # Tryb interaktywny - zapyta o dane logowania
python senddocs.py --host [nazwa_hosta] --user [login] --dir [katalog_docelowy]
```

## Funkcjonalności

- Rekurencyjne wysyłanie wszystkich plików i katalogów dokumentacji
- Automatyczne tworzenie katalogów na serwerze FTP, jeśli nie istnieją
- Szczegółowe logowanie procesu synchronizacji
- Obsługa błędów i komunikaty o statusie operacji
- Tryb interaktywny do wprowadzania danych logowania
- Tryb testowy do weryfikacji połączenia

## Rezultat

Po pomyślnym wykonaniu skryptu, dokumentacja będzie dostępna pod adresem:
https://wawrzen.pl/

## Logowanie

Skrypt generuje logi w konsoli, które zawierają informacje o:

- Rozpoczęciu i zakończeniu synchronizacji
- Utworzonych katalogach
- Wysłanych plikach
- Ewentualnych błędach
- Całkowitym czasie trwania operacji

## Rozwiązywanie problemów

W przypadku problemów warto sprawdzić:

1. Dostęp do serwera FTP - poprawność danych logowania
2. Istnienie lokalnego katalogu z dokumentacją
3. Uprawnienia do zapisu na serwerze FTP
4. Stabilność połączenia internetowego

## Autor

Projekt AgentMT5 