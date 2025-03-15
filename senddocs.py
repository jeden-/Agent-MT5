#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import ftplib
import sys
import socket
from datetime import datetime
import logging
import argparse
import getpass

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('senddocs')

# Domyślna konfiguracja FTP
DEFAULT_FTP_HOST = "mainpress.ftp.dhosting.pl"
DEFAULT_FTP_USER = "faih4e_wawrzenp"
DEFAULT_FTP_PASS = "AgentMT%@!2025"
DEFAULT_FTP_DIR = "/public_html/AgentMT5"

# Lokalizacja dokumentacji
LOCAL_DOCS_DIR = r"C:\Users\win\Documents\AgentMT5\docs\sphinx\build\html"

def upload_file(ftp, local_path, remote_path):
    """Wysyła pojedynczy plik na serwer FTP."""
    try:
        with open(local_path, 'rb') as file:
            ftp.storbinary(f'STOR {remote_path}', file)
        logger.info(f"Wysłano plik: {remote_path}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania pliku {local_path}: {e}")
        return False

def upload_directory(ftp, local_dir, remote_dir):
    """Rekurencyjnie wysyła cały katalog na serwer FTP."""
    
    # Sprawdź, czy katalog zdalny istnieje, jeśli nie - utwórz go
    try:
        ftp.cwd(remote_dir)
    except ftplib.error_perm:
        try:
            ftp.mkd(remote_dir)
            ftp.cwd(remote_dir)
            logger.info(f"Utworzono katalog: {remote_dir}")
        except ftplib.error_perm as e:
            logger.error(f"Nie można utworzyć katalogu {remote_dir}: {e}")
            return False

    # Wysyłanie plików i katalogów
    success = True
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = item
        
        if os.path.isfile(local_path):
            if not upload_file(ftp, local_path, remote_path):
                success = False
        elif os.path.isdir(local_path):
            # Zapamiętaj bieżący katalog
            current_dir = ftp.pwd()
            # Rekurencyjnie wyślij podkatalog
            if not upload_directory(ftp, local_path, remote_path):
                success = False
            # Wróć do poprzedniego katalogu
            ftp.cwd(current_dir)

    return success

def test_connection(host, user, password, timeout=30):
    """Testuje połączenie z serwerem FTP bez wysyłania plików."""
    logger.info(f"Testowanie połączenia z serwerem {host}...")
    try:
        ftp = ftplib.FTP(host, timeout=timeout)
        ftp.login(user, password)
        logger.info(f"Połączenie udane. Zalogowano jako {user}")
        logger.info(f"Bieżący katalog: {ftp.pwd()}")
        logger.info("Dostępne katalogi:")
        ftp.dir()
        ftp.quit()
        return True
    except ftplib.error_perm as e:
        if "530" in str(e):
            logger.error(f"Błąd logowania: {e} - Niepoprawny login lub hasło")
        else:
            logger.error(f"Błąd uprawnień: {e}")
        return False
    except socket.timeout:
        logger.error(f"Timeout podczas łączenia z {host}")
        return False
    except socket.gaierror as e:
        logger.error(f"Błąd adresu serwera: {e}")
        return False
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas testowania połączenia: {e}")
        return False

def get_credentials(args):
    """Pobiera dane logowania na podstawie argumentów wiersza poleceń lub interaktywnie."""
    host = args.host if args.host else DEFAULT_FTP_HOST
    user = args.user if args.user else DEFAULT_FTP_USER
    password = args.password if args.password else DEFAULT_FTP_PASS
    ftp_dir = args.dir if args.dir else DEFAULT_FTP_DIR
    
    # Jeśli użytkownik wybrał tryb interaktywny, zapytaj o dane
    if args.interactive:
        print("\n=== Wprowadź dane logowania do serwera FTP ===")
        host = input(f"Host [{host}]: ") or host
        user = input(f"Login [{user}]: ") or user
        password = getpass.getpass(f"Hasło (domyślne ukryte): ") or password
        ftp_dir = input(f"Katalog docelowy [{ftp_dir}]: ") or ftp_dir
    
    return host, user, password, ftp_dir

