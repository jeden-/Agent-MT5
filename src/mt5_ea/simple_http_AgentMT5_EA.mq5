//+------------------------------------------------------------------+
//|                                    simple_http_AgentMT5_EA.mq5 |
//|                                         AgentMT5 Trading System |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "AgentMT5 Trading System"
#property link      ""
#property version   "1.00"
#property strict

// Definicje stałych
#define EA_NAME "Simple_HTTP_AgentMT5_EA"
#define EA_MAGIC 123456  // Magiczny numer do identyfikacji zleceń EA

// Definicje poziomów logowania
#define LOG_DEBUG    0
#define LOG_INFO     1
#define LOG_WARNING  2
#define LOG_ERROR    3

// Importowanie potrzebnych bibliotek
#include <Trade\Trade.mqh>

// Zmienne globalne
CTrade Trade;
string EA_ID = "";  // Identyfikator EA nadany przez serwer
datetime LastCommandCheckTime = 0;  // Czas ostatniego sprawdzenia poleceń
datetime LastPingTime = 0;          // Czas ostatniego ping
datetime LastMarketDataTime = 0;    // Czas ostatniego wysłania danych rynkowych
datetime LastPositionsUpdateTime = 0;  // Czas ostatniej aktualizacji pozycji
MqlTick lastTick;                   // Zmienna do przechowywania danych o ostatnim ticku
bool InitSent = false;              // Czy wysłano wiadomość inicjalizacyjną

// Parametry wejściowe - konfiguracja HTTP
input string   ServerURL = "http://127.0.0.1:5555";  // URL serwera HTTP
input int      CommandCheckInterval = 5;   // Częstotliwość sprawdzania poleceń (sekundy)
input int      PingInterval = 30;          // Interwał pingowania (sekundy)
input int      MarketDataInterval = 60;    // Interwał wysyłania danych rynkowych (sekundy)
input int      PositionsUpdateInterval = 15;  // Interwał aktualizacji pozycji (sekundy)
input int      HTTPTimeout = 5000;         // Timeout dla zapytań HTTP (ms)
input bool     EnableLogging = true;       // Włączenie logowania
input string   LogLevel = "INFO";          // Poziom logowania (DEBUG, INFO, WARNING, ERROR)
input bool     EnableMarketData = true;    // Włączenie wysyłania danych rynkowych

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("Simple_HTTP_AgentMT5_EA: Inicjalizacja");
   
   // Generujemy unikalny identyfikator dla EA
   EA_ID = "EA_" + IntegerToString(TimeLocal());
   
   // Konfiguracja obiektu handlowego
   Trade.SetExpertMagicNumber(EA_MAGIC);
   
   // Inicjalizacja zmiennych czasu
   LastCommandCheckTime = TimeLocal();
   LastPingTime = TimeLocal();
   LastMarketDataTime = TimeLocal();
   LastPositionsUpdateTime = TimeLocal();
   
   // Wysyłamy wiadomość inicjalizacyjną do serwera
   if (!SendInitMessage())
   {
      Print("Simple_HTTP_AgentMT5_EA: Nie można połączyć z serwerem HTTP");
      // Mimo to kontynuujemy, będziemy próbować ponownie w OnTimer
   }
   else
   {
      InitSent = true;
      Print("Simple_HTTP_AgentMT5_EA: Połączenie z serwerem HTTP nawiązane");
   }
   
   // Ustawiamy timer na 1 sekundę
   EventSetTimer(1);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("Simple_HTTP_AgentMT5_EA: Deinicjalizacja, powód: ", reason);
   
   // Zatrzymujemy timer
   EventKillTimer();
   
   // Informujemy serwer o zakończeniu pracy EA
   if (InitSent)
   {
      string url = ServerURL + "/init";
      string headers = "Content-Type: application/json\r\n";
      string postData = "{\"ea_id\":\"" + EA_ID + "\",\"action\":\"shutdown\",\"reason\":" + IntegerToString(reason) + "}";
      
      char result[];
      char request[];
      string response_headers;
      StringToCharArray(postData, request);
      
      int res = WebRequest("POST", url, headers, HTTPTimeout, request, result, response_headers);
      
      if (res == -1)
      {
         int errorCode = GetLastError();
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas informowania serwera o zamknięciu: ", errorCode);
      }
      else
      {
         Print("Simple_HTTP_AgentMT5_EA: Serwer poinformowany o zamknięciu EA");
      }
   }
   
   Print("Simple_HTTP_AgentMT5_EA: Deinicjalizacja zakończona");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // W podejściu opartym na HTTP i pollingu, funkcja OnTick nie jest
   // wykorzystywana do komunikacji z serwerem.
   // Cała komunikacja odbywa się w OnTimer, która jest wywoływana
   // regularnie, niezależnie od ticków.
   
   // Możemy tu jednak aktualizować dane rynkowe
   if (EnableMarketData)
   {
      SymbolInfoTick(Symbol(), lastTick);
   }
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
   datetime currentTime = TimeLocal();
   
   // Sprawdzamy, czy trzeba wysłać inicjalizację
   if (!InitSent)
   {
      if (SendInitMessage())
      {
         InitSent = true;
         Print("Simple_HTTP_AgentMT5_EA: Połączenie z serwerem HTTP nawiązane");
      }
      else
      {
         Print("Simple_HTTP_AgentMT5_EA: Nie można połączyć z serwerem HTTP, próba ponowna za chwilę");
      }
   }
   
   // Sprawdzamy, czy są nowe polecenia co CommandCheckInterval sekund
   if (currentTime - LastCommandCheckTime >= CommandCheckInterval)
   {
      CheckForCommands();
      LastCommandCheckTime = currentTime;
   }
   
   // Pingujemy serwer co PingInterval sekund
   if (currentTime - LastPingTime >= PingInterval)
   {
      PingServer();
      LastPingTime = currentTime;
   }
   
   // Wysyłamy dane rynkowe co MarketDataInterval sekund
   if (EnableMarketData && currentTime - LastMarketDataTime >= MarketDataInterval)
   {
      SendMarketData();
      LastMarketDataTime = currentTime;
   }
   
   // Aktualizujemy informacje o pozycjach co PositionsUpdateInterval sekund
   if (currentTime - LastPositionsUpdateTime >= PositionsUpdateInterval)
   {
      SendPositionsUpdate();
      LastPositionsUpdateTime = currentTime;
   }
}

