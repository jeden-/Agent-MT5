# Modele AI w AgentMT5

## 1. Wstęp

System AgentMT5 wykorzystuje zaawansowane modele sztucznej inteligencji do analizy rynku i podejmowania decyzji tradingowych. Dokumentacja ta opisuje architekturę, implementację i sposób wykorzystania tych modeli w systemie.

## 2. Przegląd architektury AI

AgentMT5 wykorzystuje trzy główne modele AI:

1. **Claude** - model od Anthropic, wykorzystywany do kompleksowej analizy rynku i rozpoznawania wzorców
2. **Grok** - model od xAI, stosowany do prognozowania kierunku rynku i analizy sentymentu
3. **DeepSeek** - model wyspecjalizowany w analizie danych finansowych i rozpoznawaniu wzorców cenowych

System wykorzystuje te modele w architekturze kolektywnej (ensemble), gdzie każdy model dostarcza własnej analizy, a system podejmuje decyzje na podstawie zebranych wyników.

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│     Claude    │     │      Grok     │     │    DeepSeek   │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        └───────────┬─────────┴─────────────┬──────┘
                    │                       │
        ┌───────────▼───────────┐ ┌─────────▼───────────┐
        │      AI Router        │ │    Analiza wyników  │
        │  (Wybór optymalnego   │ │    (Agregacja i     │
        │       modelu)         │ │     ewaluacja)      │
        └───────────┬───────────┘ └─────────┬───────────┘
                    │                       │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Decyzje tradingowe  │
                    │    i zarządzanie      │
                    │      pozycjami        │
                    └───────────────────────┘
```

## 3. Integracja z modelami AI

### 3.1 Claude API (claude_api.py)

Model Claude wykorzystywany jest głównie do:
- Analizy i interpretacji wzorców rynkowych
- Oceny fundamentalnej sytuacji rynkowej
- Analizy korelacji między instrumentami
- Generowania wyjaśnień dla podejmowanych decyzji

```python
# Przykład wywołania Claude API
async def analyze_market_situation(self, market_data, positions_data):
    """
    Analiza ogólnej sytuacji rynkowej przy użyciu Claude API.
    
    Args:
        market_data: Dane rynkowe dla analizowanych instrumentów
        positions_data: Informacje o otwartych pozycjach
        
    Returns:
        Dict: Wynik analizy zawierający ocenę sytuacji rynkowej
    """
    prompt = self._prepare_market_analysis_prompt(market_data, positions_data)
    
    response = await self.client.query(
        prompt=prompt,
        max_tokens=2000,
        temperature=0.2,
        model="claude-3-opus-20240229"
    )
    
    return self._parse_market_analysis_response(response)
```

### 3.2 Grok API (grok_api.py)

Model Grok specjalizuje się w:
- Krótkoterminowych prognozach kierunku rynku
- Analizie sentymentu i emocji rynkowych
- Identyfikacji punktów zwrotnych
- Analizie zmienności i momentów rynku

```python
# Przykład wywołania Grok API
async def predict_price_movement(self, symbol, timeframe, historical_data):
    """
    Prognozowanie ruchu cenowego dla określonego instrumentu.
    
    Args:
        symbol: Symbol instrumentu
        timeframe: Interwał czasowy
        historical_data: Historyczne dane cenowe
        
    Returns:
        Dict: Prognoza ruchu cenowego
    """
    prompt = self._prepare_price_prediction_prompt(symbol, timeframe, historical_data)
    
    response = await self.client.query(
        prompt=prompt,
        max_tokens=1500,
        temperature=0.3,
        model="grok-1"
    )
    
    return self._parse_price_prediction_response(response)
```

### 3.3 DeepSeek API (deepseek_api.py)

Model DeepSeek koncentruje się na:
- Rozpoznawaniu złożonych wzorców cenowych
- Analizie wieloczasowej (multi-timeframe)
- Wykrywaniu anomalii rynkowych
- Identyfikacji silnych obszarów wsparcia/oporu

```python
# Przykład wywołania DeepSeek API
async def identify_price_patterns(self, symbol, multi_timeframe_data):
    """
    Identyfikacja wzorców cenowych na wykresie.
    
    Args:
        symbol: Symbol instrumentu
        multi_timeframe_data: Dane z wielu interwałów czasowych
        
    Returns:
        Dict: Zidentyfikowane wzorce cenowe
    """
    prompt = self._prepare_pattern_recognition_prompt(symbol, multi_timeframe_data)
    
    response = await self.client.query(
        prompt=prompt,
        max_tokens=1800,
        temperature=0.2,
        model="deepseek-r1:8b"
    )
    
    return self._parse_pattern_recognition_response(response)
