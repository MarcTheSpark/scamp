__author__ = 'mpevans'

from .musicXML_exporter import *
from .measures_beats_notes import *
from copy import deepcopy
from .thirdparty.interval import IntervalSet
from itertools import permutations
from .playcorder_utilities import make_flat_list, round_to_multiple, get_standard_indispensability_array, prime_factor
import re

notation_locations = {
    # any notation without an entry is assumed to be distributed to all tied noteheads
    "staccato": "end",
    "tenuto": "end",
    "accent": "start",
}


def save_to_xml_file(recorded_parts, part_names, file_name, measure_schemes=None, time_signature="4/4", tempo=60,
                     divisions=8, max_indigestibility=4, simplicity_preference=0.5, title=None, composer=None,
                     separate_voices_in_separate_staves=True, show_cent_values=True, add_sibelius_pitch_bend=True,
                     max_overlap=0.001):

    print("Saving Output...")

    # get measure schemes from time signature if not supplied
    if measure_schemes is None:
        measure_schemes = [MeasureScheme.from_time_signature(time_signature, tempo, divisions=divisions,
                                                             max_indigestibility=max_indigestibility,
                                                             simplicity_preference=simplicity_preference)]

    # make a list of the beat schemes (up to repeating the last one)
    beat_schemes = []
    for ms in measure_schemes:
        beat_schemes.extend(ms.beat_quantization_schemes)

    # now that we have all the tempo info from the beat schemes, let's figure out the length in quarters
    total_quarters_length = _get_recording_quarters_length(recorded_parts, beat_schemes)

    # keep repeating the last measure_scheme until we get to the end of the recording
    total_measure_schemes_length = sum(ms.length for ms in measure_schemes)
    while total_measure_schemes_length <= total_quarters_length:
        measure_schemes.append(deepcopy(measure_schemes[-1]))
        beat_schemes.extend(measure_schemes[-1].beat_quantization_schemes)
        total_measure_schemes_length += measure_schemes[-1].length

    # set the start_times of all the measure and beat schemes
    current_time = 0
    for measure_scheme in measure_schemes:
        measure_scheme.start_time = current_time
        for beat_scheme in measure_scheme.beat_quantization_schemes:
            beat_scheme.start_time = current_time
            current_time += beat_scheme.beat_length

    xml_score = Score(title, composer)
    for which_part, (part_recording, part_name) in enumerate(zip(recorded_parts, part_names)):
        print("Working on Part " + str(which_part+1) + "...")

        # make the music21 part object, and add the instrument
        xml_part = Part(part_name)

        # quantize the recording, also noting the beat divisors
        quantized_recording, beat_divisors = quantize_recording(part_recording, beat_schemes)
        # merge notes into chords
        quantized_recording = _collapse_recording_chords(quantized_recording)
        # separate it into non-overlapping voices
        quantized_separated_voices = separate_into_non_overlapping_voices(quantized_recording, max_overlap)
        # clean up pc_voices: add rests, break into ties, etc.
        clean_pc_voices = [_process_voice(v, beat_schemes, beat_divisors) for v in quantized_separated_voices]
        num_voices_this_part = len(clean_pc_voices)

        # create xml measure objects with time signatures and add to the part
        last_time_signature = None
        last_tempo = None
        measure_num = 1
        for measure_scheme in measure_schemes:
            measure_start, measure_time_signature = measure_scheme.start_time, measure_scheme.tuple_time_signature
            measure_end = measure_scheme.end_time
            beat_lengths = [beat_scheme.beat_length for beat_scheme in measure_scheme.beat_quantization_schemes]
            beat_start_times = [measure_start + sum(beat_lengths[0:i]) for i in range(len(beat_lengths))]

            # now we add the notes to the measure
            # first group notes into the voices in the measure
            voices_in_measure = []
            for voice in clean_pc_voices:
                voice_in_measure = [pc_note for pc_note in voice
                                    if measure_start <= pc_note.start_time < measure_end]

                # make sure one of them is not a rest
                if len([n for n in voice_in_measure if n.pitch is not None]) > 0:
                    voice_in_measure = _combine_long_notes_voice_measure(voice_in_measure, beat_start_times)
                    voice_in_measure = _add_beaming(voice_in_measure, measure_scheme.beat_quantization_schemes)
                    voices_in_measure.append(voice_in_measure)

            voices_in_measure.sort(key=lambda x: get_average_pitch(x), reverse=True)

            # make a xml measure with the appropriate time signature
            clef = "treble" if measure_num == 1 else None
            time_signature = measure_time_signature if measure_time_signature != last_time_signature else None
            num_staves = num_voices_this_part if separate_voices_in_separate_staves else 1
            xml_measure = Measure(number=measure_num, clef=clef, time_signature=time_signature,
                                  staves=num_staves)
            last_time_signature = measure_time_signature

            # add the measure to the part, and increment measure_num
            xml_part.append(xml_measure)
            measure_num += 1

            # add any metronome marks we need based on beat tempos
            offset = 0
            for beat_scheme in measure_scheme.beat_quantization_schemes:
                if beat_scheme.tempo != last_tempo:
                    xml_measure.append(MetronomeMark("quarter", beat_scheme.tempo, offset=offset))
                    last_tempo = beat_scheme.tempo
                offset += beat_scheme.beat_length

            # populate the xml measure object with xml notes
            if len(voices_in_measure) == 0:
                # if the measure's empty, add a bar rest
                xml_measure.append(Note.bar_rest(measure_end - measure_start))
            else:
                # otherwise go through each voice present in the measure
                for which_voice, voice_in_measure in enumerate(voices_in_measure):
                    if which_voice != 0:
                        # not the first voice; we need to rewind to the start of the measure
                        xml_measure.append(Backup(measure_scheme.length))

                    # each note in each voice
                    for pc_note in voice_in_measure:
                        assert isinstance(pc_note, MPNote)
                        if isinstance(pc_note.pitch, (list, tuple)):
                            # it's a chord
                            xml_notes = Note.make_chord(
                                pc_note.pitch,
                                duration=Duration(pc_note.length_without_tuplet, pc_note.time_modification),
                                voice=which_voice+1, staff=(which_voice+1) if separate_voices_in_separate_staves else 1,
                                notations=pc_note.notations, articulations=pc_note.articulations, beams=pc_note.beams,
                                ties=pc_note.tie, notehead=pc_note.notehead
                            )
                        else:
                            xml_notes = [
                                Note(
                                    None if pc_note.pitch is None else Pitch(pc_note.pitch),
                                    duration=Duration(pc_note.length_without_tuplet, pc_note.time_modification),
                                    voice=which_voice+1, staff=(which_voice+1) if separate_voices_in_separate_staves
                                    else 1, notations=pc_note.notations, articulations=pc_note.articulations,
                                    beams=pc_note.beams, ties=pc_note.tie, notehead=pc_note.notehead
                                )
                            ]

                        if pc_note.tie is None or pc_note.tie == "start":
                            # add in some last minute text annotations for microtonal pitch deviations and pitch bends
                            if show_cent_values and pc_note.pitch is not None:
                                micro_tone_deviations = []
                                for m, a_pitch in enumerate(make_flat_list([pc_note.pitch])):
                                    if a_pitch != int(a_pitch):
                                        micro_tone_deviations.append(str(round(a_pitch, 2)))
                                if len(micro_tone_deviations) > 0:
                                    pc_note.text_annotations.append(Text(
                                        ", ".join(micro_tone_deviations),
                                        staff=1 if separate_voices_in_separate_staves else which_voice+1,
                                        voice=which_voice+1,
                                    ))
                            if add_sibelius_pitch_bend and pc_note.pitch is not None \
                                    and not isinstance(pc_note.pitch, (list, tuple)) \
                                    and pc_note.pitch != int(pc_note.pitch):
                                # single microtonal pitch, so notate pitch bend. Since this is all in one voice, we
                                # can't play back different pitch bends at the same time, so ignore chords
                                xml_note = xml_notes[0]
                                assert isinstance(xml_note, Note)
                                pc_note.text_annotations.append(Text(
                                    get_pitch_bend_text(pc_note.pitch - xml_note.pitch.rounded_pitch),
                                    staff=1 if separate_voices_in_separate_staves else which_voice+1,
                                    voice=which_voice+1,
                                ))

                        # before adding the note itself, we add any text annotations
                        for text_annotation in pc_note.text_annotations:
                            assert isinstance(text_annotation, Text)
                            text_annotation.set_staff(1 if separate_voices_in_separate_staves else which_voice+1)
                            text_annotation.set_voice(which_voice+1)
                            xml_measure.append(text_annotation)

                        for xml_note in xml_notes:
                            xml_measure.append(xml_note)
        xml_score.add_part(xml_part)
    print("Done.")
    xml_score.save_to_file(file_name)

