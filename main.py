"""
main.py

Reads a RAT26S source file, tokenizes it using the lexer, and writes
the token/lexeme pairs to an output file.

RAT26S Compiler Project

Class: CPSC 323-07
Authors: Braedon Collett, Jackson Thompson, and Tony Lin
"""
import os
import sys
from pathlib import Path
from rat_parser import Parser

# Get the directory where the executable (or main.py) lives
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller executable
    BASE_DIR = Path(os.path.dirname(sys.executable))
else:
    # Running as a normal .py script
    BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

def main():
    inPath = BASE_DIR / 'input'
    outPath = BASE_DIR / 'output'

    is_empty = not any(inPath.iterdir())
    if is_empty:
        print ("No test cases exist in the input directory. Add some to test the lexer.")
    else:
        for file in inPath.iterdir():
            source  = file.read_text()
            outName = file.name.removesuffix('.txt') + "_output.txt"
    
            with open(outPath / outName, 'w') as f:
                f.write(f"{'=' * 50}\n")
                f.write(f"Source file: {file.name}\n")
                f.write(f"{'=' * 50}\n\n")
    
                try:
                    p = Parser(source, out=f)
                    p.parse()
                    f.write("\nParse completed successfully.\n")
                except SyntaxError:
                    # Error details already written by Parser._error()
                    f.write("\nParse terminated due to syntax error.\n")

if __name__ == '__main__':
    main()
    
