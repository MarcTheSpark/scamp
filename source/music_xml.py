from xml.etree import ElementTree
from abc import ABC, abstractmethod
from fractions import Fraction
import math

MAX_DOTS_ALLOWED = 3
DEFAULT_BEAT_DIVISIONS = 10080


def least_common_multiple(*args):
    # utility for getting the least_common_multiple of a list of numbers
    if len(args) == 0:
        return 1
    elif len(args) == 1:
        return args[0]
    elif len(args) == 2:
        return args[0] * args[1] // math.gcd(args[0], args[1])
    else:
        return least_common_multiple(args[0], least_common_multiple(*args[1:]))


class MusicXMLComponent(ABC):

    @abstractmethod
    def render(self):
        # Renders this component to an ElementTree.Element or a list of ElementTree.Elements
        pass

    def to_xml(self, pretty_print=False):
        element_rendering = self.render()

        if not isinstance(element_rendering, tuple):
            element_rendering = [element_rendering]
        if pretty_print:
            # this is not ideal; it's ugly and requires parsing and re-rendering and then removing version tags
            # for now, though, it's good enough and gets the desired results
            from xml.dom import minidom
            import re
            return ''.join(
                re.sub(
                    "<\?xml version.*\?>\n",
                    "",
                    minidom.parseString(ElementTree.tostring(element, 'utf-8')).toprettyxml(indent="\t")
                )
                for element in element_rendering
            )
        else:
            return b''.join(ElementTree.tostring(element, 'utf-8') for element in element_rendering)


class Pitch(MusicXMLComponent):

    def __init__(self, step, octave, alteration=0):
        self.step = step
        self.octave = octave
        self.alteration = alteration

    def render(self):
        element = ElementTree.Element("pitch")
        step_el = ElementTree.Element("step")
        step_el.text = self.step
        alter_el = ElementTree.Element("alter")
        alter_el.text = str(self.alteration)
        octave_el = ElementTree.Element("octave")
        octave_el.text = str(self.octave)
        element.append(step_el)
        element.append(alter_el)
        element.append(octave_el)
        return element


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
        1.0 / 32: "128th"
    }

    def __init__(self, written_length, tuplet_ratio=None):
        """
        Represents a length that can be written as a single note or rest.
        :param written_length: the written length of the note, not considering tuplet modification
        :param tuplet_ratio: a tuple of either (# actual notes, # normal notes) or (# actual, # normal, note type),
        e.g. (4, 3, 0.5) for 4 in the space of 3 eighths.
        """
        self.divisions = DEFAULT_BEAT_DIVISIONS
        self.actual_length = float(written_length)
        if tuplet_ratio is not None:
            self.actual_length *= float(tuplet_ratio[1]) / tuplet_ratio[0]

        try:
            self.type, self.num_dots = Duration.get_note_type_and_number_of_dots(written_length)
        except ValueError as err:
            raise err

        self.tuplet_ratio = tuplet_ratio

    @staticmethod
    def get_note_type_and_number_of_dots(length):
        if length in Duration.length_to_note_type:
            return Duration.length_to_note_type[length], 0
        else:
            dots_multiplier = 1.5
            dots = 1
            while length / dots_multiplier not in Duration.length_to_note_type:
                dots += 1
                dots_multiplier = (2.0 ** (dots + 1) - 1) / 2.0 ** dots
                if dots > MAX_DOTS_ALLOWED:
                    raise ValueError("Duration length of {} does not resolve to single note type.".format(length))
            return Duration.length_to_note_type[length / dots_multiplier], dots

    def render(self):
        elements = []
        # specify all the duration-related attributes
        duration_el = ElementTree.Element("duration")
        duration_el.text = str(int(round(self.actual_length * self.divisions)))
        elements.append(duration_el)

        type_el = ElementTree.Element("type")
        type_el.text = self.type
        elements.append(type_el)

        for _ in range(self.num_dots):
            elements.append(ElementTree.Element("dot"))

        if self.tuplet_ratio is not None:
            time_modification = ElementTree.Element("time-modification")
            ElementTree.SubElement(time_modification, "actual-notes").text = str(self.tuplet_ratio[0])
            ElementTree.SubElement(time_modification, "normal-notes").text = str(self.tuplet_ratio[1])
            if len(self.tuplet_ratio) > 2:
                if self.tuplet_ratio[2] not in Duration.length_to_note_type:
                    raise ValueError("Tuplet normal note type is not a standard power of two length.")
                ElementTree.SubElement(time_modification, "normal-type").text = \
                    Duration.length_to_note_type[self.tuplet_ratio[2]]
            elements.append(time_modification)
        return elements