# [ ---------- Utilities -----------]


def _get_recording_quarters_length(recorded_parts, beat_schemes):
    # returns the length in seconds, and then the length in quarters, taking into account the tempos of the beats
    length = max([max([pc_note.start_time + pc_note.length for pc_note in part] + [0])
                  for part in recorded_parts])
    quarter_length = 0
    current_beat = 0
    while length > 0:
        current_beat_scheme = beat_schemes[current_beat]
        assert isinstance(current_beat_scheme, BeatQuantizationScheme)
        beat_length_in_seconds = current_beat_scheme.beat_length * 60.0 / current_beat_scheme.tempo
        quarter_length += current_beat_scheme.beat_length
        length -= beat_length_in_seconds
        if current_beat + 1 < len(beat_schemes):
            current_beat += 1
    return quarter_length


# [ ------- Part Processing ------- ]


def quantize_recording(recording_in_seconds, beat_schemes, onset_termination_weighting=0.3):

    """

    :param recording_in_seconds: a voice consisting of MPNotes, with timings in seconds
    :param beat_schemes: a list of beat_schemes through which we iterate, which determine the quantization
    parameters. The last beat scheme is looped through till the end.
    :param onset_termination_weighting: 0 means we only care about onsets when determining the best quantization,
    and 1 means we only care about terminations. In between is a weighting.
    """
    # raw_onsets and raw_terminations are in seconds
    raw_onsets = [(pc_note.start_time, pc_note) for pc_note in recording_in_seconds]
    raw_terminations = [(pc_note.start_time + pc_note.length, pc_note) for pc_note in recording_in_seconds]
    raw_onsets.sort(key=lambda x: x[0])
    raw_terminations.sort(key=lambda x: x[0])

    pc_note_to_quantize_start_time = {}
    pc_note_to_quantize_end_time = {}
    current_beat_scheme = 0
    quarters_beat_start_time = 0.0
    seconds_beat_start_time = 0.0
    beat_divisors = []
    while len(raw_onsets) + len(raw_terminations) > 0:
        # move forward one beat at a time
        # get the beat scheme for this beat
        this_beat_scheme = beat_schemes[current_beat_scheme] if current_beat_scheme < len(beat_schemes) \
            else beat_schemes[-1]
        assert isinstance(this_beat_scheme, BeatQuantizationScheme)
        current_beat_scheme += 1

        # get the beat length and end time in quarters and seconds
        quarters_beat_length = this_beat_scheme.beat_length
        seconds_beat_length = this_beat_scheme.beat_length * 60.0 / this_beat_scheme.tempo
        quarters_beat_end_time = quarters_beat_start_time + this_beat_scheme.beat_length
        seconds_beat_end_time = seconds_beat_start_time + seconds_beat_length

        # find the onsets in this beat
        onsets_to_quantize = []
        while len(raw_onsets) > 0 and raw_onsets[0][0] < seconds_beat_end_time:
            onsets_to_quantize.append(raw_onsets.pop(0))

        # find the terminations in this beat
        terminations_to_quantize = []
        while len(raw_terminations) > 0 and raw_terminations[0][0] < seconds_beat_end_time:
            terminations_to_quantize.append(raw_terminations.pop(0))

        if len(onsets_to_quantize) + len(terminations_to_quantize) == 0:
            # an empty beat, nothing to see here
            beat_divisors.append(None)
        else:
            # try out each quantization division
            best_divisor = None
            best_error = float("inf")

            for divisor, undesirability in this_beat_scheme.quantization_divisions:
                seconds_piece_length = seconds_beat_length / divisor
                total_squared_onset_error = 0
                for onset in onsets_to_quantize:
                    time_since_beat_start = onset[0] - seconds_beat_start_time
                    total_squared_onset_error += (time_since_beat_start - round_to_multiple(time_since_beat_start, seconds_piece_length)) ** 2
                total_squared_term_error = 0
                for term in terminations_to_quantize:
                    time_since_beat_start = term[0] - seconds_beat_start_time
                    total_squared_term_error += (time_since_beat_start - round_to_multiple(time_since_beat_start, seconds_piece_length)) ** 2
                this_div_error_score = undesirability * (onset_termination_weighting * total_squared_term_error +
                                                         (1 - onset_termination_weighting) * total_squared_onset_error)
                if this_div_error_score < best_error:
                    best_divisor = divisor
                    best_error = this_div_error_score
            best_piece_length_quarters = this_beat_scheme.beat_length / best_divisor
            best_piece_length_seconds = seconds_beat_length / best_divisor

            for onset, pc_note in onsets_to_quantize:
                pieces_past_beat_start = round((onset - seconds_beat_start_time) / best_piece_length_seconds)
                pc_note_to_quantize_start_time[pc_note] = quarters_beat_start_time + pieces_past_beat_start * best_piece_length_quarters
                # save this info for later, when we need to assure they all have the same Tuplet
                pc_note.start_time_divisor = best_divisor

            for termination, pc_note in terminations_to_quantize:
                pieces_past_beat_start = round((termination - seconds_beat_start_time) / best_piece_length_seconds)
                pc_note_to_quantize_end_time[pc_note] = quarters_beat_start_time + pieces_past_beat_start * best_piece_length_quarters
                if pc_note_to_quantize_end_time[pc_note] == pc_note_to_quantize_start_time[pc_note]:
                    # if the quantization collapses the start and end times of a note to the same point, adjust the
                    # end time so the the note is a single piece_length long.
                    if pc_note_to_quantize_end_time[pc_note] + best_piece_length_quarters <= quarters_beat_end_time:
                        # unless both are quantized to the start of the next beat, just move the end one piece forward
                        pc_note_to_quantize_end_time[pc_note] += best_piece_length_quarters
                    else:
                        # if they're at the start of the next beat, move the start one piece back
                        pc_note_to_quantize_start_time[pc_note] -= best_piece_length_quarters
                # save this info for later, when we need to assure they all have the same Tuplet
                pc_note.end_time_divisor = best_divisor

            beat_divisors.append(best_divisor)

        quarters_beat_start_time += quarters_beat_length
        seconds_beat_start_time += seconds_beat_length

    quantized_recording = []
    for pc_note in recording_in_seconds:
        quantized_recording.append(MPNote(start_time=pc_note_to_quantize_start_time[pc_note],
                                   length=pc_note_to_quantize_end_time[pc_note] - pc_note_to_quantize_start_time[pc_note],
                                   pitch=pc_note.pitch, volume=pc_note.volume, variant=pc_note.variant, tie=pc_note.tie))

    return quantized_recording, beat_divisors


