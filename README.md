# AgentMT5 - System automatycznego handlu z wykorzystaniem sztucznej inteligencji

## Opis projektu

AgentMT5 to zaawansowany system automatycznego handlu wykorzystujący sztuczną inteligencję do analizy rynku i podejmowania decyzji tradingowych. Projekt integruje zaawansowane modele AI (Claude, Grok, DeepSeek) z platformą MetaTrader 5, zapewniając autonomiczne zarządzanie pozycjami przy zachowaniu ścisłej kontroli ryzyka.

## Cele projektu

Głównym celem projektu jest stworzenie systemu, który:
- Wykorzystuje zaawansowane algorytmy AI do analizy rynku finansowego
- Automatycznie podejmuje decyzje tradingowe oparte na analizie danych
- Zarządza ryzykiem i pozycjami w sposób autonomiczny
- Dąży do podwojenia powierzonego kapitału w możliwie najkrótszym czasie
- Zapewnia stabilną i niezawodną komunikację między MT5 a silnikiem AI

## Komponenty systemu

System składa się z następujących komponentów:

### Expert Advisor (EA) dla MetaTrader 5
- Znajduje się w katalogu `src/mt5_ea/`
- Odpowiada za bezpośrednią interakcję z platformą tradingową
- Zbiera dane rynkowe i wykonuje operacje handlowe
- Komunikuje się z serwerem poprzez gniazda (sockets)

### Serwer komunikacyjny
- Znajduje się w katalogu `src/server/`
- Obsługuje komunikację między EA a silnikiem AI
- Zapewnia trwałe połączenie i przetwarzanie komunikatów
- Dostępne są różne implementacje serwera (standardowy, persistentny, keep-alive)

### Silnik AI
- Analizuje dane rynkowe dostarczone przez EA
- Generuje sygnały i rekomendacje handlowe
- Wykorzystuje zaawansowane modele uczenia maszynowego

## Aktualny status projektu

Na ten moment zrealizowano:

1. **Expert Advisor (EA) dla MetaTrader 5**:
   - Podstawowa struktura EA z obsługą komunikacji socket
   - Mechanizm inicjalizacji, deinicjalizacji i obsługi timera
   - Funkcje wysyłania i odbierania danych
   - Obsługa podstawowych operacji handlowych

2. **Serwer komunikacyjny**:
   - Implementacja podstawowego serwera socket
   - Alternatywne implementacje z obsługą trwałego połączenia
   - Obsługa protokołu komunikacyjnego

3. **Narzędzia diagnostyczne**:
   - Skrypty do testowania połączenia
   - Monitorowanie stanu komunikacji

## Problemy i wyzwania

Aktualnie trwają prace nad stabilizacją połączenia socket między EA a serwerem. Zidentyfikowane problemy:
- Socket rozłącza się po krótkim czasie komunikacji
- Potrzebne są mechanizmy keep-alive i ponownego łączenia
- Wymaga poprawy obsługa błędów i wyjątków

## Instrukcja użycia

1. Skompiluj EA z katalogu `src/mt5_ea/AgentMT5_EA.mq5` w MetaEditor
2. Uruchom jeden z serwerów komunikacyjnych:
   ```
   python scripts/run_mt5_server.py
   ```
   lub
   ```
   python scripts/persistent_mt5_server.py
   ```
3. Załaduj skompilowany EA na wykres w MetaTrader 5
4. Skonfiguruj parametry EA (adres serwera, port, interwały)

## Plany rozwoju

W najbliższej przyszłości planowane są:
- Stabilizacja połączenia socket między EA a serwerem
- Integracja zaawansowanych algorytmów AI
- Rozwój mechanizmów zarządzania ryzykiem
- Testy z wykorzystaniem danych historycznych
- Implementacja automatycznego dostrajania parametrów

## Licencja

Projekt jest własnością prywatną. Wszelkie prawa zastrzeżone.