//+------------------------------------------------------------------+
//| Send initialization message to server                           |
//+------------------------------------------------------------------+
bool SendInitMessage()
{
   string url = ServerURL + "/init";
   string headers = "Content-Type: application/json\r\n";
   
   // Tworzymy JSON z danymi inicjalizacyjnymi
   string postData = StringFormat(
      "{\"ea_id\":\"%s\",\"terminal_info\":{\"account\":%d,\"company\":\"%s\",\"symbol\":\"%s\",\"timeframe\":%d,\"build\":%d}}",
      EA_ID,
      AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_COMPANY),
      Symbol(),
      Period(),
      TerminalInfoInteger(TERMINAL_BUILD)
   );
   
   char result[];
   char request[];
   string response_headers;
   StringToCharArray(postData, request);
   
   int res = WebRequest("POST", url, headers, HTTPTimeout, request, result, response_headers);
   
   if (res == -1)
   {
      int errorCode = GetLastError();
      // Jeśli błąd to nieprawidłowy adres URL, to informujemy o potrzebie zezwolenia na WebRequest
      if (errorCode == 4060)
      {
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas inicjalizacji: ", errorCode, 
            " - Upewnij się, że dodałeś ", url, " do listy dozwolonych URL w narzędziach->opcje->doradcy eksperci");
      }
      else
      {
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas inicjalizacji: ", errorCode);
      }
      return false;
   }
   
   // Parsujemy odpowiedź
   string response = CharArrayToString(result);
   Print("Simple_HTTP_AgentMT5_EA: Odpowiedź serwera na inicjalizację: ", response);
   
   return true;
}