def main(args=None):
    if not args:
        args = parser.parse_args()
    
    # Pobierz dane logowania
    host, user, password, ftp_dir = get_credentials(args)
    
    if args.test_connection:
        return test_connection(host, user, password)
        
    start_time = datetime.now()
    logger.info(f"Rozpoczęcie synchronizacji dokumentacji o {start_time.strftime('%H:%M:%S')}")
    
    try:
        # Sprawdź, czy katalog źródłowy istnieje
        if not os.path.exists(LOCAL_DOCS_DIR):
            logger.error(f"Katalog źródłowy nie istnieje: {LOCAL_DOCS_DIR}")
            return False
        
        # Połącz z serwerem FTP
        logger.info(f"Łączenie z serwerem FTP: {host}")
        try:
            ftp = ftplib.FTP(host, timeout=30)
            try:
                ftp.login(user, password)
                logger.info("Zalogowano pomyślnie")
            except ftplib.error_perm as e:
                if "530" in str(e):
                    logger.error(f"Błąd logowania: {e} - Niepoprawny login lub hasło")
                else:
                    logger.error(f"Błąd uprawnień: {e}")
                return False
        except socket.timeout:
            logger.error(f"Timeout podczas łączenia z {host}")
            return False
        except socket.gaierror as e:
            logger.error(f"Błąd adresu serwera: {e}")
            return False
        
        # Przejdź do katalogu docelowego
        try:
            # Upewnij się, że ścieżka katalogu istnieje
            dirs = ftp_dir.split('/')
            current_dir = ""
            
            for d in dirs:
                if not d:
                    continue
                
                current_dir += f"/{d}"
                try:
                    ftp.cwd(current_dir)
                except ftplib.error_perm:
                    try:
                        ftp.mkd(current_dir)
                        ftp.cwd(current_dir)
                        logger.info(f"Utworzono katalog: {current_dir}")
                    except ftplib.error_perm as e:
                        logger.error(f"Nie można utworzyć katalogu {current_dir}: {e}")
                        ftp.quit()
                        return False
            
            # Wróć do katalogu głównego i przejdź bezpośrednio do docelowego
            ftp.cwd(ftp_dir)
            logger.info(f"Przejście do katalogu docelowego: {ftp_dir}")
            
        except ftplib.error_perm as e:
            logger.error(f"Błąd podczas przechodzenia do katalogu docelowego: {e}")
            ftp.quit()
            return False
        
        # Wyślij dokumentację
        success = upload_directory(ftp, LOCAL_DOCS_DIR, '.')
        
        # Zakończ połączenie
        ftp.quit()
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Zakończono synchronizację dokumentacji w {duration.total_seconds():.2f} sekund")
        
        if success:
            logger.info(f"Dokumentacja została pomyślnie wysłana na {host}{ftp_dir}")
            # Prawidłowy adres do dokumentacji
            logger.info(f"Dostępna pod adresem: https://wawrzen.pl/")
        
        return success
        
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Wysyła dokumentację na serwer FTP')
    parser.add_argument('--test', dest='test_connection', action='store_true',
                      help='Testuj tylko połączenie z serwerem FTP bez wysyłania plików')
    parser.add_argument('-i', '--interactive', action='store_true',
                      help='Tryb interaktywny - poproś o dane logowania')
    parser.add_argument('--host', help=f'Adres serwera FTP (domyślnie: {DEFAULT_FTP_HOST})')
    parser.add_argument('--user', help=f'Nazwa użytkownika FTP (domyślnie: {DEFAULT_FTP_USER})')
    parser.add_argument('--password', help='Hasło FTP (lepiej podać interaktywnie)')
    parser.add_argument('--dir', help=f'Katalog docelowy na serwerze (domyślnie: {DEFAULT_FTP_DIR})')
    
    args = parser.parse_args()
    
    try:
        if main(args):
            logger.info("Synchronizacja zakończona pomyślnie")
            sys.exit(0)
        else:
            logger.error("Synchronizacja zakończona z błędami")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Przerwano przez użytkownika")
        sys.exit(1) 