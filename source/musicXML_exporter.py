from xml.etree import ElementTree
import math
from datetime import date
import numbers
import random
from playcorder.settings import engraving_settings


# TODO: Accidental key preference
# TODO: Key Signature
# TODO: Performances record score hints? E.g. key signature.
# TODO: Articulations, slurs
# TODO: Barlines

#  -------------------------------------------------- GLOBALS ----------------------------------------------------- #

num_beat_divisions = 10080

#  -------------------------------------------------- PITCH ----------------------------------------------------- #

pc_number_to_step_and_sharp_alteration = {0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("D", 1),
                                          4: ("E", 0), 5: ("F", 0), 6: ("F", 1), 7: ("G", 0),
                                          8: ("G", 1), 9: ("A", 0), 10: ("A", 1), 11: ("B", 0)}

pc_number_to_step_and_flat_alteration = {0: ("C", 0), 1: ("D", -1), 2: ("D", 0), 3: ("E", -1),
                                         4: ("E", 0), 5: ("F", 0), 6: ("G", -1), 7: ("G", 0),
                                         8: ("A", -1), 9: ("A", 0), 10: ("B", -1), 11: ("B", 0)}

pc_number_to_step_and_standard_alteration = {0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("E", -1),
                                             4: ("E", 0), 5: ("F", 0), 6: ("F", 1), 7: ("G", 0),
                                             8: ("A", -1), 9: ("A", 0), 10: ("B", -1), 11: ("B", 0)}


def get_pitch_step_alter_and_octave(pitch, accidental_preference="standard"):

    if accidental_preference == "sharp":
        rounded_pitch = math.floor(pitch)
        step, alteration = pc_number_to_step_and_sharp_alteration[rounded_pitch % 12]
    elif accidental_preference == "flat":
        rounded_pitch = math.ceil(pitch)
        step, alteration = pc_number_to_step_and_flat_alteration[rounded_pitch % 12]
    else:
        rounded_pitch = round(pitch)
        step, alteration = pc_number_to_step_and_standard_alteration[rounded_pitch % 12]
    octave = int(rounded_pitch/12) - 1

    # if a quarter-tone, adjust the accidental
    if pitch != rounded_pitch:
        alteration += pitch - rounded_pitch
        alteration = round(alteration, ndigits=3)
    return step, alteration, octave, rounded_pitch


class Pitch(ElementTree.Element):

    def __init__(self, midi_val, accidental_preference="standard"):
        super(Pitch, self).__init__("pitch")
        self.step, self.alter, self.octave, self.rounded_pitch = \
            get_pitch_step_alter_and_octave(midi_val, accidental_preference=accidental_preference)
        step_el = ElementTree.Element("step")
        step_el.text = self.step
        alter_el = ElementTree.Element("alter")
        alter_el.text = str(self.alter)
        octave_el = ElementTree.Element("octave")
        octave_el.text = str(self.octave)
        self.append(step_el)
        self.append(alter_el)
        self.append(octave_el)

    def __repr__(self):
        return "{}{}, {}".format(self.step, self.octave, self.alter)

#  -------------------------------------------------- DURATION ----------------------------------------------------- #


length_to_note_type = {
    8.0: "breve",
    4.0: "whole",
    2.0: "half",
    1.0: "quarter",
    0.5: "eighth",
    0.25: "16th",
    1.0/8: "32nd",
    1.0/16: "64th",
    1.0/32: "128th"
}


def get_basic_length_and_num_dots(length):
    if length in length_to_note_type:
        return length, 0
    else:
        dots_multiplier = 1.5
        dots = 1
        while length / dots_multiplier not in length_to_note_type:
            dots += 1
            dots_multiplier = (2.0 ** (dots + 1) - 1) / 2.0 ** dots
            if dots > engraving_settings.max_dots_allowed:
                raise ValueError("Duration length of {} does not resolve to "
                                 "single note type.".format(length))
        return length / dots_multiplier, dots


def is_single_note_length(length):
    try:
        get_basic_length_and_num_dots(length)
        return True
    except ValueError:
        return False