def _collapse_recording_chords(recording):
    # sort it
    out = sorted(recording, key=lambda x: x.start_time)
    # combine contemporaneous notes into chords
    i = 0
    while i + 1 < len(out):
        if out[i].start_time == out[i+1].start_time and out[i].length == out[i+1].length \
                and out[i].volume == out[i+1].volume and out[i].variant == out[i+1].variant:
            chord_pitches = make_flat_list([out[i].pitch, out[i+1].pitch])
            out = out[:i] + [MPNote(start_time=out[i].start_time, length=out[i].length, pitch=chord_pitches,
                             volume=out[i].volume, variant=out[i].variant, tie=out[i].tie)] + out[i+2:]
        else:
            i += 1
    # Now split it into non-overlapping voices, and then we're good.
    return out


def separate_into_non_overlapping_voices(recording, max_overlap):
    # takes a recording of MPNotes and breaks it up into separate voices that don't overlap more than max_overlap
    assert isinstance(recording, list)
    recording.sort(key=lambda note: note.start_time)
    voices = []
    for pc_note in recording:
        # find the first non-conflicting voices
        voice_to_add_to = None
        for voice in voices:
            voice_end_time = voice[-1].start_time + voice[-1].length
            if voice_end_time - pc_note.start_time < max_overlap:
                voice_to_add_to = voice
                break
        if voice_to_add_to is None:
            voice_to_add_to = []
            voices.append(voice_to_add_to)
        voice_to_add_to.append(pc_note)

    return voices

