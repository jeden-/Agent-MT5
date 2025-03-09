#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt startowy dla Trading Agent MT5
"""

import sys
import os

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.main import main

if __name__ == "__main__":
    main() 