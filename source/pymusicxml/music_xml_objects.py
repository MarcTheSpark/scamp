from collections import MutableSequence, Sequence
from .utilities import _least_common_multiple, _is_power_of_two, _escape_split
from xml.etree import ElementTree
from abc import ABC, abstractmethod
from fractions import Fraction
from numbers import Number
import math
import datetime
import tempfile
import subprocess


# TODO: Make nested printing possible


# --------------------------------------------------- Utilities ----------------------------------------------------


def _pad_with_rests(components, desired_length):
    """
    Appends rests to a list of components to fill out the desired length
    :param components: a list of MusicXMLComponents
    :param desired_length: in quarters
    :return: an expanded list of components
    """
    components = [components] if not isinstance(components, (tuple, list)) else components
    assert all(hasattr(component, "true_length") for component in components)
    sum_length = sum(component.true_length for component in components)
    assert sum_length <= desired_length
    remaining_length = Fraction(desired_length - sum_length).limit_denominator()
    assert _is_power_of_two(remaining_length.denominator), "Remaining length cannot require tuplets."
    components = list(components)

    longer_rests = []
    for longer_rest_length in (4, 2, 1):
        while remaining_length >= longer_rest_length:
            longer_rests.append(Rest(longer_rest_length))
            remaining_length -= longer_rest_length
            remaining_length = Fraction(remaining_length).limit_denominator()
    longer_rests.reverse()

    while remaining_length > 0:
        odd_remainder = 1 / remaining_length.denominator
        components.append(Rest(odd_remainder))
        remaining_length -= odd_remainder
        remaining_length = Fraction(remaining_length).limit_denominator()

    return components + longer_rests


# --------------------------------------------- Abstract Parent Class -----------------------------------------------


class MusicXMLComponent(ABC):

    @abstractmethod
    def render(self):
        # Renders this component to a tuple of ElementTree.Element
        # the reason for making it a tuple is that musical objects like chords are represented by several
        # notes side by side, with all but the first containing a </chord> tag.
        pass

    @abstractmethod
    def wrap_as_score(self):
        # Wrap this component in a score so that it can be exported and viewed
        pass

    def to_xml(self, pretty_print=False):
        element_rendering = self.render()

        if pretty_print:
            # this is not ideal; it's ugly and requires parsing and re-rendering and then removing version tags
            # for now, though, it's good enough and gets the desired results
            from xml.dom import minidom
            header = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD ' \
                     'MusicXML 3.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n'
            import re
            return header + ''.join(
                re.sub(
                    "<\?xml version.*\?>\n",
                    "",
                    minidom.parseString(ElementTree.tostring(element, 'utf-8')).toprettyxml(indent="\t")
                )

                for element in element_rendering
            )
        else:
            header = b'<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD ' \
                     b'MusicXML 3.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">'
            return (header + b''.join(ElementTree.tostring(element, 'utf-8') for element in element_rendering)).decode()

    def export_to_file(self, file_path, pretty_print=True):
        with open(file_path, 'w') as file:
            file.write(self.wrap_as_score().to_xml(pretty_print))

    def view_in_software(self, command):
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as file:
            # Note: For some reason the minified (non-pretty print) version causes MuseScore to spin out and fail
            # This seems to be on MuseScore's end, because there's no difference aside from minification
            file.write(self.wrap_as_score().to_xml(pretty_print=True).encode())
        subprocess.Popen(_escape_split(command, " ") + [file.name])


class MusicXMLContainer(MutableSequence):

    def __init__(self, contents, allowed_types):
        contents = [] if contents is None else contents
        assert isinstance(allowed_types, tuple) and all(isinstance(x, type) for x in allowed_types)
        assert isinstance(contents, Sequence) and all(isinstance(x, allowed_types) for x in contents)
        self.contents = list(contents)

    def insert(self, i, o):
        self.contents.insert(i, o)

    def __getitem__(self, i):
        self.contents.__getitem__(i)

    def __setitem__(self, i, o):
        self.contents.__setitem__(i, o)

    def __delitem__(self, i):
        self.contents.__delitem__(i)

    def __len__(self):
        return self.contents.__len__()


# --------------------------------------------- Pitch and Duration -----------------------------------------------


class Pitch(MusicXMLComponent):

    def __init__(self, step, octave, alteration=0):
        self.step = step
        self.octave = octave
        self.alteration = alteration

    @classmethod
    def from_string(cls, pitch_string: str):
        """
        Constructs Pitch from lilypond pitch string or from standard pitch octave notation
        :param pitch_string: can take the form "C#5" (specifying octave with number, and using '#' for sharp) or "cs'"
        (specifying octave in the lilypond style and using 's' for sharp)
        :return: a Pitch
        """
        pitch_string = pitch_string.lower()
        assert pitch_string[0] in ('c', 'd', 'e', 'f', 'g', 'a', 'b'), "Pitch string not understood"
        step = pitch_string[0].upper()
        if pitch_string[1:].startswith(('b', 'f', '#', 's')):
            alteration = -1 if pitch_string[1:].startswith(('b', 'f')) else 1
            octave_string = pitch_string[2:]
        elif pitch_string[1:].startswith(('qb', 'qf', 'q#', 'qs')):
            alteration = -0.5 if pitch_string[1:].startswith(('qb', 'qf')) else 0.5
            octave_string = pitch_string[3:]
        else:
            alteration = 0
            octave_string = pitch_string[1:]

        try:
            octave = int(octave_string)
        except ValueError:
            if all(x == '\'' for x in octave_string):
                octave = 3 + len(octave_string)
            elif all(x == ',' for x in octave_string):
                octave = 3 - len(octave_string)
            else:
                raise ValueError("Pitch string not understood")
        return cls(step, octave, alteration)

    def render(self):
        pitch_element = ElementTree.Element("pitch")
        step_el = ElementTree.Element("step")
        step_el.text = self.step
        alter_el = ElementTree.Element("alter")
        alter_el.text = str(self.alteration)
        octave_el = ElementTree.Element("octave")
        octave_el.text = str(self.octave)
        pitch_element.append(step_el)
        pitch_element.append(alter_el)
        pitch_element.append(octave_el)
        return pitch_element,

    def wrap_as_score(self):
        return Note(self, 1.0).wrap_as_score()

    def __eq__(self, other):
        if not isinstance(other, Pitch):
            return False
        return self.step == other.step and self.octave == other.octave and self.alteration == other.alteration

    def __repr__(self):
        return "Pitch(\"{}\", {}{})".format(self.step, self.octave,
                                            ", {}".format(self.alteration) if self.alteration != 0 else "")


