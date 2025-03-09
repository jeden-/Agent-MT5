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
   // Proste parsowanie JSON dla poleceń
   string commandType = ExtractJsonString(commandJson, "command");
   string commandId = ExtractJsonString(commandJson, "id");
   
   Print("Simple_HTTP_AgentMT5_EA: Przetwarzanie polecenia: ", commandType, ", ID: ", commandId);
   
   if (commandType == "PING")
   {
      // To jest prosty ping-pong, odpowiadamy PONGiem
      PingServer();
   }
   else if (commandType == "OPEN_POSITION")
   {
      // Otwieranie pozycji
      string dataObject = ExtractJsonObject(commandJson, "data");
      if (dataObject != "")
      {
         string symbol = ExtractJsonString(dataObject, "symbol");
         string typeStr = ExtractJsonString(dataObject, "type");
         double volume = ExtractJsonDouble(dataObject, "volume");
         double price = ExtractJsonDouble(dataObject, "price");
         double sl = ExtractJsonDouble(dataObject, "sl");
         double tp = ExtractJsonDouble(dataObject, "tp");
         
         HandleOpenPosition(symbol, typeStr, volume, price, sl, tp);
      }
   }
   else if (commandType == "CLOSE_POSITION")
   {
      // Zamykanie pozycji
      string dataObject = ExtractJsonObject(commandJson, "data");
      if (dataObject != "")
      {
         long ticket = ExtractJsonLong(dataObject, "ticket");
         HandleClosePosition(ticket);
      }
   }
   else if (commandType == "MODIFY_POSITION")
   {
      // Modyfikacja pozycji
      string dataObject = ExtractJsonObject(commandJson, "data");
      if (dataObject != "")
      {
         long ticket = ExtractJsonLong(dataObject, "ticket");
         double sl = ExtractJsonDouble(dataObject, "sl");
         double tp = ExtractJsonDouble(dataObject, "tp");
         HandleModifyPosition(ticket, sl, tp);
      }
   }
   else if (commandType == "GET_ACCOUNT_INFO")
   {
      // Wysyłanie informacji o koncie
      SendAccountInfo();
   }
   else
   {
      Print("Simple_HTTP_AgentMT5_EA: Nieznane polecenie: ", commandType);
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
//| Handle open position command                                    |
//+------------------------------------------------------------------+
void HandleOpenPosition(string symbol, string typeStr, double volume, double price, double sl, double tp)
{
   // Weryfikacja danych
   if (symbol == "" || typeStr == "" || volume <= 0)
   {
      Print("Simple_HTTP_AgentMT5_EA: Nieprawidłowe dane dla otwarcia pozycji");
      return;
   }
   
   // Określamy typ zlecenia
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
   
   // Pobieramy aktualną cenę, jeśli nie jest podana
   if (price <= 0)
   {
      MqlTick tick;
      if (SymbolInfoTick(symbol, tick))
      {
         if (orderType == ORDER_TYPE_BUY)
            price = tick.ask;
         else
            price = tick.bid;
      }
      else
      {
         Print("Simple_HTTP_AgentMT5_EA: Nie można pobrać danych ticku dla symbolu ", symbol);
         return;
      }
   }
   
   // Otwieramy pozycję
   Trade.SetExpertMagicNumber(EA_MAGIC);
   if (!Trade.PositionOpen(symbol, orderType, volume, price, sl, tp, "Simple_HTTP_AgentMT5_EA"))
   {
      Print("Simple_HTTP_AgentMT5_EA: Błąd otwarcia pozycji: ", GetLastError());
      return;
   }
   
   Print("Simple_HTTP_AgentMT5_EA: Pozycja otwarta pomyślnie. Ticket: ", Trade.ResultOrder());
}

//+------------------------------------------------------------------+
//| Handle close position command                                   |
//+------------------------------------------------------------------+
void HandleClosePosition(long ticket)
{
   // Weryfikacja danych
   if (ticket <= 0)
   {
      Print("Simple_HTTP_AgentMT5_EA: Nieprawidłowy ticket dla zamknięcia pozycji");
      return;
   }
   
   // Wybieramy pozycję
   if (!PositionSelectByTicket(ticket))
   {
      Print("Simple_HTTP_AgentMT5_EA: Nie można znaleźć pozycji z ticketem: ", ticket);
      return;
   }
   
   // Zamykamy pozycję
   Trade.SetExpertMagicNumber(EA_MAGIC);
   if (!Trade.PositionClose(ticket))
   {
      Print("Simple_HTTP_AgentMT5_EA: Błąd zamknięcia pozycji: ", GetLastError());
      return;
   }
   
   Print("Simple_HTTP_AgentMT5_EA: Pozycja zamknięta pomyślnie. Ticket: ", ticket);
}

//+------------------------------------------------------------------+
//| Handle modify position command                                  |
//+------------------------------------------------------------------+
void HandleModifyPosition(long ticket, double sl, double tp)
{
   // Weryfikacja danych
   if (ticket <= 0)
   {
      Print("Simple_HTTP_AgentMT5_EA: Nieprawidłowy ticket dla modyfikacji pozycji");
      return;
   }
   
   // Wybieramy pozycję
   if (!PositionSelectByTicket(ticket))
   {
      Print("Simple_HTTP_AgentMT5_EA: Nie można znaleźć pozycji z ticketem: ", ticket);
      return;
   }
   
   // Modyfikujemy pozycję
   Trade.SetExpertMagicNumber(EA_MAGIC);
   if (!Trade.PositionModify(ticket, sl, tp))
   {
      Print("Simple_HTTP_AgentMT5_EA: Błąd modyfikacji pozycji: ", GetLastError());
      return;
   }
   
   Print("Simple_HTTP_AgentMT5_EA: Pozycja zmodyfikowana pomyślnie. Ticket: ", ticket);
}

//+------------------------------------------------------------------+
//| Trade function                                                   |
//+------------------------------------------------------------------+
void OnTrade()
{
   // Przy każdej zmianie w handlu, aktualizujemy pozycje
   SendPositionsUpdate();
}

//+------------------------------------------------------------------+
//| Pomocnicze funkcje do parsowania JSON                           |
//+------------------------------------------------------------------+

// Funkcja pomocnicza do wyciągania wartości string z JSON
string ExtractJsonString(string json, string key)
{
   string keyPattern = "\"" + key + "\":\"";
   int pos = StringFind(json, keyPattern);
   if (pos >= 0)
   {
      int startPos = pos + StringLen(keyPattern);
      int endPos = StringFind(json, "\"", startPos);
      if (endPos >= 0)
      {
         return StringSubstr(json, startPos, endPos - startPos);
      }
   }
   return "";
}

// Funkcja pomocnicza do wyciągania wartości numerycznej z JSON
double ExtractJsonDouble(string json, string key)
{
   string keyPattern = "\"" + key + "\":";
   int pos = StringFind(json, keyPattern);
   if (pos >= 0)
   {
      int startPos = pos + StringLen(keyPattern);
      int endPos = StringFind(json, ",", startPos);
      if (endPos < 0) endPos = StringFind(json, "}", startPos);
      if (endPos >= 0)
      {
         string numStr = StringSubstr(json, startPos, endPos - startPos);
         return StringToDouble(numStr);
      }
   }
   return 0.0;
}

// Funkcja pomocnicza do wyciągania liczby całkowitej z JSON
long ExtractJsonLong(string json, string key)
{
   string keyPattern = "\"" + key + "\":";
   int pos = StringFind(json, keyPattern);
   if (pos >= 0)
   {
      int startPos = pos + StringLen(keyPattern);
      int endPos = StringFind(json, ",", startPos);
      if (endPos < 0) endPos = StringFind(json, "}", startPos);
      if (endPos >= 0)
      {
         string numStr = StringSubstr(json, startPos, endPos - startPos);
         return StringToInteger(numStr);
      }
   }
   return 0;
}

// Funkcja pomocnicza do wyciągania obiektu JSON z innego JSON
string ExtractJsonObject(string json, string key)
{
   string keyPattern = "\"" + key + "\":{";
   int pos = StringFind(json, keyPattern);
   if (pos >= 0)
   {
      int startPos = pos + StringLen(keyPattern) - 1; // -1 żeby zachować początkowy nawias "{"
      int braceCount = 1;
      int endPos = startPos + 1;
      
      while (endPos < StringLen(json) && braceCount > 0)
      {
         if (StringGetCharacter(json, endPos) == '{') braceCount++;
         else if (StringGetCharacter(json, endPos) == '}') braceCount--;
         endPos++;
      }
      
      if (braceCount == 0)
      {
         return StringSubstr(json, startPos, endPos - startPos);
      }
   }
   return "";
}

//+------------------------------------------------------------------+ 