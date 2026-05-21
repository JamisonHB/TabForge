from dataclasses import dataclass

@dataclass (frozen=True)
class Position:
    """
    Position class represents the position of a note on the guitar fretboard, defined by its string number and fret number.
    """
    
    string: int
    fret: int