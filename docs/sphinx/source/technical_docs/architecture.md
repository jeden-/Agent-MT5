# Architektura systemu

## Schemat blokowy systemu

System AgentMT5 składa się z następujących głównych komponentów:

1. **MT5 Bridge** - moduł komunikacji z platformą MetaTrader 5
2. **AI Controller** - moduł zarządzający modelami AI i ich predykcjami
3. **Position Manager** - moduł zarządzania pozycjami i ryzykiem
4. **Monitoring System** - moduł monitorowania wyników i generowania alertów
5. **User Interface** - interfejs użytkownika do kontroli i konfiguracji systemu

## Diagram przepływu danych

```
+----------------+      +----------------+      +----------------+
|                |      |                |      |                |
|  MetaTrader 5  | <--> |   MT5 Bridge   | <--> |  AI Controller |
|                |      |                |      |                |
+----------------+      +----------------+      +----------------+
                                |                      |
                                v                      v
                        +----------------+      +----------------+
                        |                |      |                |
                        |    Database    | <--> |    Position    |
                        |                |      |    Manager     |
                        +----------------+      |                |
                                |               +----------------+
                                v                      |
                        +----------------+             |
                        |                |             |
                        |   Monitoring   | <-----------+
                        |    System      |
                        |                |
                        +----------------+
                                |
                                v
                        +----------------+
                        |                |
                        |      UI        |
                        |                |
                        +----------------+
```

## Opis komponentów

### MT5 Bridge

Moduł odpowiedzialny za komunikację z platformą MetaTrader 5. Główne funkcje:

- Pobieranie danych rynkowych (ceny, wolumen, wskaźniki)
- Wykonywanie operacji tradingowych (otwieranie, modyfikacja, zamykanie pozycji)
- Synchronizacja stanu konta i pozycji
- Obsługa zdarzeń rynkowych

### AI Controller

Moduł zarządzający modelami sztucznej inteligencji. Główne funkcje:

- Integracja z zewnętrznymi API modeli AI (Claude, Grok, DeepSeek)
- Przygotowanie danych dla modeli AI
- Interpretacja wyników i generowanie sygnałów tradingowych
- Adaptacja strategii na podstawie wyników historycznych

### Position Manager

Moduł zarządzający pozycjami i ryzykiem. Główne funkcje:

- Implementacja strategii zarządzania pozycjami
- Kontrola ryzyka (wielkość pozycji, stop-loss, take-profit)
- Monitorowanie otwartych pozycji
- Optymalizacja wejść i wyjść z rynku

### Monitoring System

Moduł monitorujący wyniki i generujący alerty. Główne funkcje:

- Śledzenie wyników tradingowych
- Generowanie raportów wydajności
- Wykrywanie anomalii i generowanie alertów
- Archiwizacja danych historycznych

### User Interface

Interfejs użytkownika do kontroli i konfiguracji systemu. Główne funkcje:

- Wizualizacja danych rynkowych i wyników
- Konfiguracja parametrów systemu
- Ręczne sterowanie operacjami (w razie potrzeby)
- Dostęp do raportów i alertów

## Przepływ danych

1. MT5 Bridge pobiera dane rynkowe z platformy MetaTrader 5
2. Dane są przetwarzane i przechowywane w bazie danych
3. AI Controller analizuje dane i generuje sygnały tradingowe
4. Position Manager podejmuje decyzje o otwarciu, modyfikacji lub zamknięciu pozycji
5. MT5 Bridge wykonuje operacje tradingowe na platformie MetaTrader 5
6. Monitoring System śledzi wyniki i generuje raporty
7. User Interface prezentuje dane i umożliwia interakcję z systemem

## Technologie

- **Backend**: Python 3.10+, FastAPI
- **Baza danych**: PostgreSQL
- **Komunikacja z MT5**: MetaTrader 5 API, ZeroMQ
- **AI**: Claude API, Grok API, DeepSeek API
- **Frontend**: React, TypeScript, Material-UI 