```

## 4. AI Router (ai_router.py)

AI Router jest kluczowym komponentem systemu, który decyduje, który model AI powinien być użyty dla danego zadania. Router wybiera optymalny model na podstawie:

- Typu zadania (analiza rynku, prognoza, rozpoznanie wzorca)
- Wcześniejszej skuteczności modeli dla danego instrumentu/timeframe'u
- Aktualnego obciążenia i kosztów każdego modelu
- Priorytetu zadania w systemie

```python
# Przykład działania AI Router
async def route_query(self, query_type, data, priority=1):
    """
    Przekierowanie zapytania do optymalnego modelu AI.
    
    Args:
        query_type: Typ zapytania ('market_analysis', 'prediction', 'pattern_recognition')
        data: Dane do analizy
        priority: Priorytet zapytania (1-5)
        
    Returns:
        Dict: Wynik analizy z wybranego modelu AI
    """
    # Ustal najlepszy model dla danego typu zapytania
    model_scores = self._get_model_scores(query_type, data.get('symbol', None))
    
    # Uwzględnij koszty i aktualne obciążenie
    adjusted_scores = self._adjust_scores_by_load_and_cost(model_scores, priority)
    
    # Wybierz model z najwyższą oceną
    best_model = max(adjusted_scores, key=adjusted_scores.get)
    
    # Przekieruj zapytanie do wybranego modelu
    if best_model == 'claude':
        return await self.claude_api.query(query_type, data)
    elif best_model == 'grok':
        return await self.grok_api.query(query_type, data)
    elif best_model == 'deepseek':
        return await self.deepseek_api.query(query_type, data)
    else:
        # Fallback do modelu domyślnego
        return await self.claude_api.query(query_type, data)
