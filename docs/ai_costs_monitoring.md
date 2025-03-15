# Monitorowanie kosztów API modeli AI

## Wprowadzenie

System AgentMT5 wykorzystuje zewnętrzne API modeli AI (Claude, Grok, DeepSeek) do generowania sygnałów tradingowych. Korzystanie z tych API wiąże się z kosztami, które są zależne od liczby i typu zapytań. Moduł monitorowania kosztów API pozwala na śledzenie i analizę tych kosztów w czasie rzeczywistym.

## Architektura systemu monitorowania kosztów

System monitorowania kosztów API składa się z następujących komponentów:

1. **Kolektor kosztów** - zbiera informacje o każdym zapytaniu do API
2. **Repozytorium kosztów** - przechowuje dane o kosztach w bazie danych
3. **Analizator kosztów** - analizuje koszty i generuje raporty
4. **Interfejs użytkownika** - wyświetla informacje o kosztach

## Dane gromadzone przez system

Dla każdego zapytania do API modeli AI, system gromadzi następujące informacje:

- **Model** - nazwa modelu AI (np. Claude-3, Grok-1, DeepSeek)
- **Timestamp** - data i czas zapytania
- **Rodzaj zapytania** - typ zapytania (generowanie sygnału, analiza rynku, itp.)
- **Instrument** - instrument finansowy, którego dotyczyło zapytanie
- **Timeframe** - ramy czasowe analizy
- **Liczba tokenów wejściowych** - liczba tokenów w zapytaniu
- **Liczba tokenów wyjściowych** - liczba tokenów w odpowiedzi
- **Koszt** - koszt zapytania w USD/EUR
- **Status** - status zapytania (sukces, błąd, itp.)

## Analiza kosztów

System analizuje zgromadzone dane i generuje następujące informacje:

- **Całkowity koszt** - suma kosztów wszystkich zapytań
- **Koszty per model** - suma kosztów zapytań dla każdego modelu
- **Koszty per instrument** - suma kosztów zapytań dla każdego instrumentu
- **Koszty w czasie** - wykres kosztów w czasie (dzienny, tygodniowy, miesięczny)
- **Prognoza kosztów** - przewidywane koszty na koniec miesiąca
- **Średni koszt per sygnał** - średni koszt generowania jednego sygnału

## Implementacja w systemie

### Endpoint API `/ai/costs`

Endpoint `/ai/costs` w serwisie MT5 Bridge zwraca informacje o kosztach wykorzystania API modeli AI. Endpoint zwraca dane w następującym formacie:

```json
{
  "status": "ok",
  "total_cost": 12.34,
  "currency": "USD",
  "period": "month",
  "start_date": "2025-03-01",
  "end_date": "2025-03-14",
  "forecast_end_month": 25.67,
  "models": [
    {
      "name": "Claude-3",
      "cost": 7.89,
      "requests": 120,
      "avg_cost_per_request": 0.065
    },
    {
      "name": "Grok-1",
      "cost": 3.45,
      "requests": 80,
      "avg_cost_per_request": 0.043
    },
    {
      "name": "DeepSeek",
      "cost": 1.00,
      "requests": 50,
      "avg_cost_per_request": 0.020
    }
  ],
  "daily_costs": [
    {
      "date": "2025-03-01",
      "cost": 0.87
    },
    {
      "date": "2025-03-02",
      "cost": 1.23
    },
    // ...pozostałe dni
  ]
}
```

### Implementacja w interfejsie użytkownika

W zakładce AI Analytics, dane o kosztach API są wyświetlane w następujący sposób:

1. **Podsumowanie kosztów** - całkowity koszt w bieżącym miesiącu i prognoza na koniec miesiąca
2. **Wykres kosztów w czasie** - liniowy wykres dziennych kosztów
3. **Tabela kosztów per model** - tabela z kosztami dla każdego modelu
4. **Wykres kosztów per model** - kołowy wykres pokazujący udział kosztów dla każdego modelu

## Limity kosztów i alerty

System umożliwia ustawienie limitów kosztów i generowanie alertów, gdy koszty przekroczą określony próg:

- **Dzienny limit** - maksymalny koszt dzienny
- **Miesięczny limit** - maksymalny koszt miesięczny
- **Limit per model** - maksymalny koszt dla konkretnego modelu

Gdy koszty przekroczą 80% limitu, system generuje alert ostrzegawczy. Gdy koszty przekroczą 100% limitu, system generuje alert krytyczny i może automatycznie ograniczyć wykorzystanie API.

## Optymalizacja kosztów

Na podstawie analizy kosztów, system może rekomendować optymalizacje, takie jak:

- Zmiana modelu AI dla konkretnych instrumentów
- Zmiana częstotliwości zapytań
- Optymalizacja promptów dla zmniejszenia liczby tokenów
- Wybór najbardziej efektywnych kosztowo modeli dla konkretnych typów analiz

## Przykładowa konfiguracja limitów kosztów

Limity kosztów można skonfigurować w pliku konfiguracyjnym systemu:

```toml
[ai_costs]
daily_limit = 5.0  # USD
monthly_limit = 100.0  # USD
alert_threshold = 0.8  # 80% limitu

[ai_costs.models]
claude = 50.0  # USD
grok = 30.0  # USD
deepseek = 20.0  # USD
```

## Zarządzanie kosztami w przypadku problemów

W przypadku problemów z kosztami API (np. przekroczenie limitów), system może podejmować następujące działania:

1. **Automatyczne przełączanie na tańsze modele** - system może przełączyć się na tańsze modele AI
2. **Zmniejszenie częstotliwości zapytań** - system może zmniejszyć częstotliwość generowania sygnałów
3. **Przełączenie w tryb offline** - system może przełączyć się w tryb offline i korzystać tylko z lokalnych modeli
4. **Wstrzymanie generowania nowych sygnałów** - system może wstrzymać generowanie nowych sygnałów do czasu ręcznego potwierdzenia przez użytkownika

## Integracja z systemem monitorowania

System monitorowania kosztów API jest zintegrowany z ogólnym systemem monitorowania AgentMT5. Alerty dotyczące kosztów są wyświetlane w zakładce System Status wraz z innymi alertami systemowymi.

## Dostęp do danych historycznych

Dane historyczne o kosztach API są przechowywane w bazie danych i mogą być wyeksportowane do plików CSV lub JSON. Użytkownik może przeglądać historyczne dane o kosztach za pomocą interfejsu web.

## Podsumowanie

System monitorowania kosztów API modeli AI zapewnia pełną kontrolę nad wydatkami związanymi z wykorzystaniem zewnętrznych API. Dzięki temu użytkownik może optymalizować strategię wykorzystania modeli AI i kontrolować budżet. 