class Duration(MusicXMLComponent):

    length_to_note_type = {
        8.0: "breve",
        4.0: "whole",
        2.0: "half",
        1.0: "quarter",
        0.5: "eighth",
        0.25: "16th",
        1.0 / 8: "32nd",
        1.0 / 16: "64th",
        1.0 / 32: "128th",
        1.0 / 64: "256th",
        1.0 / 128: "512th",
        1.0 / 256: "1024th"
    }

    note_type_to_length = {b: a for a, b in length_to_note_type.items()}

    valid_divisors = tuple(4 / x for x in length_to_note_type)

    note_type_to_num_beams = {
        "breve": 0,
        "whole": 0,
        "half": 0,
        "quarter": 0,
        "eighth": 1,
        "16th": 2,
        "32nd": 3,
        "64th": 4,
        "128th": 5,
        "256th": 6,
        "512th": 7,
        "1024th": 8
    }

    def __init__(self, note_type, num_dots=0, tuplet_ratio=None):
        """
        Represents a length that can be written as a single note or rest.
        :param note_type: written musicXML duration type, e.g. quarter
        :param num_dots: self-explanatory
        :param tuplet_ratio: a tuple of either (# actual notes, # normal notes) or (# actual, # normal, note type),
        e.g. (4, 3, 0.5) for 4 in the space of 3 eighths.
        """
        assert note_type in Duration.length_to_note_type.values()
        self.note_type = note_type
        self.num_dots = num_dots
        assert isinstance(tuplet_ratio, (type(None), tuple))
        self.tuplet_ratio = tuplet_ratio
        self.divisions = Fraction(self.true_length).limit_denominator().denominator

    @staticmethod
    def _dot_multiplier(num_dots):
        return (2.0 ** (num_dots + 1) - 1) / 2.0 ** num_dots

    @property
    def written_length(self):
        return Duration.note_type_to_length[self.note_type] * Duration._dot_multiplier(self.num_dots)

    @property
    def true_length(self):
        # length taking into account tuplet time modification
        tuplet_modification = 1 if self.tuplet_ratio is None else float(self.tuplet_ratio[1]) / self.tuplet_ratio[0]
        return self.written_length * tuplet_modification

    @property
    def length_in_divisions(self):
        return int(round(self.true_length * self.divisions))

    def num_beams(self):
        return Duration.note_type_to_num_beams[self.note_type]

    @classmethod
    def from_written_length(cls, written_length, tuplet_ratio=None, max_dots_allowed=4):
        try:
            note_type, num_dots = Duration.get_note_type_and_number_of_dots(written_length, max_dots_allowed)
        except ValueError as err:
            raise err
        tuplet_ratio = tuplet_ratio
        return cls(note_type, num_dots, tuplet_ratio)

    @classmethod
    def from_divisor(cls, divisor, num_dots=0, tuplet_ratio=None):
        assert isinstance(divisor, int) and (4.0 / divisor) in Duration.length_to_note_type, "Bad divisor"
        return cls.from_written_length(4.0 / divisor * Duration._dot_multiplier(num_dots), tuplet_ratio=tuplet_ratio)

    @classmethod
    def from_string(cls, duration_string: str):
        if duration_string in Duration.note_type_to_length:
            return cls(duration_string)
        elif duration_string.startswith("dotted "):
            assert duration_string[7:] in Duration.note_type_to_length
            return cls(duration_string[7:], 1)

        num_dots = 0
        while duration_string.endswith('.'):
            duration_string = duration_string[:-1]
            num_dots += 1
        try:
            divisor = int(duration_string)
            assert divisor in Duration.valid_divisors
        except (ValueError, AssertionError):
            raise ValueError("Bad duration string.")
        return cls.from_divisor(divisor, num_dots=num_dots)

    @staticmethod
    def get_note_type_and_number_of_dots(length, max_dots_allowed=4):
        if length in Duration.length_to_note_type:
            return Duration.length_to_note_type[length], 0
        else:
            dots_multiplier = 1.5
            dots = 1
            while length / dots_multiplier not in Duration.length_to_note_type:
                dots += 1
                dots_multiplier = (2.0 ** (dots + 1) - 1) / 2.0 ** dots
                if dots > max_dots_allowed:
                    raise ValueError("Duration length of {} does not resolve to single note type.".format(length))
            return Duration.length_to_note_type[length / dots_multiplier], dots

    def render(self):
        duration_elements = []
        # specify all the duration-related attributes
        duration_el = ElementTree.Element("duration")
        duration_el.text = str(self.length_in_divisions)
        duration_elements.append(duration_el)

        type_el = ElementTree.Element("type")
        type_el.text = self.note_type
        duration_elements.append(type_el)

        for _ in range(self.num_dots):
            duration_elements.append(ElementTree.Element("dot"))

        if self.tuplet_ratio is not None:
            time_modification = ElementTree.Element("time-modification")
            ElementTree.SubElement(time_modification, "actual-notes").text = str(self.tuplet_ratio[0])
            ElementTree.SubElement(time_modification, "normal-notes").text = str(self.tuplet_ratio[1])
            if len(self.tuplet_ratio) > 2:
                if self.tuplet_ratio[2] not in Duration.length_to_note_type:
                    raise ValueError("Tuplet normal note type is not a standard power of two length.")
                ElementTree.SubElement(time_modification, "normal-type").text = \
                    Duration.length_to_note_type[self.tuplet_ratio[2]]
            duration_elements.append(time_modification)
        return tuple(duration_elements)

    def render_to_beat_unit_tags(self):
        beat_unit_el = ElementTree.Element("beat-unit")
        beat_unit_el.text = self.note_type
        out = (beat_unit_el, )
        for _ in range(self.num_dots):
            out += (ElementTree.Element("beat-unit-dot"), )
        return out

    def wrap_as_score(self):
        return Note("c4", self).wrap_as_score()

    def __repr__(self):
        return "Duration(\"{}\", {}{})".format(
            self.note_type, self.num_dots, ", {}".format(self.tuplet_ratio) if self.tuplet_ratio is not None else ""
        )


class BarRestDuration(MusicXMLComponent):

    def __init__(self, length):
        self.length = length
        self.divisions = Fraction(length).limit_denominator().denominator

    @property
    def length_in_divisions(self):
        return int(round(self.true_length * self.divisions))

    @property
    def true_length(self):
        return self.length

    def render(self):
        duration_el = ElementTree.Element("duration")
        duration_el.text = str(int(round(self.length * self.divisions)))
        return duration_el,

    def wrap_as_score(self):
        return BarRest(self).wrap_as_score()


