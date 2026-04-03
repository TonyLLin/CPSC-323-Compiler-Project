"""
rat_parser.py

Recursive Descent Parser (RDP) for the RAT26S language.

Grammar (left-recursion removed, left-factored):

  <Rat26S>               -> <Opt Function Defs> @ <Opt Declaration List> @ <Statement List>

  <Opt Function Defs>    -> <Function Defs> | ε
  <Function Defs>        -> <Function> <Function Defs Prime>
  <Function Defs Prime>  -> <Function Defs> | ε

  <Function>             -> function <Identifier> ( <Opt Parameter List> ) { <Opt Declaration List> <Statement List> }
  <Opt Parameter List>   -> <Parameter List> | ε
  <Parameter List>       -> <Parameter> <Parameter List Prime>
  <Parameter List Prime> -> , <Parameter List> | ε
  <Parameter>            -> <IDs> <Qualifier>
  <Qualifier>            -> integer | real | boolean

  <Opt Declaration List> -> <Declaration List> | ε
  <Declaration List>     -> <Declaration> ; <Declaration List Prime>
  <Declaration List Prime> -> <Declaration List> | ε
  <Declaration>          -> <Qualifier> <IDs>
  <IDs>                  -> <Identifier> <IDs Prime>
  <IDs Prime>            -> , <IDs> | ε

  <Statement List>       -> <Statement> <Statement List Prime>
  <Statement List Prime> -> <Statement List> | ε
  <Statement>            -> <Compound> | <Assign> | <If> | <Return> | <Print> | <Scan> | <While>

  <Compound>             -> { <Statement List> }
  <Assign>               -> <Identifier> = <Expression> ;
  <If>                   -> if ( <Condition> ) <Statement> <If Prime>
  <If Prime>             -> otherwise <Statement> fi | fi
  <Return>               -> return <Return Prime>
  <Return Prime>         -> ; | <Expression> ;
  <Print>                -> print ( <Expression> ) ;
  <Scan>                 -> scan ( <IDs> ) ;
  <While>                -> while ( <Condition> ) <Statement>

  <Condition>            -> <Expression> <Relop> <Expression>
  <Relop>                -> == | != | > | < | <= | >=

  <Expression>           -> <Term> <Expression Prime>
  <Expression Prime>     -> + <Term> <Expression Prime> | - <Term> <Expression Prime> | ε

  <Term>                 -> <Factor> <Term Prime>
  <Term Prime>           -> * <Factor> <Term Prime> | / <Factor> <Term Prime> | ε

  <Factor>               -> - <Primary> | <Primary>
  <Primary>              -> <Identifier> <Primary Prime> | <Integer> | ( <Expression> ) | <Real> | true | false
  <Primary Prime>        -> ( <IDs> ) | ε
"""

from lexer import lexer

# ─────────────────────────────────────────────────────────────────────────────
# Toggle: set to True to print each production rule as it is applied
# ─────────────────────────────────────────────────────────────────────────────
PRINT_RULES: bool = True

# ─────────────────────────────────────────────────────────────────────────────
# Keywords that can begin a statement (used for synchronization / FIRST sets)
# ─────────────────────────────────────────────────────────────────────────────
STATEMENT_FIRST_KEYWORDS = {"if", "return", "print", "scan", "while"}
QUALIFIER_KEYWORDS        = {"integer", "real", "boolean"}


