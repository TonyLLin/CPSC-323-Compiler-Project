"""
rat_parser.py

Recursive Descent Parser (RDP) for the RAT26S language.

Grammar (left-recursion removed, left-factored):

  <Rat26S>               -> @ <Opt Function Defs> @ <Opt Declaration List> @ <Statement List> @

  <Opt Function Defs>    -> <Function Defs> | eps
  <Function Defs>        -> <Function> <Function Defs Prime>
  <Function Defs Prime>  -> <Function Defs> | eps

  <Function>             -> function <Identifier> ( <Opt Parameter List> ) { <Opt Declaration List> <Statement List> }
  <Opt Parameter List>   -> <Parameter List> | eps
  <Parameter List>       -> <Parameter> <Parameter List Prime>
  <Parameter List Prime> -> , <Parameter List> | eps
  <Parameter>            -> <IDs> <Qualifier>
  <Qualifier>            -> integer | real | boolean

  <Opt Declaration List> -> <Declaration List> | eps
  <Declaration List>     -> <Declaration> ; <Declaration List Prime>
  <Declaration List Prime> -> <Declaration List> | eps
  <Declaration>          -> <Qualifier> <IDs>
  <IDs>                  -> <Identifier> <IDs Prime>
  <IDs Prime>            -> , <IDs> | eps

  <Statement List>       -> <Statement> <Statement List Prime>
  <Statement List Prime> -> <Statement List> | eps
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
  <Expression Prime>     -> + <Term> <Expression Prime> | - <Term> <Expression Prime> | eps

  <Term>                 -> <Factor> <Term Prime>
  <Term Prime>           -> * <Factor> <Term Prime> | / <Factor> <Term Prime> | eps

  <Factor>               -> - <Primary> | <Primary>
  <Primary>              -> <Identifier> <Primary Prime> | <Integer> | ( <Expression> ) | <Real> | true | false
  <Primary Prime>        -> ( <IDs> ) | eps
"""

from lexer import lexer
from FinalAssembler import CodeGenerator, SymbolTable, SemanticError

# ─────────────────────────────────────────────────────────────────────────────
# Toggle: set to True to print each production rule as it is applied
# ─────────────────────────────────────────────────────────────────────────────
PRINT_RULES: bool = True

