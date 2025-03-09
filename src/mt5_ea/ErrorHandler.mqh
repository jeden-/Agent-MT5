//+------------------------------------------------------------------+
//|                                                ErrorHandler.mqh |
//|                                         AgentMT5 Trading System |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "AgentMT5 Trading System"
#property link      ""
#property version   "1.00"
#property strict

// Dołączamy loggera
#include "Logger.mqh"

//+------------------------------------------------------------------+
//| Klasa odpowiedzialna za obsługę błędów                           |
//+------------------------------------------------------------------+
class ErrorHandler
{
private:
   Logger* m_logger;     // Wskaźnik na logger
   int     m_lastError;  // Ostatni kod błędu
   
   // Mapowanie kodów błędów na opisy
   string GetErrorDescription(int errorCode)
   {
      switch(errorCode)
      {
         // Ogólne błędy
         case 0:     return "Brak błędu";
         case 4001:  return "Nieoczekiwany błąd";
         case 4002:  return "Nieprawidłowy parametr w funkcji wewnętrznej";
         case 4003:  return "Nieprawidłowy parametr podczas wywołania funkcji systemowej";
         case 4004:  return "Brak pamięci do wykonania funkcji systemowej";
         case 4005:  return "Nieprawidłowa struktura w pliku";
         case 4006:  return "Brak dostępu";
         case 4007:  return "Brak wystarczających uprawnień";
         case 4008:  return "Zbyt częste wywołania";
         case 4014:  return "Za dużo otwartych plików";
         case 4015:  return "Nie można otworzyć pliku";
         case 4016:  return "Zbyt długa nazwa pliku";
         case 4017:  return "Zbyt duża wielkość pliku";
         case 4019:  return "Plik nie pasuje";
         case 4020:  return "Nieprawidłowa nazwa pliku";
         
         // Błędy handlowe
         case 10004: return "Wymagane ponowne kwotowanie";
         case 10006: return "Żądanie odrzucone";
         case 10007: return "Żądanie anulowane przez tradera";
         case 10008: return "Zlecenie już wykonane";
         case 10009: return "Zlecenie już w kolejce";
         case 10010: return "Tylko część zlecenia wykonana";
         case 10011: return "Błąd przetwarzania żądania zlecenia";
         case 10012: return "Żądanie anulowane przez timeout";
         case 10013: return "Nieprawidłowe zlecenie";
         case 10014: return "Nieznany symbol";
         case 10015: return "Nieprawidłowy wolumen w zleceniu";
         case 10016: return "Nieprawidłowa cena w zleceniu";
         case 10017: return "Nieprawidłowy Stop Loss";
         case 10018: return "Handel wyłączony";
         case 10019: return "Rynek zamknięty";
         case 10020: return "Brak wystarczających środków";
         case 10021: return "Ceny zmieniły się";
         case 10022: return "Za niska cena";
         case 10023: return "Za wysoka cena";
         case 10024: return "Nieprawidłowy tik";
         case 10025: return "Nieprawidłowy Stop Loss lub Take Profit";
         case 10026: return "Nieprawidłowy wolumen w zleceniu";
         case 10027: return "Nieprawidłowe dane rynkowe";
         case 10028: return "Broker odmówił przyjęcia zlecenia";
         case 10029: return "Upłynął czas wykonania zlecenia";
         case 10030: return "Zlecenie wypełnione";
         case 10031: return "Żądanie przyjęte";
         case 10032: return "Żądanie wykonane";
         
         // Jeśli nieznany kod błędu
         default:    return StringFormat("Nieznany błąd: %d", errorCode);
      }
   }
   
public:
   // Konstruktor
   ErrorHandler(Logger* logger)
   {
      m_logger = logger;
      m_lastError = 0;
   }
   
   // Destruktor
   ~ErrorHandler() {}
   
   // Sprawdzenie błędów handlowych
   bool CheckTradingErrors()
   {
      int error = GetLastError();
      if(error != 0 && error != m_lastError)
      {
         m_lastError = error;
         string errorDesc = GetErrorDescription(error);
         m_logger.Log(LOG_ERROR, StringFormat("Błąd handlowy: %d - %s", error, errorDesc));
         return true;
      }
      return false;
   }
   
   // Logowanie błędu
   void LogError(string functionName, string details="")
   {
      int error = GetLastError();
      if(error != 0)
      {
         string errorDesc = GetErrorDescription(error);
         string logMessage = StringFormat("Błąd w funkcji %s: %d - %s", functionName, error, errorDesc);
         
         if(details != "")
            logMessage += ". Szczegóły: " + details;
            
         m_logger.Log(LOG_ERROR, logMessage);
         
         // Czyszczenie kodu błędu
         ResetLastError();
      }
   }
   
   // Czyszczenie kodu błędu
   void ClearError()
   {
      ResetLastError();
      m_lastError = 0;
   }
   
   // Sprawdzenie konkretnego błędu
   bool IsError(int errorCode)
   {
      int lastError = GetLastError();
      return (lastError == errorCode);
   }
   
   // Sprawdzenie czy ostatni błąd był krytyczny (przerwanie handlu)
   bool IsCriticalError()
   {
      int error = GetLastError();
      
      // Lista krytycznych błędów
      switch(error)
      {
         case 4001:  // Nieoczekiwany błąd
         case 4018:  // Nieprawidłowy wskaźnik
         case 10018: // Handel wyłączony
         case 10019: // Rynek zamknięty
         case 10020: // Brak wystarczających środków
            return true;
      }
      
      return false;
   }
}; 