# ---------------------------------------- Note class and all it variations -----------------------------------------


class _XMLNote(MusicXMLComponent):

    def __init__(self, pitch, duration, ties=None, notations=(), articulations=(), notehead=None, beams=None,
                 directions=(), stemless=False, grace=False, is_chord_member=False, voice=None, staff=None):
        """
        Implementation for the xml note element, which includes notes and rests
        :param pitch: a Pitch, or None to indicate a rest, or "bar rest" to indicate that it's a bar rest
        :param duration: a Duration, or just a float representing the bar length in quarter in the case of "bar rest"
        :param ties: "start", "continue", "stop", or None
        :param notations: list for contents of the musicXML "notations" tag
        :param articulations: list of articulations to go in the musicXML "articulations" tag (itself in "notations")
        :param notehead: str representing XML notehead type
        :param beams: a dict of { beam_level (int): beam_type } where beam type is one of ("begin", "continue", "end",
        "forward hook", "backward hook")
        :param directions: list of TextAnnotation's / MetronomeMark's / EndDashedLine's. Things that go in the
        <directions> tag of the resulting musicXML
        :param stemless: boolean for whether to render the note with no stem
        :param grace: boolean for whether to render the note a grace note with no actual duration, or the string
        "slashed" if it's a slashed grace note
        :param is_chord_member: boolean for whether this is a secondary member of a chord (in which case it contains
        the <chord /> tag
        :param voice: which voice this note belongs to within its given staff
        :param staff: which staff this note belongs to within its given part
        """
        assert not (grace and pitch is None)  # can't have grace rests
        self.pitch = pitch
        assert isinstance(duration, (Duration, BarRestDuration))
        self.duration = duration
        # self._divisions stores the divisions per quarter note in the case that this is a bar rest and the duration
        # of the note is a float rather than a Duration object. Otherwise, we just use the "divisions" member of
        # the self.duration object
        assert ties in ("start", "continue", "stop", None)
        self.ties = ties
        self.notations = list(notations) if isinstance(notations, (list, tuple)) else [notations]
        self.articulations = list(articulations) if isinstance(articulations, (list, tuple)) else [articulations]
        self.tuplet_bracket = None
        assert isinstance(notehead, (Notehead, str, type(None)))
        self.notehead = Notehead(notehead) if isinstance(notehead, str) else notehead
        self.beams = {} if beams is None else beams
        self.directions = list(directions) if isinstance(directions, (list, tuple)) else [directions]
        self.stemless = stemless
        self.is_grace = grace is not False
        self.slashed = grace == "slashed"
        self.is_chord_member = is_chord_member
        self.voice = voice
        self.staff = staff

    @property
    def true_length(self):
        if self.is_grace:
            return 0
        return self.duration.true_length if isinstance(self.duration, Duration) else self.duration

    @property
    def written_length(self):
        return self.duration.written_length if isinstance(self.duration, Duration) else self.duration

    @property
    def length_in_divisions(self):
        if self.is_grace:
            return 0
        return self.duration.length_in_divisions

    @property
    def divisions(self):
        return self.duration.divisions

    @divisions.setter
    def divisions(self, value):
        self.duration.divisions = value

    def min_denominator(self):
        if self.is_grace:
            return 1
        return Fraction(self.duration.true_length).limit_denominator().denominator

    def num_beams(self):
        return 0 if self.pitch is None else self.duration.num_beams()

    def render(self):
        note_element = ElementTree.Element("note")

        # ------------ set pitch and duration attributes ------------

        if self.pitch == "bar rest":
            # bar rest; in this case the duration is just a float, since it looks like a whole note regardless
            note_element.append(ElementTree.Element("rest"))
            note_element.extend(self.duration.render())
        else:
            if self.is_grace:
                ElementTree.SubElement(note_element, "grace", {"slash": "yes"} if self.slashed else {})

            # a note or rest with explicit written duration
            if self.pitch is None:
                # normal rest
                note_element.append(ElementTree.Element("rest"))
            else:
                # pitched note
                assert isinstance(self.pitch, Pitch)

                if self.is_chord_member:
                    note_element.append(ElementTree.Element("chord"))
                note_element.extend(self.pitch.render())

            duration_elements = self.duration.render()

            if not self.is_grace:
                # this is the actual duration tag; gracenotes don't have them
                note_element.append(duration_elements[0])

            # for some reason, the tie element and the voice are generally sandwiched in here

            if self.ties is not None:
                if self.ties.lower() == "start" or self.ties.lower() == "continue":
                    note_element.append(ElementTree.Element("tie", {"type": "start"}))
                if self.ties.lower() == "stop" or self.ties.lower() == "continue":
                    note_element.append(ElementTree.Element("tie", {"type": "stop"}))

            if self.voice is not None:
                ElementTree.SubElement(note_element, "voice").text = str(self.voice)

            # these are the note type and any dot tags
            note_element.extend(duration_elements[1:])

        # --------------- stem / notehead -------------

        if self.stemless:
            ElementTree.SubElement(note_element, "stem").text = "none"

        if self.notehead is not None:
            note_element.extend(self.notehead.render())

        # ------------------ set staff ----------------

        if self.staff is not None:
            ElementTree.SubElement(note_element, "staff").text = str(self.staff)

        # ---------------- set attributes that apply to notes only ----------------

        if self.pitch is not None:
            if self.ties is not None:
                if self.ties.lower() == "start" or self.ties.lower() == "continue":
                    self.notations.append(ElementTree.Element("tied", {"type": "start"}))
                if self.ties.lower() == "stop" or self.ties.lower() == "continue":
                    self.notations.append(ElementTree.Element("tied", {"type": "stop"}))
            for beam_num in self.beams:
                beam_text = self.beams[beam_num]
                beam_el = ElementTree.Element("beam", {"number": str(beam_num)})
                beam_el.text = beam_text
                note_element.append(beam_el)

        # ------------------ add any notations and articulations ----------------

        if len(self.notations) + len(self.articulations) > 0 or self.tuplet_bracket is not None:
            # there is either a notation or an articulation, so we'll add a notations tag
            notations_el = ElementTree.Element("notations")
            for notation in self.notations:
                if isinstance(notation, ElementTree.Element):
                    notations_el.append(notation)
                else:
                    notations_el.append(ElementTree.Element(notation))

            if self.tuplet_bracket in ("start", "both"):
                notations_el.append(ElementTree.Element("tuplet", {"type": "start"}))
            if self.tuplet_bracket in ("stop", "both"):
                notations_el.append(ElementTree.Element("tuplet", {"type": "stop"}))

            if len(self.articulations) > 0:
                articulations_el = ElementTree.SubElement(notations_el, "articulations")
                for articulation in self.articulations:
                    if isinstance(articulation, ElementTree.Element):
                        articulations_el.append(articulation)
                    else:
                        articulations_el.append(ElementTree.Element(articulation))
            note_element.append(notations_el)

        # place any text annotations before the note so that they show up at the same time as the note start
        return sum((direction.render() for direction in self.directions), ()) + (note_element,)

    def wrap_as_score(self):
        if isinstance(self, BarRest):
            duration_as_fraction = Fraction(self.true_length).limit_denominator()
            assert _is_power_of_two(duration_as_fraction.denominator)
            time_signature = (duration_as_fraction.numerator, duration_as_fraction.denominator * 4)
            return Measure([self], time_signature=time_signature).wrap_as_score()
        else:
            measure_length = 4 if self.true_length <= 4 else int(self.true_length) + 1
            return Measure(_pad_with_rests(self, measure_length), (measure_length, 4)).wrap_as_score()