class Note(MusicXMLComponent):

    def __init__(self, pitch, duration, ties=None, notations=(), articulations=(), notehead=None, beams=None,
                 is_chord_member=False, voice=None, staff=None):
        self.divisions = DEFAULT_BEAT_DIVISIONS
        self.pitch = pitch
        self.duration = duration
        self.ties = ties
        self.notations = list(notations) if not isinstance(notations, list) else notations
        self.articulations = list(articulations) if not isinstance(articulations, list) else articulations
        self.notehead = notehead
        self.beams = beams
        self.is_chord_member = is_chord_member
        self.voice = voice
        self.staff = staff

    def render(self):
        element = ElementTree.Element("note")

        # ------------ set pitch and duration attributes ------------

        if self.pitch == "bar rest":
            # bar rest; in this case the duration is just a float, since it looks like a whole note regardless
            element.append(ElementTree.Element("rest", {"measure": "yes"}))
            duration_el = ElementTree.Element("duration")
            duration_el.text = str(int(round(self.duration * self.divisions)))
            element.append(duration_el)
            type_el = ElementTree.Element("type")
            type_el.text = "whole"
            element.append(type_el)
        else:
            # a note or rest with explicit written duration
            if self.pitch is None:
                # normal rest
                element.append(ElementTree.Element("rest"))
            else:
                # pitched note
                assert isinstance(self.pitch, Pitch)

                if self.is_chord_member:
                    element.append(ElementTree.Element("chord"))
                element.append(self.pitch.render())

            assert isinstance(self.duration, Duration)
            self.duration.divisions = self.divisions
            element.extend(self.duration.render())

        # ------------------ set voice and staff ----------------

        if self.voice is not None:
            voice_el = ElementTree.Element("voice")
            voice_el.text = str(self.voice)
            element.append(voice_el)

        if self.staff is not None:
            staff_el = ElementTree.Element("staff")
            staff_el.text = str(self.staff)
            element.append(staff_el)

        # ---------------- set attributes that apply to notes only ----------------

        if self.pitch is not None:
            if self.notehead is not None:
                element.append(notehead)
            if self.ties is not None:
                if self.ties.lower() == "start" or self.ties.lower() == "continue":
                    element.append(ElementTree.Element("tie", {"type": "start"}))
                    self.notations.append(ElementTree.Element("tied", {"type": "start"}))
                if self.ties.lower() == "stop" or self.ties.lower() == "continue":
                    element.append(ElementTree.Element("tie", {"type": "stop"}))
                    self.notations.append(ElementTree.Element("tied", {"type": "stop"}))
            if self.beams is not None:
                for beam_num in self.beams:
                    beam_text = self.beams[beam_num]
                    beam_el = ElementTree.Element("beam", {"number": str(beam_num)})
                    beam_el.text = beam_text
                    element.append(beam_el)

        # ------------------ add any notations and articulations ----------------

        if len(self.notations) + len(self.articulations) > 0:
            # there is either a notation or an articulation, so we'll add a notations tag
            notations_el = ElementTree.Element("notations")
            for notation in self.notations:
                if isinstance(notation, ElementTree.Element):
                    notations_el.append(notation)
                else:
                    notations_el.append(ElementTree.Element(notation))
            if len(self.articulations) > 0:
                articulations_el = ElementTree.SubElement(notations_el, "articulations")
                for articulation in self.articulations:
                    if isinstance(articulation, ElementTree.Element):
                        articulations_el.append(articulation)
                    else:
                        articulations_el.append(ElementTree.Element(articulation))
            element.append(notations_el)

        return element

    def min_denominator(self):
        if isinstance(self.duration, Duration):
            return Fraction(self.duration.actual_length).limit_denominator().denominator
        else:
            return Fraction(self.duration).limit_denominator().denominator

    @classmethod
    def make_chord(cls, pitches, duration, ties=None, notations=(), articulations=(), beams=None,
                   noteheads=None, voice=None, staff=None):
        assert all(isinstance(x, Pitch) for x in pitches)
        return tuple(
            cls(pitch, duration, ties=ties, notations=notations, articulations=articulations,
                beams=None if i > 0 else beams, is_chord_member=(i > 0),
                notehead=noteheads[i] if noteheads is not None else None, voice=voice, staff=staff)
            for i, pitch in enumerate(pitches)
        )

    @classmethod
    def rest(cls, duration, voice=None, staff=None):
        return cls(None, duration, voice=voice, staff=staff)

    @classmethod
    def bar_rest(cls, duration, staff=None, voice=None):
        return cls("bar rest", duration, staff=staff, voice=voice)


