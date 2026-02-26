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
from FSM import classify

KEYWORDS = { "function", "integer", "real", "boolean", "if", "return",
             "print", "scan", "while", "otherwise", "fi", "write",
             "read", "true", "false"}
MULTI_CHAR_OPERATORS = {"<=", ">=", "==", "!="}
SINGLE_CHAR_OPERATORS = {"+", "-", "*", "/", "=", "<", ">"}
SEPARATORS = {"(", ")", ";", "{", "}"}

def _skip_comment(source: str, pos: int) -> int:
    """
    Skips all the text in commented block /* ... */

    :param source:
    :param pos:
    :return:
    """
    pos += 2
    while pos < len(source) - 1:
        if source[pos] == "*" and source[pos + 1] == "/":
            return pos + 2
        pos += 1
    raise SyntaxError("Unterminated comment: missing closing */")

def _scan_identifier_or_keyword(source: str, pos: int) -> tuple[tuple[str, str], int]:
    """
    Scans for keyword and identifiers.

    :param source:
    :param pos:
    :return:
    """
    start = pos

    while pos < len(source) and (source[pos].isalnum() or source[pos] == "_"):
        pos += 1
    word = source[start:pos].lower()

    if word in KEYWORDS:
        return ("Keyword", word), pos

    return classify(word), pos


def _scan_number(source: str, pos: int):
    """
    Scans for reals and integers to pass into FSM to classify.

    :param source:
    :param pos:
    :return:
    """
    start = pos
    while pos < len(source) and source[pos].isdigit():
        pos += 1

    if pos < len(source) and source[pos] == ".":
        pos += 1
        while pos < len(source) and source[pos].isdigit():
            pos += 1

    return classify(source[start:pos]), pos


def _scan_separator(source: str, pos: int) -> tuple[tuple[str, str], int]:
    """
    Scans for separators

    :param source:
    :param pos:
    :return:
    """
    return ("Separator", source[pos]), pos + 1


def _scan_operator(source, pos) -> tuple[tuple[str, str], int]:
    """
    Scans for operators

    :param source:
    :param pos:
    :return:
    """
    if source[pos:pos + 2] in MULTI_CHAR_OPERATORS:
        return ("Operator", source[pos:pos + 2]), pos + 2
    return ("Operator", source[pos]), pos + 1


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

    if source[pos:pos + 2] in MULTI_CHAR_OPERATORS or char in SINGLE_CHAR_OPERATORS:
        return _scan_operator(source, pos)

    return ("unknown", char), pos + 1

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


# Temporary test cases
for _ in tokenize("while (fahr <= upper) a = 23.00; /* this is a sample */"):
    print(_)