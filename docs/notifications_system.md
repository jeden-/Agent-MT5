# Dokumentacja Techniczna Systemu Powiadomień

## Spis treści
1. [Wprowadzenie](#wprowadzenie)
2. [Architektura Systemu Powiadomień](#architektura-systemu-powiadomień)
3. [Obsługiwane Typy Powiadomień](#obsługiwane-typy-powiadomień)
4. [Kanały Powiadomień](#kanały-powiadomień)
   - [Email](#email)
   - [Discord](#discord)
5. [Konfiguracja](#konfiguracja)
6. [Integracja z Generatorem Sygnałów](#integracja-z-generatorem-sygnałów)
7. [Jak Użyć w Kodzie](#jak-użyć-w-kodzie)
8. [Testowanie](#testowanie)
9. [Rozszerzanie Systemu](#rozszerzanie-systemu)

## Wprowadzenie

System powiadomień jest odpowiedzialny za wysyłanie alertów o ważnych wydarzeniach, takich jak nowe sygnały handlowe, wykonane transakcje, błędy systemu itp. System wspiera wiele kanałów doręczania powiadomień, aktualnie w tym email i Discord.

## Architektura Systemu Powiadomień

System powiadomień składa się z kilku głównych komponentów:

1. **NotificationManager** - centralny punkt zarządzania powiadomieniami, odpowiedzialny za routing powiadomień do odpowiednich kanałów.
2. **Notyfikatory** - klasy odpowiedzialne za wysyłanie powiadomień przez konkretne kanały komunikacji (EmailNotifier, DiscordNotifier).
3. **Typy powiadomień** - zdefiniowane jako enumy w klasie NotificationType.
4. **Inicjalizator** - moduł odpowiedzialny za inicjalizację systemu na podstawie konfiguracji.

## Obsługiwane Typy Powiadomień

System obsługuje następujące typy powiadomień:

- `NEW_SIGNAL` - powiadomienie o nowym sygnale handlowym
- `SIGNAL_EXPIRED` - powiadomienie o wygaśnięciu sygnału handlowego
- `SIGNAL_EXECUTED` - powiadomienie o wykonaniu sygnału handlowego
- `ERROR` - powiadomienie o błędzie w systemie
- `WARNING` - powiadomienie o ostrzeżeniu
- `SYSTEM` - powiadomienie systemowe
- `BALANCE_CHANGE` - powiadomienie o zmianie salda
- `POSITION_OPENED` - powiadomienie o otwarciu pozycji
- `POSITION_CLOSED` - powiadomienie o zamknięciu pozycji

Każdy typ powiadomienia ma przypisany unikatowy emoji i kolor dla lepszej identyfikacji wizualnej.

## Kanały Powiadomień

### Email

Kanał email wykorzystuje protokół SMTP do wysyłania wiadomości email. Wysyłane wiadomości zawierają:
- Temat z prefiksem odpowiadającym typowi powiadomienia (np. "🔔 [AgentMT5] Nowy sygnał BUY dla EURUSD (M15)")
- Treść zawierającą szczegóły powiadomienia
- Informacje o nadawcy i odbiorcy

### Discord

Kanał Discord wykorzystuje webhooks Discord do wysyłania wiadomości na serwer Discord. Wysyłane wiadomości zawierają:
- Embed z tytułem zawierającym emoji odpowiadający typowi powiadomienia
- Opis zawierający treść powiadomienia
- Pola zawierające dodatkowe szczegóły (np. cena wejścia, stop loss, take profit)
- Kolor odpowiadający typowi powiadomienia
- Stopkę z datą i godziną wygenerowania powiadomienia

## Konfiguracja

System powiadomień jest konfigurowany za pomocą pliku YAML znajdującego się w `src/config/notifications_config.yaml`. Plik ten zawiera:

1. **Włączone typy powiadomień**:
```yaml
enabled_notification_types:
  - new_signal
  - signal_executed
  - position_opened
  - position_closed
  - error
  - warning
```

2. **Konfiguracja email**:
```yaml
email:
  enabled: true  # Czy powiadomienia email są włączone
  smtp_server: "smtp.example.com"  # Adres serwera SMTP
  smtp_port: 587  # Port serwera SMTP
  username: "user@example.com"  # Nazwa użytkownika
  password: "your-password"  # Hasło
  sender_email: "agent-mt5@example.com"  # Adres nadawcy
  recipient_emails:  # Lista adresów odbiorców
    - "recipient1@example.com"
    - "recipient2@example.com"
  use_ssl: false  # Czy używać SSL
  use_tls: true  # Czy używać TLS
```

3. **Konfiguracja Discord**:
```yaml
discord:
  enabled: true  # Czy powiadomienia Discord są włączone
  webhook_url: "https://discord.com/api/webhooks/your-webhook-url"  # URL webhooka Discord
  username: "AgentMT5"  # Nazwa użytkownika wyświetlana na Discord
  avatar_url: "https://example.com/agent-mt5-logo.png"  # URL do avatara (opcjonalne)
```

4. **Ogólne ustawienia**:
```yaml
general:
  include_ai_analysis: true  # Czy dołączać analizę AI do powiadomień
  max_analysis_length: 500  # Maksymalna długość analizy AI w powiadomieniach
  include_charts: false  # Czy dołączać wykresy do powiadomień (funkcja przyszła)
```

## Integracja z Generatorem Sygnałów

System powiadomień jest zintegrowany z generatorem sygnałów handlowych. Gdy generator tworzy nowy sygnał, automatycznie wysyłane jest powiadomienie o nowym sygnale. Integracja odbywa się w metodzie `generate_signal_from_data` klasy `SignalGenerator`, która po zapisaniu sygnału do bazy danych wywołuje metodę `send_notification`.

## Jak Użyć w Kodzie

Aby wysłać powiadomienie z dowolnego miejsca w kodzie, należy:

```python
from src.notifications.notification_manager import get_notification_manager, NotificationType

# Pobierz instancję menedżera powiadomień
notification_manager = get_notification_manager()

# Wysłanie prostego powiadomienia
notification_manager.send_notification(
    NotificationType.SYSTEM,
    "Tytuł powiadomienia",
    "Treść powiadomienia",
    {"key1": "value1", "key2": "value2"}  # Opcjonalne szczegóły
)

# Wysłanie powiadomienia o nowym sygnale handlowym
from src.database.models import TradingSignal

# Pobierz lub utwórz obiekt sygnału handlowego
signal = TradingSignal(...)

# Wyślij powiadomienie o nowym sygnale
notification_manager.notify_new_signal(signal)
```

## Testowanie

System powiadomień można przetestować za pomocą skryptu `test_notifications.py` znajdującego się w głównym katalogu projektu. Skrypt ten:

1. Tworzy tymczasową konfigurację powiadomień
2. Inicjalizuje system powiadomień
3. Rejestruje testowy notyfikator, który zamiast wysyłać powiadomienia, loguje je
4. Wysyła testowe powiadomienia różnych typów
5. Tworzy testowy sygnał handlowy i wysyła powiadomienie o nim

## Rozszerzanie Systemu

System powiadomień można łatwo rozszerzyć o nowe kanały doręczania powiadomień, tworząc nowe klasy implementujące interfejs notyfikatora. Każdy notyfikator musi implementować metodę `send_notification` przyjmującą następujące parametry:

- `notification_type: NotificationType` - typ powiadomienia
- `subject: str` - temat powiadomienia
- `message: str` - treść powiadomienia
- `details: Optional[Dict[str, Any]]` - dodatkowe szczegóły (opcjonalne)

Przykład implementacji nowego notyfikatora:

```python
class SMSNotifier:
    def __init__(self, api_key, phone_numbers):
        self.api_key = api_key
        self.phone_numbers = phone_numbers
    
    def send_notification(self, notification_type, subject, message, details=None):
        # Implementacja wysyłania SMS
        # ...
        return True  # Zwraca True jeśli wysłanie powiodło się
```

Po stworzeniu nowego notyfikatora, należy zarejestrować go w menedżerze powiadomień:

```python
notification_manager = get_notification_manager()
sms_notifier = SMSNotifier(api_key="your-api-key", phone_numbers=["123456789"])
notification_manager.register_notifier("sms", sms_notifier)
notification_manager.enable_notifier("sms")
``` 