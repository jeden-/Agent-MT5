# Dokumentacja Projektu AgentMT5

## Spis dokumentacji

### 1. Dokumentacja techniczna
- [Dokumentacja techniczna systemu](DOKUMENTACJA_TECHNICZNA.md) - Szczegółowy opis architektury i komponentów systemu
- [Integracja z MetaTrader 5](MT5_INTEGRACJA.md) - Opis metod komunikacji z platformą MT5
- [Modele AI](AI_MODELS.md) - Dokumentacja modeli AI wykorzystywanych w systemie

### 2. Przewodniki
- Instalacja i konfiguracja systemu (do napisania)
- Rozwiązywanie problemów (do napisania)
- Przewodnik użytkownika (do napisania)

### 3. Specyfikacje API
- Dokumentacja API MT5Bridge (do napisania)
- Specyfikacja interfejsów komunikacyjnych (do napisania)

### 4. Szczegółowe informacje o modułach
- Dokumentacja modułu zarządzania pozycjami (do napisania)
- Dokumentacja modułu zarządzania ryzykiem (do napisania)
- Dokumentacja modułu analizy rynku (do napisania)

## Struktura projektu

```
AgentMT5/
├── src/                      # Kod źródłowy
│   ├── ai_models/            # Modele AI
│   ├── database/             # Baza danych
│   ├── monitoring/           # Monitoring
│   ├── mt5_bridge/           # Most MT5
│   ├── mt5_ea/               # Expert Advisor
│   ├── position_management/  # Zarządzanie pozycjami
│   ├── risk_management/      # Zarządzanie ryzykiem
│   ├── ui/                   # Interfejs użytkownika
│   └── utils/                # Narzędzia
├── docs/                     # Dokumentacja
├── scripts/                  # Skrypty
├── tests/                    # Testy
├── config/                   # Konfiguracja
└── README.md                 # Główny plik README
```

## Jak korzystać z dokumentacji

1. Zacznij od [dokumentacji technicznej](DOKUMENTACJA_TECHNICZNA.md), aby zrozumieć ogólną architekturę systemu.
2. Następnie zapoznaj się z dokumentacją dotyczącą [integracji z MT5](MT5_INTEGRACJA.md) i [modeli AI](AI_MODELS.md).
3. Szczegółowe informacje o poszczególnych modułach znajdziesz w odpowiednich sekcjach dokumentacji.

## Utrzymanie dokumentacji

Dokumentacja jest aktualizowana równolegle z rozwojem kodu. Jeśli zauważysz rozbieżności między dokumentacją a faktycznym działaniem systemu, zgłoś to w sekcji Issues.

## Wkład w dokumentację

Zachęcamy do wkładu w rozwój dokumentacji. Aby to zrobić:
1. Sklonuj repozytorium
2. Wprowadź zmiany w odpowiednich plikach markdownowych
3. Utwórz Pull Request z opisem wprowadzonych zmian 