class Tuplet(MusicXMLComponent):

    def __init__(self, notes, placement=None):
        assert hasattr(notes, '__len__') and all(isinstance(x, (Note, tuple)) for x in notes)
        assert placement in (None, "above", "below")
        # expand any chord tuples
        self.notes = [note for note_or_chord in notes
                      for note in (note_or_chord if isinstance(note_or_chord, tuple) else (note_or_chord, ))]
        self.placement = placement
        self.notes[0].notations.append(ElementTree.Element(
            "tuplet", {"type": "start", "placement": placement} if placement is not None else {"type": "start"})
        )
        self.notes[-1].notations.append(ElementTree.Element(
            "tuplet", {"type": "stop", "placement": placement} if placement is not None else {"type": "stop"})
        )

    def render(self):
        return tuple(note.render() for note in self.notes)

    def min_denominator(self):
        return least_common_multiple(*[n.min_denominator() for n in self.notes])

    def __repr__(self):
        return "Tuplet({})".format(self.notes, self.placement)


clef_name_to_letter_and_line = {
    "treble": ("G", 2),
    "bass": ("F", 4),
    "alto": ("C", 3),
    "tenor": ("C", 4)
}


class Measure(MusicXMLComponent):

    barline_name_to_xml_name = {
        "double": "light-light",
        "end": "light-heavy",
    }

    def __init__(self, number, contents, time_signature=None, clef=None, barline=None, staves=None):
        assert hasattr(contents, '__len__') and all(isinstance(x, (Note, Tuplet, tuple)) for x in contents)
        self.number = number
        # expand any chord tuples
        self.contents = [note for note_tuplet_or_chord in contents
                         for note in (note_tuplet_or_chord if isinstance(note_tuplet_or_chord, tuple)
                                      else (note_tuplet_or_chord, ))]
        self.time_signature = time_signature
        self.clef = clef
        self.barline = barline
        self.staves = staves

    def notes(self):
        out = []
        for note_or_tuplet in self.contents:
            if isinstance(note_or_tuplet, Tuplet):
                out.extend(note_or_tuplet.notes)
            else:
                out.append(note_or_tuplet)
        return out

    def render(self):
        element = ElementTree.Element("measure", {"number": str(self.number)})

        attributes_el = ElementTree.SubElement(element, "attributes")

        num_beat_divisions = least_common_multiple(*[x.min_denominator() for x in self.notes()])
        for note in self.notes():
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
            # clef is a tuple: the first element is the sign ("G" clef of "F" clef)
            # the second element is the line the sign centers on
            # an optional third element expresses the number of octaves transposition up or down
            # however, we also take words like "treble" and convert them
            if clef in clef_name_to_letter_and_line:
                self.clef = clef_name_to_letter_and_line[self.clef]
            clef_el = ElementTree.SubElement(attributes_el, "clef")
            ElementTree.SubElement(clef_el, "sign").text = self.clef[0]
            ElementTree.SubElement(clef_el, "line").text = str(self.clef[1])
            if len(clef) > 2:
                ElementTree.SubElement(clef_el, "clef-octave-change").text = str(clef[2])

        if self.staves is not None:
            staves_el = ElementTree.SubElement(attributes_el, "staves")
            staves_el.text = str(self.staves)

        for note_or_tuplet in self.contents:
            if isinstance(note_or_tuplet, Tuplet):
                element.extend(note_or_tuplet.render())
            else:
                element.append(note_or_tuplet.render())

        if self.barline is not None:
            barline_el = ElementTree.Element("barline", {"location": "right"})
            element.append(barline_el)
            if self.barline in Measure.barline_name_to_xml_name:
                self.barline = Measure.barline_name_to_xml_name[self.barline]
            ElementTree.SubElement(barline_el, "bar-style").text = self.barline
        return element

bob = Measure(1, [
    Note(Pitch("D", 4), Duration(1.5)),
    Note(Pitch("F", 4, 1), Duration(0.5)),
    Note.make_chord([Pitch("C", 4, 1), Pitch("A", 4, -1)], Duration(1.0)),
    Tuplet([
        Note(Pitch("G", 5), Duration(0.5, (3, 2))),
        Note(Pitch("A", 5), Duration(0.5, (3, 2))),
        Note(Pitch("B", 5, -1), Duration(0.5, (3, 2)))
    ])
], time_signature=(4, 4), barline="end")


print(bob.to_xml(True))
