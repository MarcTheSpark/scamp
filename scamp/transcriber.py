"""Module containing the :class:`Transcriber` class which records the playback of a group of
:class:`~scamp.instruments.ScampInstrument` objects to create a :class:`~scamp.performance.Performance`"""

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
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

from .performance import Performance
from expenvelope import Envelope
from clockblocks import Clock, TempoEnvelope
from .instruments import ScampInstrument
from typing import Union, Sequence


class Transcriber:
    """
    Class responsible for transcribing notes played by instruments into a :class:`~scamp.performance.Performance`.
    It is possible to run multiple transcriptions simultaneously, for instance starting at different times,
    recording different instruments, or recording relative to different clocks.
    """

    def __init__(self):
        self._transcriptions_in_progress = []

    def start_transcribing(self, instrument_or_instruments: Union[ScampInstrument, Sequence[ScampInstrument]],
                           clock: Clock, units: str = "beats") -> Performance:
        """
        Starts transcribing new performance on the given clock, consisting of the given instrument

        :param instrument_or_instruments: the instruments we notate in this Performance
        :param clock: which clock all timings are relative to
        :param units: one of ["beats", "time"]. Do we use the beats of the clock or the time?
        :return: the Performance that this transcription writes to, which will be updated as notes are played and acts
            as a handle when calling stop_transcribing.
        """
        assert units in ("beats", "time")

        if not hasattr(instrument_or_instruments, "__len__"):
            instrument_or_instruments = [instrument_or_instruments]

        if len(instrument_or_instruments) == 0:
            raise ValueError("No instruments specified for transcription!")

        performance = Performance()
        for instrument in instrument_or_instruments:
            performance.new_part(instrument)
            if self not in instrument._transcribers_to_notify:
                instrument._transcribers_to_notify.append(self)

        self._transcriptions_in_progress.append(
            (performance, clock, clock.beat(), units)
        )

        return performance

    def register_note(self, instrument: ScampInstrument, note_info: dict) -> None:
        """
        Called when an instrument wants to register that it finished a note, records note in all transcriptions

        :param instrument: the ScampInstrument that played the note
        :param note_info: the note info dictionary on that note, containing time stamps, parameter changes, etc.
        """
        assert note_info["end_time_stamp"] is not None, "Cannot register unfinished note!"
        param_change_segments = note_info["parameter_change_segments"]

        if note_info["start_time_stamp"].time_in_master == note_info["end_time_stamp"].time_in_master:
            return

        # loop through all the transcriptions in progress
        for performance, clock, clock_start_beat, units in self._transcriptions_in_progress:
            # figure out the start_beat and length relative to this transcription's clock and start beat
            start_beat_in_clock = Transcriber._resolve_time_stamp(note_info["start_time_stamp"], clock, units)
            end_beat_in_clock = Transcriber._resolve_time_stamp(note_info["end_time_stamp"], clock, units)

            note_start_beat = start_beat_in_clock - clock_start_beat
            note_length = end_beat_in_clock - start_beat_in_clock

            # handle split points (if applicable) by creating a note length sections tuple
            note_length_sections = None
            if len(note_info["split_points"]) > 0:
                note_length_sections = []
                last_split = note_start_beat
                for split_point in note_info["split_points"]:
                    split_point_beat = Transcriber._resolve_time_stamp(split_point, clock, units)
                    note_length_sections.append(split_point_beat - last_split)
                    last_split = split_point_beat
                if end_beat_in_clock > last_split:
                    note_length_sections.append(end_beat_in_clock - last_split)
                note_length_sections = tuple(note_length_sections)

            # get curves for all the parameters
            extra_parameters = {}
            for param in note_info["parameter_start_values"]:
                if param in param_change_segments and len(param_change_segments[param]) > 0:
                    levels = [note_info["parameter_start_values"][param]]
                    # keep track of this in case of gaps between segments
                    beat_of_last_level_recorded = start_beat_in_clock
                    durations = []
                    curve_shapes = []
                    for param_change_segment in param_change_segments[param]:
                        # no need to transcribe a param_change_segment that was aborted immediately
                        if param_change_segment.duration == 0 and \
                                param_change_segment.end_level == param_change_segment.start_level:
                            continue

                        param_start_beat_in_clock = Transcriber._resolve_time_stamp(
                            param_change_segment.start_time_stamp, clock, units)
                        param_end_beat_in_clock = Transcriber._resolve_time_stamp(
                            param_change_segment.end_time_stamp, clock, units)

                        # if there's a gap between the last level we recorded and this segment, we need to fill it with
                        # a flat segment that holds the last level recorded
                        if param_start_beat_in_clock > beat_of_last_level_recorded:
                            durations.append(param_start_beat_in_clock - beat_of_last_level_recorded)
                            levels.append(levels[-1])
                            curve_shapes.append(0)

                        durations.append(param_end_beat_in_clock - param_start_beat_in_clock)
                        levels.append(param_change_segment.end_level)
                        curve_shapes.append(param_change_segment.curve_shape)

                        beat_of_last_level_recorded = param_end_beat_in_clock

                    # again, if we end the curve early, then we need to add a flat filler segment
                    if beat_of_last_level_recorded < note_start_beat + note_length:
                        durations.append(note_start_beat + note_length - beat_of_last_level_recorded)
                        levels.append(levels[-1])
                        curve_shapes.append(0)

                    # assign to specific variables for pitch and volume, otherwise put in a dictionary of extra params
                    if param == "pitch":
                        # note that if the length of levels is 1, then there's been no meaningful animation
                        # so just act like it's not animated. This probably shouldn't really come up. (It was
                        # coming up before with zero-length notes, but now those are just skipped anyway.)
                        if len(levels) == 1:
                            pitch = levels[0]
                        else:
                            pitch = Envelope(levels, durations, curve_shapes)
                    elif param == "volume":
                        if len(levels) == 1:
                            volume = levels[0]
                        else:
                            volume = Envelope(levels, durations, curve_shapes)
                    else:
                        if len(levels) == 1:
                            extra_parameters[param] = levels[0]
                        else:
                            extra_parameters[param] = Envelope(levels, durations, curve_shapes)
                else:
                    # assign to specific variables for pitch and volume, otherwise put in a dictionary of extra params
                    if param == "pitch":
                        pitch = note_info["parameter_start_values"]["pitch"]
                    elif param == "volume":
                        volume = note_info["parameter_start_values"]["volume"]
                    else:
                        extra_parameters[param] = note_info["parameter_start_values"][param]

            for instrument_part in performance.get_parts_by_instrument(instrument):
                # it'd be kind of weird for more than one part to have the same instrument, but if they did,
                # I suppose that each part should transcribe the note
                instrument_part.new_note(
                    note_start_beat, note_length_sections if note_length_sections is not None else note_length,
                    pitch, volume, note_info["properties"]
                )

    @staticmethod
    def _resolve_time_stamp(time_stamp, clock, units):
        assert units in ("beats", "time")
        return time_stamp.beat_in_clock(clock) if units == "beats" else time_stamp.time_in_clock(clock)

    def stop_transcribing(self, which_performance=None, tempo_envelope_tolerance=0.001) -> Performance:
        """
        Stops transcribing a Performance and returns it. Defaults to the oldest started performance, unless
        otherwise specified.

        :param which_performance: which performance to stop transcribing; defaults to oldest started
        :param tempo_envelope_tolerance: error tolerance when extracting the absolute tempo envelope for the Performance
        :return: the created Performance
        """
        transcription = None
        if which_performance is None:
            if len(self._transcriptions_in_progress) == 0:
                raise ValueError("Cannot stop transcribing performance, as none has been started!")
            transcription = self._transcriptions_in_progress.pop(0)
        else:
            for i, transcription in enumerate(self._transcriptions_in_progress):
                if transcription[0] == which_performance:
                    transcription = self._transcriptions_in_progress.pop(i)
                    break
            if transcription is None:
                raise ValueError("Cannot stop transcribing given performance, as it was never started!")

        transcribed_performance, transcription_clock, transcription_start_beat, units = transcription
        if units == "beats":
            transcribed_performance.tempo_envelope = transcription_clock.extract_absolute_tempo_envelope(
                transcription_start_beat, tolerance=tempo_envelope_tolerance
            )
        elif transcription_clock.is_master():
            # transcribing based on master time, so there can't be any tempo changes; just use a blank TempoEnvelope
            transcribed_performance.tempo_envelope = TempoEnvelope()
        else:
            transcribed_performance.tempo_envelope = transcription_clock.parent.extract_absolute_tempo_envelope(
                transcription_start_beat, tolerance=tempo_envelope_tolerance
            )
        return transcribed_performance
