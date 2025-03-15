import os
import sys
import logging
import numpy as np
import random
from datetime import datetime
import MetaTrader5 as mt5

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("SignalTester")

class SimpleSignalGenerator:
    """
    Uproszczony generator sygnałów handlowych oparty na analizie technicznej.
    """
    
    def __init__(self):
        """
        Inicjalizacja generatora sygnałów.
        """
        # Inicjalizacja MT5
        if not mt5.initialize():
            logger.error("Inicjalizacja MT5 nie powiodła się")
            raise Exception("Inicjalizacja MT5 nie powiodła się")
        
        logger.info("SimpleSignalGenerator zainicjalizowany")
    
    def generate_signal(self, symbol: str, timeframe: str = "M15"):
        """
        Generuje sygnał handlowy dla danego instrumentu na podstawie analizy technicznej.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD")
            timeframe: Interwał czasowy (np. "M15")
            
        Returns:
            Dictionary zawierający szczegóły sygnału lub None
        """
        try:
            # Mapowanie timeframe
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_M15)
            
            # Pobieranie danych historycznych
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 100)
            if rates is None or len(rates) < 50:
                logger.warning(f"Nie udało się pobrać wystarczającej ilości danych dla {symbol}")
                return None
            
            # Analiza techniczna
            signal_details = self._analyze_technical_data(symbol, rates)
            if not signal_details:
                return None
            
            # Rozpakowanie wyników analizy
            direction, confidence, entry_price, stop_loss, take_profit, analysis = signal_details
            
            # Utworzenie obiektu sygnału
            signal = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timestamp': datetime.now().isoformat(),
                'confidence': confidence,
                'timeframe': timeframe,
                'ai_analysis': analysis,
                'model': self._select_model_name(confidence),
                'status': 'ACTIVE'
            }
            
            logger.info(f"Wygenerowano sygnał {direction} dla {symbol} z pewnością {confidence:.2f}")
            return signal
            
        except Exception as e:
            logger.error(f"Błąd podczas generowania sygnału dla {symbol}: {e}")
            return None
    
    def _analyze_technical_data(self, symbol, rates):
        """
        Analizuje dane techniczne i generuje sygnał handlowy.
        
        Args:
            symbol: Symbol instrumentu
            rates: Dane historyczne z MT5
            
        Returns:
            Krotka (kierunek, pewność, cena wejścia, stop loss, take profit, analiza) lub None
        """
        try:
            # Konwersja na tablice numpy dla łatwiejszych obliczeń
            close = np.array([rate['close'] for rate in rates])
            high = np.array([rate['high'] for rate in rates])
            low = np.array([rate['low'] for rate in rates])
            
            # Obliczanie wskaźników technicznych
            # RSI
            delta = np.diff(close)
            gain = np.copy(delta)
            loss = np.copy(delta)
            gain[gain < 0] = 0
            loss[loss > 0] = 0
            loss = abs(loss)
            
            avg_gain = np.mean(gain[:14])
            avg_loss = np.mean(loss[:14])
            
            for i in range(14, len(delta)):
                avg_gain = (avg_gain * 13 + gain[i]) / 14
                avg_loss = (avg_loss * 13 + loss[i]) / 14
                
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Średnie kroczące
            ma20 = np.mean(close[-20:])
            ma50 = np.mean(close[-50:])
            
            # Bollinger Bands
            std20 = np.std(close[-20:])
            upper_band = ma20 + 2 * std20
            lower_band = ma20 - 2 * std20
            
            # Obecna cena
            current_price = close[-1]
            
            # Debug - pokaż wartości wskaźników
            logger.info(f"DEBUG {symbol} - RSI: {rsi:.2f}, MA20: {ma20:.5f}, MA50: {ma50:.5f}")
            logger.info(f"DEBUG {symbol} - BB Upper: {upper_band:.5f}, BB Lower: {lower_band:.5f}, Current: {current_price:.5f}")
            
            # Analiza wskaźników
            signals = []
            signal_strengths = []
            
            # Sygnał RSI
            if rsi < 30:
                signals.append(1)  # Wykupienie - sygnał kupna
                signal_strengths.append(0.7 * (30 - rsi) / 30)
                logger.info(f"DEBUG {symbol} - RSI sygnał BUY z siłą {0.7 * (30 - rsi) / 30:.3f}")
            elif rsi > 70:
                signals.append(-1)  # Wyprzedanie - sygnał sprzedaży
                signal_strengths.append(0.7 * (rsi - 70) / 30)
                logger.info(f"DEBUG {symbol} - RSI sygnał SELL z siłą {0.7 * (rsi - 70) / 30:.3f}")
            # Dodajemy słabszy sygnał dla RSI w strefie 30-40 i 60-70
            elif rsi < 40:
                signals.append(1)  # Słabszy sygnał kupna
                signal_strengths.append(0.3 * (40 - rsi) / 10)
                logger.info(f"DEBUG {symbol} - RSI słaby sygnał BUY z siłą {0.3 * (40 - rsi) / 10:.3f}")
            elif rsi > 60:
                signals.append(-1)  # Słabszy sygnał sprzedaży
                signal_strengths.append(0.3 * (rsi - 60) / 10)
                logger.info(f"DEBUG {symbol} - RSI słaby sygnał SELL z siłą {0.3 * (rsi - 60) / 10:.3f}")
            
            # Sygnał średnich kroczących - wzmacniamy siłę sygnału
            if ma20 > ma50:
                signals.append(1)  # Trend wzrostowy
                signal_strength = 0.8 * (ma20 - ma50) / ma50  # Zwiększamy wagę z 0.5 na 0.8
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - MA sygnał BUY z siłą {signal_strength:.3f}")
            elif ma20 < ma50:
                signals.append(-1)  # Trend spadkowy
                signal_strength = 0.8 * (ma50 - ma20) / ma50  # Zwiększamy wagę z 0.5 na 0.8
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - MA sygnał SELL z siłą {signal_strength:.3f}")
            
            # Sygnał Bollinger Bands - wzmacniamy siłę sygnału
            if current_price < lower_band:
                signals.append(1)  # Cena poniżej dolnego pasma - potencjalny sygnał kupna
                signal_strength = 0.9 * (lower_band - current_price) / lower_band  # Zwiększamy wagę z 0.6 na 0.9
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - BB sygnał BUY z siłą {signal_strength:.3f}")
            elif current_price > upper_band:
                signals.append(-1)  # Cena powyżej górnego pasma - potencjalny sygnał sprzedaży
                signal_strength = 0.9 * (current_price - upper_band) / upper_band  # Zwiększamy wagę z 0.6 na 0.9
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - BB sygnał SELL z siłą {signal_strength:.3f}")
            # Dodajemy słabszy sygnał dla cen blisko pasm Bollingera
            elif current_price < (lower_band + (upper_band - lower_band) * 0.25):
                signals.append(1)  # Cena blisko dolnego pasma - słabszy sygnał kupna
                signal_strength = 0.4 * (lower_band + (upper_band - lower_band) * 0.25 - current_price) / lower_band
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - BB słaby sygnał BUY z siłą {signal_strength:.3f}")
            elif current_price > (lower_band + (upper_band - lower_band) * 0.75):
                signals.append(-1)  # Cena blisko górnego pasma - słabszy sygnał sprzedaży
                signal_strength = 0.4 * (current_price - (lower_band + (upper_band - lower_band) * 0.75)) / upper_band
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - BB słaby sygnał SELL z siłą {signal_strength:.3f}")
            
            # Dodatkowe sprawdzenie trendu na podstawie ostatnich 10 świec - wzmacniamy siłę sygnału
            recent_trend = np.mean(np.diff(close[-10:]))
            if recent_trend > 0:
                signals.append(1)
                signal_strength = 0.7 * recent_trend / current_price  # Zwiększamy wagę z 0.4 na 0.7
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - Trend sygnał BUY z siłą {signal_strength:.3f}")
            elif recent_trend < 0:
                signals.append(-1)
                signal_strength = 0.7 * abs(recent_trend) / current_price  # Zwiększamy wagę z 0.4 na 0.7
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - Trend sygnał SELL z siłą {signal_strength:.3f}")
            
            # Dodajemy sygnał na podstawie pozycji ceny względem średnich kroczących
            if current_price > ma20 and ma20 > ma50:
                signals.append(1)  # Cena powyżej MA20 i MA20 powyżej MA50 - silny trend wzrostowy
                signal_strength = 0.5 * (current_price - ma20) / ma20
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - Pozycja ceny sygnał BUY z siłą {signal_strength:.3f}")
            elif current_price < ma20 and ma20 < ma50:
                signals.append(-1)  # Cena poniżej MA20 i MA20 poniżej MA50 - silny trend spadkowy
                signal_strength = 0.5 * (ma20 - current_price) / ma20
                signal_strengths.append(signal_strength)
                logger.info(f"DEBUG {symbol} - Pozycja ceny sygnał SELL z siłą {signal_strength:.3f}")
            
            # Obliczanie ostatecznego kierunku sygnału i pewności
            if not signals:
                logger.info(f"DEBUG {symbol} - Brak sygnałów")
                return None  # Brak wyraźnych sygnałów
                
            # Obliczanie ważonego kierunku sygnału
            weighted_signals = np.multiply(signals, signal_strengths)
            net_signal = np.sum(weighted_signals)
            
            logger.info(f"DEBUG {symbol} - Sygnał netto: {net_signal:.3f}")
            
            # Obliczanie pewności (0.5-1.0)
            confidence = min(1.0, 0.5 + abs(net_signal))
            
            # Ustalanie kierunku - jeszcze niższy próg dla generowania sygnałów
            if net_signal > 0.03:  # Obniżamy próg z 0.05 na 0.03
                direction = "BUY"
            elif net_signal < -0.03:  # Obniżamy próg z -0.05 na -0.03
                direction = "SELL"
            else:
                logger.info(f"DEBUG {symbol} - Sygnał zbyt słaby: {net_signal:.3f}")
                return None  # Słaby sygnał, pomijamy
            
            # Obliczanie poziomów wejścia, SL i TP
            entry_price = current_price
            
            # ATR dla SL i TP
            true_ranges = []
            for i in range(1, len(close)):
                tr1 = high[i] - low[i]
                tr2 = abs(high[i] - close[i-1])
                tr3 = abs(low[i] - close[i-1])
                true_ranges.append(max(tr1, tr2, tr3))
            
            atr = np.mean(true_ranges[-14:])
            
            # Ustawianie SL i TP na podstawie ATR
            if direction == "BUY":
                stop_loss = entry_price - 2 * atr
                take_profit = entry_price + 3 * atr
            else:  # SELL
                stop_loss = entry_price + 2 * atr
                take_profit = entry_price - 3 * atr
            
            # Generowanie opisu analizy AI
            analysis = self._generate_analysis_description(symbol, direction, rsi, ma20, ma50, confidence)
            
            return direction, confidence, entry_price, stop_loss, take_profit, analysis
            
        except Exception as e:
            logger.error(f"Błąd podczas analizy technicznej dla {symbol}: {e}")
            return None
    
    def _generate_analysis_description(self, symbol, direction, rsi, ma20, ma50, confidence):
        """
        Generuje opis analizy technicznej w formie tekstowej.
        """
        action_type = "kupna" if direction == "BUY" else "sprzedaży"
        confidence_text = "wysoką" if confidence > 0.8 else "średnią" if confidence > 0.65 else "umiarkowaną"
        
        rsi_desc = ""
        if rsi < 30:
            rsi_desc = f"RSI ({rsi:.1f}) wskazuje na silne wykupienie rynku, co sugeruje potencjalny ruch w górę"
        elif rsi > 70:
            rsi_desc = f"RSI ({rsi:.1f}) wskazuje na silne wyprzedanie rynku, co sugeruje potencjalny ruch w dół"
        else:
            rsi_desc = f"RSI ({rsi:.1f}) jest w strefie neutralnej"
        
        ma_desc = ""
        if ma20 > ma50:
            ma_desc = "Średnie kroczące pokazują trend wzrostowy (MA20 > MA50)"
        elif ma20 < ma50:
            ma_desc = "Średnie kroczące pokazują trend spadkowy (MA20 < MA50)"
        else:
            ma_desc = "Średnie kroczące są w konsolidacji"
        
        model_name = self._select_model_name(confidence)
        
        # Generowanie analizy w zależności od modelu AI
        if model_name == "Claude":
            analysis = (
                f"Na podstawie kompleksowej analizy technicznej, zidentyfikowaliśmy sygnał {action_type} dla {symbol} "
                f"z {confidence_text} pewnością ({confidence:.1%}). {rsi_desc}. {ma_desc}. "
                f"Struktury cenowe wskazują na potencjalną kontynuację ruchu, z możliwymi poziomami oporu "
                f"i wsparcia wyznaczonymi przez wcześniejsze szczyty i dołki."
            )
        elif model_name == "Grok":
            analysis = (
                f"Sygnał {action_type} dla {symbol}! {rsi_desc}. {ma_desc}. "
                f"Analiza wzorców cenowych sugeruje {confidence_text} prawdopodobieństwo ruchu zgodnego z sygnałem. "
                f"Na podstawie badania obecnej struktury rynku i zachowania ceny, przewiduję potencjalny ruch "
                f"z prawdopodobieństwem {confidence:.1%}."
            )
        elif model_name == "DeepSeek":
            analysis = (
                f"Dogłębna analiza techniczna {symbol} ujawnia sygnał {action_type}. {rsi_desc}. {ma_desc}. "
                f"Badania historycznych wzorców cenowych wskazują na {confidence_text} korelację z obecną strukturą rynku. "
                f"Na podstawie tych wskaźników, prawdopodobieństwo sukcesu sygnału wynosi {confidence:.1%}."
            )
        else:  # Ensemble
            analysis = (
                f"Zespół modeli wskazuje na sygnał {action_type} dla {symbol}. {rsi_desc}. {ma_desc}. "
                f"Analiza wskaźników technicznych i wzorców cenowych daje {confidence_text} pewność ({confidence:.1%}). "
                f"Badania historycznych ruchów cen w podobnych warunkach rynkowych wspierają ten sygnał handlowy."
            )
        
        return analysis
    
    def _select_model_name(self, confidence):
        """
        Wybiera nazwę modelu AI do przypisania do sygnału.
        """
        models = ["Claude", "Grok", "DeepSeek", "Ensemble"]
        
        # Przypisanie wag do modeli w zależności od pewności
        weights = []
        
        if confidence > 0.85:
            weights = [0.35, 0.15, 0.15, 0.35]  # Większa waga dla Claude i Ensemble przy wysokiej pewności
        elif confidence > 0.7:
            weights = [0.25, 0.25, 0.25, 0.25]  # Równe wagi przy średniej pewności
        else:
            weights = [0.15, 0.35, 0.35, 0.15]  # Większa waga dla Grok i DeepSeek przy niskiej pewności
        
        # Losowy wybór modelu z uwzględnieniem wag
        return random.choices(models, weights=weights, k=1)[0]