# ─────────────────────────────────────────────────────────────────────────────
# Keywords that can begin a statement (used for synchronization / FIRST sets)
# ─────────────────────────────────────────────────────────────────────────────
STATEMENT_FIRST_KEYWORDS = {"if", "return", "write", "read", "while"}
# "real" is excluded — Simplified RAT26S only permits integer and boolean
QUALIFIER_KEYWORDS        = {"integer", "boolean"}


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
        # place their eps productions here so they appear in the output AFTER
        # the token that caused the parser to exit those non-terminals.
        self._pending_rules: list = []

        # Attach the symbol table and code generator:
        # Every grammar method that needs to record a declaration or emit an
        # instruction will reach them through self.st and self.cg.
        self.st = SymbolTable()    # tracks declared identifiers
        self.cg = CodeGenerator()  # accumulates virtual-machine instructions

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
        Output order: token line first, then any deferred (eps) rules.
        """
        tok, lex = self._token if self._token else ("EOF", "EOF")

        if tok != expected_token:
            self._error(f"expected token '{expected_token}'"
                        + (f" ('{expected_lexeme}')" if expected_lexeme else "")
                        + f", got '{tok}' ('{lex}')")

        if expected_lexeme is not None and lex != expected_lexeme:
            self._error(f"expected lexeme '{expected_lexeme}', got '{lex}'")

        self._print_token()      # token first
        self._flush_pending()    # then any deferred eps rules
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

    def _semantic_error(self, message: str):
        """Raise a SemanticError with location context"""
        tok = self._current_token()
        lex = self._current_lexeme()
        err = (f"\n*** Semantic Error ***\n"
               f"  Line   : {self._line}\n"
               f"  Token  : {tok}\n"
               f"  Lexeme : {lex}\n"
               f"  Detail : {message}\n")
        self._write(err)
        raise SemanticError(err)

    # ─────────────────────────────────────────────────────────────────────────
    # Entry point
    # ─────────────────────────────────────────────────────────────────────────

    def parse(self):
        """Parse the full source. Call this once after constructing the Parser."""
        self._rat26s()
        self._flush_pending()   # emit any trailing deferred eps rules
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

    # <Opt Function Defs> -> <Function Defs> | eps
    def _opt_function_defs(self):
        if self._current_lexeme() == "function":
            # Simplified RAT26S does not allow function definitions
            self._error("Simplified RAT26S does not support function definitions.")
        else:
            self._print_rule("<Opt Function Defs> -> eps")

    # <Function Defs> -> <Function> <Function Defs Prime>
    def _function_defs(self):
        self._print_rule("<Function Defs> -> <Function> <Function Defs Prime>")
        self._function()
        self._function_defs_prime()

    # <Function Defs Prime> -> <Function Defs> | eps
    def _function_defs_prime(self):
        if self._current_lexeme() == "function":
            self._print_rule("<Function Defs Prime> -> <Function Defs>")
            self._function_defs()
        else:
            self._print_rule("<Function Defs Prime> -> eps")

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

    # <Opt Parameter List> -> <Parameter List> | eps
    def _opt_parameter_list(self):
        if self._current_token() == "Identifier":
            self._print_rule("<Opt Parameter List> -> <Parameter List>")
            self._parameter_list()
        else:
            self._print_rule("<Opt Parameter List> -> eps")

    # <Parameter List> -> <Parameter> <Parameter List Prime>
    def _parameter_list(self):
        self._print_rule("<Parameter List> -> <Parameter> <Parameter List Prime>")
        self._parameter()
        self._parameter_list_prime()

    # <Parameter List Prime> -> , <Parameter List> | eps
    def _parameter_list_prime(self):
        if self._current_lexeme() == ",":
            self._match_lexeme(",")
            self._print_rule("<Parameter List Prime> -> , <Parameter List>")
            self._parameter_list()
        else:
            self._print_rule("<Parameter List Prime> -> eps")

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

    # <Opt Declaration List> -> <Declaration List> | eps
    def _opt_declaration_list(self):
        if self._current_lexeme() in QUALIFIER_KEYWORDS:
            self._print_rule("<Opt Declaration List> -> <Declaration List>")
            self._declaration_list()
        else:
            self._print_rule("<Opt Declaration List> -> eps")

    # <Declaration List> -> <Declaration> ; <Declaration List Prime>
    def _declaration_list(self):
        self._print_rule("<Declaration List> -> <Declaration> ; <Declaration List Prime>")
        self._declaration()
        self._match("Separator", ";")
        self._declaration_list_prime()

    # <Declaration List Prime> -> <Declaration List> | eps
    def _declaration_list_prime(self):
        if self._current_lexeme() in QUALIFIER_KEYWORDS:
            self._print_rule("<Declaration List Prime> -> <Declaration List>")
            self._declaration_list()
        else:
            self._print_rule("<Declaration List Prime> -> eps")

    # <Declaration> -> <Qualifier> <IDs>
    def _declaration(self):
        self._print_rule("<Declaration> -> <Qualifier> <IDs>")
        var_type = self._current_lexeme()   # capture the type BEFORE _qualifier consumes it
        self._qualifier()
        self._ids(declared_type=var_type)   # pass the type down so _ids can insert into ST

    # <IDs> -> <Identifier> <IDs Prime>
    def _ids(self, declared_type: str = None):
        """
        :param declared_type: When called from a declaration context, the type
                              keyword ('integer' or 'boolean') so we can insert
                              each identifier into the symbol table.
                              Pass None (default) when IDs appear in non-
                              declaration contexts (e.g. read statement).
        """
        lex = self._current_lexeme()        # capture the identifier name
        self._match("Identifier")
        self._print_rule("<IDs> -> <Identifier> <IDs Prime>")

        # Insert into symbol table when inside a declaration
        if declared_type is not None:
            try:
                self.st.insert(lex, declared_type)
            except SemanticError as e:
                self._semantic_error(str(e))

        self._ids_prime(declared_type=declared_type)

    # <IDs Prime> -> , <IDs> | eps
    def _ids_prime(self, declared_type: str = None):
        if self._current_lexeme() == ",":
            self._match_lexeme(",")
            self._print_rule("<IDs Prime> -> , <IDs>")
            self._ids(declared_type=declared_type)
        else:
            self._print_rule("<IDs Prime> -> eps")

    # ─── Statements ───────────────────────────────────────────────────────────

    # <Statement List> -> <Statement> <Statement List Prime>
    def _statement_list(self):
        self._print_rule("<Statement List> -> <Statement> <Statement List Prime>")
        self._statement()
        self._statement_list_prime()

    # <Statement List Prime> -> <Statement List> | eps
    def _statement_list_prime(self):
        tok = self._current_token()
        lex = self._current_lexeme()
        if (tok == "Identifier"
                or lex == "{"
                or lex in STATEMENT_FIRST_KEYWORDS):
            self._print_rule("<Statement List Prime> -> <Statement List>")
            self._statement_list()
        else:
            self._print_rule("<Statement List Prime> -> eps")

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
        lex = self._current_lexeme()        # capture identifier before consuming it
        self._match("Identifier")
        self._print_rule("<Statement> -> <Assign>")
        self._print_rule("<Assign> -> <Identifier> = <Expression> ;")

        # Validate that the LHS identifier has been declared
        try:
            addr = self.st.get_address(lex)
        except SemanticError as e:
            self._semantic_error(str(e))

        self._match("Operator", "=")
        self._expression()

        # Expression result is on TOS, so store it at the variable's address
        self.cg.gen_instr("POPM", addr)

        self._match("Separator", ";")

    # <If> -> if ( <Condition> ) <Statement> <If Prime>
    def _if_stmt(self):
        self._match("Keyword", "if")
        self._print_rule("<Statement> -> <If>")
        self._print_rule("<If> -> if ( <Condition> ) <Statement> <If Prime>")
        self._match("Separator", "(")
        self._condition()
        self._match("Separator", ")")

        # JMPZ placeholder: exit address filled in by _if_prime
        jmpz_idx = self.cg.gen_instr("JMPZ", "nil")

        self._statement()
        self._if_prime(jmpz_idx)

    # <If Prime> -> otherwise <Statement> fi | fi
    def _if_prime(self, jmpz_idx: int):
        if self._current_lexeme() == "otherwise":
            self._match("Keyword", "otherwise")
            self._print_rule("<If Prime> -> otherwise <Statement> fi")

            # JMP to skip over the else body; then patch the JMPZ to
            # land at the start of the else body (next instruction after JMP)
            jmp_idx = self.cg.gen_instr("JMP", "nil")
            self.cg.backpatch(jmpz_idx, self.cg.get_next_index())

            self._statement()

            # patch the JMP to land after the else body; emit LABEL
            self.cg.backpatch(jmp_idx, self.cg.get_next_index())
            self.cg.gen_instr("LABEL", "nil")
        else:
            self._print_rule("<If Prime> -> fi")
            # no else, patch JMPZ to land right after the then body
            self.cg.backpatch(jmpz_idx, self.cg.get_next_index())
            self.cg.gen_instr("LABEL", "nil")

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

        # pop TOS and send to standard output
        self.cg.gen_instr("SOUT", "nil")

    # <Scan> -> read ( <IDs> ) ;
    def _scan_stmt(self):
        self._match("Keyword", "read")
        self._print_rule("<Statement> -> <Scan>")
        self._print_rule("<Scan> -> read ( <IDs> ) ;")
        self._match("Separator", "(")

        # collect all identifiers in the read list, then emit
        # SIN + POPM for each one in order
        self._scan_ids()

        self._match("Separator", ")")
        self._match("Separator", ";")

    def _scan_ids(self):
        """
        Variant of _ids used exclusively inside read().
        Emits SIN + POPM <addr> for every identifier consumed.
        Validates each identifier against the symbol table.
        """
        lex = self._current_lexeme()
        self._match("Identifier")
        self._print_rule("<IDs> -> <Identifier> <IDs Prime>")

        try:
            addr = self.st.get_address(lex)
        except SemanticError as e:
            self._semantic_error(str(e))

        # read one value from stdin and store it at this variable's address
        self.cg.gen_instr("SIN", "nil")
        self.cg.gen_instr("POPM", addr)

        # handle comma-separated list recursively
        if self._current_lexeme() == ",":
            self._match_lexeme(",")
            self._print_rule("<IDs Prime> -> , <IDs>")
            self._scan_ids()
        else:
            self._print_rule("<IDs Prime> -> eps")

    # <While> -> while ( <Condition> ) <Statement>
    def _while_stmt(self):
        self._match("Keyword", "while")
        self._print_rule("<Statement> -> <While>")
        self._print_rule("<While> -> while ( <Condition> ) <Statement>")

        # record the top-of-loop address, emit LABEL
        top = self.cg.gen_instr("LABEL", "nil")

        self._match("Separator", "(")
        self._condition()
        self._match("Separator", ")")

        # emit JMPZ as placeholder; address filled in after body
        jmpz_idx = self.cg.gen_instr("JMPZ", "nil")

        self._statement()

        # jump back to LABEL, then backpatch the JMPZ to exit address
        self.cg.gen_instr("JMP", top)
        self.cg.backpatch(jmpz_idx, self.cg.get_next_index())

    # ─── Condition / Relop ────────────────────────────────────────────────────

    # <Condition> -> <Expression> <Relop> <Expression>
    def _condition(self):
        self._print_rule("<Condition> -> <Expression> <Relop> <Expression>")
        self._expression()
        op = self._relop()          # returns the instruction mnemonic
        self._expression()
        # both operands are now on the stack — emit the comparison
        self.cg.gen_instr(op, "nil")

    # <Relop> -> == | != | > | < | <= | =>
    def _relop(self) -> str:
        """Consume the relational operator and return its VM instruction mnemonic."""
        lex = self._current_lexeme()
        if lex not in {"==", "!=", ">", "<", "<=", "=>"}:
            self._error(f"expected a relational operator, got '{lex}'")
        self._match("Operator", lex)
        self._print_rule("<Relop> -> == | != | > | < | <= | =>")

        _RELOP_INSTR = {"<": "LES", ">": "GRT", "==": "EQU",
                        "!=": "NEQ", "<=": "LEQ", "=>": "GEQ"}
        return _RELOP_INSTR[lex]

    # ─── Expressions ──────────────────────────────────────────────────────────

    # <Expression> -> <Term> <Expression Prime>
    def _expression(self):
        self._print_rule("<Expression> -> <Term> <Expression Prime>")
        self._term()
        self._expression_prime()

    # <Expression Prime> -> + <Term> <Expression Prime> | - <Term> <Expression Prime> | eps
    def _expression_prime(self):
        lex = self._current_lexeme()
        if lex in {"+", "-"}:
            self._match("Operator", lex)
            self._print_rule("<Expression Prime> -> + <Term> <Expression Prime> | - <Term> <Expression Prime>")
            self._term()
            # both operands now on stack. emit arithmetic instruction
            self.cg.gen_instr("A" if lex == "+" else "S", "nil")
            self._expression_prime()
        else:
            self._defer_rule("<Expression Prime> -> eps")

    # <Term> -> <Factor> <Term Prime>
    def _term(self):
        self._print_rule("<Term> -> <Factor> <Term Prime>")
        self._factor()
        self._term_prime()

    # <Term Prime> -> * <Factor> <Term Prime> | / <Factor> <Term Prime> | eps
    def _term_prime(self):
        lex = self._current_lexeme()
        if lex in {"*", "/"}:
            self._match("Operator", lex)
            self._print_rule("<Term Prime> -> * <Factor> <Term Prime> | / <Factor> <Term Prime>")
            self._factor()
            # both operands now on stack. emit multiply or divide
            self.cg.gen_instr("M" if lex == "*" else "D", "nil")
            self._term_prime()
        else:
            self._defer_rule("<Term Prime> -> eps")

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
            lex = self._current_lexeme()    # capture before consuming
            self._match("Identifier")
            self._print_rule("<Factor> -> <Identifier>")

            # Validate identifier is declared before use
            try:
                addr = self.st.get_address(lex)
            except SemanticError as e:
                self._semantic_error(str(e))

            # push the variable's value onto the stack
            self.cg.gen_instr("PUSHM", addr)

            # <Primary Prime>: optional function-call suffix — no output line
            if self._current_lexeme() == "(":
                self._match("Separator", "(")
                self._ids()
                self._match("Separator", ")")
        elif tok == "Integer":
            lex = self._current_lexeme()
            self._match("Integer")
            self._print_rule("<Factor> -> <Integer>")
            # push the integer literal directly onto the stack
            self.cg.gen_instr("PUSHI", lex)
        elif tok == "Real":
            self._match("Real")
            self._print_rule("<Factor> -> <Real>")
            # Real is disallowed in Simplified RAT26S. Flag it as a semantic error
            self._semantic_error("Type 'real' is not allowed in Simplified RAT26S.")
        elif lex == "(":
            self._match("Separator", "(")
            self._print_rule("<Factor> -> ( <Expression> )")
            self._expression()
            self._match("Separator", ")")
        elif lex in {"true", "false"}:
            self._match("Keyword", lex)
            self._print_rule("<Factor> -> <Boolean>")
            # booleans are integers. true=1, false=0
            self.cg.gen_instr("PUSHI", 1 if lex == "true" else 0)
        else:
            self._error(
                f"expected a primary expression (identifier, number, or '('), got '{lex}'"
            )