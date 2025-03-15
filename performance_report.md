# Raport wydajności mechanizmu regularnego odświeżania danych

Data: 2025-03-13 11:57:15

## Informacje o środowisku

- System: win32
- Python: 3.9.13
- Procesor: 4 rdzeni fizycznych, 4 wątków
- Pamięć: 15.89 GB całkowita

## Test pojedynczego odświeżenia

| Symbol | Timeframe | Średni czas (s) | Średnie CPU (%) | Średnia pamięć (MB) |
|--------|-----------|-----------------|-----------------|---------------------|
| EURUSD | M1 | 0.0010 | -22.37 | 0.23 |
| EURUSD | M5 | 0.0003 | 0.00 | 0.00 |
| EURUSD | M15 | 0.0010 | 16.67 | 0.00 |
| EURUSD | H1 | 0.0003 | 0.00 | 0.00 |
| EURUSD | D1 | 0.0013 | 33.33 | 0.00 |
| GBPUSD | M1 | 0.0010 | 0.00 | 0.00 |
| GBPUSD | M5 | 0.0017 | 33.33 | 0.00 |
| GBPUSD | M15 | 0.0007 | 0.00 | 0.00 |
| GBPUSD | H1 | 0.0010 | 33.33 | 0.00 |
| GBPUSD | D1 | 0.0007 | 0.00 | 0.00 |
| USDJPY | M1 | 0.0422 | 25.23 | 0.00 |
| USDJPY | M5 | 0.0007 | 0.00 | 0.00 |
| USDJPY | M15 | 0.0017 | 25.00 | 0.00 |
| USDJPY | H1 | 0.0007 | 0.00 | 0.00 |
| USDJPY | D1 | 0.0013 | -33.33 | 0.00 |
| GOLD | M1 | 0.0003 | 0.00 | 0.00 |
| GOLD | M5 | 0.0007 | -33.33 | 0.00 |
| GOLD | M15 | 0.0003 | 0.00 | 0.00 |
| GOLD | H1 | 0.0013 | -33.33 | 0.00 |
| GOLD | D1 | 0.0003 | 0.00 | 0.00 |
| SILVER | M1 | 0.0017 | 33.33 | 0.00 |
| SILVER | M5 | 0.0007 | 0.00 | 0.00 |
| SILVER | M15 | 0.0010 | 33.33 | 0.00 |
| SILVER | H1 | 0.0013 | 0.00 | 0.00 |
| SILVER | D1 | 0.0010 | -33.33 | 0.00 |

## Porównanie sekwencyjnego i równoległego odświeżania

| Metryka | Sekwencyjne | Równoległe | Stosunek |
|---------|-------------|------------|----------|
| Całkowity czas (s) | 0.0010 | 0.0130 | 0.08 |
| Zadań na sekundę | 24977.99 | 1923.00 | 0.08 |
| Zmiana CPU (%) | 0.00 | 75.00 | - |
| Zmiana pamięci (MB) | 0.00 | 0.15 | - |

## Wyniki testu długotrwałego

| Metryka | Wartość |
|---------|--------|
| Liczba odświeżeń | 12 |
| Całkowity czas (s) | 60.10 |
| Średni czas odświeżenia (s) | 0.0006 |
| Odświeżeń na sekundę | 0.20 |
| Średnie użycie CPU (%) | 29.59 |
| Maksymalne użycie CPU (%) | 38.80 |
| Wzrost zużycia pamięci (MB) | 0.06 |

## Wnioski i rekomendacje

### Rekomendowane interwały odświeżania

| Timeframe | Rekomendowany interwał (s) |
|-----------|----------------------------|
| M1 | 5 |
| M5 | 5 |
| M15 | 5 |
| H1 | 5 |
| D1 | 5 |

### Ogólne wnioski

- ℹ️ Równoległe odświeżanie daje umiarkowany zysk wydajności (0.08x). Zaleca się jego stosowanie dla większej liczby instrumentów.
- ⚠️ Niska częstotliwość odświeżania. Warto rozważyć optymalizację kodu lub zwiększenie mocy obliczeniowej.