# [ ------- Voice Pre-Processing ------- ]


def _process_voice(pc_voice, beat_schemes, beat_divisors):
    pc_voice = _add_rests(pc_voice, beat_schemes)
    pc_voice = _break_into_ties(pc_voice, beat_schemes)
    # the following modify the voice in place (mostly because they iterate through the notes)
    _convert_variants_to_notations_in_voice(pc_voice)
    _set_tuplets_for_notes_in_voice(pc_voice, beat_schemes, beat_divisors)
    _break_notes_into_undotted_constituents(pc_voice, beat_schemes, beat_divisors)
    # this one doesn't modify in place, since we're changing the number of notes
    pc_voice = _separate_note_components_into_different_notes(pc_voice)
    return pc_voice


def _break_into_ties(recording_in_seconds, beat_schemes):
    # first, create an array of beat lengths that repeats the length of
    # the last beat_scheme until we reach the end of the voice

    for beat_scheme in beat_schemes:
        beat_start_time = beat_scheme.start_time
        for i in range(len(recording_in_seconds)):
            this_pc_note = recording_in_seconds[i]
            if this_pc_note.start_time < beat_start_time < this_pc_note.start_time + this_pc_note.length:
                # split it in two
                first_half_tie = "continue" if this_pc_note.tie is "stop" or this_pc_note.tie is "continue" else "start"
                second_half_tie = "continue" if this_pc_note.tie is "start" or this_pc_note.tie is "continue" else "stop"
                first_half = MPNote(this_pc_note.start_time, beat_start_time - this_pc_note.start_time,
                                    this_pc_note.pitch, this_pc_note.volume, this_pc_note.variant, first_half_tie)
                second_half = MPNote(beat_start_time, this_pc_note.start_time + this_pc_note.length - beat_start_time,
                                     this_pc_note.pitch, this_pc_note.volume, this_pc_note.variant, second_half_tie)
                recording_in_seconds[i] = [first_half, second_half]
        recording_in_seconds = make_flat_list(recording_in_seconds, indivisible=MPNote)

    return recording_in_seconds


