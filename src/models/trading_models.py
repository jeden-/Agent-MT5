from datetime import datetime, timedelta

class TradingSignal:
    def __init__(
        self,
        symbol: str,
        direction: str,
        confidence: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        analysis: str,
        timeframe: str,
        timestamp: datetime = None,
        expiry: datetime = None,
        model_name: str = "AutoMLTrader",
        metadata: dict = None,
        id: int = None
    ):
        self.id = id
        self.symbol = symbol
        self.direction = direction
        self.confidence = confidence
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.analysis = analysis
        self.timeframe = timeframe
        self.timestamp = timestamp or datetime.now()
        self.expiry = expiry or (self.timestamp + timedelta(hours=24))
        self.model_name = model_name
        self.metadata = metadata or {}
        self.status = "ACTIVE"
        
    def __str__(self):
        return (
            f"TradingSignal(symbol={self.symbol}, direction={self.direction}, "
            f"confidence={self.confidence:.2f}, entry_price={self.entry_price:.5f}, "
            f"stop_loss={self.stop_loss:.5f}, take_profit={self.take_profit:.5f}, "
            f"timeframe={self.timeframe}, timestamp={self.timestamp}, "
            f"model_name={self.model_name}, status={self.status})"
        )
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "analysis": self.analysis,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "expiry": self.expiry.isoformat() if self.expiry else None,
            "model_name": self.model_name,
            "metadata": self.metadata,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Tworzy obiekt TradingSignal z dictionary"""
        # Konwersja timestamp i expiry ze stringów na datetime, jeśli są dostępne
        timestamp = datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None
        expiry = datetime.fromisoformat(data['expiry']) if data.get('expiry') else None
        
        return cls(
            id=data.get('id'),
            symbol=data['symbol'],
            direction=data['direction'],
            confidence=data['confidence'],
            entry_price=data['entry_price'],
            stop_loss=data['stop_loss'],
            take_profit=data['take_profit'],
            analysis=data['analysis'],
            timeframe=data['timeframe'],
            timestamp=timestamp,
            expiry=expiry,
            model_name=data.get('model_name', "AutoMLTrader"),
            metadata=data.get('metadata', {})
        ) 