class Duration:

    def __init__(self, length_without_tuplet, tuplet=None):
        # expresses a length that can be written as a single note head.
        # Optionally, a tuplet ratio, e.g. (4, 3).
        # The tuplet ratio can also include the normal type, e.g. (4, 3, 0.5) for 4 in the space of 3 eighths
        self.actual_length = float(length_without_tuplet)
        if tuplet is not None:
            self.actual_length *= float(tuplet[1]) / tuplet[0]

        try:
            note_type_length, self.dots = get_basic_length_and_num_dots(length_without_tuplet)
            self.type = length_to_note_type[note_type_length]
        except ValueError as err:
            raise err

        if tuplet is not None:
            self.time_modification = ElementTree.Element("time-modification")
            ElementTree.SubElement(self.time_modification, "actual-notes").text = str(tuplet[0])
            ElementTree.SubElement(self.time_modification, "normal-notes").text = str(tuplet[1])
            if len(tuplet) > 2:
                if tuplet[2] not in length_to_note_type:
                    ValueError("Tuplet normal note type is not a standard power of two length.")
                ElementTree.SubElement(self.time_modification, "normal-type").text = length_to_note_type[tuplet[2]]
        else:
            self.time_modification = None


#  -------------------------------------------------- NOTATIONS ----------------------------------------------------- #


class Tuplet(ElementTree.Element):
    def __init__(self, start_or_end, number=1, placement="above"):
        self.start_or_end = start_or_end
        super(Tuplet, self).__init__("tuplet", {"type": start_or_end, "number": str(number), "placement": placement})

    def __repr__(self):
        return "Tuplet({})".format(self.start_or_end)


#  ---------------------------------------------------- NOTE ------------------------------------------------------- #


class Note(ElementTree.Element):
    # represents notes, or rests by setting pitch to 0
    # to build a chord include several Notes, and set is_chord_member to True on all but the first

    def __init__(self, pitch, duration, ties=None, notations=(), articulations=(), beams=None,
                 notehead=None, is_chord_member=False, voice=None, staff=None):
        super(Note, self).__init__("note")

        if pitch == "bar rest":
            # special case: a bar rest. Here, duration is just the length in quarters rather than
            # a duration object, since that requires a note expressible as a single note head, and
            # we might be dealing with a bar of length, say 2.5
            duration = float(duration)
            self.append(ElementTree.Element("rest", {"measure": "yes"}))
            duration_el = ElementTree.Element("duration")
            duration_el.text = str(int(round(duration * num_beat_divisions)))
            self.append(duration_el)
            type_el = ElementTree.Element("type")
            type_el.text = "whole"
            self.append(type_el)
            # okay, no need for the rest of this stuff, so return now
            return

        assert isinstance(duration, Duration)

        notations, articulations = list(notations), list(articulations)
        if pitch is None:
            self.append(ElementTree.Element("rest"))
        else:
            assert isinstance(pitch, Pitch)
            self.pitch = pitch
            self.append(pitch)
        duration_el = ElementTree.Element("duration")
        duration_el.text = str(int(round(duration.actual_length * num_beat_divisions)))
        self.append(duration_el)

        if is_chord_member:
            self.append(ElementTree.Element("chord"))

        if voice is not None:
            voice_el = ElementTree.Element("voice")
            voice_el.text = str(voice)
            self.append(voice_el)

        if staff is not None:
            staff_el = ElementTree.Element("staff")
            staff_el.text = str(staff)
            self.append(staff_el)

        if ties is not None:
            if ties.lower() == "start" or ties.lower() == "continue":
                self.append(ElementTree.Element("tie", {"type": "start"}))
                notations.append(ElementTree.Element("tied", {"type": "start"}))
            if ties.lower() == "stop" or ties.lower() == "continue":
                self.append(ElementTree.Element("tie", {"type": "stop"}))
                notations.append(ElementTree.Element("tied", {"type": "stop"}))

        type_el = ElementTree.Element("type")
        type_el.text = duration.type
        self.append(type_el)
        for _ in range(duration.dots):
            self.append(ElementTree.Element("dot"))

        if notehead is not None:
            self.append(notehead)

        if duration.time_modification is not None:
            self.append(duration.time_modification)

        if beams is not None:
            for beam_num in beams:
                beam_text = beams[beam_num]
                beam_el = ElementTree.Element("beam", {"number": str(beam_num)})
                beam_el.text = beam_text
                self.append(beam_el)

        if len(notations) + len(articulations) > 0:
            # there is either a notation or an articulation, so we'll add a notations tag
            notations_el = ElementTree.Element("notations")
            for notation in notations:
                if isinstance(notation, ElementTree.Element):
                    notations_el.append(notation)
                else:
                    notations_el.append(ElementTree.Element(notation))
            if len(articulations) > 0:
                articulations_el = ElementTree.SubElement(notations_el, "articulations")
                for articulation in articulations:
                    if isinstance(articulation, ElementTree.Element):
                        articulations_el.append(articulation)
                    else:
                        articulations_el.append(ElementTree.Element(articulation))
            self.append(notations_el)

    @classmethod
    def make_chord(cls, pitches, duration, ties=None, notations=(), articulations=(), beams=None,
                   notehead=None, voice=None, staff=None):
        out = []
        chord_switch = False
        for pitch in pitches:
            # Note that we don't reiterate the beaming information on subsequent elements of a chord
            out.append(cls(Pitch(pitch), duration, ties=ties, notations=notations, articulations=articulations,
                           beams=None if chord_switch else beams, is_chord_member=chord_switch,
                           notehead=notehead, voice=voice, staff=staff))
            chord_switch = True
        return out

    @classmethod
    def bar_rest(cls, duration_of_bar, staff=None, voice=None):
        return cls("bar rest", duration_of_bar, staff=staff, voice=voice)