```

## 5. Typy analiz i zapytań

### 5.1 Analiza rynku

Kompleksowa analiza sytuacji rynkowej, uwzględniająca:
- Trendy na różnych timeframe'ach
- Poziomy wsparcia i oporu
- Wskaźniki techniczne
- Korelacje między instrumentami
- Sentyment rynkowy

### 5.2 Prognozowanie kierunku

Prognozowanie prawdopodobnego kierunku ruchu ceny w określonym horyzoncie czasowym:
- Krótkoterminowa prognoza (1-24h)
- Średnioterminowa prognoza (1-7 dni)
- Określenie prawdopodobieństwa ruchu

### 5.3 Rozpoznawanie wzorców

Identyfikacja klasycznych i zaawansowanych wzorców cenowych:
- Formacje kontynuacji trendu
- Formacje odwrócenia trendu
- Wzorce harmoniczne
- Wzorce świecowe
- Price action

### 5.4 Analiza okazji handlowych

Identyfikacja i ocena potencjalnych okazji handlowych:
- Określenie punktów wejścia
- Sugerowane poziomy SL/TP
- Ocena jakości setupu (0-10)
- Określenie optymalnej wielkości pozycji

## 6. Proces przetwarzania danych

### 6.1 Przygotowanie danych

Przed wysłaniem do modeli AI, dane są odpowiednio przygotowane:
- Normalizacja wartości
- Obliczenie pochodnych wskaźników i oscylatorów
- Transformacja danych do formatu odpowiedniego dla modeli
- Filtracja szumu i anomalii

### 6.2 Konstrukcja promptów

Dla każdego typu analizy i modelu, system konstruuje odpowiednie prompty zawierające:
- Dane rynkowe w odpowiednim formacie
- Kontekst analizy (cel, horyzont czasowy)
- Ograniczenia i wymogi formatu odpowiedzi
- Instrukcje dotyczące struktury i zawartości analizy

### 6.3 Parsowanie odpowiedzi

Odpowiedzi z modeli AI są przetwarzane w celu wyodrębnienia:
- Konkretnych decyzji i rekomendacji
- Wartości liczbowych (poziomy wejścia, SL/TP)
- Ocen jakościowych i prawdopodobieństw
- Uzasadnień i wyjaśnień

## 7. Ewaluacja modeli

System prowadzi ciągłą ewaluację skuteczności modeli AI:

### 7.1 Metryki wydajności

- **Win Rate** - procent udanych prognoz
- **Profit Factor** - stosunek zysków do strat
- **ROI** - zwrot z inwestycji na podstawie rekomendacji
- **Trafność kierunku** - celność przewidywania kierunku ruchu
- **Jakość setupów** - korelacja między ocenami jakości a wynikami

### 7.2 Adaptacyjne dostosowanie

Na podstawie metryk wydajności, system adaptacyjnie dostosowuje:
- Wagi przypisane do różnych modeli
- Progi akceptacji dla rekomendacji
- Parametry strategii i zarządzania ryzykiem
- Alokację zasobów między modelami

## 8. Koszty i optymalizacja

### 8.1 Monitorowanie kosztów

System prowadzi szczegółowy monitoring kosztów związanych z wykorzystaniem API modeli AI:
- Koszt per zapytanie
- Całkowity koszt dzienny/miesięczny
- ROI z wykorzystania poszczególnych modeli

### 8.2 Strategie optymalizacji

W celu optymalizacji kosztów, system implementuje:
- Buforowanie wyników dla podobnych zapytań
- Priorytetyzację zapytań według potencjalnego wpływu
- Adaptacyjne dostosowanie częstotliwości zapytań
- Automatyczne przełączanie na modele o lepszym stosunku koszt/efektywność

## 9. Bezpieczeństwo

### 9.1 Zabezpieczenie API Keys

Klucze API do modeli AI są przechowywane w zmiennych środowiskowych i nigdy nie są zapisywane w kodzie.

### 9.2 Mechanizmy ochronne

System implementuje szereg mechanizmów ochronnych:
- Limity częstotliwości zapytań
- Walidacja danych wejściowych i wyjściowych
- Monitorowanie anomalii w odpowiedziach modeli
- Automatyczne wykrywanie potencjalnych problemów

## 10. Rozszerzanie funkcjonalności

### 10.1 Dodawanie nowych modeli

System jest zaprojektowany modułowo, co umożliwia łatwe dodawanie nowych modeli AI:
1. Utworzenie nowego modułu API dla modelu
2. Implementacja standardowych metod (analiza rynku, prognoza, itp.)
3. Rejestracja modelu w AI Router
4. Kalibracja i testowanie nowego modelu

### 10.2 Rozszerzanie typów analiz

Dodawanie nowych typów analiz wymaga:
1. Zdefiniowania nowego typu zapytania
2. Implementacji przygotowania danych i promptów
3. Implementacji parsowania odpowiedzi
4. Dodania metryk ewaluacji dla nowego typu analizy

## 11. FAQ

### 11.1 Jaki model jest najskuteczniejszy?

Skuteczność modeli zależy od typu analizy i instrumentu. Generalnie:
- Claude wykazuje najlepsze wyniki w kompleksowej analizie rynku
- Grok jest najskuteczniejszy w prognozowaniu krótkoterminowych ruchów
- DeepSeek osiąga najlepsze wyniki w rozpoznawaniu wzorców cenowych

### 11.2 Jak często modele są zapytywane?

Częstotliwość zapytań zależy od typu analizy i aktywności rynku:
- Analiza rynku: co 4-6 godzin
- Prognozowanie kierunku: co 1-2 godziny dla aktywnych instrumentów
- Rozpoznawanie wzorców: przy każdej znaczącej zmianie struktury rynku
- Analiza okazji handlowych: na żądanie i przy spełnieniu określonych warunków

### 11.3 Jak zapewnić ciągłość działania przy problemach z API?

System implementuje wielopoziomową strategię obsługi awarii:
1. Automatyczne przełączanie na alternatywne modele
2. Wykorzystanie buforowanych wyników
3. Fallback do prostszych algorytmów decyzyjnych
4. Automatyczne ograniczenie działania do trybu obserwacyjnego w przypadku długotrwałych problemów 