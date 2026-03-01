"""
FSM.py

Object-oriented DFSM for classifying identifiers, integers, and reals.

Regular Expressions:
  Integer:    [0-9]+
  Real:       [0-9]+ '.' [0-9]+
  Identifier: [a-zA-Z_][a-zA-Z0-9_]*
"""
from enum import IntEnum

#====================================================================#
# States (as enumerations)
#====================================================================#
# Each value is a row index in TRANSITION_TABLE
class State(IntEnum):
    START         = 0
    INTEGER       = 1
    DECIMAL_POINT = 2
    REAL          = 3
    IDENTIFIER    = 4
    ERROR         = 5

# Each value is a column index in TRANSITION_TABLE
class CharClass(IntEnum):
    DIGIT = 0
    ALPHA = 1
    UNDER = 2
    DOT   = 3
    OTHER = 4


# ====================================================================#
# 2D Transition Table
# ====================================================================#
# TRANSITION_TABLE[state][char_class] -> next State
#
# To read the table, think: "I'm in this current state (row) and I'm this char
# class type (col), let move to this next state based on (row)(col)"
# (e.g. I am in the start state (first row) and my char is a digit class (first column),
# then I move to integer state.)

#           DIGIT             ALPHA             UNDER             DOT                   OTHER
TRANSITION_TABLE: list[list[State]] = [
    # START
    [ State.INTEGER,        State.IDENTIFIER, State.IDENTIFIER, State.ERROR,       State.ERROR ],
    # INTEGER
    [ State.INTEGER,        State.ERROR,      State.ERROR,      State.DECIMAL_POINT, State.ERROR ],
    # DECIMAL_POINT
    [ State.REAL,           State.ERROR,      State.ERROR,      State.ERROR,       State.ERROR ],
    # REAL
    [ State.REAL,           State.ERROR,      State.ERROR,      State.ERROR,       State.ERROR ],
    # IDENTIFIER
    [ State.IDENTIFIER,     State.IDENTIFIER, State.IDENTIFIER, State.ERROR,       State.ERROR ],
    # ERROR
    [ State.ERROR,          State.ERROR,      State.ERROR,      State.ERROR,       State.ERROR ],
]

# Accepting states and the token type they produce
ACCEPTING_STATES: dict[State, str] = {
    State.INTEGER:    "Integer",
    State.REAL:       "Real",
    State.IDENTIFIER: "Identifier",
}

#====================================================================#
# FSM OOP
#====================================================================#
class myFSM:
    def __init__(self):
        """
        Holds the current state of FSM and initializes to START state
        """
        self.curState: State = State.START

    def execute(self, char_class: CharClass):
        """
        Executes the FSM and finds the current state based on previous state.
        and character in the 2D-Table

        :param char_class: Enumeration of character passed from classify function
        """
        self.curState = TRANSITION_TABLE[self.curState][char_class]


class Char:
    def __init__(self):
        """
        Always creates a new instance of the FSM to guarantee tokens begin in START state
        """
        self.FSM = myFSM() # create instance of FSM


def _char_class(char: str) -> CharClass:
    """
    Takes the character read from lexeme in classify function and assigns it
    to a corresponding enumeration for index use in 2D-Table.

    :param char: Single character from the lexeme string
    :return: Enumeration corresponding to the character read from lexeme
    """
    if char.isdigit(): return CharClass.DIGIT
    if char.isalpha(): return CharClass.ALPHA
    if char == '_':    return CharClass.UNDER
    if char == '.':    return CharClass.DOT
    return CharClass.OTHER

#====================================================================#
# Classify (Starting point)
#====================================================================#
def classify(source: str) -> tuple[str, str]:
    """
    Starting point of FSM.py after having a lexeme source string passed from the lexer.
    Uses a DFSM to determine token type of lexeme

    :param source: Lexeme source string
    :return: "Integer" | "Real" | "Identifier", lexeme
    """
    # Create new FSM instance
    char_machine = Char()

    for char in source:
        # Using the FSM instance, we execute the FSM based on the current character's enumeration
        # and the state which is stored in the char_machine.FSM class already. Repeat until EOS and
        # we get our final state
        char_machine.FSM.execute(_char_class(char))
        if char_machine.FSM.curState == State.ERROR:
            return "Unknown", source

    # Based on the last state that the FSM was in, we check if it is an accepting state or unknown otherwise
    token_type = ACCEPTING_STATES.get(char_machine.FSM.curState, "Unknown")
    return token_type, source