#  -------------------------------------------------- MEASURE ------------------------------------------------------ #


clef_name_to_letter_and_line = {
    "treble": ("G", 2),
    "bass": ("F", 4),
    "alto": ("C", 3),
    "tenor": ("C", 4)
}

barline_name_to_xml_name = {
    "double": "light-light",
    "end": "light-heavy",
}


class Measure(ElementTree.Element):

    def __init__(self, number, time_signature=None, clef=None, barline=None, staves=None):
        super(Measure, self).__init__("measure", {"number": str(number)})

        self.has_barline = False

        attributes_el = ElementTree.Element("attributes")
        self.append(attributes_el)
        divisions_el = ElementTree.SubElement(attributes_el, "divisions")
        divisions_el.text = str(num_beat_divisions)

        if time_signature is not None:
            # time_signature is expressed as a tuple
            time_el = ElementTree.SubElement(attributes_el, "time")
            ElementTree.SubElement(time_el, "beats").text = str(time_signature[0])
            ElementTree.SubElement(time_el, "beat-type").text = str(time_signature[1])

        if clef is not None:
            # clef is a tuple: the first element is the sign ("G" clef of "F" clef)
            # the second element is the line the sign centers on
            # an optional third element expresses the number of octaves transposition up or down
            # however, we also take words like "treble" and convert them
            if clef in clef_name_to_letter_and_line:
                clef = clef_name_to_letter_and_line[clef]
            clef_el = ElementTree.SubElement(attributes_el, "clef")
            ElementTree.SubElement(clef_el, "sign").text = clef[0]
            ElementTree.SubElement(clef_el, "line").text = str(clef[1])
            if len(clef) > 2:
                ElementTree.SubElement(clef_el, "clef-octave-change").text = str(clef[2])

        if staves is not None:
            staves_el = ElementTree.SubElement(attributes_el, "staves")
            staves_el.text = str(staves)

        if barline is not None:
            barline_el = ElementTree.Element("barline", {"location": "right"})
            self.append(barline_el)
            self.has_barline = True
            if barline in barline_name_to_xml_name:
                barline = barline_name_to_xml_name[barline]
            ElementTree.SubElement(barline_el, "bar-style").text = barline

    def append(self, element):
        if self.has_barline:
            super(Measure, self).insert(-1, element)
        else:
            super(Measure, self).append(element)


#  -------------------------------------------------- Part ------------------------------------------------------ #

class PartGroup:
    next_available_number = 1

    def __init__(self, has_bracket=True, has_group_bar_line=True):
        self.number = PartGroup.next_available_number
        PartGroup.next_available_number += 1
        self.has_bracket = has_bracket
        self.has_group_bar_line = has_group_bar_line

    def get_start_element(self):
        start_element = ElementTree.Element("part-group", {"number": str(self.number), "type": "start"})
        if self.has_bracket:
            ElementTree.SubElement(start_element, "group-symbol").text = "bracket"
        ElementTree.SubElement(start_element, "group-barline").text = "yes" if self.has_group_bar_line else "no"
        return start_element

    def get_stop_element(self):
        return ElementTree.Element("part-group", {"number": str(self.number), "type": "stop"})


