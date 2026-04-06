"""
rat_parser.py

Recursive Descent Parser (RDP) for the RAT26S language.

Grammar (left-recursion removed, left-factored):

  <Rat26S>               -> @ <Opt Function Defs> @ <Opt Declaration List> @ <Statement List> @

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
  <Print>                -> write ( <Expression> ) ;
  <Scan>                 -> read ( <IDs> ) ;
  <While>                -> while ( <Condition> ) <Statement>

  <Condition>            -> <Expression> <Relop> <Expression>
  <Relop>                -> == | != | > | < | <= | =>

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
STATEMENT_FIRST_KEYWORDS = {"if", "return", "write", "read", "while"}
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
        self._source         = source
        self._pos            = 0       # current byte-offset into source
        self._line           = 1       # approximate line number (for error messages)
        self._out            = out
        self._token          = None    # current (token_type, lexeme) pair
        # Queue of deferred rule strings.  _term_prime and _expression_prime
        # place their ε productions here so they appear in the output AFTER
        # the token that caused the parser to exit those non-terminals.
        self._pending_rules: list = []
        self._advance()                # prime the pump: load the first token

    # ─────────────────────────────────────────────────────────────────────────
    # Output helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _write(self, text: str):
        if self._out:
            self._out.write(text + "\n")
        else:
            print(text)

    def _print_token(self):
        """Print 'Token: X  Lexeme: Y' for the current token."""
        if self._token:
            tok, lex = self._token
            self._write(f"Token: {tok:<15} Lexeme: {lex}")

    def _print_rule(self, rule: str):
        """Print a production rule if the switch is on."""
        if PRINT_RULES:
            self._write(f"  {rule}")

    def _defer_rule(self, rule: str):
        """Queue a rule string to be printed after the next token is consumed."""
        self._pending_rules.append(rule)

    def _flush_pending(self):
        """Print and clear all deferred rules."""
        for rule in self._pending_rules:
            self._print_rule(rule)
        self._pending_rules.clear()

    # ─────────────────────────────────────────────────────────────────────────
    # Lexer interface
    # ─────────────────────────────────────────────────────────────────────────

    def _advance(self):
        """
        Fetch the next token from the lexer and store it in self._token.
        Updates the approximate line counter as we move through the source.
        """
        prev_pos = self._pos
        self._token, self._pos = lexer(self._source, self._pos)

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
        Consume the current token if it matches, then advance.
        Output order: token line first, then any deferred (ε) rules.
        """
        tok, lex = self._token if self._token else ("EOF", "EOF")

        if tok != expected_token:
            self._error(f"expected token '{expected_token}'"
                        + (f" ('{expected_lexeme}')" if expected_lexeme else "")
                        + f", got '{tok}' ('{lex}')")

        if expected_lexeme is not None and lex != expected_lexeme:
            self._error(f"expected lexeme '{expected_lexeme}', got '{lex}'")

        self._print_token()      # token first
        self._flush_pending()    # then any deferred ε rules
        self._advance()

    def _match_lexeme(self, expected_lexeme: str):
        """Match by lexeme regardless of token category."""
        tok, lex = self._token if self._token else ("EOF", "EOF")
        if lex != expected_lexeme:
            self._error(f"expected '{expected_lexeme}', got '{lex}'")
        self._print_token()
        self._flush_pending()
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
        self._flush_pending()   # emit any trailing deferred ε rules
        if self._token is not None:
            self._error("unexpected tokens after end of program")

    # ─────────────────────────────────────────────────────────────────────────
    # Grammar rules — one method per non-terminal
    # ─────────────────────────────────────────────────────────────────────────

    # <Rat26S> -> @ <Opt Function Defs> @ <Opt Declaration List> @ <Statement List> @
    def _rat26s(self):
        self._match("Separator", "@")
        self._print_rule("<Rat26S> -> @ <Opt Function Defs> @ <Opt Declaration List> @ <Statement List> @")
        self._opt_function_defs()
        self._match("Separator", "@")
        self._opt_declaration_list()
        self._match("Separator", "@")
        self._statement_list()
        self._match("Separator", "@")

    # ─── Function definitions ─────────────────────────────────────────────────

    # <Opt Function Defs> -> <Function Defs> | ε
    def _opt_function_defs(self):
        if self._current_lexeme() == "function":
            self._print_rule("<Opt Function Defs> -> <Function Defs>")
            self._function_defs()
        else:
            self._print_rule("<Opt Function Defs> -> ε")

    # <Function Defs> -> <Function> <Function Defs Prime>
    def _function_defs(self):
        self._print_rule("<Function Defs> -> <Function> <Function Defs Prime>")
        self._function()
        self._function_defs_prime()

    # <Function Defs Prime> -> <Function Defs> | ε
    def _function_defs_prime(self):
        if self._current_lexeme() == "function":
            self._print_rule("<Function Defs Prime> -> <Function Defs>")
            self._function_defs()
        else:
            self._print_rule("<Function Defs Prime> -> ε")

    # <Function> -> function <Identifier> ( <Opt Parameter List> ) { <Opt Declaration List> <Statement List> }
    def _function(self):
        self._match("Keyword", "function")
        self._print_rule("<Function> -> function <Identifier> ( <Opt Parameter List> ) "
                         "{ <Opt Declaration List> <Statement List> }")
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
        if self._current_token() == "Identifier":
            self._print_rule("<Opt Parameter List> -> <Parameter List>")
            self._parameter_list()
        else:
            self._print_rule("<Opt Parameter List> -> ε")

    # <Parameter List> -> <Parameter> <Parameter List Prime>
    def _parameter_list(self):
        self._print_rule("<Parameter List> -> <Parameter> <Parameter List Prime>")
        self._parameter()
        self._parameter_list_prime()

    # <Parameter List Prime> -> , <Parameter List> | ε
    def _parameter_list_prime(self):
        if self._current_lexeme() == ",":
            self._match_lexeme(",")
            self._print_rule("<Parameter List Prime> -> , <Parameter List>")
            self._parameter_list()
        else:
            self._print_rule("<Parameter List Prime> -> ε")

    # <Parameter> -> <IDs> <Qualifier>
    def _parameter(self):
        self._print_rule("<Parameter> -> <IDs> <Qualifier>")
        self._ids()
        self._qualifier()

    # <Qualifier> -> integer | real | boolean
    def _qualifier(self):
        lex = self._current_lexeme()
        if lex not in QUALIFIER_KEYWORDS:
            self._error(f"expected a type qualifier (integer, real, boolean), got '{lex}'")
        self._match("Keyword", lex)
        self._print_rule("<Qualifier> -> integer | real | boolean")

    # ─── Declarations ─────────────────────────────────────────────────────────

    # <Opt Declaration List> -> <Declaration List> | ε
    def _opt_declaration_list(self):
        if self._current_lexeme() in QUALIFIER_KEYWORDS:
            self._print_rule("<Opt Declaration List> -> <Declaration List>")
            self._declaration_list()
        else:
            self._print_rule("<Opt Declaration List> -> ε")

    # <Declaration List> -> <Declaration> ; <Declaration List Prime>
    def _declaration_list(self):
        self._print_rule("<Declaration List> -> <Declaration> ; <Declaration List Prime>")
        self._declaration()
        self._match("Separator", ";")
        self._declaration_list_prime()

    # <Declaration List Prime> -> <Declaration List> | ε
    def _declaration_list_prime(self):
        if self._current_lexeme() in QUALIFIER_KEYWORDS:
            self._print_rule("<Declaration List Prime> -> <Declaration List>")
            self._declaration_list()
        else:
            self._print_rule("<Declaration List Prime> -> ε")

    # <Declaration> -> <Qualifier> <IDs>
    def _declaration(self):
        self._print_rule("<Declaration> -> <Qualifier> <IDs>")
        self._qualifier()
        self._ids()

    # <IDs> -> <Identifier> <IDs Prime>
    def _ids(self):
        self._match("Identifier")
        self._print_rule("<IDs> -> <Identifier> <IDs Prime>")
        self._ids_prime()

    # <IDs Prime> -> , <IDs> | ε
    def _ids_prime(self):
        if self._current_lexeme() == ",":
            self._match_lexeme(",")
            self._print_rule("<IDs Prime> -> , <IDs>")
            self._ids()
        else:
            self._print_rule("<IDs Prime> -> ε")

    # ─── Statements ───────────────────────────────────────────────────────────

    # <Statement List> -> <Statement> <Statement List Prime>
    def _statement_list(self):
        self._print_rule("<Statement List> -> <Statement> <Statement List Prime>")
        self._statement()
        self._statement_list_prime()

    # <Statement List Prime> -> <Statement List> | ε
    def _statement_list_prime(self):
        tok = self._current_token()
        lex = self._current_lexeme()
        if (tok == "Identifier"
                or lex == "{"
                or lex in STATEMENT_FIRST_KEYWORDS):
            self._print_rule("<Statement List Prime> -> <Statement List>")
            self._statement_list()
        else:
            self._print_rule("<Statement List Prime> -> ε")

    # <Statement> -> dispatches to the appropriate sub-rule.
    # Each sub-method prints "<Statement> -> <X>" after consuming its first
    # token, so the token always appears before the rule in the output.
    def _statement(self):
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
        elif lex == "write":
            self._print_stmt()
        elif lex == "read":
            self._scan_stmt()
        elif lex == "while":
            self._while_stmt()
        else:
            self._error(f"expected a statement, got '{lex}'")

    # <Compound> -> { <Statement List> }
    def _compound(self):
        self._match("Separator", "{")
        self._print_rule("<Statement> -> <Compound>")
        self._print_rule("<Compound> -> { <Statement List> }")
        self._statement_list()
        self._match("Separator", "}")

    # <Assign> -> <Identifier> = <Expression> ;
    def _assign(self):
        self._match("Identifier")
        self._print_rule("<Statement> -> <Assign>")
        self._print_rule("<Assign> -> <Identifier> = <Expression> ;")
        self._match("Operator", "=")
        self._expression()
        self._match("Separator", ";")

    # <If> -> if ( <Condition> ) <Statement> <If Prime>
    def _if_stmt(self):
        self._match("Keyword", "if")
        self._print_rule("<Statement> -> <If>")
        self._print_rule("<If> -> if ( <Condition> ) <Statement> <If Prime>")
        self._match("Separator", "(")
        self._condition()
        self._match("Separator", ")")
        self._statement()
        self._if_prime()

    # <If Prime> -> otherwise <Statement> fi | fi
    def _if_prime(self):
        if self._current_lexeme() == "otherwise":
            self._match("Keyword", "otherwise")
            self._print_rule("<If Prime> -> otherwise <Statement> fi")
            self._statement()
        else:
            self._print_rule("<If Prime> -> fi")
        self._match("Keyword", "fi")

    # <Return> -> return <Return Prime>
    def _return_stmt(self):
        self._match("Keyword", "return")
        self._print_rule("<Statement> -> <Return>")
        self._print_rule("<Return> -> return <Return Prime>")
        self._return_prime()

    # <Return Prime> -> ; | <Expression> ;
    def _return_prime(self):
        if self._current_lexeme() == ";":
            self._print_rule("<Return Prime> -> ;")
            self._match("Separator", ";")
        else:
            self._print_rule("<Return Prime> -> <Expression> ;")
            self._expression()
            self._match("Separator", ";")

    # <Print> -> write ( <Expression> ) ;
    def _print_stmt(self):
        self._match("Keyword", "write")
        self._print_rule("<Statement> -> <Print>")
        self._print_rule("<Print> -> write ( <Expression> ) ;")
        self._match("Separator", "(")
        self._expression()
        self._match("Separator", ")")
        self._match("Separator", ";")

    # <Scan> -> read ( <IDs> ) ;
    def _scan_stmt(self):
        self._match("Keyword", "read")
        self._print_rule("<Statement> -> <Scan>")
        self._print_rule("<Scan> -> read ( <IDs> ) ;")
        self._match("Separator", "(")
        self._ids()
        self._match("Separator", ")")
        self._match("Separator", ";")

    # <While> -> while ( <Condition> ) <Statement>
    def _while_stmt(self):
        self._match("Keyword", "while")
        self._print_rule("<Statement> -> <While>")
        self._print_rule("<While> -> while ( <Condition> ) <Statement>")
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

    # <Relop> -> == | != | > | < | <= | =>
    def _relop(self):
        lex = self._current_lexeme()
        if lex not in {"==", "!=", ">", "<", "<=", "=>"}:
            self._error(f"expected a relational operator, got '{lex}'")
        self._match("Operator", lex)
        self._print_rule("<Relop> -> == | != | > | < | <= | =>")

    # ─── Expressions ──────────────────────────────────────────────────────────

    # <Expression> -> <Term> <Expression Prime>
    def _expression(self):
        self._print_rule("<Expression> -> <Term> <Expression Prime>")
        self._term()
        self._expression_prime()

    # <Expression Prime> -> + <Term> <Expression Prime> | - <Term> <Expression Prime> | ε
    #
    # ε case: defer the rule so it prints AFTER the next token upstream
    # (the token that caused us to exit this non-terminal).
    # Non-ε case: _match() prints the operator token and then flushes the
    # pending queue (which holds the ε from _term_prime), producing the
    # correct interleaving: Token → <Term Prime> ε → <Expression Prime> rule.
    def _expression_prime(self):
        lex = self._current_lexeme()
        if lex in {"+", "-"}:
            self._match("Operator", lex)          # prints token, then flushes pending ε rules
            self._print_rule("<Expression Prime> -> + <Term> <Expression Prime> | - <Term> <Expression Prime>")
            self._term()
            self._expression_prime()
        else:
            self._defer_rule("<Expression Prime> -> ε")

    # <Term> -> <Factor> <Term Prime>
    def _term(self):
        self._print_rule("<Term> -> <Factor> <Term Prime>")
        self._factor()
        self._term_prime()

    # <Term Prime> -> * <Factor> <Term Prime> | / <Factor> <Term Prime> | ε
    #
    # ε case: defer so it prints after the token that exits this non-terminal.
    def _term_prime(self):
        lex = self._current_lexeme()
        if lex in {"*", "/"}:
            self._match("Operator", lex)
            self._print_rule("<Term Prime> -> * <Factor> <Term Prime> | / <Factor> <Term Prime>")
            self._factor()
            self._term_prime()
        else:
            self._defer_rule("<Term Prime> -> ε")

    # ─── Factor / Primary ─────────────────────────────────────────────────────
    #
    # <Factor> is responsible for printing its own rule in the form
    # "<Factor> -> <Identifier>", "<Factor> -> <Integer>", etc.
    # <Primary> and <Primary Prime> are collapsed into _factor — they do not
    # emit any output lines of their own, matching the expected output format.

    def _factor(self):
        if self._current_lexeme() == "-":
            self._match("Operator", "-")
            self._print_rule("<Factor> -> - <Primary>")
        # Fall through to consume the primary regardless of negation
        self._consume_primary()

    def _consume_primary(self):
        """
        Consume one primary value and print the specific <Factor> -> <X> rule.
        Called by _factor() after handling an optional leading minus.
        """
        tok = self._current_token()
        lex = self._current_lexeme()

        if tok == "Identifier":
            self._match("Identifier")
            self._print_rule("<Factor> -> <Identifier>")
            # <Primary Prime>: optional function-call suffix — no output line
            if self._current_lexeme() == "(":
                self._match("Separator", "(")
                self._ids()
                self._match("Separator", ")")
        elif tok == "Integer":
            self._match("Integer")
            self._print_rule("<Factor> -> <Integer>")
        elif tok == "Real":
            self._match("Real")
            self._print_rule("<Factor> -> <Real>")
        elif lex == "(":
            self._match("Separator", "(")
            self._print_rule("<Factor> -> ( <Expression> )")
            self._expression()
            self._match("Separator", ")")
        elif lex in {"true", "false"}:
            self._match("Keyword", lex)
            self._print_rule("<Factor> -> <Boolean>")
        else:
            self._error(
                f"expected a primary expression (identifier, number, or '('), got '{lex}'"
            )