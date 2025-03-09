#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt konfigurujący parametry połączenia do bazy danych PostgreSQL.
Tworzy plik .env z parametrami połączenia.
"""

import os
import sys
import argparse
from getpass import getpass
from dotenv import load_dotenv

def parse_args():
    """Parsuje argumenty wiersza poleceń."""
    parser = argparse.ArgumentParser(description='Konfiguracja połączenia do bazy danych PostgreSQL')
    
    parser.add_argument('--host', default='localhost', help='Host bazy danych (domyślnie: localhost)')
    parser.add_argument('--port', type=int, default=5432, help='Port bazy danych (domyślnie: 5432)')
    parser.add_argument('--db', default='agent_mt5', help='Nazwa bazy danych (domyślnie: agent_mt5)')
    parser.add_argument('--user', help='Nazwa użytkownika bazy danych')
    parser.add_argument('--password', help='Hasło użytkownika bazy danych (jeśli nie podane, zostaniesz poproszony o wprowadzenie)')
    parser.add_argument('--force', action='store_true', help='Nadpisz istniejący plik .env bez pytania')
    
    return parser.parse_args()

def setup_postgres_env(host, port, db, user, password, force=False):
    """Tworzy plik .env z parametrami połączenia do bazy danych PostgreSQL."""
    env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    # Sprawdzenie, czy plik .env już istnieje
    if os.path.exists(env_file_path) and not force:
        overwrite = input(f"Plik .env już istnieje. Nadpisać? [t/N]: ")
        if overwrite.lower() != 't':
            print("Operacja anulowana.")
            return
    
    # Wczytanie istniejących zmiennych środowiskowych, jeśli plik istnieje
    existing_env = {}
    if os.path.exists(env_file_path):
        load_dotenv(env_file_path)
        for key in os.environ:
            existing_env[key] = os.environ.get(key)
    
    # Aktualizacja zmiennych środowiskowych dla bazy danych
    existing_env['DB_HOST'] = host
    existing_env['DB_PORT'] = str(port)
    existing_env['DB_NAME'] = db
    existing_env['DB_USER'] = user
    existing_env['DB_PASSWORD'] = password
    
    # Zapisanie zmiennych do pliku .env
    with open(env_file_path, 'w', encoding='utf-8') as env_file:
        for key, value in existing_env.items():
            env_file.write(f"{key}={value}\n")
    
    print(f"Plik .env został utworzony w {env_file_path}")
    print(f"Parametry połączenia do bazy danych PostgreSQL zostały skonfigurowane:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Baza danych: {db}")
    print(f"  Użytkownik: {user}")
    print(f"  Hasło: {'*' * len(password)}")

def main():
    """Główna funkcja programu."""
    args = parse_args()
    
    # Jeśli hasło nie zostało podane, poproś o nie
    password = args.password
    if not password:
        password = getpass("Podaj hasło do bazy danych: ")
    
    # Jeśli użytkownik nie został podany, użyj domyślnego
    user = args.user
    if not user:
        user = input("Podaj nazwę użytkownika bazy danych (domyślnie: postgres): ") or 'postgres'
    
    setup_postgres_env(args.host, args.port, args.db, user, password, args.force)

if __name__ == "__main__":
    main() 