class Part(ElementTree.Element):
    next_available_number = 1

    def __init__(self, part_name, manual_part_id=None):
        self.part_id = manual_part_id if manual_part_id is not None else "P" + str(Part.next_available_number)
        if manual_part_id is None:
            Part.next_available_number += 1
        super(Part, self).__init__("part", {"id": str(self.part_id)})
        self.part_name = part_name

    def get_part_list_entry(self):
        score_part_el = ElementTree.Element("score-part", {"id": str(self.part_id)})
        ElementTree.SubElement(score_part_el, "part-name").text = self.part_name
        return score_part_el

#  ------------------------------------------------- Score ------------------------------------------------------ #


class Score(ElementTree.Element):

    def __init__(self, title=None, composer=None):
        super(Score, self).__init__("score-partwise")
        title = random.choice(engraving_settings.default_titles) if title is None else title
        composer = random.choice(engraving_settings.default_composers) if composer is None else composer
        str(date.today())
        work_el = ElementTree.Element("work")
        self.append(work_el)
        ElementTree.SubElement(work_el, "work-title").text = title
        id_el = ElementTree.Element("identification")
        self.append(id_el)
        ElementTree.SubElement(id_el, "creator", {"type": "composer"}).text = composer
        encoding_el = ElementTree.SubElement(id_el, "encoding")
        ElementTree.SubElement(encoding_el, "encoding-date").text = str(date.today())
        ElementTree.SubElement(encoding_el, "software").text = "marcpy"
        self.part_list = ElementTree.Element("part-list")
        self.append(self.part_list)

    def add_part(self, part):
        self.append(part)
        self.part_list.append(part.get_part_list_entry())

    def add_parts_as_group(self, parts, part_group):
        self.part_list.append(part_group.get_start_element())
        for part in parts:
            self.append(part)
            self.part_list.append(part.get_part_list_entry())
        self.part_list.append(part_group.get_stop_element())

    def save_to_file(self, file_name):
        file_ = open(file_name, 'w')
        file_.write(ElementTree.tostring(self, encoding="unicode"))
        file_.close()

#  ----------------------------------------------- Other Elements --------------------------------------------------- #


class MetronomeMark(ElementTree.Element):

    def __init__(self, unit_type, bpm, voice=1, staff=1, offset=0):
        super(MetronomeMark, self).__init__("direction")
        d_type_el = ElementTree.Element("direction-type")
        self.append(d_type_el)

        metronome_el = ElementTree.SubElement(d_type_el, "metronome")
        if isinstance(unit_type, numbers.Number):
            if float(unit_type) not in length_to_note_type:
                raise ValueError("Unit type not valid")
            unit_type = length_to_note_type[float(unit_type)]
        ElementTree.SubElement(metronome_el, "beat-unit").text = unit_type
        ElementTree.SubElement(metronome_el, "per-minute").text = str(bpm)

        if offset != 0:
            offset_el = ElementTree.Element("offset", {"sound": "no"})
            offset_el.text = str(int(offset * num_beat_divisions))
            self.append(offset_el)

        voice_el = ElementTree.Element("voice")
        voice_el.text = str(voice)
        self.append(voice_el)
        staff_el = ElementTree.Element("staff")
        staff_el.text = str(staff)
        self.append(staff_el)


class Text(ElementTree.Element):
    def __init__(self, text, voice=1, staff=1, **kwargs):
        super(Text, self).__init__("direction")
        type_el = ElementTree.Element("direction-type")
        self.append(type_el)
        words_el = ElementTree.Element("words", kwargs)
        words_el.text = text
        type_el.append(words_el)
        self.voice_el = ElementTree.Element("voice")
        self.voice_el.text = str(voice)
        self.staff_el = ElementTree.Element("staff")
        self.staff_el.text = str(staff)
        self.append(self.voice_el)
        self.append(self.staff_el)

    def set_voice(self, voice):
        self.voice_el.text = str(voice)

    def set_staff(self, staff):
        self.staff_el.text = str(staff)


class Backup(ElementTree.Element):

    def __init__(self, quarters_length):
        super(Backup, self).__init__("backup")
        duration_el = ElementTree.Element("duration")
        self.append(duration_el)
        duration_el.text = str(num_beat_divisions * quarters_length)


#  --------------------------------------------------- EXAMPLE ----------------------------------------------------- #

