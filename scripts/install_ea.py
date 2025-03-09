#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do instalacji Expert Advisora w MetaTrader 5
"""

import os
import sys
import shutil
from pathlib import Path
import logging
import argparse
import winreg

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("EA_Installer")

def find_mt5_terminals():
    """Znajduje ścieżki do terminali MT5 zainstalowanych na komputerze."""
    terminals = []
    
    try:
        # Próbujemy otworzyć klucz rejestru z instalacjami MT5
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
        
        # Sprawdzamy każdy podklucz
        i = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(registry_key, i)
                subkey = winreg.OpenKey(registry_key, subkey_name)
                
                try:
                    display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                    install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                    
                    if "MetaTrader 5" in display_name:
                        terminals.append(install_location)
                except:
                    pass
                
                winreg.CloseKey(subkey)
                i += 1
            except WindowsError:
                break
        
        winreg.CloseKey(registry_key)
    except Exception as e:
        logger.warning(f"Nie udało się znaleźć instalacji MT5 w rejestrze: {str(e)}")
    
    # Sprawdzamy typowe lokalizacje
    typical_paths = [
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'MetaTrader 5'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'MetaTrader 5')
    ]
    
    for path in typical_paths:
        if os.path.exists(path) and path not in terminals:
            terminals.append(path)
    
    return terminals

def find_mt5_data_folders():
    """Znajduje foldery danych MT5 w AppData."""
    data_folders = []
    
    try:
        appdata_path = os.path.join(os.environ.get('APPDATA', ''), 'MetaQuotes', 'Terminal')
        
        if os.path.exists(appdata_path):
            # Dla każdego identyfikatora instalacji
            for terminal_id in os.listdir(appdata_path):
                terminal_path = os.path.join(appdata_path, terminal_id)
                
                # Sprawdzamy czy to rzeczywiście folder danych MT5
                if os.path.isdir(terminal_path) and os.path.exists(os.path.join(terminal_path, 'MQL5')):
                    data_folders.append(terminal_path)
    except Exception as e:
        logger.warning(f"Nie udało się znaleźć folderów danych MT5: {str(e)}")
    
    return data_folders

def install_ea(mt5_path, source_dir):
    """Instaluje pliki EA w folderze MT5."""
    try:
        # Ścieżka do katalogu Experts
        experts_path = os.path.join(mt5_path, 'MQL5', 'Experts', 'AgentMT5')
        
        # Tworzymy katalog docelowy, jeśli nie istnieje
        os.makedirs(experts_path, exist_ok=True)
        
        # Kopiujemy pliki EA
        ea_files = {
            'AgentMT5_EA.mq5': os.path.join(source_dir, 'src', 'mt5_ea', 'AgentMT5_EA.mq5'),
            'Communication.mqh': os.path.join(source_dir, 'src', 'mt5_ea', 'Communication.mqh'),
            'ErrorHandler.mqh': os.path.join(source_dir, 'src', 'mt5_ea', 'ErrorHandler.mqh'),
            'Logger.mqh': os.path.join(source_dir, 'src', 'mt5_ea', 'Logger.mqh')
        }
        
        for dest_name, source_path in ea_files.items():
            if os.path.exists(source_path):
                dest_path = os.path.join(experts_path, dest_name)
                shutil.copy2(source_path, dest_path)
                logger.info(f"Skopiowano {source_path} -> {dest_path}")
            else:
                logger.error(f"Nie znaleziono pliku źródłowego: {source_path}")
        
        logger.info(f"Pliki EA zostały zainstalowane w: {experts_path}")
        logger.info("Teraz musisz skompilować EA w MetaEditor!")
        logger.info("1. Uruchom MetaEditor (F4 w MT5)")
        logger.info("2. Otwórz plik AgentMT5_EA.mq5")
        logger.info("3. Skompiluj projekt (F7)")
        
        return True
    except Exception as e:
        logger.error(f"Błąd podczas instalacji EA: {str(e)}")
        return False

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description='Instalator Expert Advisora dla MetaTrader 5')
    parser.add_argument('--path', type=str, help='Ścieżka do folderu danych MT5 (opcjonalnie)')
    
    args = parser.parse_args()
    
    # Ścieżka do katalogu projektu
    project_dir = str(Path(__file__).parent.parent)
    
    if args.path:
        # Instalujemy w podanej ścieżce
        install_ea(args.path, project_dir)
    else:
        # Szukamy instalacji MT5
        data_folders = find_mt5_data_folders()
        
        if not data_folders:
            logger.error("Nie znaleziono folderów danych MT5!")
            logger.info("Upewnij się, że MetaTrader 5 jest zainstalowany i uruchomiony przynajmniej raz.")
            logger.info("Możesz podać ścieżkę ręcznie używając parametru --path.")
            return 1
        
        # Wyświetlamy znalezione foldery
        logger.info(f"Znaleziono {len(data_folders)} folderów danych MT5:")
        for i, folder in enumerate(data_folders):
            logger.info(f"{i+1}. {folder}")
        
        # Pytamy użytkownika, który folder wybrać
        if len(data_folders) > 1:
            while True:
                try:
                    choice = input("Wybierz numer folderu (lub 'q' aby zakończyć): ")
                    if choice.lower() == 'q':
                        return 0
                    
                    choice = int(choice)
                    if 1 <= choice <= len(data_folders):
                        selected_folder = data_folders[choice-1]
                        break
                    else:
                        logger.error(f"Podaj liczbę od 1 do {len(data_folders)}")
                except ValueError:
                    logger.error("Podaj poprawną liczbę lub 'q'")
        else:
            selected_folder = data_folders[0]
            
        # Instalujemy EA
        install_ea(selected_folder, project_dir)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 