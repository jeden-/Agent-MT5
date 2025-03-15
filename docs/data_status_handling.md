# Obsługa statusów danych w interfejsie AgentMT5

## Wprowadzenie

Interfejs użytkownika AgentMT5 wyświetla dane z różnych źródeł, które mogą mieć różny status. System obsługi statusów danych zapewnia jednolity sposób informowania użytkownika o stanie danych, które są prezentowane w interfejsie. Pozwala to na lepsze zrozumienie, czy dane są rzeczywiste, demonstracyjne, czy wystąpił błąd podczas ich pobierania.

## Rodzaje statusów danych

System rozróżnia następujące statusy danych:

1. **ok** - dane rzeczywiste pobrane z systemu
2. **demo** - dane demonstracyjne, używane gdy rzeczywiste dane nie są dostępne
3. **no_data** - brak danych (np. gdy system jeszcze nie wygenerował żadnych sygnałów)
4. **error** - błąd podczas pobierania danych

## Implementacja w API

Endpointy API serwera MT5 Bridge zwracają dane wraz z informacją o ich statusie. Przykładowa struktura odpowiedzi:

```json
{
  "status": "ok", // lub "demo", "no_data", "error"
  "message": "Opcjonalny komunikat wyjaśniający status",
  "timestamp": "2025-03-14T12:34:56Z",
  "data": { ... } // dane właściwe dla endpointu
}
```

### Przykład: Endpoint `/ai/models`

```json
{
  "status": "demo",
  "message": "Wyświetlane są dane demonstracyjne. Rzeczywiste dane będą dostępne po wykonaniu zapytań do modeli AI.",
  "timestamp": "2025-03-14T12:34:56Z",
  "models": [
    {
      "name": "Claude-3",
      "accuracy": 0.78,
      "roi": 0.12
    },
    {
      "name": "Grok-1",
      "accuracy": 0.65,
      "roi": 0.08
    }
  ]
}
```

## Implementacja w interfejsie użytkownika

### Wizualne oznaczenie statusu

Każdy status jest wizualnie oznaczony w interfejsie:

- **ok** - brak specjalnego oznaczenia (dane są wyświetlane normalnie)
- **demo** - pomarańczowy banner/obramowanie z komunikatem o danych demonstracyjnych
- **no_data** - niebieski banner/obramowanie z komunikatem o braku danych
- **error** - czerwony banner/obramowanie z komunikatem o błędzie

### Szczegółowe komunikaty

Dla każdego statusu, interfejs wyświetla odpowiedni komunikat:

#### Dane demonstracyjne (demo)

```
Wyświetlane są dane demonstracyjne. Rzeczywiste dane będą dostępne po wykonaniu zapytań do modeli AI.

Aby zacząć gromadzić rzeczywiste dane:
1. Aktywuj modele AI w ustawieniach agenta
2. Przełącz agenta w tryb automatyczny lub generuj sygnały ręcznie
3. Wykonaj co najmniej kilka transakcji na podstawie wygenerowanych sygnałów
```

#### Brak danych (no_data)

```
Brak danych do wyświetlenia. System nie wygenerował jeszcze żadnych sygnałów.

Możliwe przyczyny:
1. Agent został niedawno uruchomiony
2. Agent nie znalazł jeszcze żadnych okazji handlowych
3. Modele AI nie są aktywowane

Sprawdź ustawienia agenta w zakładce Control Panel.
```

#### Błąd (error)

```
Wystąpił błąd podczas pobierania danych: [szczegóły błędu].

Możliwe przyczyny:
1. Problem z połączeniem z serwerem MT5
2. Błąd wewnętrzny systemu
3. Brak uprawnień do dostępu do danych

Spróbuj odświeżyć stronę lub sprawdź logi systemu.
```

## Implementacja w kodzie

### Endpoint `/ai/models` w `src/mt5_bridge/server.py`

Przykładowa implementacja endpointu z obsługą różnych statusów:

```python
@app.get("/ai/models")
async def get_ai_models():
    """Pobiera informacje o modelach AI i ich wydajności."""
    try:
        # Próba pobrania rzeczywistych danych
        ai_monitor = get_ai_monitor()
        if ai_monitor:
            models_stats = ai_monitor.get_models_statistics()
            
            if models_stats and len(models_stats) > 0:
                # Mamy rzeczywiste dane
                return {
                    "status": "ok",
                    "timestamp": datetime.now().isoformat(),
                    "models": models_stats
                }
            else:
                # Nie ma jeszcze danych
                return {
                    "status": "no_data",
                    "message": "Brak danych o modelach AI. Aby rozpocząć zbieranie danych, aktywuj modele AI w ustawieniach agenta.",
                    "timestamp": datetime.now().isoformat(),
                    "models": []
                }
        
        # Jeśli nie udało się pobrać danych, wyświetl dane demonstracyjne
        demo_data = get_demo_ai_models_data()
        return {
            "status": "demo",
            "message": "Wyświetlane są dane demonstracyjne. Rzeczywiste dane będą dostępne po wykonaniu zapytań do modeli AI.",
            "timestamp": datetime.now().isoformat(),
            "models": demo_data
        }
    except Exception as e:
        # W przypadku błędu, zwróć informację o błędzie
        logger.error(f"Błąd podczas pobierania danych o modelach AI: {str(e)}")
        return {
            "status": "error",
            "message": f"Wystąpił błąd podczas pobierania danych o modelach AI: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "models": []
        }
```

