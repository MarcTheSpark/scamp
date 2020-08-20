"""
Module containing the abstract base class :class:`PlaybackImplementation`, as well as several of its concrete
subclasses: :class:`SoundfontPlaybackImplementation`, :class:`MidiPlaybackImplementations`, and
:class:`OSCPlaybackImplementation`. :class:`PlaybackImplementations` do the actual work of playback, either by
playing sounds or by sending messages to external synthesizers to play sounds.
A :class:`~scamp.instruments.ScampInstrument` can have one or more :class:`PlaybackImplementations`.
"""

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

from ._midi import SimpleRtMidiOut
from ._soundfont_host import SoundfontHost
from . import instruments as instruments_module
from clockblocks import fork_unsynchronized
import time
from abc import abstractmethod
import atexit
from ._dependencies import pythonosc
from typing import Tuple, Optional
import logging
from .settings import playback_settings
from .utilities import SavesToJSON, SavesToJSONMeta


class _PlaybackImplementationMeta(SavesToJSONMeta):

    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        instance._try_to_bind_host_instrument()
        return instance


class PlaybackImplementation(SavesToJSON, metaclass=_PlaybackImplementationMeta):

    """
    Abstract base class for playback implementations, which do the actual work of playback, either by playing sounds or
    by sending messages to external synthesizers to play sounds.

    :param host_instrument: The :class:`~scamp.instruments.ScampInstrument` that will use this playback implementation
        for playback. When this PlaybackImplementation is constructed, it is automatically added to the list of
        PlaybackImplementations that the host instrument uses.
    """

    def __init__(self, host_instrument: 'instruments_module.ScampInstrument'):
        # this is a fallback: if the instrument does not belong to an ensemble, it does not have
        # shared resources and so it will rely on its own privately held resources.
        self._resources = None
        self._host_instrument = host_instrument
        # This are set when the host instrument is set
        self._note_info_dict = None

    def _try_to_bind_host_instrument(self):
        if self._host_instrument is not None:
            self.set_host_instrument(self._host_instrument)

    def set_host_instrument(self, host_instrument: 'instruments_module.ScampInstrument'):
        """
        Sets the host instrument for this PlaybackImplementation. Ordinarily, the host instrument is supplied as an
        argument to the `__init__` method, which then automatically calls this method. However, it is also possible
        to pass the value None to the host instrument argument initially and later set it with this method.

        :param host_instrument: The :class:`~scamp.instruments.ScampInstrument` that will use this playback
            implementation for playback. This PlaybackImplementation will be added to the host instrument's
            `playback_implementations` attribute.
        """
        # these get populated when the PlaybackImplementation is registered
        self._host_instrument = host_instrument
        self._note_info_dict = host_instrument._note_info_by_id
        if self not in host_instrument.playback_implementations:
            host_instrument.playback_implementations.append(self)
        self._initialize_shared_resources()

    def _initialize_shared_resources(self):
        """
        Called right after this PlaybackImplementation has been attached to a host instrument. Any initialization that
        relies upon setting and accessing shared ensemble resources needs to happen here.
        If a host instrument is passed to the constructor, this will happen at the end of the PlaybackImplementation
        constructor; otherwise it will happen when :func:`set_host_instrument` is called.
        """
        pass

    """
    Methods for storing and accessing shared resources for the ensemble. 
    """

    @property
    def resource_dictionary(self) -> dict:
        """
        Dictionary of shared resources for this type of playback implementation.
        For instance, SoundfontPlaybackImplementation uses this to store an instance of SoundfontHost. Only one
        instance of fluidsynth (and therefore SoundfontHost) needs to be running for all instruments in the ensemble,
        so this is a way of pooling that resource.
        """
        if self._host_instrument is None:
            raise RuntimeError("PlaybackImplementation was never attached to a host instrument. "
                               "Cannot access resources.")
        if self._host_instrument.ensemble is None:
            # if this instrument is not part of an ensemble, it can't really have shared resources
            # instead, it creates a local resources dictionary and uses that
            if self._resources is None:
                self._resources = {}
            return self._resources
        else:
            # if this instrument is part of an ensemble, that ensemble holds the shared resources for all the
            # different playback implementations. Each playback implementation type has its own resource dictionary,
            # stored with its type as a key in the ensemble's shared resources dictionary. This way there can't be
            # name conflicts between different playback implementations
            if type(self) not in self._host_instrument.ensemble.shared_resources:
                self._host_instrument.ensemble.shared_resources[type(self)] = {}
            return self._host_instrument.ensemble.shared_resources[type(self)]

    def has_shared_resource(self, key) -> bool:
        """
        Checks whether there is a shared resource for this type of playback implementation under the given key.

        :param key: key name for this resource
        """
        return key in self.resource_dictionary

    def get_shared_resource(self, key):
        """
        Gets the shared resource for this type of playback implementation under the given key.

        :param key: key name for this resource
        """
        return None if key not in self.resource_dictionary else self.resource_dictionary[key]

    def set_shared_resource(self, key, value):
        """
        Sets a shared resource for this type of playback implementation under the given key.

        :param key: key name for this resource
        :param value: value to set for that key
        """
        self.resource_dictionary[key] = value

    """
    The actual abstract methods to override in creating a new PlaybackImplementation
    """

    @abstractmethod
    def start_note(self, note_id: int, pitch: float, volume: float, properties: dict,
                   other_parameter_values: dict = None) -> None:
        """
        Method that implements the start of a note

        :param note_id: unique identifier for the note we are starting
        :param pitch: floating-point MIDI pitch value
        :param volume: floating-point volume value (from 0 to 1)
        :param properties: a NotePropertiesDictionary
        :param other_parameter_values: dictionary mapping parameter name to parameter value for parameters other than
            pitch and volume. (This information was extracted from the properties dictionary.)
        """
        pass

    @abstractmethod
    def end_note(self, note_id: int) -> None:
        """
        Method that implements the end of a note

        :param note_id: unique identifier of the note to end
        """
        pass

    @abstractmethod
    def change_note_pitch(self, note_id: int, new_pitch: float) -> None:
        """
        Method that implements the change of a note's pitch

        :param note_id: unique identifier of the note whose pitch to change
        :param new_pitch: new (floating-point) MIDI pitch value
        """
        pass

    @abstractmethod
    def change_note_volume(self, note_id: int, new_volume: float) -> None:
        """
        Method that implements the change of a note's volume

        :param note_id: unique identifier of the note whose volume to change
        :param new_volume: new floating point volume value from 0 to 1
        """
        pass

    @abstractmethod
    def change_note_parameter(self, note_id: int, parameter_name: str, new_value: float) -> None:
        """
        Method that implements the change of a parameter other than pitch or volume

        :param note_id: unique identifier of the note to effect
        :param parameter_name: name of the parameter to change
        :param new_value: new floating-point value of that parameter
        """
        pass

    @abstractmethod
    def set_max_pitch_bend(self, semitones: int) -> None:
        """
        Method that sets the max pitch bend for MIDI-based playback implementations
        This is only relevant when playback is happening via the MIDI protocol.

        :param semitones: unique identifier of the note to effect
        """
        pass


