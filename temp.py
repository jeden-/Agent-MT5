f = open('create_reporter.py', 'w')
f.write('''with open(\
src/backtest/backtest_reporter.py\, \w\) as f:\\n''')
f.write('''    f.write(\
\\#!/usr/bin/env
python\\n#
-*-
coding:
utf-8
-*-\\n\\n\\\\\\\\\\\nModu do generowania rozszerzonych raportów i wizualizacji wyników backtestingu.\\n\\\\\\\\\\\n\\n\\\)\n'''
