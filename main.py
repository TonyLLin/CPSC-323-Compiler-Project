"""
main.py

RAT26S Compiler Project

Class: CPSC 323-07
Authors: Braedon Collett, Jackson Thompson, and Tony Lin
Description:
"""
from lexer import tokenize
def main():
    #Example 1: 
    print("Example 1")
    for _ in tokenize("while (fahr <= upper) a = 23.00;"):
        print(_)
    print("Example 2")
    for _ in tokenize("if (fahr <= upper) a = 23.00;"):
        print(_)
    print("Example 3")
    for _ in tokenize("var_1 = 1"):
        print(_)
    pass

if __name__ == '__main__':
    main()
    
