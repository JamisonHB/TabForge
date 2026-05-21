from .Position import Position

class Fretboard:
    """
    Fretboard class is responsible for mapping MIDI note numbers to their corresponding string and fret positions on a guitar fretboard.
    Supports dynamic tuning and allows for a configurable maximum fret number (default is 24).
    The class builds a mapping of MIDI pitches to their possible string and fret positions during initialization, which
    can be efficiently queried using the get_positions method.
    """
    
    GUITAR_STANDARD = [40, 45, 50, 55, 59, 64]  # E2, A2, D3, G3, B3, E4

    def __init__(self, tuning = GUITAR_STANDARD, max_fret = 24):
        """
        Initialize a Fretboard with a specific tuning and maximum fret.

        Builds a mapping from MIDI pitches to all possible string/fret positions on the guitar.

        Args:
            tuning (List[int], optional): List of MIDI numbers for the open strings (default is standard 6-string tuning).
            max_fret (int, optional): Maximum fret number on the guitar neck (default is 24).
        """

        self.tuning = tuning
        self.max_fret = max_fret
        self.num_strings = len(self.tuning)
        self.pitch_map = self._build_map()

    def _build_map(self):
        """
        Build a mapping from MIDI pitches to all possible positions on the guitar fretboard.

        Iterates over each string in the tuning and all frets up to the maximum fret. 
        Each pitch is mapped to a list of Position objects indicating the string and fret
        where the pitch can be played.

        Returns:
            dict[int, List[Position]]: A dictionary mapping MIDI note numbers to lists of Position objects.
        """

        pitch_map = {}
        
        for string_index, open_note in enumerate(self.tuning):
            string_number = string_index + 1

            for fret in range(self.max_fret + 1):
                pitch = open_note + fret
                pitch_map.setdefault(pitch, []).append(Position(string_number, fret))
        
        return pitch_map

    def get_positions(self, midi_pitch):
        """Return a list of Position objects for the given MIDI pitch."""
        
        return self.pitch_map.get(midi_pitch, [])