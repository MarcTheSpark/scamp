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

from __future__ import annotations
from .performance import Performance
from expenvelope import Envelope
from cb2 import Clock, TempoEnvelope, TimeStamp
from cb2.utilities import meaningfully_less_than, meaningfully_greater_than
from .instruments import ScampInstrument
from typing import Sequence


class Transcriber:
    """
    Class responsible for transcribing notes played by instruments into a :class:`~scamp.performance.Performance`.
    It is possible to run multiple transcriptions simultaneously, for instance starting at different times,
    recording different instruments, or recording relative to different clocks.
    """

    def __init__(self):
        self._transcriptions_in_progress = []

    @property
    def transcriptions_in_progress(self) -> tuple[Performance]:
        """Tuple of all current transcriptions."""
        return tuple(self._transcriptions_in_progress)

    def is_transcribing(self) -> bool:
        """Checks if any transcriptions are in progress."""
        return len(self._transcriptions_in_progress) > 0

    def start_transcribing(self, instrument_or_instruments: ScampInstrument | Sequence[ScampInstrument],
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

        # Hold the scheduler quiescent so that, if called from a foreign thread (e.g. a pygame event
        # handler), a concurrently-firing scheduled action can't observe a half-registered
        # transcription. Safe from any thread — see Clock.while_scheduler_quiescent.
        with clock.while_scheduler_quiescent():
            self._transcriptions_in_progress.append(
                (performance, clock, TimeStamp.now(clock), units)
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
        start_stamp = note_info["start_time_stamp"]
        end_stamp = note_info["end_time_stamp"]

        if start_stamp.time_in_master == end_stamp.time_in_master:
            return

        # loop through all the transcriptions in progress
        for performance, clock, transcription_start_stamp, units in self._transcriptions_in_progress:
            # To recover the note start beat and length in this transcription's clock, first subtract (from the
            # transcription start time stamp and from each other), and then resolve the resulting TimeStampInterval
            # to beats in the transcription clock.
            note_start_beat = Transcriber._resolve_interval(start_stamp - transcription_start_stamp, clock, units)
            note_length = Transcriber._resolve_interval(end_stamp - start_stamp, clock, units)

            # handle split points (if applicable) by creating a note length sections tuple
            note_length_sections = None
            if len(note_info["split_points"]) > 0:
                note_length_sections = []
                last_split_stamp = start_stamp
                for split_point in note_info["split_points"]:
                    note_length_sections.append(
                        Transcriber._resolve_interval(split_point - last_split_stamp, clock, units))
                    last_split_stamp = split_point
                # tolerant comparison on absolute beats (whose reconstruction noise scales with magnitude) so a
                # negligible final sliver isn't recorded as its own section
                if meaningfully_greater_than(Transcriber._resolve_time_stamp(end_stamp, clock, units),
                                             Transcriber._resolve_time_stamp(last_split_stamp, clock, units)):
                    # Note: this actually redundantly double converts the times stamps to beats,
                    # first in the if condition, and then if it passes, in _resolve_interval. But it's
                    # cleaner and easier to read this way, and we don't want to convert to the length
                    # in beats first and check > 0 because that's a less tolerant absolute comparison
                    note_length_sections.append(
                        Transcriber._resolve_interval(end_stamp - last_split_stamp, clock, units)
                    )
                note_length_sections = tuple(note_length_sections)

            # get curves for all the parameters
            extra_parameters = {}
            for param in note_info["parameter_start_values"]:
                if param in param_change_segments and len(param_change_segments[param]) > 0:
                    levels = [note_info["parameter_start_values"][param]]
                    # the stamp of the last level we recorded, for filling gaps between segments
                    last_level_stamp = start_stamp
                    durations = []
                    curve_shapes = []
                    for param_change_segment in param_change_segments[param]:
                        # no need to transcribe a param_change_segment that was aborted immediately
                        if param_change_segment.duration == 0 and \
                                param_change_segment.end_level == param_change_segment.start_level:
                            continue

                        param_start_stamp = param_change_segment.start_time_stamp
                        param_end_stamp = param_change_segment.end_time_stamp

                        # if there's a gap between the last level we recorded and this segment, fill it with a flat
                        # segment holding the last level. Tolerant absolute-beat comparison (these beats carry
                        # root-finding noise that scales with magnitude, so a bare ">" would spuriously insert a
                        # negligible filler segment); the recorded duration itself is a snapped TimeStampInterval.
                        if meaningfully_greater_than(
                                Transcriber._resolve_time_stamp(param_start_stamp, clock, units),
                                Transcriber._resolve_time_stamp(last_level_stamp, clock, units)):
                            durations.append(
                                Transcriber._resolve_interval(param_start_stamp - last_level_stamp, clock, units))
                            levels.append(levels[-1])
                            curve_shapes.append(0)

                        durations.append(
                            Transcriber._resolve_interval(param_end_stamp - param_start_stamp, clock, units))
                        levels.append(param_change_segment.end_level)
                        curve_shapes.append(param_change_segment.curve_shape)

                        last_level_stamp = param_end_stamp

                    # again, if the curve ends before the note does, add a flat filler segment out to the note end
                    # (same tolerant-comparison rationale as the gap-fill above)
                    if meaningfully_less_than(Transcriber._resolve_time_stamp(last_level_stamp, clock, units),
                                              Transcriber._resolve_time_stamp(end_stamp, clock, units)):
                        durations.append(
                            Transcriber._resolve_interval(end_stamp - last_level_stamp, clock, units))
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

    @staticmethod
    def _resolve_interval(interval, clock, units):
        # A TimeStampInterval projected into `clock`, in the transcription's units; snaps the difference of its
        # endpoints to a nice decimal (see cb2.TimeStampInterval).
        assert units in ("beats", "time")
        return interval.beats_duration_in_clock(clock) if units == "beats" else interval.time_duration_in_clock(clock)

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

        transcribed_performance, transcription_clock, transcription_start_stamp, units = transcription
        # the transcription start is now stored as a TimeStamp; resolve it to a beat for tempo extraction
        transcription_start_beat = transcription_start_stamp.beat_in_clock(transcription_clock)
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
