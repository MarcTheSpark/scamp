import functools

_c_spellings = ((0, 0), (0, 1), (1, 0), (2, -1), (2, 0), (3, 0), (3, 1), (4, 0), (5, -1), (5, 0), (6, -1), (6, 0))
_sharp_spellings = ((0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (3, 0), (3, 1), (4, 0), (4, 1), (5, 0), (5, 1), (6, 0))
_flat_spellings = ((0, 0), (1, -1), (1, 0), (2, -1), (2, 0), (3, 0), (4, -1), (4, 0), (5, -1), (5, 0), (6, -1), (6, 0))
_step_names = ('c', 'd', 'e', 'f', 'g', 'a', 'b')
_step_circle_of_fifths_positions = (0, 2, 4, -1, 1, 3, 5)  # number of sharps or flats for the white keys
_sharp_order = (3, 0, 4, 1, 5, 2, 6)  # order in which sharps are added to a key signature
_flat_order = tuple(reversed(_sharp_order))


class SpellingPolicy:

    def __init__(self, step_alteration_pairs=_c_spellings):
        """
        Object that translates pitches or pitch classes to the actual spelling used in a score
        Note that functools.lru_cache results in the same classmethod calls returning identical objects
        This is valuable because if we play a bunch of notes with properties="spelling: D major", then each time
        that string is converted to a SpellingPolicy class, it gets to reuse the same instance.
        :param step_alteration_pairs: a container of 12 (step, alteration) tuples shoeing how to spell each pitch class
        """
        self.step_alteration_pairs = step_alteration_pairs

    @classmethod
    @functools.lru_cache()
    def all_sharps(cls):
        return cls(_sharp_spellings)

    @classmethod
    @functools.lru_cache()
    def all_flats(cls):
        return cls(_flat_spellings)

    @classmethod
    @functools.lru_cache()
    def from_circle_of_fifths_position(cls, num_sharps_or_flats, avoid_double_accidentals=False):
        if num_sharps_or_flats == 0:
            return c_spellings

        new_spellings = []
        # translate each step, alteration pair to what it would be in the new key
        for step, alteration in _c_spellings:
            new_step = (step + 4 * num_sharps_or_flats) % 7
            # new alteration adds to the c alteration (key_alteration // 7) for each time round the circle of fifths
            # and (key_alteration % 7 > sharp_order.index(new_step)) checks to see if we've added this sharp or flat yet
            new_alteration = alteration + num_sharps_or_flats // 7 + \
                             (num_sharps_or_flats % 7 > _sharp_order.index(new_step))

            while avoid_double_accidentals and abs(new_alteration) > 1:
                if new_alteration > 0:
                    new_alteration -= 1 if new_step in (2, 6) else 2
                    new_step = (new_step + 1) % 7
                else:
                    new_alteration += 1 if new_step in (3, 0) else 2
                    new_step = (new_step - 1) % 7
            new_spellings.append((new_step, new_alteration))

        return cls(tuple(sorted(new_spellings, key=lambda x: (_c_spellings.index((x[0], 0)) + x[1]) % 12)))

    @classmethod
    @functools.lru_cache()
    def from_string(cls, string_initializer: str):
        """
        Creates an instance of SpellingPolicy from several possible input string formats
        :param string_initializer: one of the following:
            - "flat" or "sharp", indicating that black keys are always expressed a particular way
            - a key center (case insensitive), such as "C#" or "f" or "Gb"
            - key centers with modes attached (such as "g minor") are fine, too, but the mode is ignored since it
            doesn't actually affect the way that the accidentals are interpreted.
        """
        if string_initializer == "flat":
            return SpellingPolicy.all_flats()
        elif string_initializer == "sharp":
            return SpellingPolicy.all_sharps()
        else:
            string_initializer_lower = string_initializer.lower().replace(" ", "")
            try:
                num_sharps_or_flats = _step_circle_of_fifths_positions[_step_names.index(string_initializer_lower[0])]
            except ValueError:
                raise ValueError("Bad spelling policy initialization string. Use only 'sharp', 'flat', "
                                 "or the name of the desired key center (e.g. 'G#' or 'Db')")
            if string_initializer_lower[1:].startswith(("b", "flat", "f", "-f", "-flat")):
                num_sharps_or_flats -= 7
            elif string_initializer_lower[1:].startswith(("#", "sharp", "s", "-s", "-sharp")):
                num_sharps_or_flats += 7
            return SpellingPolicy.from_circle_of_fifths_position(num_sharps_or_flats)

    def get_name_alteration_and_octave(self, midi_num):
        rounded_midi_num = int(round(midi_num))
        octave = int(rounded_midi_num / 12) - 1
        pitch_class = rounded_midi_num % 12
        step, alteration = self.step_alteration_pairs[pitch_class]
        name = _step_names[step]
        # add back in any potential quarter tonal deviation
        # (round the different between midi_num and rounded_midi_num to the nearest multiple of 0.5)
        if rounded_midi_num != midi_num:
            alteration += round(2 * (midi_num - rounded_midi_num)) / 2
        return name, alteration, octave

    def get_abjad_pitch(self, midi_num):
        name, alteration, octave = self.get_name_alteration_and_octave(midi_num)
        import abjad
        return abjad.NamedPitch(name, accidental=alteration, octave=octave)
