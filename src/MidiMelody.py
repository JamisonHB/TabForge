import pretty_midi
import numpy as np
from .ChordStep import ChordStep

class MidiMelody:
    """
    Loads a MIDI file and prepares it for the tab generation pipeline.

    Responsibilities:
      - Extracting notes from all instrument tracks
      - Grouping simultaneous notes into ChordStep objects (polyphonic support)
      - Estimating key signature, tempo, and time signature for display

    The chord grouping logic is the primary interface to TabGenerator: every
    note event — whether monophonic or part of a harmony — is represented as
    a ChordStep so the downstream DP operates on a uniform data structure.
    """

    # Krumhansl-Schmuckler key profiles
    MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    # Notes whose onsets fall within this window are treated as simultaneous.
    # 30ms is below human rhythmic perception threshold (~50ms) but forgiving
    # of Basic Pitch's timing imprecision on attacked or strummed notes.
    SIMULTANEITY_WINDOW = 0.030

    # Hard cap on notes per chord — mirrors the physical guitar limit and keeps
    # the Cartesian product in TabGenerator tractable.
    MAX_NOTES_PER_CHORD = 4

    def __init__(self, file_path: str):
        self.midi = pretty_midi.PrettyMIDI(file_path)
        self.notes = self._extract_notes()
        self.chord_steps = self.group_notes(self.notes)
        self.tempo = self._estimate_tempo(self.notes)
        self.key_signature = self._estimate_key(
            self.midi.get_pitch_class_histogram(use_duration=True, use_velocity=False, normalize=True)
        )
        self.time_signature = self._estimate_time_signature(self.notes, self.tempo)

    # ------------------------------------------------------------------
    # Note extraction
    # ------------------------------------------------------------------

    def _extract_notes(self):
        """Extract all notes from every instrument track, sorted by onset."""
        notes = []
        for instrument in self.midi.instruments:
            notes.extend(instrument.notes)
        notes.sort(key=lambda n: n.start)
        return notes

    # ------------------------------------------------------------------
    # Polyphonic grouping
    # ------------------------------------------------------------------

    @staticmethod
    def group_notes(
        notes,
        simultaneity_window: float = SIMULTANEITY_WINDOW,
        max_notes_per_chord: int = MAX_NOTES_PER_CHORD,
    ):
        """
        Cluster notes into ChordStep objects based on onset proximity.

        Notes whose start times fall within `simultaneity_window` seconds of the
        earliest note in a cluster are merged into one ChordStep. When a cluster
        exceeds `max_notes_per_chord`, extras are dropped using a spread-preserving
        algorithm that unconditionally keeps the bass and melody voices.

        Args:
            notes: All notes from the MIDI file, sorted by onset.
            simultaneity_window: Onset tolerance in seconds (default 30ms).
            max_notes_per_chord: Maximum notes per ChordStep (default 4).

        Returns:
            List[ChordStep]: Time-ordered list of chord steps.
        """
        if not notes:
            return []

        steps = []
        current_group = [notes[0]]

        for note in notes[1:]:
            if note.start - current_group[0].start <= simultaneity_window:
                current_group.append(note)
            else:
                steps.append(MidiMelody._make_chord_step(current_group, max_notes_per_chord))
                current_group = [note]

        steps.append(MidiMelody._make_chord_step(current_group, max_notes_per_chord))
        return steps

    @staticmethod
    def _make_chord_step(group, max_notes: int) -> ChordStep:
        """
        Convert a raw note group into a ChordStep, trimming to max_notes if needed.

        Trimming strategy: keep the lowest pitch (bass) and highest pitch (melody)
        unconditionally, then evenly sample inner voices to preserve harmonic spread.

        Args:
            group: Raw cluster of simultaneous notes.
            max_notes: Maximum notes to retain.

        Returns:
            ChordStep with deduplicated, sorted pitches.
        """
        onset = group[0].start
        unique_pitches = sorted(set(n.pitch for n in group))

        if len(unique_pitches) <= max_notes:
            return ChordStep(pitches=unique_pitches, onset=onset)

        kept = [unique_pitches[0], unique_pitches[-1]]  # bass + melody
        remaining_slots = max_notes - 2
        inner = unique_pitches[1:-1]

        if remaining_slots > 0 and inner:
            step = max(1, len(inner) // remaining_slots)
            kept += inner[::step][:remaining_slots]

        return ChordStep(pitches=sorted(set(kept)), onset=onset)

    # ------------------------------------------------------------------
    # Musical analysis — implementation details omitted
    # Full source available upon request.
    # ------------------------------------------------------------------

    def _estimate_key(self, hist) -> str:
        """
        Estimate key signature using the Krumhansl-Schmuckler key-finding algorithm.

        Correlates the pitch-class histogram of the piece against major and minor
        key profiles for all 12 roots, returning the best-matching key.

        Returns:
            str: e.g. "C Major", "A Minor"
        """
        # Implementation omitted — full source available upon request
        ...

    def _estimate_tempo(self, notes) -> float:
        """
        Estimate tempo in BPM from inter-onset intervals (IOIs).

        Builds a histogram of IOIs filtered to a musically plausible range,
        finds the modal IOI bin, and converts to BPM. Applies octave correction
        to keep the result in a standard 50–150 BPM range.

        Returns:
            float: Estimated tempo in BPM
        """
        # Implementation omitted — full source available upon request
        ...

    def _estimate_time_signature(self, notes, tempo) -> str:
        """
        Estimate time signature by scoring note alignment against rhythmic grids.

        Compares 4/4 and 3/4 alignment scores for each note onset and returns
        the meter with the higher score.

        Returns:
            str: "4/4" or "3/4"
        """
        # Implementation omitted — full source available upon request
        ...