from xml.etree import ElementTree


class Duration:

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

    @staticmethod
    def get_note_type_and_number_of_dots(length):
        if length in length_to_note_type:
            return length, 0
        else:
            dots_multiplier = 1.5
            dots = 1
            while length / dots_multiplier not in length_to_note_type:
                dots += 1
                dots_multiplier = (2.0 ** (dots + 1) - 1) / 2.0 ** dots
                if dots > engraving_settings.max_dots_allowed:
                    raise ValueError("Duration length of {} does not resolve to single note type.".format(length))
            return Duration.length_to_note_type[length / dots_multiplier], dots