//+------------------------------------------------------------------+
//| Check for commands from server                                  |
//+------------------------------------------------------------------+
void CheckForCommands()
{
   string url = StringFormat("%s/commands?ea_id=%s", ServerURL, EA_ID);
   string headers = "Content-Type: application/json\r\n";
   string response_headers;
   
   char result[];
   char empty_data[1]; // Pusty bufor dla zapytania GET
   
   int res = WebRequest("GET", url, headers, HTTPTimeout, empty_data, result, response_headers);
   
   if (res == -1)
   {
      int errorCode = GetLastError();
      Print("Simple_HTTP_AgentMT5_EA: Błąd podczas sprawdzania poleceń: ", errorCode);
      return;
   }
   
   // Parsujemy odpowiedź
   string response = CharArrayToString(result);
   
   if (EnableLogging && LogLevel == "DEBUG")
      Print("Simple_HTTP_AgentMT5_EA: Sprawdzanie poleceń, odpowiedź: ", response);
   
   // Proste parsowanie JSON - szukamy poleceń w odpowiedzi
   if (StringFind(response, "\"commands\":[") >= 0)
   {
      // Znajdujemy tablicę poleceń
      int startPos = StringFind(response, "\"commands\":[") + 12;
      int endPos = StringFind(response, "]", startPos);
      
      if (endPos > startPos)
      {
         string commandsArray = StringSubstr(response, startPos, endPos - startPos);
         
         // Jeśli tablica nie jest pusta, parsujemy polecenia
         if (StringLen(commandsArray) > 0)
         {
            // Dzielimy tablicę na poszczególne obiekty JSON
            int commandsCount = 0;
            int curPos = 0;
            
            while (curPos < StringLen(commandsArray))
            {
               // Znajdujemy początek i koniec obiektu JSON
               int objStart = StringFind(commandsArray, "{", curPos);
               if (objStart < 0) break;
               
               // Teraz musimy znaleźć odpowiedni nawias zamykający
               int objEnd = objStart + 1;
               int braceCount = 1;
               
               while (objEnd < StringLen(commandsArray) && braceCount > 0)
               {
                  if (StringGetCharacter(commandsArray, objEnd) == '{') braceCount++;
                  else if (StringGetCharacter(commandsArray, objEnd) == '}') braceCount--;
                  objEnd++;
               }
               
               if (braceCount == 0)
               {
                  // Mamy pełny obiekt JSON
                  string command = StringSubstr(commandsArray, objStart, objEnd - objStart);
                  ProcessCommand(command);
                  commandsCount++;
                  curPos = objEnd;
               }
               else
               {
                  // Coś poszło nie tak z parsowaniem
                  break;
               }
            }
            
            if (commandsCount > 0)
               Print("Simple_HTTP_AgentMT5_EA: Otrzymano ", commandsCount, " poleceń do wykonania");
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Process command from server                                     |
//+------------------------------------------------------------------+
void ProcessCommand(string commandJson)
{
   // Parsowanie JSON dla poleceń
   string action = ExtractJsonString(commandJson, "action");
   
   Print("Simple_HTTP_AgentMT5_EA: Przetwarzanie polecenia: ", action);
   
   if (action == "PING")
   {
      // To jest prosty ping-pong, odpowiadamy PONGiem
      PingServer();
   }
   else if (action == "OPEN_POSITION")
   {
      // Otwieranie pozycji
      string symbol = ExtractJsonString(commandJson, "symbol");
      string typeStr = ExtractJsonString(commandJson, "type");
      double volume = ExtractJsonDouble(commandJson, "volume");
      double price = 0;
      double sl = 0;
      double tp = 0;
      string comment = "";
      
      // Pobranie opcjonalnych parametrów
      if (StringFind(commandJson, "\"price\"") >= 0)
         price = ExtractJsonDouble(commandJson, "price");
      if (StringFind(commandJson, "\"sl\"") >= 0)
         sl = ExtractJsonDouble(commandJson, "sl");
      if (StringFind(commandJson, "\"tp\"") >= 0)
         tp = ExtractJsonDouble(commandJson, "tp");
      if (StringFind(commandJson, "\"comment\"") >= 0)
         comment = ExtractJsonString(commandJson, "comment");
      
      HandleOpenPosition(symbol, typeStr, volume, price, sl, tp, comment);
   }
   else if (action == "CLOSE_POSITION")
   {
      // Zamykanie pozycji
      long ticket = ExtractJsonLong(commandJson, "ticket");
      double volume = 0;
      
      // Pobranie opcjonalnego parametru volume dla częściowego zamknięcia
      if (StringFind(commandJson, "\"volume\"") >= 0)
         volume = ExtractJsonDouble(commandJson, "volume");
      
      HandleClosePosition(ticket, volume);
   }
   else if (action == "MODIFY_POSITION")
   {
      // Modyfikacja pozycji
      long ticket = ExtractJsonLong(commandJson, "ticket");
      double sl = 0;
      double tp = 0;
      
      // Pobranie opcjonalnych parametrów
      if (StringFind(commandJson, "\"sl\"") >= 0)
         sl = ExtractJsonDouble(commandJson, "sl");
      if (StringFind(commandJson, "\"tp\"") >= 0)
         tp = ExtractJsonDouble(commandJson, "tp");
      
      HandleModifyPosition(ticket, sl, tp);
   }
   else if (action == "GET_ACCOUNT_INFO")
   {
      // Wysyłanie informacji o koncie
      SendAccountInfo();
   }
   else
   {
      Print("Simple_HTTP_AgentMT5_EA: Nieznane polecenie: ", action);
   }
}

//+------------------------------------------------------------------+
//| Ping server                                                     |
//+------------------------------------------------------------------+
void PingServer()
{
   string url = ServerURL + "/ping";
   string headers = "Content-Type: application/json\r\n";
   string response_headers;
   
   char result[];
   char empty_data[1]; // Pusty bufor dla zapytania GET
   
   int res = WebRequest("GET", url, headers, HTTPTimeout, empty_data, result, response_headers);
   
   if (res == -1)
   {
      int errorCode = GetLastError();
      if (errorCode == 4060)
      {
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas pingowania serwera: ", errorCode,
            " - Upewnij się, że dodałeś ", url, " do listy dozwolonych URL w narzędziach->opcje->doradcy eksperci");
      }
      else
      {
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas pingowania serwera: ", errorCode);
      }
      return;
   }
   
   string response = CharArrayToString(result);
   if (EnableLogging && LogLevel == "DEBUG")
      Print("Simple_HTTP_AgentMT5_EA: Odpowiedź na ping: ", response);
}

//+------------------------------------------------------------------+
//| Send market data to server                                      |
//+------------------------------------------------------------------+
void SendMarketData()
{
   // Pobieramy aktualny tick
   if (!SymbolInfoTick(Symbol(), lastTick))
   {
      Print("Simple_HTTP_AgentMT5_EA: Nie można pobrać danych ticku");
      return;
   }
   
   string url = ServerURL + "/market_data";
   string headers = "Content-Type: application/json\r\n";
   string response_headers;
   
   // Tworzymy JSON z danymi rynkowymi
   string postData = StringFormat(
      "{\"ea_id\":\"%s\",\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"time\":\"%s\",\"volume\":%I64d,\"spread\":%d}",
      EA_ID,
      Symbol(),
      lastTick.bid,
      lastTick.ask,
      TimeToString(lastTick.time),
      lastTick.volume,
      (int)SymbolInfoInteger(Symbol(), SYMBOL_SPREAD)
   );
   
   char result[];
   char request[];
   StringToCharArray(postData, request);
   
   int res = WebRequest("POST", url, headers, HTTPTimeout, request, result, response_headers);
   
   if (res == -1)
   {
      int errorCode = GetLastError();
      if (errorCode == 4060)
      {
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas wysyłania danych rynkowych: ", errorCode, 
            " - Upewnij się, że dodałeś ", url, " do listy dozwolonych URL w narzędziach->opcje->doradcy eksperci");
      }
      else
      {
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas wysyłania danych rynkowych: ", errorCode);
      }
      return;
   }
   
   string response = CharArrayToString(result);
   if (EnableLogging && LogLevel == "DEBUG")
      Print("Simple_HTTP_AgentMT5_EA: Odpowiedź na wysłanie danych rynkowych: ", response);
}

//+------------------------------------------------------------------+
//| Send positions update to server                                 |
//+------------------------------------------------------------------+
void SendPositionsUpdate()
{
   string url = ServerURL + "/position/update";
   string headers = "Content-Type: application/json\r\n";
   string response_headers;
   
   // Pobieramy wszystkie pozycje i wysyłamy je pojedynczo
   int totalPositions = PositionsTotal();
   
   for (int i = 0; i < totalPositions; i++)
   {
      string symbol = PositionGetSymbol(i);
      if (PositionSelect(symbol))
      {
         long ticket = PositionGetInteger(POSITION_TICKET);
         double volume = PositionGetDouble(POSITION_VOLUME);
         double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
         double currentPrice = PositionGetDouble(POSITION_PRICE_CURRENT);
         double sl = PositionGetDouble(POSITION_SL);
         double tp = PositionGetDouble(POSITION_TP);
         double profit = PositionGetDouble(POSITION_PROFIT);
         datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
         
         // Określamy typ pozycji (buy/sell)
         long posType = PositionGetInteger(POSITION_TYPE);
         string posTypeStr = (posType == POSITION_TYPE_BUY) ? "BUY" : "SELL";
         
         // Tworzymy JSON z danymi pozycji
         string postData = StringFormat(
            "{\"ea_id\":\"%s\",\"ticket\":%I64d,\"symbol\":\"%s\",\"type\":\"%s\",\"volume\":%.2f,\"open_price\":%.5f,\"current_price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"profit\":%.2f,\"open_time\":\"%s\"}",
            EA_ID,
            ticket,
            symbol,
            posTypeStr,
            volume,
            openPrice,
            currentPrice,
            sl,
            tp,
            profit,
            TimeToString(openTime)
         );
         
         char result[];
         char request[];
         StringToCharArray(postData, request);
         
         int res = WebRequest("POST", url, headers, HTTPTimeout, request, result, response_headers);
         
         if (res == -1)
         {
            int errorCode = GetLastError();
            if (errorCode == 4060)
            {
               Print("Simple_HTTP_AgentMT5_EA: Błąd podczas wysyłania aktualizacji pozycji ", ticket, ": ", errorCode, 
                  " - Upewnij się, że dodałeś ", url, " do listy dozwolonych URL w narzędziach->opcje->doradcy eksperci");
               break; // Przerywamy pętlę, bo wszystkie kolejne wywołania też się nie powiodą
            }
            else
            {
               Print("Simple_HTTP_AgentMT5_EA: Błąd podczas wysyłania aktualizacji pozycji ", ticket, ": ", errorCode);
            }
         }
         else
         {
            string response = CharArrayToString(result);
            if (EnableLogging && LogLevel == "DEBUG")
               Print("Simple_HTTP_AgentMT5_EA: Odpowiedź na aktualizację pozycji ", ticket, ": ", response);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Send account info to server                                     |
//+------------------------------------------------------------------+
void SendAccountInfo()
{
   string url = ServerURL + "/account_info";
   string headers = "Content-Type: application/json\r\n";
   string response_headers;
   
   // Tworzymy JSON z informacjami o koncie
   string postData = StringFormat(
      "{\"ea_id\":\"%s\",\"account\":%I64d,\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,\"free_margin\":%.2f,\"currency\":\"%s\",\"profit\":%.2f,\"name\":\"%s\",\"leverage\":%d}",
      EA_ID,
      AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoDouble(ACCOUNT_BALANCE),
      AccountInfoDouble(ACCOUNT_EQUITY),
      AccountInfoDouble(ACCOUNT_MARGIN),
      AccountInfoDouble(ACCOUNT_MARGIN_FREE),
      AccountInfoString(ACCOUNT_CURRENCY),
      AccountInfoDouble(ACCOUNT_PROFIT),
      AccountInfoString(ACCOUNT_NAME),
      (int)AccountInfoInteger(ACCOUNT_LEVERAGE)
   );
   
   char result[];
   char request[];
   StringToCharArray(postData, request);
   
   int res = WebRequest("POST", url, headers, HTTPTimeout, request, result, response_headers);
   
   if (res == -1)
   {
      int errorCode = GetLastError();
      if (errorCode == 4060)
      {
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas wysyłania informacji o koncie: ", errorCode,
            " - Upewnij się, że dodałeś ", url, " do listy dozwolonych URL w narzędziach->opcje->doradcy eksperci");
      }
      else
      {
         Print("Simple_HTTP_AgentMT5_EA: Błąd podczas wysyłania informacji o koncie: ", errorCode);
      }
      return;
   }
   
   string response = CharArrayToString(result);
   if (EnableLogging && LogLevel == "DEBUG")
      Print("Simple_HTTP_AgentMT5_EA: Odpowiedź na wysłanie informacji o koncie: ", response);
}

//+------------------------------------------------------------------+
//| Handle open position                                            |
//+------------------------------------------------------------------+
void HandleOpenPosition(string symbol, string typeStr, double volume, double price = 0, double sl = 0, double tp = 0, string comment = "")
{
   Print("Simple_HTTP_AgentMT5_EA: Próba otwarcia pozycji ", symbol, " ", typeStr, " ", volume);
   
   ENUM_ORDER_TYPE orderType;
   if (typeStr == "BUY")
      orderType = ORDER_TYPE_BUY;
   else if (typeStr == "SELL")
      orderType = ORDER_TYPE_SELL;
   else
   {
      Print("Simple_HTTP_AgentMT5_EA: Nieznany typ zlecenia: ", typeStr);
      return;
   }
   
   // Struktury do przechowywania danych zlecenia i wyniku
   MqlTradeRequest request;
   MqlTradeResult result;
   
   // Przygotowanie zapytania
   ZeroMemory(request);
   ZeroMemory(result);
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = symbol;
   request.volume = volume;
   request.type = orderType;
   
   // Jeśli cena nie jest określona, używamy bieżącej ceny rynkowej
   if (price <= 0)
   {
      MqlTick tick;
      if (SymbolInfoTick(symbol, tick))
      {
         if (orderType == ORDER_TYPE_BUY)
            request.price = tick.ask;
         else
            request.price = tick.bid;
      }
      else
      {
         Print("Simple_HTTP_AgentMT5_EA: Nie można uzyskać danych tick dla ", symbol);
         return;
      }
   }
   else
   {
      request.price = price;
   }
   
   // Dodanie SL i TP
   if (sl > 0)
      request.sl = sl;
   if (tp > 0)
      request.tp = tp;
   
   // Dodanie komentarza
   if (comment != "")
      request.comment = comment;
   
   // Dodatkowe parametry zlecenia
   request.deviation = 5;  // Dopuszczalne odchylenie ceny w punktach
   request.type_filling = ORDER_FILLING_FOK;  // Wykonaj całość lub anuluj
   
   // Wysłanie zlecenia
   bool success = OrderSend(request, result);
   
   // Obsługa wyniku
   if (success && result.retcode == TRADE_RETCODE_DONE)
   {
      Print("Simple_HTTP_AgentMT5_EA: Pozycja otwarta pomyślnie. Ticket: ", result.order);
   }
   else
   {
      Print("Simple_HTTP_AgentMT5_EA: Błąd podczas otwierania pozycji. Kod: ", result.retcode, ", Opis: ", GetErrorDescription(result.retcode));
   }
}

//+------------------------------------------------------------------+
//| Handle close position                                           |
//+------------------------------------------------------------------+
void HandleClosePosition(long ticket, double volume = 0)
{
   Print("Simple_HTTP_AgentMT5_EA: Próba zamknięcia pozycji #", ticket);
   
   // Sprawdzenie czy pozycja istnieje
   if (!PositionSelectByTicket(ticket))
   {
      Print("Simple_HTTP_AgentMT5_EA: Pozycja #", ticket, " nie istnieje");
      return;
   }
   
   // Struktury do przechowywania danych zlecenia i wyniku
   MqlTradeRequest request;
   MqlTradeResult result;
   
   // Przygotowanie zapytania
   ZeroMemory(request);
   ZeroMemory(result);
   
   request.action = TRADE_ACTION_DEAL;
   request.position = ticket;
   
   // Pobieranie danych o pozycji
   string symbol = PositionGetString(POSITION_SYMBOL);
   double posVolume = PositionGetDouble(POSITION_VOLUME);
   ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   
   request.symbol = symbol;
   
   // Jeśli podano volume, zamykamy częściowo
   if (volume > 0 && volume < posVolume)
      request.volume = volume;
   else
      request.volume = posVolume;
   
   // Jeśli pozycja jest BUY, to zamykamy jako SELL i odwrotnie
   if (posType == POSITION_TYPE_BUY)
      request.type = ORDER_TYPE_SELL;
   else
      request.type = ORDER_TYPE_BUY;
   
   // Pobieranie bieżącej ceny
   MqlTick tick;
   if (SymbolInfoTick(symbol, tick))
   {
      if (posType == POSITION_TYPE_BUY)
         request.price = tick.bid;
      else
         request.price = tick.ask;
   }
   else
   {
      Print("Simple_HTTP_AgentMT5_EA: Nie można uzyskać danych tick dla ", symbol);
      return;
   }
   
   // Dodatkowe parametry zlecenia
   request.deviation = 5;  // Dopuszczalne odchylenie ceny w punktach
   request.type_filling = ORDER_FILLING_FOK;  // Wykonaj całość lub anuluj
   
   // Wysłanie zlecenia
   bool success = OrderSend(request, result);
   
   // Obsługa wyniku
   if (success && result.retcode == TRADE_RETCODE_DONE)
   {
      Print("Simple_HTTP_AgentMT5_EA: Pozycja zamknięta pomyślnie. Ticket: ", result.order);
   }
   else
   {
      Print("Simple_HTTP_AgentMT5_EA: Błąd podczas zamykania pozycji. Kod: ", result.retcode, ", Opis: ", GetErrorDescription(result.retcode));
   }
}

//+------------------------------------------------------------------+
//| Handle modify position                                          |
//+------------------------------------------------------------------+
void HandleModifyPosition(long ticket, double sl, double tp)
{
   Print("Simple_HTTP_AgentMT5_EA: Próba modyfikacji pozycji #", ticket, " SL=", sl, " TP=", tp);
   
   // Sprawdzenie czy pozycja istnieje
   if (!PositionSelectByTicket(ticket))
   {
      Print("Simple_HTTP_AgentMT5_EA: Pozycja #", ticket, " nie istnieje");
      return;
   }
   
   // Sprawdzenie czy SL lub TP są różne od obecnych
   double currentSL = PositionGetDouble(POSITION_SL);
   double currentTP = PositionGetDouble(POSITION_TP);
   
   if ((sl <= 0 || MathAbs(sl - currentSL) < 0.00001) && 
       (tp <= 0 || MathAbs(tp - currentTP) < 0.00001))
   {
      Print("Simple_HTTP_AgentMT5_EA: Modyfikacja nie jest potrzebna, wartości SL i TP są takie same");
      return;
   }
   
   // Struktury do przechowywania danych zlecenia i wyniku
   MqlTradeRequest request;
   MqlTradeResult result;
   
   // Przygotowanie zapytania
   ZeroMemory(request);
   ZeroMemory(result);
   
   request.action = TRADE_ACTION_SLTP;
   request.symbol = PositionGetString(POSITION_SYMBOL);
   request.position = ticket;
   
   // Ustawienie nowych wartości SL i TP
   if (sl > 0)
      request.sl = sl;
   else
      request.sl = currentSL;  // Zachowanie obecnego SL
   
   if (tp > 0)
      request.tp = tp;
   else
      request.tp = currentTP;  // Zachowanie obecnego TP
   
   // Wysłanie zlecenia
   bool success = OrderSend(request, result);
   
   // Obsługa wyniku
   if (success && result.retcode == TRADE_RETCODE_DONE)
   {
      Print("Simple_HTTP_AgentMT5_EA: Pozycja zmodyfikowana pomyślnie");
   }
   else
   {
      Print("Simple_HTTP_AgentMT5_EA: Błąd podczas modyfikacji pozycji. Kod: ", result.retcode, ", Opis: ", GetErrorDescription(result.retcode));
   }
}

//+------------------------------------------------------------------+
//| Get error description                                           |
//+------------------------------------------------------------------+
string GetErrorDescription(int errorCode)
{
   switch(errorCode)
   {
      case TRADE_RETCODE_REQUOTE: return "Requote";
      case TRADE_RETCODE_REJECT: return "Request rejected";
      case TRADE_RETCODE_CANCEL: return "Request canceled";
      case TRADE_RETCODE_PLACED: return "Order placed";
      case TRADE_RETCODE_DONE: return "Request completed";
      case TRADE_RETCODE_DONE_PARTIAL: return "Request completed partially";
      case TRADE_RETCODE_ERROR: return "Request processing error";
      case TRADE_RETCODE_TIMEOUT: return "Request canceled by timeout";
      case TRADE_RETCODE_INVALID: return "Invalid request";
      case TRADE_RETCODE_INVALID_VOLUME: return "Invalid volume";
      case TRADE_RETCODE_INVALID_PRICE: return "Invalid price";
      case TRADE_RETCODE_INVALID_STOPS: return "Invalid stops";
      case TRADE_RETCODE_TRADE_DISABLED: return "Trade is disabled";
      case TRADE_RETCODE_MARKET_CLOSED: return "Market is closed";
      case TRADE_RETCODE_NO_MONEY: return "Not enough money";
      case TRADE_RETCODE_PRICE_CHANGED: return "Price changed";
      case TRADE_RETCODE_PRICE_OFF: return "No quotes";
      case TRADE_RETCODE_INVALID_EXPIRATION: return "Invalid expiration";
      case TRADE_RETCODE_ORDER_CHANGED: return "Order changed";
      case TRADE_RETCODE_TOO_MANY_REQUESTS: return "Too many requests";
      case TRADE_RETCODE_NO_CHANGES: return "No changes in request";
      case TRADE_RETCODE_SERVER_DISABLES_AT: return "Autotrading disabled by server";
      case TRADE_RETCODE_CLIENT_DISABLES_AT: return "Autotrading disabled by client";
      case TRADE_RETCODE_LOCKED: return "Request locked";
      case TRADE_RETCODE_FROZEN: return "Order or position frozen";
      case TRADE_RETCODE_INVALID_FILL: return "Invalid order filling type";
      case TRADE_RETCODE_CONNECTION: return "No connection";
      case TRADE_RETCODE_ONLY_REAL: return "Operation available only for real accounts";
      case TRADE_RETCODE_LIMIT_ORDERS: return "Limit of pending orders reached";
      case TRADE_RETCODE_LIMIT_VOLUME: return "Limit of volume for this symbol reached";
      case TRADE_RETCODE_INVALID_ORDER: return "Invalid or prohibited order type";
      case TRADE_RETCODE_POSITION_CLOSED: return "Position already closed";
      default: return StringFormat("Unknown error %d", errorCode);
   }
}

//+------------------------------------------------------------------+ 