# Instrukcja użytkowania

## Uruchamianie systemu

Aby uruchomić system AgentMT5, wykonaj następujące kroki:

1. Aktywuj środowisko wirtualne:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. Uruchom główny skrypt aplikacji:
   ```bash
   python main.py
   ```

3. Otwórz przeglądarkę i przejdź do adresu:
   ```
   http://127.0.0.1:8502/
   ```

## Interfejs użytkownika

### Panel główny

Panel główny zawiera następujące sekcje:

- **Przegląd konta** - informacje o stanie konta, dostępnych środkach i marży
- **Aktywne pozycje** - lista otwartych pozycji z możliwością zarządzania
- **Historia transakcji** - historia ostatnich transakcji
- **Analiza AI** - wyniki analizy rynku przez modele AI
- **Alerty** - lista aktywnych alertów i powiadomień

### Zarządzanie pozycjami

Aby zarządzać pozycjami:

1. Przejdź do sekcji "Aktywne pozycje"
2. Wybierz pozycję, którą chcesz zarządzać
3. Dostępne opcje:
   - Modyfikacja Stop Loss / Take Profit
   - Częściowe zamknięcie pozycji
   - Pełne zamknięcie pozycji
   - Dodanie trailingu

### Konfiguracja strategii

Aby skonfigurować strategię handlową:

1. Przejdź do sekcji "Ustawienia" -> "Strategie"
2. Wybierz model AI do wykorzystania
3. Ustaw parametry strategii:
   - Maksymalna wielkość pozycji
   - Poziomy Stop Loss / Take Profit
   - Instrumenty do handlu
   - Godziny handlu
4. Zapisz konfigurację

### Monitorowanie wyników

Aby monitorować wyniki:

1. Przejdź do sekcji "Raporty"
2. Wybierz zakres dat
3. Dostępne raporty:
   - Wyniki finansowe
   - Statystyki transakcji
   - Wydajność modeli AI
   - Dziennik operacji

## Tryby pracy

System może działać w trzech trybach:

### Tryb obserwacji

W tym trybie system analizuje rynek i generuje sygnały, ale nie otwiera pozycji automatycznie. Użytkownik musi ręcznie zatwierdzić każdą transakcję.

Aby aktywować:
```
Ustawienia -> Tryb pracy -> Obserwacja
```

### Tryb półautomatyczny

W tym trybie system automatycznie otwiera pozycje, ale wymaga zatwierdzenia zamknięcia pozycji przez użytkownika.

Aby aktywować:
```
Ustawienia -> Tryb pracy -> Półautomatyczny
```

### Tryb automatyczny

W tym trybie system działa całkowicie autonomicznie, otwierając i zamykając pozycje bez ingerencji użytkownika.

Aby aktywować:
```
Ustawienia -> Tryb pracy -> Automatyczny
```

## Rozwiązywanie problemów

### Problem: System nie łączy się z MT5

**Rozwiązanie:**
1. Sprawdź, czy MetaTrader 5 jest uruchomiony
2. Sprawdź, czy EA jest aktywny na wykresie
3. Zweryfikuj dane logowania w pliku `.env`
4. Sprawdź logi w pliku `mt5remoteai.log`

### Problem: Błędy w analizie AI

**Rozwiązanie:**
1. Sprawdź połączenie z API modeli AI
2. Zweryfikuj klucze API w pliku `.env`
3. Sprawdź logi w sekcji "Logi" -> "AI Controller"

### Problem: Nieoczekiwane zachowanie systemu

**Rozwiązanie:**
1. Zatrzymaj system (`Ctrl+C` w terminalu)
2. Sprawdź logi w pliku `mt5remoteai.log`
3. Uruchom system ponownie
4. Jeśli problem się powtarza, przełącz na tryb obserwacji 