class _MIDIPlaybackImplementation(PlaybackImplementation):

    """
    This is the abstract base class for playback implementations that use the MIDI protocol.
    It handles all of the channel management nonsense so that that pitch bends don't conflict with
    one another, and that kind of thing, exposing the more basic note_on/note_off abstract methods
    to be overridden.

    :param host_instrument: The ScampInstrument that will use this playback implementation for playback. When this
        PlaybackImplementation is constructed, it is automatically added to the list of PlaybackImplementations that
        the host instrument uses.
    :param num_channels: how many MIDI channels to use for this instrument. Where channel-wide messages (such as
        pitch-bend messages) are involved, it is essential to have several channels at our disposal.
    :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or other
        cc messages. Valuable when using :code:`start_note` instead of :code:`play_note` in music that doesn't do any
        dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on separate MIDI channels,
        since they could potentially change pitch or volume; with this flags, we know they won't, so they can share
        the same MIDI channels, only using an extra one due to microtonality.
    """

    def __init__(self, host_instrument: 'instruments_module.ScampInstrument' = None, num_channels: int = 8,
                 note_on_and_off_only: bool = False):
        super().__init__(host_instrument)
        self.note_on_and_off_only = note_on_and_off_only
        self.num_channels = num_channels
        self.ringing_notes = []
    # -------------------------- Abstract methods to be implemented by subclasses--------------

    @abstractmethod
    def note_on(self, chan: int, pitch: int, velocity_from_0_to_1: float) -> None:
        """
        Sends a note_on MIDI message

        :param chan: channel to send message on
        :param pitch: integer MIDI pitch value
        :param velocity_from_0_to_1: velocity to send (NB: scaled from 0 to 1)
        """
        pass

    @abstractmethod
    def note_off(self, chan: int, pitch: int) -> None:
        """
        Sends a note_off MIDI message

        :param chan: channel to send message on
        :param pitch: integer MIDI pitch value
        """
        pass

    @abstractmethod
    def pitch_bend(self, chan: int, bend_in_semitones: float) -> None:
        """
        Sends a MIDI pitch bend message

        :param chan: channel to send message on
        :param bend_in_semitones: the pitch bend amount (in semitones!)
        """
        pass

    @abstractmethod
    def set_max_pitch_bend(self, max_bend_in_semitones: int) -> None:
        """
        Sets the max pitch bend for this MIDI device

        :param max_bend_in_semitones: value to set as maximum pitch bend
        """
        pass

    @abstractmethod
    def expression(self, chan, expression_from_0_to_1) -> None:
        """
        Sends a midi expression message

        :param chan: channel to send message on
        :param expression_from_0_to_1: expression to send (NB: scaled from 0 to 1)
        :return:
        """
        pass

    @abstractmethod
    def cc(self, chan: int, cc_number: int, value_from_0_to_1: float) -> None:
        """
        Sends an arbitrary midi CC message

        :param chan: channel to send the message on
        :param cc_number: number representing the type of the control change message
        :param value_from_0_to_1: value to send (NB: scaled from 0 to 1)
        """

    # -------------------------------- Main Playback Methods --------------------------------

    def start_note(self, note_id, pitch, volume, properties, other_parameter_values: dict = None):
        other_parameter_cc_codes = [int(key) for key in other_parameter_values.keys()
                                    if key.isdigit() and 0 <= int(key) < 128]
        this_note_info = self._note_info_dict[note_id]
        this_note_fixed = "fixed" in this_note_info["flags"] or self.note_on_and_off_only
        if this_note_fixed:
            this_note_info["max_volume"] = volume
        int_pitch = int(round(pitch))

        # make a list of available channels to add this note to that won't cause pitch bend / expression conflicts
        available_channels = list(range(self.num_channels))
        oldest_note_id = None

        # go through all currently active notes
        for other_note_id, other_note_info in self._note_info_dict.items():
            # check that this other note has been handled by this playback implementation (for instance, a silent
            # note will be skipped, since it was never passed to the playback implementations). Also check that it
            # hasn't been prematurely ended.
            if self in other_note_info and not other_note_info[self]["prematurely_ended"]:
                other_note_channel = other_note_info[self]["channel"]
                other_note_fixed = "fixed" in other_note_info["flags"]
                other_note_pitch = other_note_info["parameter_values"]["pitch"]
                other_note_int_pitch = other_note_info[self]["midi_note"]
                # this new note only share a midi channel with the old note if:
                #   1) both notes are fixed (i.e. will not do a pitch or expression change, which is channel-wide)
                #   2) the notes aren't on the same midi key (since a note off in one would affect the other)
                #   3) the notes don't have conflicting microtonality (i.e. one or both need a pitch bend, and it's
                # not the exact same pitch bend.)
                conflicting_microtonality = (pitch != int_pitch or other_note_pitch != other_note_int_pitch) and \
                                            (round(pitch - int_pitch, 5) !=  # round to fix float error
                                             round(other_note_pitch - other_note_int_pitch, 5))

                # now we check if there are any conflicting cc messages, since these are also channel-wide
                conflicting_cc_codes = False
                # first figure out which, if any, cc codes the other note is using, and then which both are using
                other_note_used_cc_codes = [int(key) for key in other_note_info["parameter_values"].keys()
                                            if key.isdigit() and 0 <= int(key) < 128]
                if len(other_parameter_cc_codes) + len(other_parameter_cc_codes) > 0:
                    # if either note is using a cc code, we need to check that they are compatible
                    if set(other_parameter_cc_codes) == set(other_note_used_cc_codes):
                        # it's only possible to be compatible if both notes use the exact same cc numbers and have the
                        # same values for those cc numbers. Otherwise there may be unwanted side effects
                        for cc_code in other_parameter_cc_codes:
                            param = str(cc_code)
                            if other_note_info["parameter_values"][param] != other_parameter_values[param]:
                                conflicting_cc_codes = True
                                break
                    else:
                        conflicting_cc_codes = True

                channel_compatible = this_note_fixed and other_note_fixed and not conflicting_microtonality \
                                     and int_pitch != other_note_int_pitch and not conflicting_cc_codes
                if not channel_compatible:
                    if other_note_channel in available_channels:
                        available_channels.remove(other_note_channel)
                    # keep track of the oldest note that's holding onto a channel
                    if oldest_note_id is None or other_note_id < oldest_note_id:
                        oldest_note_id = other_note_id

        # go through all ringing notes, and remove those channels if not compatible
        # this means a note that has ended, which was microtonal, and which may still be ringing
        for ringing_channel, ringing_midi_note, ringing_pitch in self.ringing_notes:
            conflicting_microtonality = (pitch != int_pitch or ringing_midi_note != ringing_pitch) and \
                                        (round(pitch - int_pitch, 5) !=  # round to fix float error
                                         round(ringing_pitch - ringing_midi_note, 5))
            # Note that here, unlike above, there's no need to check if the other note is fixed, since it's done
            # and just ringing. Also, it's okay if the other note is of the same pitch, since the note_off message
            # has already been sent.
            channel_compatible = this_note_fixed and not conflicting_microtonality
            if not channel_compatible and ringing_channel in available_channels:
                available_channels.remove(ringing_channel)

        # pick the first free channel, or free one up if there are no free channels
        if len(available_channels) > 0:
            # if there's a free channel, return the lowest number available
            channel = available_channels[0]
        elif len(self.ringing_notes) > 0:
            # if we avoided any channels because they have ringing microtonal pitches, we turn to those first
            channel, _, _ = self.ringing_notes.pop(0)
        else:
            # otherwise, we'll have to kill an old note to find a free channel
            # get the info we stored on this note, related to this specific playback implementation
            # (see end of start_note method for explanation)
            oldest_note_info = self._note_info_dict[oldest_note_id][self]
            self.note_off(oldest_note_info["channel"], oldest_note_info["midi_note"])
            # flag it as prematurely ended so that we send no further midi commands
            oldest_note_info["prematurely_ended"] = True
            # if every channel is playing this pitch, we will end the oldest note so we can
            channel = oldest_note_info["channel"]

        self._prep_channel(
            channel, pitch, volume / this_note_info["max_volume"] if this_note_info["max_volume"] > 0 else 0,
            other_parameter_cc_codes, other_parameter_values
        )
        self.note_on(channel, int_pitch, this_note_info["max_volume"])

        # store the midi note that we pressed for this note, the channel we pressed it on, and make an entry
        # initially false) for whether or not we ended this note prematurely (to free up a channel for a newer
        # note). Note that we're creating here a dictionary within the note_info dictionary, using this
        # PlaybackImplementation instance as the key. This way, there can never be conflict between data
        # stored by this PlaybackImplementation and data stored by other PlaybackImplementations
        this_note_info[self] = {
            "midi_note": int_pitch,
            "channel": channel,
            "prematurely_ended": False
        }

    def _prep_channel(self, channel, pitch, expression, other_parameter_cc_codes, other_parameter_values):
        """
        Preps the channel before a note_on call by setting the appropriate pitch, expression, cc codes.
        """
        int_pitch = int(round(pitch))
        # start the note on that channel by first setting pitch bend and expression and then sending a note on
        if pitch != int_pitch:
            self.pitch_bend(channel, pitch - int_pitch)
        else:
            self.pitch_bend(channel, 0)

        if not self.note_on_and_off_only:
            # start it at the max volume that it will ever reach, and use expression to get to the start volume
            self.expression(channel, expression)
            for cc_code in other_parameter_cc_codes:
                self.cc(channel, cc_code, other_parameter_values[str(cc_code)])

    def end_note(self, note_id):
        this_note_info = self._note_info_dict[note_id]
        assert self in this_note_info, "Note was never started by the SoundfontPlaybackImplementer; this is bad."
        this_note_implementation_info = this_note_info[self]
        if not this_note_implementation_info["prematurely_ended"]:
            self.note_off(this_note_implementation_info["channel"], this_note_implementation_info["midi_note"])
            ringing_note_info = (this_note_implementation_info["channel"],
                                 this_note_implementation_info["midi_note"],
                                 this_note_info["parameter_values"]["pitch"])

            # we need to consider this note as potentially still ringing for some period
            # after it finished. We don't want to  accidentally pitch-shift the release trail
            self.ringing_notes.append(ringing_note_info)

            def delete_after_pause():
                time.sleep(0.5)
                # make sure this note is still in self.ringing_notes. If not, it's channel was probably reused
                if ringing_note_info in self.ringing_notes:
                    # this note is done ringing, so remove it from the ringing notes list
                    self.ringing_notes.remove(ringing_note_info)

                    with self._host_instrument._note_info_lock:
                        # if there's another active note on this channel, don't reset the pitch and expression
                        for other_note_id, other_note_info in self._note_info_dict.items():
                            if self in other_note_info and other_note_info[self]["channel"] == ringing_note_info[0]:
                                return

                    # likewise if there's another ringing note on this channel
                    for other_ringing_note in self.ringing_notes:
                        if other_ringing_note[0] == ringing_note_info[0]:
                            return

                    self.pitch_bend(ringing_note_info[0], 0)
                    self.expression(ringing_note_info[0], 1)

            fork_unsynchronized(delete_after_pause)

    def change_note_pitch(self, note_id, new_pitch):
        if self.note_on_and_off_only:
            logging.warning("Change of pitch being called on a {} with the "
                            "note_on_and_off_only flag set".format(type(self)))
        if note_id not in self._note_info_dict:
            # theoretically could happen if the end_note call happens right before this is called in the
            # asynchronous animation function. We don't want to cause a KeyError, so this avoids that possibility
            return
        this_note_info = self._note_info_dict[note_id]
        assert self in this_note_info, "Note was never started by the SoundfontPlaybackImplementer; this is bad."
        this_note_implementation_info = this_note_info[self]
        if not this_note_implementation_info["prematurely_ended"]:
            self.pitch_bend(this_note_implementation_info["channel"],
                            new_pitch - this_note_implementation_info["midi_note"])

    def change_note_volume(self, note_id, new_volume):
        if self.note_on_and_off_only:
            logging.warning("Change of volume being called on a {} with the "
                            "note_on_and_off_only flag set".format(type(self)))
        if note_id not in self._note_info_dict:
            # theoretically could happen if the end_note call happens right before this is called in the
            # asynchronous animation function. We don't want to cause a KeyError, so this avoids that possibility
            return
        this_note_info = self._note_info_dict[note_id]
        assert self in this_note_info, "Note was never started by the SoundfontPlaybackImplementer; this is bad."
        this_note_implementation_info = this_note_info[self]
        if not this_note_implementation_info["prematurely_ended"]:
            self.expression(this_note_implementation_info["channel"], new_volume / this_note_info["max_volume"])

    def change_note_parameter(self, note_id, parameter_name, new_value):
        if self.note_on_and_off_only:
            logging.warning("Change of parameter being called on a {} with the "
                            "note_on_and_off_only flag set".format(type(self)))
        if note_id not in self._note_info_dict:
            # theoretically could happen if the end_note call happens right before this is called in the
            # asynchronous animation function. We don't want to cause a KeyError, so this avoids that possibility
            return

        try:
            cc_number = int(parameter_name)
        except ValueError:
            cc_number = None

        if cc_number is not None:
            this_note_info = self._note_info_dict[note_id]
            assert self in this_note_info, "Note was never started by the SoundfontPlaybackImplementer; this is bad."
            this_note_implementation_info = this_note_info[self]
            if not this_note_implementation_info["prematurely_ended"]:
                self.cc(this_note_implementation_info["channel"], cc_number, new_value / 127)


