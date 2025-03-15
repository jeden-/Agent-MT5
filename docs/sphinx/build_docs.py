#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do budowania dokumentacji Sphinx dla projektu AgentMT5.
Automatycznie kopiuje pliki Markdown z głównego katalogu docs do struktury Sphinx.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ścieżki
ROOT_DIR = Path(__file__).parent.parent.parent
DOCS_DIR = ROOT_DIR / "docs"
SPHINX_DIR = DOCS_DIR / "sphinx"
SPHINX_SOURCE_DIR = SPHINX_DIR / "source"
SPHINX_BUILD_DIR = SPHINX_DIR / "build"

# Mapowanie plików Markdown do struktury Sphinx
FILE_MAPPING = {
    "DOKUMENTACJA_TECHNICZNA.md": "technical_docs/architecture_full.md",
    "AI_MODELS.md": "technical_docs/ai_models.md",
    "MT5_INTEGRACJA.md": "technical_docs/mt5_integration_full.md",
    "position_management.md": "technical_docs/position_management.md",
    "ui_interface.md": "technical_docs/ui_interface.md",
    "monitoring_system.md": "technical_docs/monitoring_system.md",
    "trading_operations.md": "technical_docs/trading_operations.md",
    "next_steps.md": "development/next_steps.md",
    "mt5_ea.md": "technical_docs/mt5_ea.md",
}

def ensure_dir(directory):
    """Upewnij się, że katalog istnieje."""
    os.makedirs(directory, exist_ok=True)

def copy_markdown_files():
    """Kopiuj pliki Markdown do struktury Sphinx."""
    print("Kopiowanie plików Markdown...")
    
    # Upewnij się, że katalogi docelowe istnieją
    ensure_dir(SPHINX_SOURCE_DIR / "technical_docs")
    ensure_dir(SPHINX_SOURCE_DIR / "development")
    
    # Kopiuj pliki zgodnie z mapowaniem
    for source_file, target_path in FILE_MAPPING.items():
        source_path = DOCS_DIR / source_file
        target_full_path = SPHINX_SOURCE_DIR / target_path
        
        if source_path.exists():
            print(f"Kopiowanie {source_file} do {target_path}")
            shutil.copy2(source_path, target_full_path)
        else:
            print(f"Plik {source_file} nie istnieje, pomijam.")

def build_documentation(format="html"):
    """Buduj dokumentację w określonym formacie."""
    print(f"Budowanie dokumentacji w formacie {format}...")
    
    # Przejdź do katalogu Sphinx
    os.chdir(SPHINX_DIR)
    
    # Uruchom sphinx-build
    result = subprocess.run(
        [
            "sphinx-build",
            "-b", format,
            "source",
            f"build/{format}"
        ],
        capture_output=True,
        text=True
    )
    
    # Wyświetl wynik
    print(result.stdout)
    if result.stderr:
        print("Błędy:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    
    print(f"Dokumentacja została zbudowana w katalogu {SPHINX_BUILD_DIR}/{format}")

def main():
    """Główna funkcja skryptu."""
    # Sprawdź, czy jesteśmy w środowisku wirtualnym
    if not os.environ.get("VIRTUAL_ENV"):
        print("UWAGA: Nie wykryto aktywnego środowiska wirtualnego!")
        response = input("Czy chcesz kontynuować? (t/n): ")
        if response.lower() != 't':
            print("Przerwano budowanie dokumentacji.")
            return
    
    # Kopiuj pliki Markdown
    copy_markdown_files()
    
    # Buduj dokumentację HTML
    build_documentation("html")
    
    print("\nDokumentacja została pomyślnie zbudowana!")
    print(f"Możesz ją przeglądać otwierając plik: {SPHINX_BUILD_DIR}/html/index.html")

if __name__ == "__main__":
    main() 