"""
Lexical Conventions

- keywords: function, integer, real, boolean, if, return,
            print, scan, while, otherwise, fi, write, read, true, false
- separators: {, }, ;, (, ),
- operators: ==, !=, >, <, <=, =>, +, -, *, /, =, E(epsilon?)
- identifiers: L(L|d|_)*
- integers: d+
- reals: d+.d+
- comments: anything enclose in /* ... */

L = Letter
d = Digit
+ = 1+ times
* = 0+ times
"""

KEYWORDS = { "function", "integer", "real", "boolean", "if", "return",
             "print", "scan", "while", "otherwise", "fi", "write",
             "read", "true", "false"}
OPERATORS = {"<=", ">=", "==", "!=", "+", "-", "*", "/", "=", "<", ">"}
SEPARATORS = {"(", ")", ";", "{", "}"}

def _skip_comment(source: str, pos: int) -> int:
    # Code goes here
    pass

def _scan_identifier_or_keyword(source, pos):
    # Code goes here
    pass


def _scan_number(source, pos):
    # Code goes here
    pass


def _scan_separator(source, pos):
    # Code goes here
    pass


def _scan_operator(source, pos):
    # Code goes here
    pass


def _next_token(source: str, pos: int) -> tuple[tuple[str, str], int]:
    """
    Determines the correct scanner based on current character.
    :param source:
    :param pos:
    :return:
    """
    char = source[pos]

    if char.isalpha():
        return _scan_identifier_or_keyword(source, pos)

    if char.isdigit():
        return _scan_number(source, pos)

    if char in SEPARATORS:
        return _scan_separator(source, pos)

    if source[pos:pos + 2] in OPERATORS:
        return _scan_operator(source, pos)

    return ("uknown", char), pos + 1

def lexer(source: str, pos: int) -> tuple[tuple[str, str] | None, int]:
    """
    Returns the next (token, lexeme) tuple from the source, starting at pos.
    :param source:
    :param pos:
    :return:
    """
    while pos < len(source):
        # Skip whitespace
        if source[pos].isspace():
            pos += 1
            continue

        # Skip comment blocks
        if source[pos:pos + 2] == '/*':
            pos = _skip_comment(source, pos)
            continue

        token, pos = _next_token(source, pos)
        return token, pos

    return None, pos

def tokenize(source: str) -> list[tuple[str, str]]:
    """
    Tokenize a source string into (token, lexeme) pairs.

    :param source: String to be tokenized.
    :return: List of (token, lexeme) pairs.
    """
    tokens = []
    pos = 0

    while pos < len(source):
        token, pos = lexer(source, pos)
        if token is None:
            break
        tokens.append(token)
    return tokens