class Parser:
    """
    Hand-written Recursive Descent Parser for RAT26S.

    Usage:
        p = Parser(source_code, output_file_handle)
        p.parse()
    """

    def __init__(self, source: str, out=None):
        """
        :param source: Full RAT26S source string
        :param out:    File-like object for output (defaults to stdout if None)
        """
        self._source    = source
        self._pos       = 0          # current byte-offset into source
        self._line      = 1          # approximate line number (for error messages)
        self._out       = out
        self._token     = None       # current (token_type, lexeme) pair
        self._advance()              # prime the pump: load the first token

    # ─────────────────────────────────────────────────────────────────────────
    # Output helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _write(self, text: str):
        if self._out:
            self._out.write(text + "\n")
        else:
            print(text)

    def _print_token(self):
        """Print 'Token: X  Lexeme: Y' for the token that was just consumed."""
        if self._token:
            tok, lex = self._token
            self._write(f"Token: {tok:<15} Lexeme: {lex}")

    def _print_rule(self, rule: str):
        """Print a production rule if the switch is on."""
        if PRINT_RULES:
            self._write(f"  {rule}")

    # ─────────────────────────────────────────────────────────────────────────
    # Lexer interface
    # ─────────────────────────────────────────────────────────────────────────

    def _advance(self):
        """
        Fetch the next token from the lexer and store it in self._token.
        Updates the approximate line counter as we move through the source.
        """
        # Count newlines in the portion we are skipping
        prev_pos = self._pos
        self._token, self._pos = lexer(self._source, self._pos)

        # Count any newlines in the skipped whitespace/comments
        skipped = self._source[prev_pos:self._pos - (len(self._token[1]) if self._token else 0)]
        self._line += skipped.count("\n")

    def _current_token(self) -> str:
        """Return the token type of the current lookahead, or '' at EOF."""
        return self._token[0] if self._token else ""

    def _current_lexeme(self) -> str:
        """Return the lexeme of the current lookahead, or '' at EOF."""
        return self._token[1] if self._token else ""

    # ─────────────────────────────────────────────────────────────────────────
    # Match / error
    # ─────────────────────────────────────────────────────────────────────────

    def _match(self, expected_token: str, expected_lexeme: str = None):
        """
        Consume the current token if it matches the expectation, then advance.
        Raises SyntaxError with a descriptive message on mismatch.

        :param expected_token:  Token type string, e.g. "Separator"
        :param expected_lexeme: Optional specific lexeme, e.g. ";"
        """
        tok, lex = self._token if self._token else ("EOF", "EOF")

        if tok != expected_token:
            self._error(f"expected token '{expected_token}'"
                        + (f" ('{expected_lexeme}')" if expected_lexeme else "")
                        + f", got '{tok}' ('{lex}')")

        if expected_lexeme is not None and lex != expected_lexeme:
            self._error(f"expected lexeme '{expected_lexeme}', got '{lex}'")

        # Print the token *before* consuming it so output order matches assignment example
        self._print_token()
        self._advance()

    def _match_lexeme(self, expected_lexeme: str):
        """
        Convenience wrapper: match by lexeme regardless of token category.
        Useful for operators and separators where lexeme is more descriptive.
        """
        tok, lex = self._token if self._token else ("EOF", "EOF")
        if lex != expected_lexeme:
            self._error(f"expected '{expected_lexeme}', got '{lex}'")
        self._print_token()
        self._advance()

    def _error(self, message: str):
        tok = self._current_token()
        lex = self._current_lexeme()
        err = (f"\n*** Syntax Error ***\n"
               f"  Line   : {self._line}\n"
               f"  Token  : {tok}\n"
               f"  Lexeme : {lex}\n"
               f"  Detail : {message}\n")
        self._write(err)
        raise SyntaxError(err)

    # ─────────────────────────────────────────────────────────────────────────
    # Entry point
    # ─────────────────────────────────────────────────────────────────────────

    def parse(self):
        """Parse the full source. Call this once after constructing the Parser."""
        self._rat26s()
        if self._token is not None:
            self._error("unexpected tokens after end of program")

    # ─────────────────────────────────────────────────────────────────────────
    # Grammar rules — one method per non-terminal
    # ─────────────────────────────────────────────────────────────────────────

    # <Rat26S> -> <Opt Function Defs> @ <Opt Declaration List> @ <Statement List>
    def _rat26s(self):
        self._print_rule("<Rat26S> -> <Opt Function Defs> @ <Opt Declaration List> @ <Statement List>")
        self._opt_function_defs()
        self._match("Separator", "@")
        self._opt_declaration_list()
        self._match("Separator", "@")
        self._statement_list()

    # ─── Function definitions ─────────────────────────────────────────────────

    # <Opt Function Defs> -> <Function Defs> | ε
    def _opt_function_defs(self):
        self._print_rule("<Opt Function Defs> -> <Function Defs>")
        if self._current_lexeme() == "function":
            self._function_defs()

    # <Function Defs> -> <Function> <Function Defs Prime>
    def _function_defs(self):
        self._print_rule("<Function Defs> -> <Function> <Function Defs Prime>")
        self._function()
        self._function_defs_prime()

    # <Function Defs Prime> -> <Function Defs> | ε
    def _function_defs_prime(self):
        self._print_rule("<Function Defs Prime> -> <Function Defs>")
        if self._current_lexeme() == "function":
            self._function_defs()

    # <Function> -> function <Identifier> ( <Opt Parameter List> ) { <Opt Declaration List> <Statement List> }
    def _function(self):
        self._print_rule("<Function> -> function <Identifier> ( <Opt Parameter List> ) "
                         "{ <Opt Declaration List> <Statement List> }")
        self._match("Keyword", "function")
        self._match("Identifier")
        self._match("Separator", "(")
        self._opt_parameter_list()
        self._match("Separator", ")")
        self._match("Separator", "{")
        self._opt_declaration_list()
        self._statement_list()
        self._match("Separator", "}")

    # <Opt Parameter List> -> <Parameter List> | ε
    def _opt_parameter_list(self):
        self._print_rule("<Opt Parameter List> -> <Parameter List>")
        if self._current_lexeme() in QUALIFIER_KEYWORDS:
            self._parameter_list()

    # <Parameter List> -> <Parameter> <Parameter List Prime>
    def _parameter_list(self):
        self._print_rule("<Parameter List> -> <Parameter> <Parameter List Prime>")
        self._parameter()
        self._parameter_list_prime()

    # <Parameter List Prime> -> , <Parameter List> | ε
    def _parameter_list_prime(self):
        self._print_rule("<Parameter List Prime> -> , <Parameter List>")
        if self._current_lexeme() == ",":
            self._match_lexeme(",")
            self._parameter_list()

    # <Parameter> -> <IDs> <Qualifier>
    def _parameter(self):
        self._print_rule("<Parameter> -> <IDs> <Qualifier>")
        self._ids()
        self._qualifier()

    # <Qualifier> -> integer | real | boolean
    def _qualifier(self):
        self._print_rule("<Qualifier> -> integer | real | boolean")
        lex = self._current_lexeme()
        if lex not in QUALIFIER_KEYWORDS:
            self._error(f"expected a type qualifier (integer, real, boolean), got '{lex}'")
        self._match("Keyword", lex)

    # ─── Declarations ─────────────────────────────────────────────────────────

    # <Opt Declaration List> -> <Declaration List> | ε
    def _opt_declaration_list(self):
        self._print_rule("<Opt Declaration List> -> <Declaration List>")
        if self._current_lexeme() in QUALIFIER_KEYWORDS:
            self._declaration_list()

    # <Declaration List> -> <Declaration> ; <Declaration List Prime>
    def _declaration_list(self):
        self._print_rule("<Declaration List> -> <Declaration> ; <Declaration List Prime>")
        self._declaration()
        self._match("Separator", ";")
        self._declaration_list_prime()

    # <Declaration List Prime> -> <Declaration List> | ε
    def _declaration_list_prime(self):
        self._print_rule("<Declaration List Prime> -> <Declaration List>")
        if self._current_lexeme() in QUALIFIER_KEYWORDS:
            self._declaration_list()

    # <Declaration> -> <Qualifier> <IDs>
    def _declaration(self):
        self._print_rule("<Declaration> -> <Qualifier> <IDs>")
        self._qualifier()
        self._ids()

    # <IDs> -> <Identifier> <IDs Prime>
    def _ids(self):
        self._print_rule("<IDs> -> <Identifier> <IDs Prime>")
        self._match("Identifier")
        self._ids_prime()

    # <IDs Prime> -> , <IDs> | ε
    def _ids_prime(self):
        self._print_rule("<IDs Prime> -> , <IDs>")
        if self._current_lexeme() == ",":
            self._match_lexeme(",")
            self._ids()

    # ─── Statements ───────────────────────────────────────────────────────────

    # <Statement List> -> <Statement> <Statement List Prime>
    def _statement_list(self):
        self._print_rule("<Statement List> -> <Statement> <Statement List Prime>")
        self._statement()
        self._statement_list_prime()

    # <Statement List Prime> -> <Statement List> | ε
    # FIRST(<Statement>): '{', Identifier, 'if', 'return', 'print', 'scan', 'while'
    def _statement_list_prime(self):
        self._print_rule("<Statement List Prime> -> <Statement List>")
        tok = self._current_token()
        lex = self._current_lexeme()
        if (tok == "Identifier"
                or lex == "{"
                or lex in STATEMENT_FIRST_KEYWORDS):
            self._statement_list()

    # <Statement> -> <Compound> | <Assign> | <If> | <Return> | <Print> | <Scan> | <While>
    def _statement(self):
        self._print_rule("<Statement> -> <Compound> | <Assign> | <If> | <Return> | <Print> | <Scan> | <While>")
        lex = self._current_lexeme()
        tok = self._current_token()

        if lex == "{":
            self._compound()
        elif tok == "Identifier":
            self._assign()
        elif lex == "if":
            self._if_stmt()
        elif lex == "return":
            self._return_stmt()
        elif lex == "print":
            self._print_stmt()
        elif lex == "scan":
            self._scan_stmt()
        elif lex == "while":
            self._while_stmt()
        else:
            self._error(f"expected a statement, got '{lex}'")

    # <Compound> -> { <Statement List> }
    def _compound(self):
        self._print_rule("<Compound> -> { <Statement List> }")
        self._match("Separator", "{")
        self._statement_list()
        self._match("Separator", "}")

    # <Assign> -> <Identifier> = <Expression> ;
    def _assign(self):
        self._print_rule("<Assign> -> <Identifier> = <Expression> ;")
        self._match("Identifier")
        self._match("Operator", "=")
        self._expression()
        self._match("Separator", ";")

    # <If> -> if ( <Condition> ) <Statement> <If Prime>
    def _if_stmt(self):
        self._print_rule("<If> -> if ( <Condition> ) <Statement> <If Prime>")
        self._match("Keyword", "if")
        self._match("Separator", "(")
        self._condition()
        self._match("Separator", ")")
        self._statement()
        self._if_prime()

    # <If Prime> -> otherwise <Statement> fi | fi
    def _if_prime(self):
        self._print_rule("<If Prime> -> otherwise <Statement> fi | fi")
        if self._current_lexeme() == "otherwise":
            self._match("Keyword", "otherwise")
            self._statement()
        self._match("Keyword", "fi")

    # <Return> -> return <Return Prime>
    def _return_stmt(self):
        self._print_rule("<Return> -> return <Return Prime>")
        self._match("Keyword", "return")
        self._return_prime()

    # <Return Prime> -> ; | <Expression> ;
    def _return_prime(self):
        self._print_rule("<Return Prime> -> ; | <Expression> ;")
        if self._current_lexeme() == ";":
            self._match("Separator", ";")
        else:
            self._expression()
            self._match("Separator", ";")

    # <Print> -> print ( <Expression> ) ;
    def _print_stmt(self):
        self._print_rule("<Print> -> print ( <Expression> ) ;")
        self._match("Keyword", "print")
        self._match("Separator", "(")
        self._expression()
        self._match("Separator", ")")
        self._match("Separator", ";")

    # <Scan> -> scan ( <IDs> ) ;
    def _scan_stmt(self):
        self._print_rule("<Scan> -> scan ( <IDs> ) ;")
        self._match("Keyword", "scan")
        self._match("Separator", "(")
        self._ids()
        self._match("Separator", ")")
        self._match("Separator", ";")

    # <While> -> while ( <Condition> ) <Statement>
    def _while_stmt(self):
        self._print_rule("<While> -> while ( <Condition> ) <Statement>")
        self._match("Keyword", "while")
        self._match("Separator", "(")
        self._condition()
        self._match("Separator", ")")
        self._statement()

    # ─── Condition / Relop ────────────────────────────────────────────────────

    # <Condition> -> <Expression> <Relop> <Expression>
    def _condition(self):
        self._print_rule("<Condition> -> <Expression> <Relop> <Expression>")
        self._expression()
        self._relop()
        self._expression()

    # <Relop> -> == | != | > | < | <= | >=
    def _relop(self):
        self._print_rule("<Relop> -> == | != | > | < | <= | >=")
        lex = self._current_lexeme()
        if lex not in {"==", "!=", ">", "<", "<=", ">="}:
            self._error(f"expected a relational operator, got '{lex}'")
        self._match("Operator", lex)

    # ─── Expressions ──────────────────────────────────────────────────────────

    # <Expression> -> <Term> <Expression Prime>
    def _expression(self):
        self._print_rule("<Expression> -> <Term> <Expression Prime>")
        self._term()
        self._expression_prime()

    # <Expression Prime> -> + <Term> <Expression Prime> | - <Term> <Expression Prime> | ε
    def _expression_prime(self):
        self._print_rule("<Expression Prime> -> + <Term> <Expression Prime> | - <Term> <Expression Prime>")
        lex = self._current_lexeme()
        if lex in {"+", "-"}:
            self._match("Operator", lex)
            self._term()
            self._expression_prime()

    # <Term> -> <Factor> <Term Prime>
    def _term(self):
        self._print_rule("<Term> -> <Factor> <Term Prime>")
        self._factor()
        self._term_prime()

    # <Term Prime> -> * <Factor> <Term Prime> | / <Factor> <Term Prime> | ε
    def _term_prime(self):
        self._print_rule("<Term Prime> -> * <Factor> <Term Prime> | / <Factor> <Term Prime>")
        lex = self._current_lexeme()
        if lex in {"*", "/"}:
            self._match("Operator", lex)
            self._factor()
            self._term_prime()

    # <Factor> -> - <Primary> | <Primary>
    def _factor(self):
        self._print_rule("<Factor> -> - <Primary> | <Primary>")
        if self._current_lexeme() == "-":
            self._match("Operator", "-")
        self._primary()

    # <Primary> -> <Identifier> <Primary Prime> | <Integer> | ( <Expression> ) | <Real> | true | false
    def _primary(self):
        self._print_rule("<Primary> -> <Identifier> <Primary Prime> | <Integer> | ( <Expression> ) | <Real> | true | false")
        tok = self._current_token()
        lex = self._current_lexeme()

        if tok == "Identifier":
            self._match("Identifier")
            self._primary_prime()
        elif tok == "Integer":
            self._match("Integer")
        elif tok == "Real":
            self._match("Real")
        elif lex == "(":
            self._match("Separator", "(")
            self._expression()
            self._match("Separator", ")")
        elif lex in {"true", "false"}:
            self._match("Keyword", lex)
        else:
            self._error(f"expected a primary expression (identifier, number, or '('), got '{lex}'")

    # <Primary Prime> -> ( <IDs> ) | ε   (function call)
    def _primary_prime(self):
        self._print_rule("<Primary Prime> -> ( <IDs> )")
        if self._current_lexeme() == "(":
            self._match("Separator", "(")
            self._ids()
            self._match("Separator", ")")