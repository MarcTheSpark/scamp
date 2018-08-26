from xml.etree import ElementTree


notehead_name_to_lilypond_type = {
    "normal": "default",
    "diamond": "diamond",
    "harmonic": "harmonic",
    "harmonic black": "harmonic black",
    "harmonic mixed": "harmonic mixed",
    "triangle": "triangle",
    "slash": "slash",
    "cross": "cross",
    "x": "cross",
    "circle-x": "xcircle",
    "xcircle": "xcircle",
    "inverted triangle": None,
    "square": None,
    "arrow down": None,
    "arrow up": None,
    "circled": None,
    "slashed": None,
    "back slashed": None,
    "cluster": None,
    "circle dot": None,
    "left triangle": None,
    "rectangle": None,
    "do": None,
    "re": None,
    "mi": None,
    "fa": None,
    "fa up": None,
    "so": None,
    "la": None,
    "ti": None,
    "none": "none",
}

notehead_name_to_xml_type = {
    "normal": "normal",
    "diamond": "diamond",
    "harmonic": "open mi",
    "harmonic black": "filled mi",
    "harmonic mixed": "mi",
    "triangle": "triangle",
    "slash": "slash",
    "cross": "cross",
    "x": "x",
    "circle-x": "circle-x",
    "xcircle": "circle-x",
    "inverted triangle": "inverted triangle",
    "square": "square",
    "arrow down": "arrow down",
    "arrow up": "arrow up",
    "circled": "circled",
    "slashed": "slashed",
    "back slashed": "back slashed",
    "cluster": "cluster",
    "circle dot": "circle dot",
    "left triangle": "left triangle",
    "rectangle": "rectangle",
    "do": "do",
    "re": "re",
    "mi": "mi",
    "fa": "fa",
    "fa up": "fa up",
    "so": "so",
    "la": "la",
    "ti": "ti",
    "none": "none",
}

notehead_type_to_xml_filled_attribute = {
    "harmonic": "no",
    "harmonic black": "yes",
}


def is_valid_notehead(notehead_string: str):
    return notehead_string.replace("filled ", "").replace("open ", "") in notehead_name_to_xml_type.keys()


def get_notehead_xml_filled_attribute(notehead_string: str):
    basic_notehead_name = notehead_string.replace("filled ", "").replace("open ", "")
    if "filled" in notehead_string:
        return "yes"
    elif "open" in notehead_string:
        return "no"
    elif basic_notehead_name in notehead_type_to_xml_filled_attribute:
        return notehead_type_to_xml_filled_attribute[basic_notehead_name]
    else:
        return None  # meaning, don't use the filled attribute


articulation_to_xml_articulation = {
    "staccato": "staccato",
    "staccatissimo": "staccatissimo",
    "marcato": "strong-accent",
    "tenuto": "tenuto",
    "accent": "accent"
}


def generate_nested_element(*args):
    out = this_element = None
    for element_info in args:
        if isinstance(element_info, str):
            out = this_element = ElementTree.Element(element_info) if out is None \
                else ElementTree.SubElement(out, element_info)
        else:
            this_element = ElementTree.Element(element_info[0]) if out is None \
                else ElementTree.SubElement(this_element, element_info[0])
            for extra_info in element_info[1:]:
                if isinstance(extra_info, dict):
                    this_element.attrib = extra_info
                elif isinstance(extra_info, str):
                    this_element.text = extra_info
    return out


notations_to_xml_element = {
    "tremolo1": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "1")),
    "tremolo2": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "2")),
    "tremolo3": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "3")),
    "tremolo4": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "4")),
    "tremolo5": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "5")),
    "tremolo8": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "1")),
    "tremolo16": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "2")),
    "tremolo32": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "3")),
    "tremolo64": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "4")),
    "tremolo128": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "5")),
}