class Note(_XMLNote):

    def __init__(self, pitch, duration, ties=None, notations=(), articulations=(), notehead=None, directions=(),
                 stemless=False):
        if isinstance(pitch, str):
            pitch = Pitch.from_string(pitch)
        assert isinstance(pitch, Pitch)

        if isinstance(duration, str):
            duration = Duration.from_string(duration)
        elif isinstance(duration, Number):
            duration = Duration.from_written_length(duration)

        assert ties in ("start", "continue", "stop", None)

        assert isinstance(duration, Duration)
        super().__init__(pitch, duration, ties=ties, notations=notations, articulations=articulations,
                         notehead=notehead, directions=directions, stemless=stemless)

    @property
    def starts_tie(self):
        return self.ties in ("start", "continue")

    @starts_tie.setter
    def starts_tie(self, value):
        if value:
            # setting it to start a tie if it isn't already
            self.ties = "start" if self.ties in ("start", None) else "continue"
        else:
            # setting it to not start a tie
            self.ties = None if self.ties in ("start", None) else "stop"

    @property
    def stops_tie(self):
        return self.ties in ("stop", "continue")

    @stops_tie.setter
    def stops_tie(self, value):
        if value:
            # setting it to stop a tie if it isn't already
            self.ties = "stop" if self.ties in ("stop", None) else "continue"
        else:
            # setting it to not stop a tie
            self.ties = None if self.ties in ("stop", None) else "start"

    def __repr__(self):
        return "Note({}, {}{}{}{}{})".format(
            self.pitch, self.duration,
            ", ties=\"{}\"".format(self.ties) if self.ties is not None else "",
            ", notations={}".format(self.notations) if len(self.notations) > 0 else "",
            ", articulations={}".format(self.articulations) if len(self.articulations) > 0 else "",
            ", notehead=\"{}\"".format(self.notehead) if self.notehead is not None else "",
            ", directions=\"{}\"".format(self.directions) if self.directions is not None else "",
            ", stemless=\"{}\"".format(self.stemless) if self.stemless is not None else ""
        )


class Rest(_XMLNote):

    def __init__(self, duration, notations=(), directions=()):
        if isinstance(duration, str):
            duration = Duration.from_string(duration)
        elif isinstance(duration, Number):
            duration = Duration.from_written_length(duration)

        assert isinstance(duration, Duration)
        super().__init__(None, duration, notations=notations, directions=directions)

    def __repr__(self):
        return "Rest({}{})".format(
            self.duration,
            ", notations={}".format(self.notations) if len(self.notations) > 0 else "",
            ", directions=\"{}\"".format(self.directions) if self.directions is not None else "",
        )


class BarRest(_XMLNote):

    def __init__(self, bar_length, directions=()):
        assert isinstance(bar_length, (Number, Duration, BarRestDuration))
        duration = BarRestDuration(bar_length) if isinstance(bar_length, Number) \
            else BarRestDuration(bar_length.true_length) if isinstance(bar_length, Duration) else bar_length
        super().__init__("bar rest", duration, directions=directions)

    def __repr__(self):
        return "BarRest({}{})".format(
            self.duration,
            ", directions=\"{}\"".format(self.directions) if self.directions is not None else "",
        )


# -------------------------------------- Chord (wrapper around multiple Notes) ---------------------------------------


