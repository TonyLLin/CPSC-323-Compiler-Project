class SymbolTable:
    """
    Tracks every declared identifier, its memory address, and its type.
    Memory addresses begin at 10000 and increment by 1 per new identifier.
    """

    def __init__(self):
        self._table: dict[str, dict] = {}
        self._next_address: int = 10000

    def insert(self, lexeme: str, var_type: str):
        """
        Insert a new identifier.  Raises if it is already declared.

        :param lexeme:   The identifier name.
        :param var_type: The declared type ('integer' or 'boolean').
        """
        if lexeme in self._table:
            raise SemanticError(f"Identifier '{lexeme}' is already declared.")
        self._table[lexeme] = {
            "address": self._next_address,
            "type":    var_type,
        }
        self._next_address += 1

    def lookup(self, lexeme: str) -> dict:
        """
        Return the symbol-table entry for *lexeme*.
        Raises if the identifier was never declared.

        :param lexeme: The identifier name.
        :return: Dict with keys 'address' and 'type'.
        """
        if lexeme not in self._table:
            raise SemanticError(f"Identifier '{lexeme}' used without declaration.")
        return self._table[lexeme]

    def get_address(self, lexeme: str) -> int:
        """Convenience wrapper — returns just the memory address."""
        return self.lookup(lexeme)["address"]

    def get_type(self, lexeme: str) -> str:
        """Convenience wrapper — returns just the declared type."""
        return self.lookup(lexeme)["type"]

    def print_table(self, out=None):
        """
        Print the full symbol table to *out* (or stdout).

        :param out: File-like object, or None for stdout.
        """
        def w(text):
            if out:
                out.write(text + "\n")
            else:
                print(text)

        w("\nSymbol Table")
        w(f"{'Identifier':<15} {'MemoryLocation':<15} {'Type':<10}")
        for name, info in self._table.items():
            w(f"{name:<15} {info['address']:<15} {info['type']:<10}")

class CodeGenerator:
    """
    Accumulates virtual-machine instructions and supports back-patching.
    Instruction indices are 1-based (matching the assignment's listing format).
    """

    def __init__(self):
        self._instructions: list[tuple[str, str]] = []  # list of (op, operand)

    def gen_instr(self, op: str, operand: str = "") -> int:
        """
        Append one instruction and return its 1-based index.

        :param op:      Mnemonic (e.g. 'PUSHM', 'POPM', 'A', 'JMPZ', …).
        :param operand: Operand string, or '' for nil-operand instructions.
        :return:        1-based index of the new instruction (usable as a jump target).
        """
        self._instructions.append((op, str(operand)))
        return len(self._instructions)

    def get_next_index(self) -> int:
        """Return the 1-based index that the *next* gen_instr call will occupy."""
        return len(self._instructions) + 1

    def backpatch(self, index: int, target: int):
        """
        Fill in the operand of a previously emitted jump instruction.

        :param index:  1-based index of the instruction to patch.
        :param target: The instruction address to jump to.
        """
        op, _ = self._instructions[index - 1]
        self._instructions[index - 1] = (op, str(target))

    def print_asm(self, out=None):
        """
        Print the full instruction listing to *out* (or stdout).

        :param out: File-like object, or None for stdout.
        """
        def w(text):
            if out:
                out.write(text + "\n")
            else:
                print(text)

        w("\nAssembly Code Listing")
        for i, (op, operand) in enumerate(self._instructions, start=1):
            line = f"{i:<5} {op}"
            if operand:
                line += f"   {operand}"
            w(line)


# =============================================================================
# Semantic error (distinct from SyntaxError so callers can tell them apart)
# =============================================================================

class SemanticError(Exception):
    pass

