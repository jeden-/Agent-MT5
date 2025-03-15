# Dokumentacja Sphinx dla AgentMT5

Ten katalog zawiera dokumentację projektu AgentMT5 w formacie Sphinx. Sphinx to generator dokumentacji, który umożliwia tworzenie profesjonalnej dokumentacji w różnych formatach (HTML, PDF, ePub) z plików źródłowych w formacie reStructuredText lub Markdown.

## Struktura katalogów

- `source/` - katalog zawierający pliki źródłowe dokumentacji
  - `conf.py` - plik konfiguracyjny Sphinx
  - `index.rst` - główny plik indeksu dokumentacji
  - `technical_docs/` - dokumentacja techniczna
  - `development/` - dokumentacja rozwojowa
- `build/` - katalog, w którym generowana jest dokumentacja
  - `html/` - dokumentacja w formacie HTML
  - `pdf/` - dokumentacja w formacie PDF (jeśli wygenerowana)

## Wymagania

Do pracy z dokumentacją Sphinx potrzebujesz:

- Python 3.10 lub nowszy
- Sphinx i rozszerzenia (zainstalowane w środowisku wirtualnym)
  - sphinx
  - sphinx-rtd-theme
  - myst-parser
  - sphinx-markdown-tables

## Budowanie dokumentacji

### Automatyczne budowanie

Użyj skryptu `build_docs.py` do automatycznego budowania dokumentacji:

```bash
python build_docs.py
```

Skrypt:
1. Sprawdza, czy środowisko wirtualne jest aktywne
2. Kopiuje pliki Markdown z głównego katalogu `docs/` do struktury Sphinx
3. Buduje dokumentację w formacie HTML
4. Wyświetla ścieżkę do wygenerowanej dokumentacji

### Ręczne budowanie

Możesz również ręcznie zbudować dokumentację:

```bash
cd docs/sphinx
sphinx-build -b html source build/html
```

Dla innych formatów (np. PDF):

```bash
cd docs/sphinx
sphinx-build -b latex source build/latex
cd build/latex
make
```

## Dodawanie nowej dokumentacji

1. Dodaj nowy plik Markdown w odpowiednim katalogu w `source/`
2. Dodaj odniesienie do pliku w odpowiednim pliku `index.rst` lub `toctree`
3. Zbuduj dokumentację ponownie

## Konwencje dokumentacji

- Używaj nagłówków Markdown (`#`, `##`, `###`) do strukturyzowania dokumentu
- Dodawaj odnośniki do innych części dokumentacji
- Używaj list i tabel do prezentacji danych
- Dodawaj przykłady kodu w odpowiednich blokach kodu

## Rozwiązywanie problemów

Jeśli napotkasz problemy podczas budowania dokumentacji:

1. Sprawdź, czy wszystkie wymagane pakiety są zainstalowane
2. Sprawdź błędy w pliku `build.log`
3. Upewnij się, że pliki Markdown są poprawnie sformatowane
4. Sprawdź, czy wszystkie odniesienia w `toctree` są poprawne 