class SoundfontPlaybackImplementation(_MIDIPlaybackImplementation):

    """
    Playback implementation that does Soundfont playback, via the MIDI protocol.

    :param host_instrument: The ScampInstrument that will use this playback implementation for playback. When this
        PlaybackImplementation is constructed, it is automatically added to the list of PlaybackImplementations that
        the host instrument uses.
    :param bank_and_preset: The bank and preset within the given soundfont to use for playback
    :param soundfont: String representing the soundfont to use for playback. Defaults to the one defined in
        playback_settings.default_soundfont
    :param num_channels: How many MIDI channels to use for this instrument. Where channel-wide messages (such as
        pitch-bend messages) are involved, it is essential to have several channels at our disposal.
    :param audio_driver: name of the audio_driver to use. Defaults to the one defined in
        playback_settings.default_audio_driver
    :param max_pitch_bend: max pitch bend allowed on this instrument. Defaults to the one defined in
        playback_settings.default_max_soundfont_pitch_bend.
    :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or other
        cc messages. Valuable when using :code:`start_note` instead of :code:`play_note` in music that doesn't do any
        dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on separate MIDI channels,
        since they could potentially change pitch or volume; with this flags, we know they won't, so they can share
        the same MIDI channels, only using an extra one due to microtonality.
    """

    def __init__(self, host_instrument: 'instruments_module.ScampInstrument', bank_and_preset: Tuple[int, int] = (0, 0),
                 soundfont: str = "default", num_channels: int = 8, audio_driver: str = "default",
                 max_pitch_bend: int = "default", note_on_and_off_only: bool = False):
        super().__init__(host_instrument, num_channels, note_on_and_off_only)

        # we hold onto these arguments for the purposes of json serialization
        # note that if the audio_driver said "default", then we save it as "default",
        # rather than what that default resolved to.
        self.audio_driver = audio_driver
        self.bank_and_preset = bank_and_preset

        self.max_pitch_bend = max_pitch_bend
        self.soundfont = playback_settings.default_soundfont if soundfont == "default" else soundfont
        # these are setup by the `_initialize_shared_resources` function
        self.soundfont_host = self.soundfont_instrument = None

    def _initialize_shared_resources(self):
        audio_driver = playback_settings.default_audio_driver if self.audio_driver == "default" else self.audio_driver
        soundfont_host_resource_key = "{}_soundfont_host".format(audio_driver)
        if not self.has_shared_resource(soundfont_host_resource_key):
            self.set_shared_resource(soundfont_host_resource_key, SoundfontHost(self.soundfont, audio_driver))
        self.soundfont_host = self.get_shared_resource(soundfont_host_resource_key)
        if self.soundfont not in self.soundfont_host.soundfont_ids:
            self.soundfont_host.load_soundfont(self.soundfont)
        self.soundfont_instrument = self.soundfont_host.add_instrument(self.num_channels, self.bank_and_preset,
                                                                       self.soundfont)
        self.set_max_pitch_bend(playback_settings.default_max_soundfont_pitch_bend
                                if self.max_pitch_bend == "default" else self.max_pitch_bend)

    # -------------------------------- Main Playback Methods --------------------------------

    def note_on(self, chan: int, pitch: int, velocity_from_0_to_1: float):
        self.soundfont_instrument.note_on(chan, pitch, velocity_from_0_to_1)

    def note_off(self, chan: int, pitch: int):
        self.soundfont_instrument.note_off(chan, pitch)

    def pitch_bend(self, chan: int, bend_in_semitones: float):
        self.soundfont_instrument.pitch_bend(chan, bend_in_semitones)

    def set_max_pitch_bend(self, semitones: int):
        self.soundfont_instrument.set_max_pitch_bend(semitones)
        self.max_pitch_bend = semitones

    def expression(self, chan: int, expression_from_0_to_1: float):
        self.soundfont_instrument.expression(chan, expression_from_0_to_1)

    def cc(self, chan: int, cc_number: int, value_from_0_to_1: float):
        self.soundfont_instrument.cc(chan, cc_number, value_from_0_to_1)

    def _to_dict(self):
        return {
            "bank_and_preset": self.bank_and_preset,
            "soundfont": self.soundfont,
            "num_channels": self.num_channels,
            "audio_driver": self.audio_driver,
            "max_pitch_bend": self.max_pitch_bend
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict, host_instrument=None)