def _add_rests(recording_in_seconds, beat_schemes):
    new_recording = list(recording_in_seconds)
    # first, create all the intervals representing the beats
    beat_intervals = [IntervalSet.between(beat_scheme.start_time, beat_scheme.end_time) for beat_scheme in beat_schemes]
    # subtract out all the time occupied by a note already
    for pc_note in recording_in_seconds:
        note_interval = IntervalSet.between(pc_note.start_time, pc_note.start_time + pc_note.length)
        for i in range(len(beat_intervals)):
            beat_intervals[i] -= note_interval

    # add in rests to fill out each beat
    for beat_interval in beat_intervals:
        for rest_range in beat_interval:
            new_recording.append(MPNote(start_time=rest_range.lower_bound,
                                        length=rest_range.upper_bound-rest_range.lower_bound,
                                        pitch=None, volume=None, variant=None, tie=None))
    new_recording.sort(key=lambda x: x.start_time)
    return new_recording


def _combine_tied_quarters_and_longer(recording_in_seconds, measure_schemes):
    # _break_into_ties has broken some long notes into tied quarters, which is ugly and unnecessary
    # so we'll recombine them
    return recording_in_seconds


def _get_tuplet_type(beat_length, beat_div):
    if beat_div is None:
        # the beat was empty...
        return None

    # preference is to express the
    beat_length_fraction = Fraction(beat_length).limit_denominator()
    normal_number = beat_length_fraction.numerator
    # if denominator is 1, normal type is quarter note, 2 -> eighth note, etc.
    normal_type = 4 * beat_length_fraction.denominator
    while normal_number * 2 <= beat_div:
        normal_number *= 2
        normal_type *= 2

    # now we have beat_div in the space of normal_number normal_type-th notes
    if normal_number == beat_div:
        return None
    else:
        return beat_div, normal_number, 4.0/normal_type


def _set_tuplets_for_notes_in_voice(voice, beat_schemes, beat_divisors):
    # we assume notes_and_rests is in order
    voice = list(voice)
    for beat_scheme, beat_div in zip(beat_schemes, beat_divisors):
        tuplet_type = _get_tuplet_type(beat_scheme.beat_length, beat_div)
        beat_scheme.length_without_tuplet = beat_scheme.beat_length * float(tuplet_type[0]) / tuplet_type[1] \
            if tuplet_type is not None else beat_scheme.beat_length
        while len(voice) > 0 and voice[0].start_time < beat_scheme.end_time:
            this_note = voice.pop(0)
            assert isinstance(this_note, MPNote)
            if tuplet_type is not None:
                this_note.time_modification = tuplet_type
                this_note.length_without_tuplet = this_note.length * float(tuplet_type[0]) / tuplet_type[1]
                if this_note.start_time == beat_scheme.start_time:
                    this_note.starts_tuplet = True
                if this_note.end_time == beat_scheme.end_time:
                    this_note.ends_tuplet = True
            else:
                this_note.length_without_tuplet = this_note.length

    # there may be still a few notes left: these will be trailing rests that have been added since quantization
    # and for which no beat divisor has been calculated. We can safely set their length_without_tuplet to their length
    for remaining_rest in voice:
        assert isinstance(remaining_rest, MPNote)
        remaining_rest.length_without_tuplet = remaining_rest.length


def _convert_variants_to_notations_in_voice(voice):
    for note in voice:
        _convert_note_variant_to_notations(note)


