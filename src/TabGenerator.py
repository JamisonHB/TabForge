from itertools import product
from typing import List, Optional, Tuple

from .Position import Position
from .ChordStep import ChordStep

# A ChordState is an immutable tuple of Positions — one per note in a chord step.
# Monophonic notes are simply a 1-tuple, so the DP structure is identical for
# both monophonic and polyphonic input.
ChordState = Tuple[Position, ...]


class TabGenerator:
    """
    Generate guitar tablature from a melody using a fretboard model.

    Supports both monophonic melodies and polyphonic harmonies. Internally every
    time step is treated as a ChordStep (which may contain only a single pitch).
    The Viterbi DP operates over ChordState tuples so the structure is uniform
    regardless of whether the input is monophonic or polyphonic.

    Playability constraints applied before the DP search:
      - No two notes in a chord may share the same string.
      - The fret span of a chord fingering may not exceed MAX_FRET_SPAN frets.
        Open-string notes (fret 0) are excluded from the span calculation because
        they require no fretting finger.

    Attributes:
        chord_steps (List[ChordStep]): Time-ordered chord steps from the melody.
        fretboard (Fretboard): Guitar fretboard model.
        hand_anchor (Optional[int]): Preferred fret position for the fretting hand.
    """

    MAX_FRET_SPAN = 4

    def __init__(self, melody, fretboard, hand_anchor: Optional[int] = None):
        """
        Initialize a TabGenerator.

        Args:
            melody (MidiMelody): A MidiMelody object whose `chord_steps` attribute
                                 drives tab generation.
            fretboard (Fretboard): The guitar fretboard model used to map pitches
                                   to string/fret positions.
            hand_anchor (int, optional): Preferred fret to hover around. When
                                         provided, fingerings near this fret are
                                         favoured by the cost function.
        """
        self.chord_steps: List[ChordStep] = melody.chord_steps
        self.fretboard = fretboard
        self.hand_anchor = hand_anchor
        self.last_total_cost: float = 0.0

    # ------------------------------------------------------------------
    # Playability filtering
    # ------------------------------------------------------------------

    def _is_playable(self, state: ChordState) -> bool:
        """
        Return True if a chord fingering is physically plausible.

        Enforces two constraints:
          1. String uniqueness — no two notes on the same string.
          2. Fret span — the distance between the lowest and highest *fretted*
             positions must not exceed MAX_FRET_SPAN.

        Args:
            state (ChordState): Candidate fingering tuple to evaluate.

        Returns:
            bool: True if the fingering passes all playability checks.
        """
        strings_used = [p.string for p in state]
        if len(strings_used) != len(set(strings_used)):
            return False

        fretted = [p.fret for p in state if p.fret > 0]
        if len(fretted) >= 2 and (max(fretted) - min(fretted)) > self.MAX_FRET_SPAN:
            return False

        return True

    def _candidate_states(self, step: ChordStep) -> List[ChordState]:
        """
        Enumerate all playable ChordState fingerings for a given ChordStep.

        Computes the Cartesian product of per-pitch position lists from the
        fretboard, then filters through `_is_playable`. Steps where any pitch
        has no valid position on the current instrument are skipped gracefully.

        Args:
            step (ChordStep): The chord step to enumerate fingerings for.

        Returns:
            List[ChordState]: All valid, playable fingering tuples for this step.
        """
        per_pitch_positions = [self.fretboard.get_positions(pitch) for pitch in step.pitches]

        if any(len(positions) == 0 for positions in per_pitch_positions):
            return []

        return [
            state
            for state in product(*per_pitch_positions)
            if self._is_playable(state)
        ]

    # ------------------------------------------------------------------
    # Transition cost
    # ------------------------------------------------------------------

    def _chord_transition_cost(
        self,
        prev_state: Optional[ChordState],
        curr_state: ChordState,
    ) -> float:
        """
        Estimate the physical cost of moving from one chord fingering to the next.

        Three cost components are summed:

        - **Frame movement (1.0x):** Mean absolute fret distance of each position
          in curr_state from the centroid (average fret) of prev_state. Using
          the centroid rather than pairing individual notes avoids penalising
          voicing changes that keep the hand in the same region of the neck.

        - **String displacement (0.5x):** Mean absolute string change from the
          previous state's string centroid. Weighted lower than fret movement
          because crossing strings is generally less effortful than shifting
          hand position.

        - **Anchor deviation (2.5x):** Mean distance of each fretted position in
          curr_state from the preferred hand_anchor fret. Open strings are
          excluded. Only applied when hand_anchor is set.

        Args:
            prev_state: Previous chord fingering, or None for the first step.
            curr_state: Current chord fingering being evaluated.

        Returns:
            float: Total heuristic transition cost.
        """
        if prev_state is None:
            return 0.0

        prev_fretted = [p.fret for p in prev_state if p.fret > 0] or [p.fret for p in prev_state]
        prev_fret_center = sum(prev_fretted) / len(prev_fretted)
        prev_string_center = sum(p.string for p in prev_state) / len(prev_state)

        fret_cost = sum(abs(p.fret - prev_fret_center) for p in curr_state) / len(curr_state)
        string_cost = sum(abs(p.string - prev_string_center) for p in curr_state) / len(curr_state) * 0.5

        anchor_cost = 0.0
        if self.hand_anchor is not None:
            fretted_curr = [p for p in curr_state if p.fret > 0]
            if fretted_curr:
                anchor_cost = (
                    sum(abs(p.fret - self.hand_anchor) for p in fretted_curr)
                    / len(fretted_curr)
                    * 2.5
                )

        return fret_cost + string_cost + anchor_cost

    # ------------------------------------------------------------------
    # Viterbi DP
    # ------------------------------------------------------------------

    def generate(self) -> List[ChordState]:
        """
        Generate an optimal fingering sequence using Viterbi dynamic programming.

        Forward pass: For each time step, compute the minimum cumulative
        transition cost for every candidate ChordState, storing a backpointer
        to the previous state that achieved that minimum.

        Backward pass: Starting from the lowest-cost state in the final layer,
        follow backpointers to reconstruct the optimal path.

        ChordSteps with no valid fingering (e.g. pitches outside the instrument's
        range) are silently skipped so that one unplayable note does not abort
        the entire piece.

        Time complexity: O(N x S^2), where N is the number of chord steps and S
        is the maximum number of candidate states per step.

        Returns:
            List[ChordState]: Optimal fingering sequence, one ChordState per
                              surviving time step. Each ChordState is a tuple of
                              Position objects — a 1-tuple for monophonic steps,
                              an n-tuple for chords.
        """
        if not self.chord_steps:
            return []

        layers: List[List[ChordState]] = []
        for step in self.chord_steps:
            candidates = self._candidate_states(step)
            if candidates:
                layers.append(candidates)

        if not layers:
            return []

        paths: List[dict] = []
        paths.append({state: (0.0, None) for state in layers[0]})

        for i in range(1, len(layers)):
            current_layer: dict = {}
            for curr_state in layers[i]:
                best_prev: Optional[ChordState] = None
                min_cost = float("inf")

                for prev_state, (cumulative_cost, _) in paths[i - 1].items():
                    cost = cumulative_cost + self._chord_transition_cost(prev_state, curr_state)
                    if cost < min_cost:
                        min_cost = cost
                        best_prev = prev_state

                current_layer[curr_state] = (min_cost, best_prev)
            paths.append(current_layer)

        last_layer = paths[-1]
        best_final = min(last_layer, key=lambda s: last_layer[s][0])
        self.last_total_cost = last_layer[best_final][0]

        best_path: List[ChordState] = []
        current_state = best_final
        for i in range(len(paths) - 1, -1, -1):
            best_path.append(current_state)
            current_state = paths[i][current_state][1]

        return best_path[::-1]