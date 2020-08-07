

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  SCAMP (Suite for Computer-Assisted Music in Python)                                           #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

def _separate_voices_into_measures(quantized_performance_part: PerformancePart):
    """
    Separates the voices of a performance part into a list of measure bins containing chunks of those voices
    :param quantized_performance_part: a PerformancePart that has been quantized
    :return: a list of measure bins, each of which is a dictionary from voice names to tuples of
    (notes in that measure for that voice, QuantizedMeasure for that measure for that voice)
    """
    # each entry is a dictionary of the form {voice name: voice notes in this measure}
    measure_bins = []

    # look within the start and end beat of each measure
    for voice_name in quantized_performance_part.voices:
        measure_start = 0
        voice = deepcopy(quantized_performance_part.voices[voice_name])
        voice_quantization_record = quantized_performance_part.voice_quantization_records[voice_name]
        for measure_num, quantized_measure in enumerate(voice_quantization_record.quantized_measures):
            measure_end = measure_start + quantized_measure.measure_length

            # make sure we have a bin for this measure
            while measure_num >= len(measure_bins):
                measure_bins.append({})
            this_measure_bin = measure_bins[measure_num]

            # we wish to isolate just the notes of this voice that would fit in this measure
            measure_voice = []
            # for each note in the voice that starts in this measure
            while len(voice) > 0 and voice[0].start_time < measure_end:
                # if the end time of the note is after the end of the measure, we need to split it
                if voice[0].end_time > measure_end:
                    first_part, second_part = _split_performance_note_at_beat(voice[0], measure_end)
                    measure_voice.append(first_part)
                    voice[0] = second_part
                else:
                    measure_voice.append(voice.pop(0))
            if len(measure_voice) > 0:
                this_measure_bin[voice_name] = measure_voice, quantized_measure

            measure_start = measure_end

    return measure_bins


def _voice_dictionary_to_list(voice_dictionary):
    """
    Takes a dictionary from voice name to (voice notes, voice quantization) tuples and returns a list of ordered voices.
    Voices with numbers as names are assigned that voice number. Others are sorted by average pitch.
    :rtype: list of voices, each of which is a tuple of (list of PerformanceNotes, quantization)
    """
    # start out by making a list of all of the named (not numbered) voices
    voice_list = [voice_dictionary[voice_name] for voice_name in voice_dictionary if not voice_name.isdigit()]
    # sort them by their average pitch. (Call average_pitch on each note, since it might be a gliss or chord)
    # note that voice[0] is the first part of the (list of PerformanceNotes, quantization) tuple, so the notes
    voice_list.sort(key=lambda voice: sum(n.average_pitch() for n in voice[0])/len(voice[0]))

    # now we insert all the numbered voices in the correct spot in the list
    numbered_voice_names = [x for x in voice_dictionary.keys() if x.isdigit()]
    numbered_voice_names.sort(key=lambda name: int(name))
    for numbered_voice_name in numbered_voice_names:
        voice_number = int(numbered_voice_name)
        if (voice_number - 1) < len(voice_list):
            voice_list.insert(voice_number, voice_dictionary[numbered_voice_name])
        else:
            # insert dummy voices if necessary
            voice_list.extend([None] * (voice_number - 1 - len(voice_list)))
            voice_list.append(voice_dictionary[numbered_voice_name])
    return voice_list