class Chord(MusicXMLComponent):

    def __init__(self, pitches, duration, ties=None, notations=(), articulations=(), noteheads=None, directions=(),
                 stemless=False):
        assert isinstance(pitches, (list, tuple)) and len(pitches) > 1, "Chord should have multiple notes."
        pitches = [Pitch.from_string(pitch) if isinstance(pitch, str) else pitch for pitch in pitches]
        assert all(isinstance(pitch, Pitch) for pitch in pitches)

        if isinstance(duration, str):
            duration = Duration.from_string(duration)
        elif isinstance(duration, Number):
            duration = Duration.from_written_length(duration)
        assert isinstance(duration, Duration)

        assert ties in ("start", "continue", "stop", None) or \
               isinstance(ties, (list, tuple)) and len(ties) == len(pitches) and \
               all(x in ("start", "continue", "stop", None) for x in ties)

        note_notations = [[] for _ in range(len(pitches))]
        for notation in (notations if isinstance(notations, (list, tuple)) else (notations, )):
            if isinstance(notation, (StartMultiGliss, StopMultiGliss)):
                for i, gliss_notation in enumerate(notation.render()):
                    if i < len(note_notations) and gliss_notation is not None:
                        note_notations[i].append(gliss_notation)
            else:
                note_notations[0].append(notation)

        self.notes = tuple(
            Note(pitch, duration,
                 ties=ties if not isinstance(ties, (list, tuple)) else ties[i],
                 notations=note_notations[i],
                 articulations=articulations if i == 0 else (),
                 notehead=noteheads if isinstance(noteheads, str) else noteheads[i] if noteheads is not None else None,
                 directions=directions if i == 0 else (),
                 stemless=stemless)
            for i, pitch in enumerate(pitches)
        )

        for note in self.notes[1:]:
            note.is_chord_member = True

    @property
    def pitches(self):
        return tuple(note.pitch for note in self.notes)

    @pitches.setter
    def pitches(self, value):
        assert isinstance(value, tuple) and len(value) == len(self.notes) \
               and all(isinstance(x, Pitch) for x in value)
        for note, pitch in zip(self.notes, value):
            note.pitch = pitch

    def num_beams(self):
        return self.notes[0].num_beams()

    @property
    def duration(self):
        return self.notes[0].duration

    @property
    def true_length(self):
        return self.notes[0].true_length

    @property
    def written_length(self):
        return self.notes[0].written_length

    @property
    def length_in_divisions(self):
        return self.notes[0].length_in_divisions

    @property
    def notations(self):
        return self.notes[0].notations

    @property
    def articulations(self):
        return self.notes[0].articulations

    @property
    def directions(self):
        return self.notes[0].directions

    @property
    def divisions(self):
        return self.notes[0].divisions

    @divisions.setter
    def divisions(self, value):
        for note in self.notes:
            note.divisions = value

    @property
    def voice(self):
        return self.notes[0].voice

    @voice.setter
    def voice(self, value):
        for note in self.notes:
            note.voice = value

    @property
    def beams(self):
        # beams are only written into the first note of a chord so we make an alias to that
        return self.notes[0].beams

    @beams.setter
    def beams(self, value):
        self.notes[0].beams = value

    @property
    def ties(self):
        # either returns a string representing the tie state of all the notes, if all notes have the same tie state
        # or returns a tuple representing the tie state of each note individually
        if all(note.ties == self.notes[0].ties for note in self.notes[1:]):
            return self.notes[0].ties
        else:
            return tuple(note.ties for note in self.notes)

    @ties.setter
    def ties(self, value):
        if isinstance(value, (list, tuple)):
            assert len(value) == len(self.notes)
            for i, note in enumerate(self.notes):
                note.ties = value[i]
        else:
            assert value in ("start", "continue", "stop", None)
            for note in self.notes:
                note.ties = value

    @property
    def tuplet_bracket(self):
        return self.notes[0].tuplet_bracket

    @tuplet_bracket.setter
    def tuplet_bracket(self, value):
        self.notes[0].tuplet_bracket = value

    def min_denominator(self):
        return self.notes[0].min_denominator()

    def render(self):
        return sum((note.render() for note in self.notes), ())

    def wrap_as_score(self):
        measure_length = 4 if self.true_length <= 4 else int(self.true_length) + 1
        return Measure(_pad_with_rests(self, measure_length), (measure_length, 4)).wrap_as_score()

    def __repr__(self):
        noteheads = None if all(n.notehead is None for n in self.notes) else tuple(n.notehead for n in self.notes)
        return "Chord({}, {}{}{}{}{})".format(
            tuple(note.pitch for note in self.notes), self.duration,
            ", ties=\"{}\"".format(self.ties) if self.ties is not None else "",
            ", notations={}".format(self.notations) if len(self.notations) > 0 else "",
            ", articulations={}".format(self.articulations) if len(self.articulations) > 0 else "",
            ", noteheads={}".format(noteheads) if noteheads is not None else "",
            ", directions=\"{}\"".format(self.directions) if self.directions is not None else "",
            ", stemless=True" if self.notes[0].stemless else ""
        )


# -------------------------------------------- Grace Notes and Chords ---------------------------------------------


class GraceNote(Note):

    def __init__(self, pitch, duration, ties=None, notations=(), articulations=(), notehead=None, directions=(),
                 stemless=False, slashed=False):
        super().__init__(pitch,  duration, ties=ties, notations=notations, articulations=articulations,
                         notehead=notehead, directions=directions, stemless=stemless)
        self.is_grace = True
        self.slashed = slashed

    def __repr__(self):
        return "Grace" + super().__repr__()


class GraceChord(Chord):

    def __init__(self, pitches, duration, ties=None, notations=(), articulations=(), noteheads=None, directions=(),
                 stemless=False, slashed=False):
        super().__init__(pitches, duration, ties=ties, notations=notations, articulations=articulations,
                         noteheads=noteheads, directions=directions, stemless=stemless)
        for note in self.notes:
            note.is_grace = True
            note.slashed = slashed

    def __repr__(self):
        return "Grace" + super().__repr__()


# -------------------------------------------------- Note Groups ------------------------------------------------


class BeamedGroup(MusicXMLComponent, MusicXMLContainer):

    def __init__(self, contents=None):
        super().__init__(contents=contents, allowed_types=(Note, Chord, Rest))

    def render_contents_beaming(self):
        for beam_depth in range(1, max(leaf.num_beams() for leaf in self.contents) + 1):
            leaf_start_time = 0
            for i, leaf in enumerate(self.contents):
                last_note_active = i > 0 and self.contents[i-1].num_beams() >= beam_depth
                this_note_active = leaf.num_beams() >= beam_depth
                next_note_active = i < len(self.contents) - 1 and self.contents[i+1].num_beams() >= beam_depth

                if this_note_active:
                    if last_note_active and next_note_active:
                        leaf.beams[beam_depth] = "continue"
                    elif last_note_active:
                        leaf.beams[beam_depth] = "end"
                    elif next_note_active:
                        leaf.beams[beam_depth] = "begin"
                    else:
                        if int(round(leaf_start_time / 0.5 ** leaf.num_beams())) % 2 == 0:
                            leaf.beams[beam_depth] = "forward hook"
                        else:
                            leaf.beams[beam_depth] = "backward hook"

                leaf_start_time += leaf.written_length

        for leaf in self.contents:
            if all("hook" in beam_value for beam_value in leaf.beams.values()):
                leaf.beams = {}

    @property
    def divisions(self):
        return self.contents[0].divisions

    @divisions.setter
    def divisions(self, value):
        for leaf in self.contents:
            leaf.divisions = value

    @property
    def true_length(self):
        return sum(leaf.true_length for leaf in self.contents)

    @property
    def written_length(self):
        return sum(leaf.written_length for leaf in self.contents)

    @property
    def length_in_divisions(self):
        return sum(leaf.length_in_divisions for leaf in self.contents)

    def min_denominator(self):
        return _least_common_multiple(*[n.min_denominator() for n in self.contents])

    def render(self):
        self.render_contents_beaming()
        return sum((leaf.render() for leaf in self.contents), ())

    def wrap_as_score(self):
        measure_length = 4 if self.true_length <= 4 else int(math.ceil(self.true_length))
        return Measure(_pad_with_rests(self, measure_length), (measure_length, 4)).wrap_as_score()