### Obsługa w interfejsie użytkownika (`src/ui/app.py`)

```python
def render_ai_analytics():
    """Renderuje zakładkę AI Analytics."""
    # Pobierz dane o modelach AI
    ai_models_data = api_request("ai/models")
    
    if ai_models_data and "status" in ai_models_data:
        status = ai_models_data.get("status", "")
        
        # Obsługa różnych statusów
        if status == "error":
            st.error("Nie udało się pobrać danych o modelach AI")
            st.info(ai_models_data.get("message", "Sprawdź połączenie z serwerem."))
        elif status == "demo":
            st.warning("Wyświetlane są dane demonstracyjne")
            st.info(ai_models_data.get("message", "Rzeczywiste dane będą dostępne po wykonaniu zapytań do modeli AI."))
            
            # Wyświetl dane demonstracyjne z wyraźnym oznaczeniem
            st.markdown("""
            <div style="border-left: 4px solid orange; padding-left: 10px; background-color: rgba(255, 165, 0, 0.1); padding: 10px; border-radius: 5px; margin-bottom: 15px;">
              <h4 style="margin-top: 0;">Dane Demonstracyjne</h4>
              <p>Poniższe wykresy i tabele pokazują <b>przykładowe</b> dane. Rzeczywiste dane będą widoczne gdy agent zacznie używać modeli AI.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Wyświetl dane demonstracyjne
            models_info = ai_models_data.get("models", [])
            if models_info:
                # Kod wyświetlania danych...
            else:
                st.info("Brak danych o modelach AI")
        elif status == "no_data":
            st.info("Nie udało się pobrać danych o modelach AI")
            st.markdown("""
            <div style="border-left: 4px solid blue; padding-left: 10px; background-color: rgba(0, 0, 255, 0.05); padding: 10px; border-radius: 5px; margin-bottom: 15px;">
              <h4 style="margin-top: 0;">Brak Danych</h4>
              <p>System nie wygenerował jeszcze żadnych danych o modelach AI.</p>
              <p>Aby zacząć gromadzić dane:</p>
              <ol>
                <li>Aktywuj modele AI w ustawieniach agenta</li>
                <li>Przełącz agenta w tryb automatyczny lub generuj sygnały ręcznie</li>
                <li>Poczekaj na wygenerowanie pierwszych sygnałów</li>
              </ol>
            </div>
            """, unsafe_allow_html=True)
        elif status == "ok":
            # Wyświetl rzeczywiste dane
            models_info = ai_models_data.get("models", [])
            if models_info:
                # Kod wyświetlania danych...
            else:
                st.info("Brak danych o modelach AI")
        else:
            st.warning("Nieznany status danych o modelach AI: " + status)
            st.info("Sprawdź połączenie z serwerem lub skontaktuj się z administratorem.")
    else:
        st.warning("Nie można pobrać danych o modelach AI")
```

## Zalecenia dotyczące obsługi statusów

1. **Jednolitość** - wszystkie endpointy API powinny zwracać dane w jednolitym formacie z informacją o statusie
2. **Czytelność** - komunikaty powinny być czytelne i zrozumiałe dla użytkownika
3. **Instrukcje** - komunikaty powinny zawierać instrukcje, jak rozwiązać problem lub rozpocząć zbieranie rzeczywistych danych
4. **Wizualne oznaczenie** - status danych powinien być wizualnie oznaczony w interfejsie
5. **Obsługa błędów** - wszystkie błędy powinny być obsługiwane i wyświetlane w przyjazny sposób

## Typowe przypadki użycia

### Pierwsze uruchomienie systemu

Przy pierwszym uruchomieniu systemu, dane są niedostępne, więc interfejs wyświetla dane demonstracyjne lub informacje o braku danych. Użytkownik jest informowany, jak rozpocząć zbieranie rzeczywistych danych.

### Rozwój systemu

W miarę korzystania z systemu, dane demonstracyjne są stopniowo zastępowane rzeczywistymi danymi. Interfejs automatycznie przełącza się na wyświetlanie rzeczywistych danych, gdy stają się one dostępne.

### Problemy z połączeniem

W przypadku problemów z połączeniem z serwerem MT5 Bridge, interfejs wyświetla komunikaty o błędach z instrukcjami, jak rozwiązać problem.

## Podsumowanie

System obsługi statusów danych zapewnia jednolity sposób informowania użytkownika o stanie danych prezentowanych w interfejsie. Dzięki temu użytkownik ma pełną świadomość, czy dane są rzeczywiste, demonstracyjne, czy wystąpił błąd podczas ich pobierania. System ułatwia także rozwiązywanie problemów i rozpoczęcie zbierania rzeczywistych danych. 