class MIDIStreamPlaybackImplementation(_MIDIPlaybackImplementation):
    """
    Playback implementation that sends an outgoing MIDI stream to an external synthesizer / program

    :param host_instrument: The ScampInstrument that will use this playback implementation for playback. When this
        PlaybackImplementation is constructed, it is automatically added to the list of PlaybackImplementations that
        the host instrument uses.
    :param midi_output_device: name or port number number of the midi output device to use. Defaults to
        playback_settings.default_midi_output_device
    :param num_channels: How many MIDI channels to use for this instrument. Where channel-wide messages (such as
        pitch-bend messages) are involved, it is essential to have several channels at our disposal.
    :param midi_output_name: name to use when sending messages
    :param max_pitch_bend: max pitch bend allowed on this instrument. Defaults to the one defined in
        playback_settings.default_max_streaming_midi_pitch_bend.
    :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or other
        cc messages. Valuable when using :code:`start_note` instead of :code:`play_note` in music that doesn't do any
        dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on separate MIDI channels,
        since they could potentially change pitch or volume; with this flags, we know they won't, so they can share
        the same MIDI channels, only using an extra one due to microtonality.
    """

    def __init__(self, host_instrument: 'instruments_module.ScampInstrument', midi_output_device: str = "default",
                 num_channels=8, midi_output_name: Optional[str] = None, max_pitch_bend: int = "default",
                 note_on_and_off_only: bool = False, start_channel=0):
        super().__init__(host_instrument, num_channels, note_on_and_off_only)

        # we hold onto these arguments for the purposes of json serialization
        # note that if the midi_output_device or midi_output_name said "default",
        # then we save it as "default", rather than what that default resolved to.
        self.start_channel = start_channel
        self.num_channels = num_channels
        self.midi_output_device = midi_output_device
        self.midi_output_name = midi_output_name

        midi_output_device = playback_settings.default_midi_output_device if midi_output_device == "default" \
            else midi_output_device
        if midi_output_name is None:
            # if no midi output name is given, fall back to the instrument name
            # if the instrument has no name, fall back to "Unnamed"
            midi_output_name = "Unnamed" if host_instrument.name is None else host_instrument.name

        # since rtmidi can only have 16 output channels, we need to create several output devices if we are using more
        if start_channel + num_channels <= 16:
            self.rt_simple_outs = [SimpleRtMidiOut(midi_output_device, midi_output_name)]
        else:
            self.rt_simple_outs = [
                SimpleRtMidiOut(midi_output_device, midi_output_name + " chans {}-{}".format(chan, chan + 15))
                for chan in range(0, start_channel + num_channels, 16)
            ]

        self.max_pitch_bend = None
        self.set_max_pitch_bend(playback_settings.default_max_streaming_midi_pitch_bend
                                if max_pitch_bend == "default" else max_pitch_bend)

    def _get_rt_simple_out_and_channel(self, chan):
        assert chan < self.num_channels
        adjusted_chan = (chan + self.start_channel) % 16
        rt_simple_out = self.rt_simple_outs[chan // 16]
        return rt_simple_out, adjusted_chan

    def note_on(self, chan: int, pitch: int, velocity_from_0_to_1: float):
        # unless it's the standard value of two semitones, reinforce the max pitch bend at the start of every note,
        # since we may start recording partway through
        if self.max_pitch_bend != 2:
            self.set_max_pitch_bend(self.max_pitch_bend)
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
        velocity = int(playback_settings.streaming_midi_volume_to_velocity_curve.value_at(velocity_from_0_to_1))
        rt_simple_out.note_on(chan, pitch, velocity)

    def note_off(self, chan: int, pitch: int):
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
        rt_simple_out.note_off(chan, pitch)

    def pitch_bend(self, chan: int, bend_in_semitones: float):
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
        directional_bend_value = int(bend_in_semitones / self.max_pitch_bend * 8192)

        if directional_bend_value > 8192 or directional_bend_value < -8192:
            logging.warning("Attempted pitch bend beyond maximum range (default is 2 semitones). Call set_max_"
                            "pitch_bend on your MidiScampInstrument to expand the range.")
        # we can't have a directional pitch bend popping up to 8192, because we'll go one above the max allowed
        # on the other hand, -8192 is fine, since that will add up to zero
        # However, notice above that we don't send a warning about going beyond max pitch bend for a value of exactly
        # 8192, since that's obnoxious and confusing. Better to just quietly clip it to 8191
        directional_bend_value = max(-8192, min(directional_bend_value, 8191))
        rt_simple_out.pitch_bend(chan, directional_bend_value + 8192)

    def set_max_pitch_bend(self, max_bend_in_semitones: int):
        if max_bend_in_semitones != int(max_bend_in_semitones):
            logging.warning("Max pitch bend must be an integer number of semitones. "
                            "The value of {} is being rounded up.".format(max_bend_in_semitones))
            max_bend_in_semitones = int(max_bend_in_semitones) + 1

        for chan in range(self.num_channels):
            rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
            rt_simple_out.cc(chan, 101, 0)
            rt_simple_out.cc(chan, 100, 0)
            rt_simple_out.cc(chan, 6, max_bend_in_semitones)
            rt_simple_out.cc(chan, 100, 127)

        self.max_pitch_bend = max_bend_in_semitones

    def expression(self, chan: int, expression_from_0_to_1: float):
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
        expression_val = max(0, min(127, int(expression_from_0_to_1 * 127)))
        rt_simple_out.expression(chan, expression_val)

    def cc(self, chan: int, cc_number: int, value_from_0_to_1: float):
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
        cc_value = max(0, min(127, int(value_from_0_to_1 * 127)))
        rt_simple_out.cc(chan, cc_number, cc_value)

    def _to_dict(self):
        return {
            "midi_output_device": self.midi_output_device,
            "num_channels": self.num_channels,
            "midi_output_name": self.midi_output_name,
            "max_pitch_bend": self.max_pitch_bend
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)


class OSCPlaybackImplementation(PlaybackImplementation):
    """
    Playback implementation that sends outgoing OSC messages to an external synthesizer / program

    :param host_instrument: The ScampInstrument that will use this playback implementation for playback. When this
        PlaybackImplementation is constructed, it is automatically added to the list of PlaybackImplementations that
        the host instrument uses.
    :param port: OSC port to use for playback
    :param ip_address: ip_address to send OSC messages to
    :param message_prefix: prefix used in the address of all messages sent. Defaults to the name of the instrument
    :param osc_message_addresses: dictionary mapping the kind of the message to the address for that message. Defaults
         to playback_settings.osc_message_addresses
    """

    def __init__(self, host_instrument: 'instruments_module.ScampInstrument', port: int, ip_address: str = "127.0.0.1",
                 message_prefix: Optional[str] = None, osc_message_addresses: dict = "default"):
        super().__init__(host_instrument)
        # the output client for OSC messages
        # by default the IP address is the local 127.0.0.1
        self.ip_address = ip_address
        self.port = port

        self.client = pythonosc.udp_client.SimpleUDPClient(ip_address, port)
        # the first part of the osc message; used to distinguish between instruments
        # by default uses the name of the instrument with spaces removed
        self.message_prefix = message_prefix if message_prefix is not None \
            else (self._host_instrument.name.replace(" ", "") if self._host_instrument.name is not None else "unnamed")

        self.osc_message_addresses = playback_settings.osc_message_addresses
        if osc_message_addresses != "default":
            assert isinstance(osc_message_addresses, dict), "osc_message_addresses argument must be a complete or " \
                                                            "incomplete dictionary of alternate osc messages"
            # for each type of osc message, use the one specified in the osc_message_addresses argument if available,
            # falling back to the one in playback_settings if it's not available
            self.osc_message_addresses = {key: osc_message_addresses[key] if key in osc_message_addresses else value
                                          for key, value in playback_settings.osc_message_addresses.items()}

        self._currently_playing = []

        def clean_up():
            for note_id in list(self._currently_playing):
                self.end_note(note_id)

        atexit.register(clean_up)

    def start_note(self, note_id: int, pitch: float, volume: float, properties: dict,
                   other_parameter_values: dict = None) -> None:
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["start_note"]),
                                 [note_id, pitch, volume])
        self._currently_playing.append(note_id)
        for param, value in other_parameter_values.items():
            self.change_note_parameter(note_id, param, value)

    def end_note(self, note_id: int) -> None:
        self.client.send_message("/{}/{}".format(self.message_prefix,
                                                 self.osc_message_addresses["end_note"]), [note_id])
        if note_id in self._currently_playing:
            self._currently_playing.remove(note_id)

    def change_note_pitch(self, note_id: int, new_pitch: float) -> None:
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["change_pitch"]),
                                 [note_id, new_pitch])

    def change_note_volume(self, note_id: int, new_volume: float) -> None:
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["change_volume"]),
                                 [note_id, new_volume])

    def change_note_parameter(self, note_id: int, parameter_name: str, new_value: float) -> None:
        self.client.send_message("/{}/{}/{}".format(
            self.message_prefix, self.osc_message_addresses["change_parameter"], parameter_name), [note_id, new_value])

    def set_max_pitch_bend(self, semitones: int) -> None:
        """
        This method does nothing in the case of an OSC-based implementation
        """
        pass

    def _to_dict(self):
        return {
            "port": self.port,
            "ip_address": self.ip_address,
            "message_prefix": self.message_prefix,
            "osc_message_addresses": self.osc_message_addresses
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)