class Tuplet(BeamedGroup):

    def __init__(self, contents, ratio):
        super().__init__(contents)
        self.ratio = ratio
        self.set_tuplet_info_for_contents(ratio)

    def set_tuplet_info_for_contents(self, ratio):
        self.contents[0].tuplet_bracket = "start"
        # it would be stupid to have a tuplet that has only one note in it, but we'll cover that case anyway
        self.contents[-1].tuplet_bracket = "stop" if len(self.contents) > 0 else "both"

        for element in self.contents:
            if isinstance(element, Chord):
                for note in element.notes:
                    note.duration.tuplet_ratio = ratio
            else:
                element.duration.tuplet_ratio = ratio

    def min_denominator(self):
        self.set_tuplet_info_for_contents(self.ratio)
        return _least_common_multiple(*[n.min_denominator() for n in self.contents])

    def render(self):
        self.set_tuplet_info_for_contents(self.ratio)
        return super().render()


# ----------------------------------------------- Clef and Measure -------------------------------------------------


class Clef(MusicXMLComponent):

    clef_name_to_letter_and_line = {
        "treble": ("G", 2),
        "bass": ("F", 4),
        "alto": ("C", 3),
        "tenor": ("C", 4),
        "soprano": ("C", 1),
        "mezzo-soprano": ("C", 2),
        "baritone": ("F", 3)
    }

    def __init__(self, sign, line, octaves_transposition=0):
        self.sign = sign
        self.line = str(line)
        self.octaves_transposition = octaves_transposition

    @classmethod
    def from_string(cls, clef_string):
        if clef_string in Clef.clef_name_to_letter_and_line:
            return cls(*Clef.clef_name_to_letter_and_line[clef_string])
        else:
            raise ValueError("Clef name not understood.")

    def render(self):
        clef_element = ElementTree.Element("clef")
        ElementTree.SubElement(clef_element, "sign").text = self.sign
        ElementTree.SubElement(clef_element, "line").text = self.line
        if self.octaves_transposition != 0:
            ElementTree.SubElement(clef_element, "clef-octave-change").text = str(self.octaves_transposition)
        return clef_element,

    def wrap_as_score(self):
        return Measure([BarRest(4)], time_signature=(4, 4), clef=self).wrap_as_score()


class Measure(MusicXMLComponent, MusicXMLContainer):

    barline_xml_names = {
        # the first two are useful aliases; the rest just retain their xml names
        "double": "light-light",
        "end": "light-heavy",
        "regular": "regular",
        "dotted": "dotted",
        "dashed": "dashed",
        "heavy": "heavy",
        "light-light": "light-light",
        "light-heavy": "light-heavy",
        "heavy-light": "heavy-light",
        "heavy-heavy": "heavy-heavy",
        "tick": "tick",
        "short": "short",
        "none": "none"
    }

    def __init__(self, contents=None, time_signature=None, clef=None, barline=None, staves=None, number=1,
                 directions_with_displacements=()):
        """

        :param contents: Either a list of Notes / Chords / Rests / Tuplets / BeamedGroups or a list of voices, each of
        which is a list of Notes / Chords / Rests / Tuplets / BeamedGroups.
        :param time_signature: in tuple form, e.g. (3, 4) for "3/4"
        :param clef: either None (for no clef), a Clef object, a string (like "treble"), or a tuple like ("G", 2) to
        represent the clef letter, the line it lands, and an optional octave transposition as the third parameter
        :param barline: either None, which means there will be a regular barline, or one of the names defined in the
        barline_xml_names dictionary.
        :param staves: for multi-part music, like piano music
        :param number: which number in the score. Will be set by the containing Part
        """
        super().__init__(contents=contents, allowed_types=(Note, Rest, Chord, BarRest, BeamedGroup,
                                                           Tuplet, type(None), Sequence))
        assert hasattr(self.contents, '__len__') and all(
            isinstance(x, (Note, Rest, Chord, BarRest, BeamedGroup, Tuplet, type(None))) or
            hasattr(x, '__len__') and all(isinstance(y, (Note, Rest, Chord, BarRest, BeamedGroup, Tuplet)) for y in x)
            for x in self.contents
        )

        self.number = number
        self.time_signature = time_signature
        assert isinstance(clef, (type(None), Clef, str, tuple)), "Clef not understood."
        self.clef = clef if isinstance(clef, (type(None), Clef)) \
            else Clef.from_string(clef) if isinstance(clef, str) \
            else Clef(*clef)
        assert barline is None or isinstance(barline, str) \
               and barline.lower() in Measure.barline_xml_names, "Barline type not understood"
        self.barline = barline
        self.staves = staves

        assert isinstance(directions_with_displacements, (tuple, list)) and \
               all(isinstance(x, (tuple, list)) and len(x) == 2 and
                   isinstance(x[0], (MetronomeMark, TextAnnotation, EndDashedLine)) and
                   isinstance(x[1], Number) for x in directions_with_displacements)
        self.directions_with_displacements = directions_with_displacements

    @property
    def voices(self):
        # convenience method for putting the voices in a list, since contents is sometimes just a single voice list
        return (self.contents, ) if not isinstance(self.contents[0], (tuple, list, type(None))) else self.contents

    def leaves(self):
        out = []
        for voice in self.voices:
            if voice is None:  # skip empty voices
                continue
            for note_or_group in voice:
                if isinstance(note_or_group, (BeamedGroup, Tuplet)):
                    out.extend(note_or_group.contents)
                else:
                    out.append(note_or_group)
        return tuple(out)

    def set_leaf_voices(self):
        for i, voice in enumerate(self.voices):
            if voice is None:  # skip empty voices
                continue
            for element in voice:
                if isinstance(element, (BeamedGroup, Tuplet)):
                    # element is a container
                    for leaf in element.contents:
                        leaf.voice = i + 1
                else:
                    # element is a leaf
                    element.voice = i + 1
                    for direction in element.directions:
                        direction.voice = i + 1

    def _get_beat_division_for_directions(self):
        # determine what beat division is ideal for the independently placed directions
        if len(self.directions_with_displacements) == 0:
            return None
        return _least_common_multiple(*[Fraction(displacement).limit_denominator(256).denominator
                                        for _, displacement in self.directions_with_displacements])

    def render(self):
        self.set_leaf_voices()

        measure_element = ElementTree.Element("measure", {"number": str(self.number)})

        attributes_el = ElementTree.SubElement(measure_element, "attributes")

        num_beat_divisions = _least_common_multiple(*[x.min_denominator() for x in self.leaves()])

        if len(self.directions_with_displacements) > 0:
            # if we're using independently placed directions, then we try to find a denominator that accommodates
            # that as precisely as possible this means
            ideal_division = _least_common_multiple(self._get_beat_division_for_directions(), num_beat_divisions)
            if ideal_division <= 1024:
                num_beat_divisions = ideal_division
            else:
                # Just in case the ideal division is totally outrageous, we just multiply the division
                # by two repeatedly until we are about to go over 1024
                num_beat_divisions *= max(1, 2 ** int(math.log2(1024 / num_beat_divisions)))

        for note in self.leaves():
            note.divisions = num_beat_divisions

        divisions_el = ElementTree.SubElement(attributes_el, "divisions")
        divisions_el.text = str(num_beat_divisions)

        if self.time_signature is not None:
            # time_signature is expressed as a tuple
            assert isinstance(self.time_signature, tuple) and len(self.time_signature) == 2
            time_el = ElementTree.SubElement(attributes_el, "time")
            ElementTree.SubElement(time_el, "beats").text = str(self.time_signature[0])
            ElementTree.SubElement(time_el, "beat-type").text = str(self.time_signature[1])

        if self.clef is not None:
            attributes_el.extend(self.clef.render())

        if self.staves is not None:
            staves_el = ElementTree.SubElement(attributes_el, "staves")
            staves_el.text = str(self.staves)

        amount_to_backup = 0
        for i, voice in enumerate(self.voices):
            if voice is None:  # skip empty voices
                continue

            if i > 0:
                # for voices after 1, we need to add a backup element to go back to the start of the measure
                backup_el = ElementTree.SubElement(measure_element, "backup")
                ElementTree.SubElement(backup_el, "duration").text = str(amount_to_backup)
            amount_to_backup = 0

            for note_or_tuplet in voice:
                amount_to_backup += note_or_tuplet.length_in_divisions
                measure_element.extend(note_or_tuplet.render())

        if len(self.directions_with_displacements) > 0:
            current_location_in_measure = amount_to_backup
            for direction, displacement in self.directions_with_displacements:
                displacement = int(round(displacement * num_beat_divisions))
                if displacement < current_location_in_measure:
                    backup_el = ElementTree.SubElement(measure_element, "backup")
                    ElementTree.SubElement(backup_el, "duration").text = str(current_location_in_measure - displacement)
                elif displacement > current_location_in_measure:
                    forward_el = ElementTree.SubElement(measure_element, "forward")
                    ElementTree.SubElement(forward_el, "duration").text = str(displacement - current_location_in_measure)
                current_location_in_measure = displacement
                measure_element.extend(direction.render())

        if self.barline is not None:
            barline_el = ElementTree.SubElement(measure_element, "barline", {"location": "right"})
            ElementTree.SubElement(barline_el, "bar-style").text = Measure.barline_xml_names[self.barline.lower()]

        return measure_element,

    def wrap_as_score(self):
        return Part("", [self]).wrap_as_score()


