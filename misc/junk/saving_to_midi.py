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

# ---------------------------------------- SAVING TO MIDI ----------------------------------------------
# TODO: Fix this pile of crap

@staticmethod
def get_good_tempo_choice(pc_note_list, max_tempo=200, max_tempo_to_divide_to=300, goal_tempo=80):
    min_beat_length = 60.0 / max_tempo_to_divide_to
    total_length = max([(pc_note.start_time + pc_note.length) for pc_note in pc_note_list])
    divisor = 1

    best_beat_length = None
    best_error = float("inf")
    while total_length / divisor >= min_beat_length:
        beat_length = total_length / divisor
        total_squared_error = 0.0
        for pc_note in pc_note_list:
            total_squared_error += \
                (pc_note.start_time - round_to_multiple(pc_note.start_time, beat_length / 4.0)) ** 2

        total_squared_error *= (abs((60.0 / beat_length) - goal_tempo) / 50 + 1.0)
        if total_squared_error < best_error:
            best_error = total_squared_error
            best_beat_length = beat_length
        divisor += 1

    best_tempo = 60 / best_beat_length
    while best_tempo > max_tempo:
        best_tempo /= 2
    return best_tempo


# TODO: Be able to add time signatures at any point, tempo changes at any point
def save_to_midi_file(self, file_name, tempo=60, beat_length=1.0, divisions=8, max_indigestibility=4,
                      simplicity_preference=0.5, beat_max_overlap=0.01, quantize=True,
                      round_pitches=True, guess_tempo=False):
    if guess_tempo:
        flattened_recording = make_flat_list(
            [part.recording for part in self.parts_recorded]
        )
        tempo = Playcorder.get_good_tempo_choice(flattened_recording)

    if quantize:
        beat_scheme = BeatQuantizationScheme(
            tempo, beat_length, divisions=divisions, max_indigestibility=max_indigestibility,
            simplicity_preference=simplicity_preference
        )

        parts = [separate_into_non_overlapping_voices(
            quantize_recording(part.recording, [beat_scheme])[0], beat_max_overlap
        ) for part in self.parts_recorded]
    else:
        parts = [separate_into_non_overlapping_voices(
            part.recording, beat_max_overlap
        ) for part in self.parts_recorded]

    midi_file = MIDIFile(sum([len(x) for x in parts]), adjust_origin=False)

    current_track = 0
    for which_part, part in enumerate(parts):
        current_voice = 0
        for voice in part:
            midi_file.addTrackName(current_track, 0,
                                   self.parts_recorded[which_part].name + " " + str(current_voice + 1))
            midi_file.addTempo(current_track, 0, tempo)

            for pc_note in voice:
                assert isinstance(pc_note, PCNote)
                pitch_to_notate = int(round(pc_note.pitch)) if round_pitches else pc_note.pitch
                midi_file.addNote(current_track, 0, pitch_to_notate, pc_note.start_time,
                                  pc_note.length, int(pc_note.volume * 127))
            current_track += 1
            current_voice += 1

    bin_file = open(file_name, 'wb')
    midi_file.writeFile(bin_file)
    bin_file.close()