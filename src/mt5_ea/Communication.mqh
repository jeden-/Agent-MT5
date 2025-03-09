//+------------------------------------------------------------------+
//|                                               Communication.mqh |
//|                                         AgentMT5 Trading System |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "AgentMT5 Trading System"
#property link      ""
#property version   "1.00"
#property strict

// Dołączamy potrzebne pliki
#include "Logger.mqh"
#include "ErrorHandler.mqh"

// Definicje stałych
#define SOCKET_TIMEOUT    1000  // Timeout w ms
#define MAX_BUFFER_SIZE   1024  // Maksymalny rozmiar bufora

//+------------------------------------------------------------------+
//| Klasa odpowiedzialna za komunikację z systemem Python            |
//+------------------------------------------------------------------+
class Communication
{
private:
   int         m_socket;          // Socket do komunikacji
   string      m_address;         // Adres serwera
   int         m_port;            // Port serwera
   int         m_timeout;         // Timeout połączenia
   Logger*     m_logger;          // Wskaźnik na logger
   ErrorHandler* m_errorHandler;  // Wskaźnik na obsługę błędów
   
   // Inicjalizacja socketu
   bool InitializeSocket()
   {
      // Tworzymy socket jeśli nie istnieje
      if(m_socket == INVALID_HANDLE)
      {
         m_socket = SocketCreate(SOCKET_DEFAULT);
         if(m_socket == INVALID_HANDLE)
         {
            m_errorHandler.LogError("InitializeSocket", "Nie można utworzyć socketu");
            return false;
         }
      }
      return true;
   }
   
   // Zamknięcie socketu
   void CloseSocket()
   {
      if(m_socket != INVALID_HANDLE)
      {
         SocketClose(m_socket);
         m_socket = INVALID_HANDLE;
      }
   }
   
   // Połączenie z serwerem
   bool ConnectToServer()
   {
      // Sprawdzamy, czy socket został zainicjalizowany
      if(m_socket == INVALID_HANDLE)
      {
         if(!InitializeSocket())
            return false;
      }
      
      // Ustawiamy timeout
      SocketSetTimeout(m_socket, m_timeout);
      
      // Próbujemy połączyć z serwerem
      if(!SocketConnect(m_socket, m_address, m_port))
      {
         m_errorHandler.LogError("ConnectToServer", StringFormat("Nie można połączyć z %s:%d", m_address, m_port));
         CloseSocket();
         return false;
      }
      
      m_logger.Log(LOG_INFO, StringFormat("Połączono z serwerem Python: %s:%d", m_address, m_port));
      return true;
   }
   
public:
   // Konstruktor
   Communication(string address, int port, int timeout, Logger* logger, ErrorHandler* errorHandler)
   {
      m_socket = INVALID_HANDLE;
      m_address = address;
      m_port = port;
      m_timeout = timeout;
      m_logger = logger;
      m_errorHandler = errorHandler;
   }
   
   // Destruktor
   ~Communication()
   {
      Close();
   }
   
   // Inicjalizacja komunikacji
   bool Initialize()
   {
      return InitializeSocket();
   }
   
   // Zamknięcie komunikacji
   void Close()
   {
      if(m_socket != INVALID_HANDLE)
      {
         // Wysyłamy wiadomość zamknięcia, jeśli to możliwe
         SendMessage("CLOSE", "EA shutting down");
         
         // Zamykamy socket
         CloseSocket();
         m_logger.Log(LOG_INFO, "Zamknięto połączenie z serwerem Python");
      }
   }
   
   // Wysłanie wiadomości do serwera Python
   bool SendMessage(string messageType, string messageData)
   {
      // Sprawdzamy, czy socket jest otwarty, jeśli nie, próbujemy połączyć
      if(m_socket == INVALID_HANDLE)
      {
         if(!ConnectToServer())
            return false;
      }
      
      // Formatujemy wiadomość: MESSAGE_TYPE:MESSAGE_DATA\n
      string message = StringFormat("%s:%s\n", messageType, messageData);
      
      // Wysyłamy wiadomość
      char buffer[];
      StringToCharArray(message, buffer);
      int bytesSent = SocketSend(m_socket, buffer, ArraySize(buffer) - 1); // -1 aby pominąć zerowy terminator
      
      if(bytesSent <= 0)
      {
         m_errorHandler.LogError("SendMessage", StringFormat("Nie można wysłać wiadomości: %s", message));
         CloseSocket(); // Zamykamy socket, aby ponownie połączyć przy następnej próbie
         return false;
      }
      
      m_logger.Log(LOG_DEBUG, StringFormat("Wysłano wiadomość [%s]: %s", messageType, messageData));
      return true;
   }
   
   // Odbieranie komendy z serwera Python
   string ReceiveCommand()
   {
      // Sprawdzamy, czy socket jest otwarty, jeśli nie, próbujemy połączyć
      if(m_socket == INVALID_HANDLE)
      {
         if(!ConnectToServer())
            return "";
      }
      
      // Sprawdzamy, czy są dostępne dane do odczytu
      if(!SocketIsReadable(m_socket))
         return "";
      
      // Odbieramy dane
      char buffer[];
      ArrayResize(buffer, MAX_BUFFER_SIZE);
      ZeroMemory(buffer);
      
      int bytesRead = SocketRead(m_socket, buffer, ArraySize(buffer) - 1, SOCKET_TIMEOUT);
      
      if(bytesRead <= 0)
      {
         // Jeśli nie ma danych lub wystąpił błąd, zwracamy pusty string
         if(bytesRead < 0)
         {
            m_errorHandler.LogError("ReceiveCommand", "Błąd odczytu z socketu");
            CloseSocket(); // Zamykamy socket, aby ponownie połączyć przy następnej próbie
         }
         return "";
      }
      
      // Konwertujemy dane na string
      string command = CharArrayToString(buffer, 0, bytesRead);
      // Usuwamy białe znaki na końcu
      command = StringTrimRight(command);
      
      if(command != "")
         m_logger.Log(LOG_DEBUG, StringFormat("Odebrano komendę: %s", command));
         
      return command;
   }
   
   // Sprawdzenie, czy połączenie jest aktywne
   bool IsConnected()
   {
      return m_socket != INVALID_HANDLE && SocketIsConnected(m_socket);
   }
}; 