//+------------------------------------------------------------------+
//|                                                     Logger.mqh |
//|                                         AgentMT5 Trading System |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "AgentMT5 Trading System"
#property link      ""
#property version   "1.00"
#property strict

// Definicje poziomów logowania
#define LOG_DEBUG    0
#define LOG_INFO     1
#define LOG_WARNING  2
#define LOG_ERROR    3

//+------------------------------------------------------------------+
//| Klasa odpowiedzialna za logowanie informacji                     |
//+------------------------------------------------------------------+
class Logger
{
private:
   string   m_name;           // Nazwa loggera
   bool     m_enabled;        // Czy logowanie jest włączone
   int      m_logLevel;       // Minimalny poziom logowania
   string   m_filename;       // Nazwa pliku z logami
   
   // Konwersja poziomu logowania z tekstu na liczbę
   int StringToLogLevel(string level)
   {
      if(level == "DEBUG") return LOG_DEBUG;
      if(level == "INFO") return LOG_INFO;
      if(level == "WARNING") return LOG_WARNING;
      if(level == "ERROR") return LOG_ERROR;
      return LOG_INFO; // Domyślnie INFO
   }
   
   // Konwersja poziomu logowania z liczby na tekst
   string LogLevelToString(int level)
   {
      switch(level)
      {
         case LOG_DEBUG:   return "DEBUG";
         case LOG_INFO:    return "INFO";
         case LOG_WARNING: return "WARNING";
         case LOG_ERROR:   return "ERROR";
      }
      return "UNKNOWN";
   }

public:
   // Konstruktor
   Logger(string name, bool enabled=true, string logLevel="INFO")
   {
      m_name = name;
      m_enabled = enabled;
      m_logLevel = StringToLogLevel(logLevel);
      
      // Tworzymy nazwę pliku logów: EA_name_YYYYMMDD.log
      datetime now = TimeCurrent();
      m_filename = StringFormat("%s_%s.log", 
                               m_name,
                               TimeToString(now, TIME_DATE));
                               
      // Inicjalizacja - wiadomość startowa
      if(m_enabled && m_logLevel <= LOG_INFO)
      {
         string message = StringFormat("Logger started at %s", TimeToString(now));
         WriteToFile(LOG_INFO, message);
         Print(LogLevelToString(LOG_INFO), ": ", message);
      }
   }
   
   // Destruktor
   ~Logger()
   {
      if(m_enabled && m_logLevel <= LOG_INFO)
      {
         datetime now = TimeCurrent();
         string message = StringFormat("Logger stopped at %s", TimeToString(now));
         WriteToFile(LOG_INFO, message);
         Print(LogLevelToString(LOG_INFO), ": ", message);
      }
   }
   
   // Zapisanie wiadomości do logu
   void Log(int level, string message)
   {
      if(!m_enabled) return;
      if(level < m_logLevel) return;
      
      WriteToFile(level, message);
      Print(LogLevelToString(level), ": ", message);
   }
   
   // Zapisanie wiadomości do pliku
   void WriteToFile(int level, string message)
   {
      // Otwieramy plik w trybie dopisywania
      int handle = FileOpen(m_filename, FILE_WRITE|FILE_READ|FILE_TXT);
      if(handle != INVALID_HANDLE)
      {
         // Przechodzimy na koniec pliku
         FileSeek(handle, 0, SEEK_END);
         
         // Formatujemy wiadomość: [TIME][LEVEL] MESSAGE
         string formattedMessage = StringFormat("[%s][%s] %s\r\n", 
                                 TimeToString(TimeCurrent()),
                                 LogLevelToString(level),
                                 message);
         
         // Zapisujemy wiadomość
         FileWriteString(handle, formattedMessage);
         
         // Zamykamy plik
         FileClose(handle);
      }
   }
   
   // Zmiana poziomu logowania
   void SetLogLevel(string level)
   {
      m_logLevel = StringToLogLevel(level);
   }
   
   // Włączenie/wyłączenie logowania
   void SetEnabled(bool enabled)
   {
      m_enabled = enabled;
   }
   
   // Sprawdzenie czy dany poziom logowania jest aktywny
   bool IsLevelEnabled(int level)
   {
      return m_enabled && level >= m_logLevel;
   }
}; 