# -------------------------------------------- Part, PartGroup, and Score ------------------------------------------


class Part(MusicXMLComponent, MusicXMLContainer):

    def __init__(self, part_name, measures=None, part_id=1):
        self.part_id = part_id
        super().__init__(contents=measures, allowed_types=(Measure,))
        self.part_name = part_name

    @property
    def measures(self):
        return self.contents

    def render(self):
        part_element = ElementTree.Element("part", {"id": "P{}".format(self.part_id)})
        for i, measure in enumerate(self.measures):
            measure.number = i + 1
            part_element.extend(measure.render())
        return part_element,

    def render_part_list_entry(self):
        score_part_el = ElementTree.Element("score-part", {"id": "P{}".format(self.part_id)})
        ElementTree.SubElement(score_part_el, "part-name").text = self.part_name
        return score_part_el,

    def wrap_as_score(self):
        return Score([self])


class PartGroup(MusicXMLComponent, MusicXMLContainer):

    def __init__(self, parts=None, has_bracket=True, has_group_bar_line=True):
        super().__init__(contents=parts, allowed_types=(Part,))
        self.has_bracket = has_bracket
        self.has_group_bar_line = has_group_bar_line

    @property
    def parts(self):
        return self.contents

    def render(self):
        return sum((part.render() for part in self.parts), ())

    def render_part_list_entry(self):
        out = [self.render_start_element()]
        for part in self.parts:
            out.extend(part.render_part_list_entry())
        out.append(self.render_stop_element())
        return tuple(out)

    def render_start_element(self):
        start_element = ElementTree.Element("part-group", {"type": "start"})
        if self.has_bracket:
            ElementTree.SubElement(start_element, "group-symbol").text = "bracket"
        ElementTree.SubElement(start_element, "group-barline").text = "yes" if self.has_group_bar_line else "no"
        return start_element

    @staticmethod
    def render_stop_element():
        return ElementTree.Element("part-group", {"type": "stop"})

    def wrap_as_score(self):
        return Score([self])


class Score(MusicXMLComponent, MusicXMLContainer):

    def __init__(self, contents=None, title=None, composer=None):
        super().__init__(contents=contents, allowed_types=(Part, PartGroup))
        self.title = title
        self.composer = composer

    @property
    def parts(self):
        return tuple(part for part_or_group in self.contents
                     for part in (part_or_group.parts if isinstance(part_or_group, PartGroup) else (part_or_group, )))

    def set_part_numbers(self):
        next_id = 1
        for part in self.parts:
            part.part_id = next_id
            next_id += 1

    def render(self):
        self.set_part_numbers()
        score_element = ElementTree.Element("score-partwise")
        work_el = ElementTree.SubElement(score_element, "work")
        if self.title is not None:
            ElementTree.SubElement(work_el, "work-title").text = self.title
        id_el = ElementTree.SubElement(score_element, "identification")
        if self.composer is not None:
            ElementTree.SubElement(id_el, "creator", {"type": "composer"}).text = self.composer
        encoding_el = ElementTree.SubElement(id_el, "encoding")
        ElementTree.SubElement(encoding_el, "encoding-date").text = str(datetime.date.today())
        ElementTree.SubElement(encoding_el, "software").text = "pymusicxml"
        part_list_el = ElementTree.SubElement(score_element, "part-list")
        for part_or_part_group in self.contents:
            part_list_el.extend(part_or_part_group.render_part_list_entry())
            score_element.extend(part_or_part_group.render())
        return score_element,

    def wrap_as_score(self):
        return self

# -------------------------------- Remaining Details: Noteheads, Notations, Directions --------------------------------


