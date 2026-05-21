from dataclasses import dataclass, field
from typing import List


@dataclass
class ChordStep:
    """
    Represents a single step in the tablature and contains a single note or a chord of simultaneous notes.
    
    Attributes:
        pitches (List[int]): Midi pitch values of all notes in this step, sorted in ascending order.
        
        onset (float): The start time in seconds of the earliest note in this group.
    """

    pitches: List[int] = field(default_factory=list)
    onset: float = 0.0

    @property
    def is_chord(self):
        """
        Check if this step contains a chord (more than one note).

        Returns:
            bool: True if this step contains more than one pitch, False otherwise.
        """
        return len(self.pitches) > 1