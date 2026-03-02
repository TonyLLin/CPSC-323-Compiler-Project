"""
main.py

Reads a RAT26S source file, tokenizes it using the lexer, and writes
the token/lexeme pairs to an output file.

RAT26S Compiler Project

Class: CPSC 323-07
Authors: Braedon Collett, Jackson Thompson, and Tony Lin
"""
import os
from pathlib import Path
from lexer import tokenize

def main():
    inPath = Path('input')
    outPath = Path('output')

    is_empty = not any(inPath.iterdir())
    if is_empty:
        print ("No test cases exist in the input directory. Add some to test the lexer.")
    else:
        for file in inPath.iterdir():
            # Read text from input files
            source = file.read_text()

            lines =(tokenize(source))

            # Create output file names based on input file names
            outName = file.name.removesuffix('.txt') + "_output.txt"

            with open(os.path.join(outPath,outName), 'w') as f:
                f.write(f"{'token':<15} {'lexeme'}\n{'-' * 30}\n")
                for _ in lines:
                    token_type, lexeme = _
                    line = f"{token_type:<15} {lexeme}"
                    f.write(f"{line}\n")

if __name__ == '__main__':
    main()
    