def _convert_note_variant_to_notations(note):
    assert isinstance(note, MPNote)
    for articulation in note.variant["articulations"]:
        note.articulations.append(ET.Element(articulation))
    for dynamic in note.variant["dynamics"]:
        dynamic_el = ET.Element("dynamic")
        ET.SubElement(dynamic_el, dynamic)
        note.notations.append(dynamic_el)
    for notation in note.variant["notations"]:
        element_name, element_dict = string_to_element_name_and_dict(notation)
        note.notations.append(ET.Element(element_name, element_dict))
    if note.variant["notehead"] is not None:
        element_name, element_dict = string_to_element_name_and_dict(note.variant["notehead"])
        note.notehead = ET.Element("notehead", element_dict)
        note.notehead.text = element_name
    for text_annotation in note.variant["text_annotations"]:
        if isinstance(text_annotation, (tuple, list)):
            element_name, element_dict = text_annotation
        else:
            element_name, element_dict = text_annotation, {}
        note.text_annotations.append(Text(element_name, **element_dict))


def string_to_element_name_and_dict(element_string):
    assert isinstance(element_string, str)
    element_name = element_string.split("(")[0]
    pieces = re.split('\(|\)|, ', element_string)
    element_dict = {}
    for piece in pieces[1:]:
        if "=" in piece:
            key_and_value = piece.split("=")
            element_dict[key_and_value[0]] = key_and_value[1]
    return element_name, element_dict


def _break_notes_into_undotted_constituents(voice, beat_schemes, beat_divisors):
    # first, we  decompose a note into its undotted constituents
    for pc_note in voice:
        if is_single_note_length(pc_note.length):
            pc_note.length_without_tuplet = [pc_note.length_without_tuplet]
        else:
            pc_note.length_without_tuplet = MPNote.length_to_undotted_constituents(pc_note.length_without_tuplet)

    # if it can't be represented with a single notehead, we order the constituent noteheads so that larger noteheads
    # sit on more important subdivisions. We use indispensability to judge the importance of subdivisions
    for beat_scheme, divisor in zip(beat_schemes, beat_divisors):
        if divisor is None:
            continue
        beat_indispensabilities = get_standard_indispensability_array(
            _get_multiplicative_beat_meter(beat_scheme.beat_length, divisor), normalize=True
        )
        notes_in_beat = [pc_note for pc_note in voice
                         if beat_scheme.start_time <= pc_note.start_time < beat_scheme.end_time]
        for pc_note in notes_in_beat:
            if len(pc_note.length_without_tuplet) == 1:
                # this case really shouldn't come up, since we returned above if there's only one constituent duration
                continue
            else:
                # try every permutation of the duration constituents. Get a score for it by multiplying the length of
                # each constituent with the indispensability of that pulse within the beat and summing them.
                best_permutation = None
                best_score = 0
                for permutation in permutations(pc_note.length_without_tuplet):
                    score = 0.
                    position = (pc_note.start_time - beat_scheme.start_time) * beat_scheme.length_without_tuplet / beat_scheme.beat_length
                    for segment in permutation:
                        score += beat_indispensabilities[int(round(position / beat_scheme.length_without_tuplet * divisor))] * segment
                        position += segment
                    if score > best_score:
                        best_score = score
                        best_permutation = permutation
                pc_note.length_without_tuplet = list(best_permutation)


def _get_multiplicative_beat_meter(beat_length, beat_divisor):
    # a beat of length 1.5 = 3/2 prefers to divide into 3 first
    natural_division = Fraction(beat_length).limit_denominator().numerator
    prime_decomposition = prime_factor(beat_divisor)
    prime_decomposition.sort()
    for preferred_factor in sorted(prime_factor(natural_division), reverse=True):
        prime_decomposition.insert(0, prime_decomposition.pop(prime_decomposition.index(preferred_factor)))
    return prime_decomposition