# my_score = Score("Test Score", "D. Bag")
# violin_part = Part("Violin")
# measure = Measure(1, (3, 4), "treble")
# measure.append(Note(Pitch(58.5), Duration(1.5, (3, 2, 1)), notations=[Tuplet("start")],
#                     articulations=[ElementTree.Element("staccato"), ElementTree.Element("tenuto")]))
# measure.append(Note(Pitch(63), Duration(0.5, (3, 2, 1)), articulations=[ElementTree.Element("tenuto")]))
# measure.append(Note(Pitch(61), Duration(1.0, (3, 2, 1)), notations=[Tuplet("end")], ties="start"))
# measure.append(Note(Pitch(61), Duration(0.5), ties="thru"))
# measure.append(Note(Pitch(61), Duration(0.25), ties="end", articulations=["staccatissimo"]))
# measure.append(Note(None, Duration(0.25)))
# violin_part.append(measure)
# measure = Measure(2, (5, 8))
# measure.append(Note(Pitch(70), Duration(1.5), articulations=[ElementTree.Element("tenuto")]))
# measure.append(MetronomeMark(2, 100))
# measure.append(Note(Pitch(65), Duration(1.0), ties="start"))
# violin_part.append(measure)
# measure = Measure(3, barline="end")
# measure.append(Note(Pitch(65), Duration(0.5, (4, 3, 0.5)), notations=[Tuplet("start")], ties="end"))
# measure.append(Note(Pitch(66), Duration(1, (4, 3, 0.5)), articulations=[ElementTree.Element("tenuto")]))
# measure.append(Note(Pitch(67), Duration(0.5, (4, 3, 0.5)), notations=[Tuplet("end")], ties="start"))
# measure.append(Note(Pitch(67), Duration(0.5), notations=[Tuplet("end")], ties="end"))
# measure.append(Note(None, Duration(0.5)))
# violin_part.append(measure)
#
# viola_part = Part("Viola")
# measure = Measure(1, (3, 4), "alto")
# measure.append(Note(Pitch(58.5), Duration(1.5, (3, 2, 1)), notations=[Tuplet("start")],
#                     articulations=[ElementTree.Element("staccato"), ElementTree.Element("tenuto")]))
# measure.append(Note(Pitch(53), Duration(0.5, (3, 2, 1)), articulations=[ElementTree.Element("tenuto")]))
# measure.append(Note(Pitch(51), Duration(1.0, (3, 2, 1)), notations=[Tuplet("end")], ties="start"))
# measure.append(Note(Pitch(51), Duration(0.5), ties="thru"))
# measure.append(Note(Pitch(51), Duration(0.25), ties="end", articulations=["staccatissimo"]))
# measure.append(Note(None, Duration(0.25)))
# viola_part.append(measure)
# measure = Measure(2, (5, 8))
# measure.append(Note(None, Duration(1.0)))
# measure.append(Note(Pitch(55), Duration(0.5, (4, 3, 0.5)), notations=[Tuplet("start")], ties="end"))
# measure.append(Note(Pitch(56), Duration(1, (4, 3, 0.5)), articulations=[ElementTree.Element("tenuto")]))
# measure.append(Note(Pitch(57), Duration(0.5, (4, 3, 0.5)), notations=[Tuplet("end")]))
# viola_part.append(measure)
# measure = Measure(3, barline="end")
# measure.append(Note(Pitch(60), Duration(1.5)))
# measure.append(Note(Pitch(60), Duration(0.5), articulations=[ElementTree.Element("tenuto")]))
# measure.append(Note(Pitch(60), Duration(0.5)))
# viola_part.append(measure)
#
# cello_part = Part("Cello")
# measure = Measure(1, (3, 4), "bass")
# measure.append(Note.bar_rest(3))
# cello_part.append(measure)
#
# measure = Measure(2, (5, 8))
# measure.extend(Note.make_chord([Pitch(41), Pitch(45), Pitch(48)], Duration(1.5)))
# measure.append(Note(Pitch(40), Duration(0.5), articulations=[ElementTree.Element("tenuto")]))
# measure.append(Note(Pitch(40), Duration(0.5)))
# cello_part.append(measure)
#
# measure = Measure(3, barline="end")
# measure.append(Note.bar_rest(2.5))
# cello_part.append(measure)
#
# my_score.add_parts_as_group([violin_part, viola_part], PartGroup())
# my_score.add_part(cello_part)
#
#
# my_score.save_to_file("testScore.xml")