class Notehead(MusicXMLComponent):

    valid_xml_types = ["normal", "diamond", "triangle", "slash", "cross", "x", "circle-x", "inverted triangle",
                       "square", "arrow down", "arrow up", "circled", "slashed", "back slashed", "cluster",
                       "circle dot", "left triangle", "rectangle", "do", "re", "mi", "fa", "fa up", "so",
                       "la", "ti",  "none"]

    def __init__(self, notehead_name: str, filled=None):
        notehead_name = notehead_name.strip().lower()
        if "filled " in notehead_name:
            filled = "yes"
            notehead_name = notehead_name.replace("filled ", "")
        elif "open " in notehead_name:
            filled = "no"
            notehead_name = notehead_name.replace("open ", "")
        assert notehead_name in Notehead.valid_xml_types, "Notehead \"{}\" not understood".format(notehead_name)
        self.notehead_name = notehead_name
        assert filled in (None, "yes", "no", True, False)
        self.filled = "yes" if filled in ("yes", True) else "no" if filled in ("no", False) else None

    def render(self):
        notehead_el = ElementTree.Element("notehead", {"filled": self.filled} if self.filled is not None else {})
        notehead_el.text = self.notehead_name
        return notehead_el,

    def wrap_as_score(self):
        return Note("c5", 1, notehead=self).wrap_as_score()

    def __repr__(self):
        return "Notehead({}{})".format(self.notehead_name,
                                       ", {}".format(self.filled) if self.filled is not None else "")


class Notation(MusicXMLComponent):

    @abstractmethod
    def render(self):
        pass

    def wrap_as_score(self):
        return Note("c5", 1, notations=(self, )).wrap_as_score()


class StartGliss(Notation, ElementTree.Element):

    def __init__(self, number=1):
        super().__init__("slide", {"type": "start", "line-type": "solid", "number": str(number)})

    def render(self):
        return self,


class StopGliss(Notation, ElementTree.Element):

    def __init__(self, number=1):
        super().__init__("slide", {"type": "stop", "line-type": "solid", "number": str(number)})

    def render(self):
        return self,


class StartMultiGliss(Notation):

    def __init__(self, numbers=(1,)):
        """
        Multi-gliss notation used for glissing multiple members of a chord
        :param numbers: most natural is to pass a range object here, for the range of numbers to assign to the glisses
        of consecutive chord member. However, in the case of a chord where, say, you want the upper two notes to
        gliss but not the bottom, pass (None, 1, 2) to this parameter.
        """
        self.numbers = numbers

    def render(self):
        return tuple(StartGliss(n) if n is not None else None for n in self.numbers)


class StopMultiGliss(Notation):

    def __init__(self, numbers=(1,)):
        self.numbers = numbers

    def render(self):
        return tuple(StopGliss(n) if n is not None else None for n in self.numbers)


class StartSlur(Notation, ElementTree.Element):

    def __init__(self, number=1):
        super().__init__("slur", {"type": "start", "number": str(number)})

    def render(self):
        return self,


class ContinueSlur(Notation, ElementTree.Element):

    def __init__(self, number=1):
        super().__init__("slur", {"type": "continue", "number": str(number)})

    def render(self):
        return self,


class StopSlur(Notation, ElementTree.Element):

    def __init__(self, number=1):
        super().__init__("slur", {"type": "stop", "number": str(number)})

    def render(self):
        return self,


class Direction(MusicXMLComponent):

    @abstractmethod
    def render(self):
        pass

    def wrap_as_score(self):
        return Measure([BarRest(4, directions=(self, ))], time_signature=(4, 4)).wrap_as_score()


class MetronomeMark(Direction):

    def __init__(self, beat_length, bpm, voice=1, staff=1, **other_attributes):
        try:
            self.beat_unit = Duration.from_written_length(beat_length)
        except ValueError:
            # fall back to quarter note tempo if the beat length is not expressible as a single notehead
            self.beat_unit = Duration.from_written_length(1.0)
            bpm /= beat_length
        self.bpm = bpm
        self.other_attributes = {key.replace("_", "-"): value for key, value in other_attributes.items()}
        self.voice = voice
        self.staff = staff

    def render(self):
        direction_element = ElementTree.Element("direction")
        type_el = ElementTree.SubElement(direction_element, "direction-type")
        metronome_el = ElementTree.SubElement(type_el, "metronome", self.other_attributes)
        metronome_el.extend(self.beat_unit.render_to_beat_unit_tags())
        ElementTree.SubElement(metronome_el, "per-minute").text = str(self.bpm)
        ElementTree.SubElement(direction_element, "voice").text = str(self.voice)
        if self.staff is not None:
            ElementTree.SubElement(direction_element, "staff").text = str(self.staff)
        return direction_element,


class TextAnnotation(Direction):

    def __init__(self, text, placement="above", font_size=None, italic=False, voice=1, staff=None,
                 dashed_line=None, **kwargs):
        # any extra properties of the musicXML "words" tag aside from font-size and italics can be passed to kwargs
        self.text = text
        self.placement = placement
        self.text_properties = kwargs
        if font_size is not None:
            self.text_properties["font-size"] = font_size
        if italic:
            self.text_properties["font-style"] = "italic"
        # by default, pass an integer to dashed_line to give it an id number. But if it's just True, set id to 1
        self.dashed_line = 1 if dashed_line is True else dashed_line
        self.voice = voice
        self.staff = staff

    def render(self):
        direction_element = ElementTree.Element("direction", {"placement": self.placement})
        type_el = ElementTree.SubElement(direction_element, "direction-type")
        ElementTree.SubElement(type_el, "words", self.text_properties).text = self.text
        if self.dashed_line is not None:
            dash_type_el = ElementTree.SubElement(direction_element, "direction-type")
            ElementTree.SubElement(dash_type_el, "dashes", {"number": str(self.dashed_line), "type": "start"})
        ElementTree.SubElement(direction_element, "voice").text = str(self.voice)
        if self.staff is not None:
            ElementTree.SubElement(direction_element, "staff").text = str(self.staff)
        return direction_element,


class EndDashedLine(Direction):

    def __init__(self, id_number=1, voice=1, staff=None):
        self.id_number = id_number
        self.voice = voice
        self.staff = staff

    def render(self):
        direction_element = ElementTree.Element("direction")
        dash_type_el = ElementTree.SubElement(direction_element, "direction-type")
        ElementTree.SubElement(dash_type_el, "dashes", {"number": str(self.id_number), "type": "stop"})
        ElementTree.SubElement(direction_element, "voice").text = str(self.voice)
        if self.staff is not None:
            ElementTree.SubElement(direction_element, "staff").text = str(self.staff)
        return direction_element,