def _separate_note_components_into_different_notes(voice):
    new_voice = []
    for pc_note in voice:
        assert isinstance(pc_note, MPNote)

        component_start_time = pc_note.start_time
        # loop through the components of each note
        for component_num, length_component in enumerate(pc_note.length_without_tuplet):
            # length_component represents the length it would be with no time modification, so when we create the new
            # MPNote object, we have to reinclude the time modification when setting the length argument
            actual_length = length_component * pc_note.time_modification[1] / pc_note.time_modification[0] \
                if pc_note.time_modification is not None else length_component
            component_note = MPNote(component_start_time, actual_length, pc_note.pitch, pc_note.volume, notations=[],
                                    articulations=[], notehead=pc_note.notehead, text_annotations=[],
                                    time_modification=pc_note.time_modification)
            # we still set the length_without_tuplet, though
            component_note.length_without_tuplet = length_component

            # Tuplets and Ties
            if component_num == 0 and component_num == len(pc_note.length_without_tuplet) - 1:
                # this is the first and last component, i.e. there is only one component,
                # so tie type is just whatever the pc_note is
                component_note.tie = pc_note.tie
                # and we are free to express either a start or an end tuplet notation
                if pc_note.starts_tuplet:
                    component_note.notations.append(Tuplet("start"))
                if pc_note.ends_tuplet:
                    component_note.notations.append(Tuplet("end"))
            elif component_num == 0:
                # multiple components, of which this is the first
                component_note.tie = "continue" \
                    if pc_note.tie == "stop" or pc_note.tie == "continue" else "start"
                # since we have split pc_notes at the beats, this cannot end a tuplet bracket
                # it can, however have a start tuplet bracket
                if pc_note.starts_tuplet:
                    component_note.notations.append(Tuplet("start"))
            elif component_num == len(pc_note.length_without_tuplet) - 1:
                # multiple components, of which this is the last
                component_note.tie = "continue" \
                    if pc_note.tie == "start" or pc_note.tie == "continue" else "stop"
                # similarly to above...
                if pc_note.ends_tuplet:
                    component_note.notations.append(Tuplet("end"))
            else:
                component_note.tie = "continue"
                # Note that a middle component will never start or end a tuplet bracket

            if component_note.tie is None:
                # this is a note represented by a single notehead, so all notations/articulations apply
                component_note.notations.extend(pc_note.notations)
                component_note.articulations.extend(pc_note.articulations)
                component_note.text_annotations.extend(pc_note.text_annotations)
            elif component_note.tie == "start":
                # this is the beginning of a note with multiple tied noteheads
                component_note.notations.extend([notation for notation in pc_note.notations
                                                 if notation.tag not in notation_locations or
                                                 notation_locations[notation.tag] == "start"])
                component_note.articulations.extend([articulation for articulation in pc_note.articulations
                                                     if articulation.tag not in notation_locations or
                                                     notation_locations[articulation.tag] == "start"])
                component_note.text_annotations.extend(pc_note.text_annotations)
            elif component_note.tie == "stop":
                # this is the end of a note with multiple tied noteheads
                component_note.notations.extend([notation for notation in pc_note.notations
                                                 if notation.tag not in notation_locations or
                                                 notation_locations[notation.tag] == "end"])
                component_note.articulations.extend([articulation for articulation in pc_note.articulations
                                                     if articulation.tag not in notation_locations or
                                                     notation_locations[articulation.tag] == "end"])
            else:
                # this is the middle of a note with multiple tied noteheads
                component_note.notations.extend([notation for notation in pc_note.notations
                                                 if notation.tag not in notation_locations])
                component_note.articulations.extend([articulation for articulation in pc_note.articulations
                                                     if articulation.tag not in notation_locations])

            new_voice.append(component_note)
            component_start_time += actual_length
    return new_voice


def _combine_long_notes_voice_measure(voice_in_measure, beat_start_times):
    i = 0
    while i < len(voice_in_measure):
        start_note = voice_in_measure[i]
        assert isinstance(start_note, MPNote)

        if (start_note.tie in ["start", "continue"] or start_note.pitch is None) \
                and start_note.start_time in beat_start_times and start_note.time_modification is None:
            combining_rests = start_note.pitch is None
            combine_up_to = None
            combined_length = None
            for j in range(i + 1, len(voice_in_measure)):
                if voice_in_measure[j].time_modification is not None:
                    # don't combine using tuplets
                    break
                if combining_rests and voice_in_measure[j].pitch is not None:
                    break
                sum_up = sum(note.length for note in voice_in_measure[i:j + 1])
                if is_single_note_length(sum_up) and (
                        start_note.start_time == beat_start_times[0] or sum_up == int(sum_up)):
                    # TODO: ALLOW DOTTED RHYTHMS ON RELATIVELY INDISPENSABLE BEATS IN UNIFORM MEASURES (AT THE MOMENT, WE'RE ALLOWING THEM ON DOWNBEATS
                    combine_up_to = j
                    combined_length = sum_up
                if not combining_rests and (voice_in_measure[j].tie == "stop" or
                                                    voice_in_measure[j].notehead != start_note.notehead):
                    break
            if combine_up_to is not None:
                if combining_rests:
                    combined_rest = MPNote(
                        start_note.start_time, combined_length, None, None
                    )
                    combined_rest.length_without_tuplet = combined_length
                    voice_in_measure[i:combine_up_to + 1] = [combined_rest]
                else:
                    end_note = voice_in_measure[combine_up_to]
                    assert isinstance(end_note, MPNote)
                    combined_tie = None if start_note.tie == "start" and end_note.tie == "stop" \
                        else ("continue" if start_note.tie == "continue" and end_note.tie == "continue"
                              else ("stop" if end_note.tie == "stop" else "start"))
                    combined_notations = []
                    combined_articulations = []
                    combined_text_annotations = []

                    for pc_note in voice_in_measure[i:combine_up_to + 1]:
                        if pc_note.notations is not None:
                            combined_notations += pc_note.notations
                        if pc_note.articulations is not None:
                            combined_articulations += pc_note.articulations
                        if pc_note.text_annotations is not None:
                            combined_articulations += pc_note.text_annotations

                    combined_note = MPNote(
                        start_note.start_time, combined_length, start_note.pitch, start_note.volume,
                        tie=combined_tie, notations=combined_notations, articulations=combined_articulations,
                        notehead=start_note.notehead, text_annotations=combined_text_annotations
                    )
                    combined_note.length_without_tuplet = combined_length
                    voice_in_measure[i:combine_up_to + 1] = [combined_note]
        i += 1
    return voice_in_measure


