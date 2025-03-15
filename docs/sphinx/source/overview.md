# Przegląd projektu AgentMT5

## Cel projektu

AgentMT5 to system automatycznego handlu wykorzystujący sztuczną inteligencję do analizy rynku i podejmowania decyzji tradingowych. Agent integruje zaawansowane modele AI (Claude, Grok, DeepSeek) z platformą MetaTrader 5, zapewniając autonomiczne zarządzanie pozycjami przy zachowaniu ścisłej kontroli ryzyka. Celem głównym Agenta jest jak najszybsze podwojenie powierzonego kapitału.

## Główne funkcjonalności

- Integracja z platformą MetaTrader 5
- Wykorzystanie zaawansowanych modeli AI do analizy rynku
- Automatyczne podejmowanie decyzji tradingowych
- Zarządzanie pozycjami i ryzykiem
- Monitorowanie wyników i generowanie raportów
- Interfejs użytkownika do kontroli i konfiguracji systemu

## Architektura systemu

System składa się z następujących głównych komponentów:

1. **MT5 Bridge** - moduł komunikacji z platformą MetaTrader 5
2. **AI Controller** - moduł zarządzający modelami AI i ich predykcjami
3. **Position Manager** - moduł zarządzania pozycjami i ryzykiem
4. **Monitoring System** - moduł monitorowania wyników i generowania alertów
5. **User Interface** - interfejs użytkownika do kontroli i konfiguracji systemu

## Technologie

- Python 3.10+
- MetaTrader 5 API
- FastAPI
- PostgreSQL
- Modele AI:
  - Claude API (zewnętrzne API)
  - Grok API (zewnętrzne API)
  - DeepSeek (lokalnie przez Ollama, model: deepseek-r1:8b)
- React (interfejs użytkownika)

## Repozytorium

Kod źródłowy projektu jest dostępny na GitHubie:
[https://github.com/jeden-/AgentMT5](https://github.com/jeden-/AgentMT5)

## Status projektu

Projekt jest w fazie aktywnego rozwoju, z funkcjonującymi podstawowymi komponentami. Trwają prace nad integracją zaawansowanych modeli AI i optymalizacją strategii tradingowych. 