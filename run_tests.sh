#!/bin/bash
# Skrypt do uruchamiania testów z poprawnie ustawionym PYTHONPATH
# Użycie: ./run_tests.sh [ścieżka_do_testu]
# Przykład: ./run_tests.sh src.tests.unit.analysis.test_feedback_loop

TEST_PATH=${1:-discover}

echo "Uruchamianie testów z poprawnie skonfigurowanym środowiskiem..."

# Ustaw PYTHONPATH na katalog główny projektu
export PYTHONPATH=$(pwd)

# Aktywuj środowisko wirtualne, jeśli jeszcze nie jest aktywne
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Aktywuję środowisko wirtualne..."
    source venv/bin/activate
fi

# Uruchom testy
if [ "$TEST_PATH" = "discover" ]; then
    echo "Uruchamianie wszystkich testów..."
    python -m unittest discover -s src/tests
else
    echo "Uruchamianie testu: $TEST_PATH"
    python -m $TEST_PATH
fi 