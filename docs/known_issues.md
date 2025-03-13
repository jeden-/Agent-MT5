# Znane problemy w projekcie AgentMT5

## Problemy z modułem raportowania (2025-03-16)

### Problem z generowaniem pliku report_generator.py

**Opis problemu:**
Podczas implementacji modułu raportowania napotkano problem z tworzeniem pliku `src/reporting/report_generator.py`. System nie pozwala na edycję tego pliku przez narzędzia automatyczne.

**Objawy:**
- Próba utworzenia pliku kończy się niepowodzeniem
- Narzędzie edit_file przerywa działanie bez informacji zwrotnej
- Plik nie jest tworzony w systemie plików

**Potencjalne przyczyny:**
1. Problem z uprawnieniami do zapisu w katalogu `src/reporting`
2. Konflikt nazwy pliku z istniejącym zasobem systemowym
3. Problem z narzędziem edit_file podczas tworzenia nowych plików o dużej objętości

**Wpływ na projekt:**
- Opóźnienie w implementacji generatora raportów
- Konieczność zmiany podejścia do tworzenia raportów

**Rozwiązanie:**
Problem został rozwiązany poprzez manualne utworzenie pliku `src/reporting/report_generator.py`. Zaimplementowano pełną funkcjonalność generowania raportów w różnych formatach (HTML, PDF, Markdown, CSV) oraz generowania wykresów wydajności.

**Priorytet:** Rozwiązany

**Status:** Zamknięty

**Odpowiedzialny:** Zespół deweloperski

## Problem z zamykaniem pozycji przez API MT5 (2025-03-18)

**Opis problemu:**
Broker (TMS OANDA) blokuje możliwość bezpośredniego zamykania pozycji przez API MetaTrader 5. W logach pojawia się błąd "Unsupported filling mode (kod 10030)" przy próbie zamknięcia pozycji.

**Objawy:**
- Funkcja `close_position` z modułu `MT5Connector` nie działa
- W logach błąd "Unsupported filling mode (kod 10030)"
- Pozycje nie są zamykane mimo poprawnych parametrów zapytania

**Potencjalne przyczyny:**
1. Ograniczenia nałożone przez brokera na API MT5
2. Brak obsługi wymaganych trybów wypełniania zleceń (filling modes) przez brokera
3. Zabezpieczenia brokera przed automatycznym handlem

**Wpływ na projekt:**
- Niemożność automatycznego zamykania pozycji przez standardowe API
- Potrzeba opracowania alternatywnego mechanizmu zamykania pozycji
- Opóźnienia w implementacji zarządzania pozycjami

**Rozwiązanie:**
Problem został rozwiązany poprzez implementację łatki `patched_close_position` w module `src.utils.patches`, która wykorzystuje komunikację z Expert Advisor (EA) przez HTTP zamiast bezpośredniego API MT5. EA jest w stanie zamykać pozycje, ponieważ działa bezpośrednio w terminalu MT5. Implementacja zawiera:
1. Modyfikację funkcji `close_position` w klasie `MT5Connector`
2. Wykorzystanie `MT5ApiClient` do komunikacji z EA
3. Aktualizację skryptu `close_excess_positions.py` do korzystania z nowej metody

**Priorytet:** Wysoki (Rozwiązany)

**Status:** Zamknięty

**Odpowiedzialny:** Zespół deweloperski

## Problem z nadmierną liczbą otwartych pozycji (2025-03-19)

**Opis problemu:**
System otworzył zbyt wiele pozycji (ok. 147), co doprowadziło do wyczerpania środków na koncie i generowało błąd "No money (kod 10019)" przy próbie otwarcia nowych pozycji.

**Objawy:**
- Bardzo duża liczba otwartych pozycji (około 147)
- W logach błąd "No money (kod 10019)"
- Całkowite wyczerpanie dostępnych środków na koncie
- Nieprawidłowe zarządzanie ryzykiem

**Potencjalne przyczyny:**
1. Brak skutecznego limitu liczby otwieranych pozycji
2. Zbyt wysoka częstotliwość generowania sygnałów handlowych
3. Błąd w klasie `RiskParameters` - limity nie były poprawnie stosowane
4. Brak sprawdzania globalnego limitu pozycji przed otwarciem nowych

**Wpływ na projekt:**
- Ryzyko dużych strat finansowych
- Brak możliwości otwierania nowych pozycji
- Utrata kontroli nad strategią handlową
- Trudności w zarządzaniu dużą liczbą pozycji

**Rozwiązanie:**
Problem został rozwiązany poprzez:
1. Zmianę parametrów w klasie `RiskParameters` - ograniczenie do max 3 pozycji w całym systemie
2. Modyfikację skryptu `close_excess_positions.py` do uwzględniania globalnego limitu pozycji
3. Naprawę skryptu `start_agent_with_limits.py` do prawidłowego uruchamiania agenta z nowymi limitami
4. Dodanie funkcji `load_config()` do modułu `start.py` do poprawnego wczytywania konfiguracji

**Priorytet:** Krytyczny (Rozwiązany)

**Status:** Zamknięty

**Odpowiedzialny:** Zespół deweloperski

## Inne znane problemy

(Tutaj można dodać inne znane problemy w projekcie) 