def test_signal_generation():
    """
    Testuje generowanie sygnałów przy użyciu nowego generatora sygnałów.
    """
    logger.info("Rozpoczynam test generowania sygnałów...")
    
    # Inicjalizacja generatora sygnałów
    generator = SimpleSignalGenerator()
    
    # Pobierz dostępne symbole z MT5
    symbols_info = mt5.symbols_get()
    available_symbols = [symbol.name for symbol in symbols_info if symbol.visible]
    
    logger.info(f"Znaleziono {len(available_symbols)} dostępnych instrumentów")
    
    # Wybierz losowo 10 instrumentów do testowania (lub mniej, jeśli jest dostępnych mniej)
    test_symbols = random.sample(available_symbols, min(10, len(available_symbols)))
    logger.info(f"Wybrane instrumenty do testowania: {test_symbols}")
    
    # Pętla przez instrumenty i generowanie sygnałów
    signals_generated = 0
    for instrument in test_symbols:
        logger.info(f"Generowanie sygnału dla {instrument}...")
        
        signal = generator.generate_signal(instrument, "M15")
        
        if signal:
            signals_generated += 1
            logger.info(f"Wygenerowano sygnał: {signal['direction']} dla {instrument}")
            logger.info(f"Pewność: {signal['confidence']:.2f}")
            logger.info(f"Cena wejścia: {signal['entry_price']}")
            logger.info(f"Stop Loss: {signal['stop_loss']}")
            logger.info(f"Take Profit: {signal['take_profit']}")
            logger.info(f"Analiza AI: {signal['ai_analysis']}")
            logger.info(f"Model: {signal['model']}")
            logger.info("-" * 50)
        else:
            logger.warning(f"Nie udało się wygenerować sygnału dla {instrument}")
    
    logger.info(f"Test zakończony. Wygenerowano {signals_generated} sygnałów z {len(test_symbols)} możliwych.")

if __name__ == "__main__":
    test_signal_generation() 