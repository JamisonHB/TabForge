from pydantic import BaseModel
from typing import List, Optional


class TabRequest(BaseModel):
    """
    Request body shared by tab generation, export, and anchor suggestion endpoints.

    Attributes:
        anchor_mode: How to determine the hand anchor fret ("auto", "manual", "none").
        anchor:      Explicit anchor fret when anchor_mode is "manual".
        tuning:      MIDI pitch numbers for each open string, low to high.
                     Defaults to standard 6-string guitar tuning on the backend.
        max_fret:    Highest fret number available on the instrument.
        transpose:   Semitones to shift every note before generating the tab.
    """

    anchor_mode: str = "none"
    anchor: Optional[int] = None
    tuning: Optional[List[int]] = None
    max_fret: Optional[int] = 24
    transpose: int = 0