def _add_beaming(voice, beat_groups):
    for beat_scheme in beat_groups:
        notes_in_beat = [n for n in voice if beat_scheme.start_time <= n.start_time < beat_scheme.end_time]
        beam_depth = 1
        beam_groups = {}
        while True:
            beam_groups[beam_depth] = []
            beam_group = []
            for note in notes_in_beat:
                # for a given beam depth, go through all the notes in the beat
                if note.pitch is not None and note.get_num_beams() >= beam_depth:
                    # if we have a note that has the requisite number of beams, add to the beam group
                    beam_group.append(note)
                elif len(beam_group) > 0:
                    # otherwise, if we've started a beam group, but we encounter a rest or a note without the
                    # requisite number of beams, then we close up the beam group.
                    beam_groups[beam_depth].append(beam_group)
                    beam_group = []
            if len(beam_group) > 0:
                beam_groups[beam_depth].append(beam_group)
            if len(beam_groups[beam_depth]) == 0:
                del beam_groups[beam_depth]
                break
            beam_depth += 1

        for beam_depth in beam_groups:
            for beam_group in beam_groups[beam_depth]:
                if len(beam_group) == 1:
                    the_note = beam_group[0]
                    assert isinstance(the_note, MPNote)
                    if int(round((the_note.start_time - beat_scheme.start_time) / 0.5 ** beam_depth)) % 2 == 0:
                        the_note.add_beam_layer(beam_depth, "forward hook")
                    else:
                        # This seems like it should be backward hook, but it's displaying badly. wtf?
                        # TODO Figure out wft is going on
                        the_note.add_beam_layer(beam_depth, "end")
                else:
                    for i, note in enumerate(beam_group):
                        if i == 0:
                            note.add_beam_layer(beam_depth, "begin")
                        elif i == len(beam_group) - 1:
                            note.add_beam_layer(beam_depth, "end")
                        else:
                            note.add_beam_layer(beam_depth, "continue")

        # for singleton notes, get rid of the beams; better to just leave as a
        # flag than have a bunch of hooked beams going nowhere
        for note in notes_in_beat:
            if note.beams is not None:
                has_non_hook = False
                for beam_depth in note.beams:
                    if "hook" not in note.beams[beam_depth]:
                        has_non_hook = True
                        break
                if not has_non_hook:
                    # all the beam layers are just hooks for this note, so it is an isolated note.
                    # This means it should just have flags, no beams
                    note.beams = None

    return voice


def get_average_pitch(notes_list):
    total_pitch = 0.0
    num_notes = 0
    for pc_note in notes_list:
        if pc_note.pitch is not None:
            # not a rest
            if isinstance(pc_note.pitch, (tuple, list)):
                # a chord
                total_pitch += float(sum(pc_note.pitch)) / len(pc_note.pitch)
            else:
                total_pitch += pc_note.pitch
            num_notes += 1
    return total_pitch / num_notes


def get_most_appropriate_clef(notes_list):
    if get_average_pitch(notes_list) > 60:
        return "treble"
    else:
        return "bass"


def get_pitch_bend_text(deviation_in_dollars):
    # where dollars = cents/100
    return "~B0,{}".format(int(round(deviation_in_dollars*32)) + 64)