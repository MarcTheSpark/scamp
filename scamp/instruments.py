"""
Module containing user-facing playback classes: :class:`Ensemble`, :class:`ScampInstrument`, and :class:`NoteHandle`/
:class:`ChordHandle`

The underlying implementation of playback is done by :class:`~scamp.playback_implementations.PlaybackImplementation` and
all of its subclasses, which are found in playback_implementations.py.
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

import itertools
from ._soundfont_host import get_best_preset_match_for_name, print_soundfont_presets
from ._midi import get_available_midi_output_devices, print_available_midi_output_devices
from .utilities import SavesToJSON, NoteProperty
from .spelling import SpellingPolicy
from .note_properties import NoteProperties
from .playback_implementations import SoundfontPlaybackImplementation, MIDIStreamPlaybackImplementation, \
    OSCPlaybackImplementation
from .settings import engraving_settings, playback_settings
from clockblocks.utilities import wait
from clockblocks.clock import current_clock, Clock, ClockKilledError, TimeStamp
from expenvelope import EnvelopeSegment
import logging
import time
from threading import Lock
from typing import Union, Sequence, Tuple
from numbers import Real
from expenvelope import Envelope
from copy import deepcopy


class Ensemble(SavesToJSON):

    """
    Host for multiple :class:`ScampInstrument` objects, keeping shared resources, and shared default settings.
    A :class:`~scamp.session.Session` is, among other things, an Ensemble.

    :param default_audio_driver: value to initialize default_audio_driver instance variable to
    :param default_soundfont: value to initialize default_soundfont instance variable to
    :param default_midi_output_device: value to initialize default_midi_output_device instance variable to
    :param default_spelling_policy: a :class:`~scamp.spelling.SpellingPolicy` (or a string or tuple interpretable as
        such) to use for all instruments in this ensemble, overriding scamp defaults.
    :param instruments: list of instruments to populate this ensemble with. NOTE: generally it is not a good idea
        to initialize an Ensemble with this argument, but better to use the new_part methods after the fact. This is
        because instrument playback implementations look to share ensemble resources when they are created, and this
        is not possible if they are not already part of an ensemble.

    :ivar default_audio_driver: the audio driver instruments in this ensemble will default to. If "default", then
        this defers to the scamp global playback_settings default.
    :ivar default_soundfont: the soundfont that instruments in this ensemble will default to. If "default", then
        this defers to the scamp global playback_settings default.
    :ivar default_midi_output_device: the midi output device that instruments in this ensemble will default to.
        If "default", then this defers to the scamp global playback_settings default.
    :ivar instruments: List of all of the ScampInstruments within the Ensemble.
    :type instruments: list
    """

    def __init__(self, default_soundfont: str = "default", default_audio_driver: str = "default",
                 default_midi_output_device: str = "default",
                 default_spelling_policy: Union[SpellingPolicy, str, tuple] = None,
                 instruments: Sequence['ScampInstrument'] = None):

        self.default_soundfont = default_soundfont
        self.default_audio_driver = default_audio_driver
        self.default_midi_output_device = default_midi_output_device

        self._default_spelling_policy = SpellingPolicy.interpret(default_spelling_policy) \
            if default_spelling_policy is not None else None

        self.instruments = list(instruments) if instruments is not None else []
        self.shared_resources = {}

    def add_instrument(self, instrument: 'ScampInstrument') -> 'ScampInstrument':
        """
        Adds an instance of ScampInstrument to this Ensemble. Generally this will be done indirectly
        by calling one of the "new_instrument" methods.

        :param instrument: instrument to add to this ensemble
        :return: self
        """
        if not hasattr(instrument, "name") or instrument.name is None:
            instrument.name = "Track " + str(len(self.instruments) + 1)
        self.instruments.append(instrument)
        for playback_implementation in instrument.playback_implementations:
            # clear out any individual playback resources the instrument has been using
            playback_implementation._resources = None
        instrument.set_ensemble(self)
        return instrument

    def new_silent_part(self, name: str = None, default_spelling_policy: SpellingPolicy = None,
                        clef_preference="from_name") -> 'ScampInstrument':
        """
        Creates and returns a new ScampInstrument for this Ensemble with no PlaybackImplementations.

        :param name: name of the new part
        :param default_spelling_policy: the :attr:`~ScampInstrument.default_spelling_policy` for the new part
        :param clef_preference: the :attr:`~ScampInstrument.clef_preference` for the new part
        :return: the newly created ScampInstrument
        """
        return self.add_instrument(ScampInstrument(name, self, default_spelling_policy=default_spelling_policy,
                                                   clef_preference=clef_preference))

    @staticmethod
    def _resolve_preset_from_name(name, soundfont):
        # if preset is auto, try to find a match in the soundfont
        if name is None:
            preset = (0, 0)
        else:
            preset_match, match_score = get_best_preset_match_for_name(name, which_soundfont=soundfont)
            if match_score > 1.0:
                preset = preset_match.bank, preset_match.preset
                print("Using preset {} for {}".format(preset_match.name, name))
            else:
                logging.warning("Could not find preset matching {}. "
                                "Falling back to preset 0 (probably piano).".format(name))
                preset = (0, 0)
        return preset

    def new_part(self, name: str = None, preset="auto", soundfont: str = "default", num_channels: int = 8,
                 audio_driver: str = "default", max_pitch_bend: int = "default",
                 note_on_and_off_only: bool = False, default_spelling_policy: SpellingPolicy = None,
                 clef_preference="from_name") -> 'ScampInstrument':
        """
        Creates and returns a new ScampInstrument for this Ensemble that uses a SoundfontPlaybackImplementation. Unless
        otherwise specified, the default soundfont for this Ensemble/Session will be used, and we will search for the
        preset that best matches the name given.

        :param name: name used for this instrument in score, etc.
        :param preset: if an int, assumes bank #0; can also be a tuple of form (bank, preset). If "auto", searches
            for a preset of the appropriate name.
        :param soundfont: the name of the soundfont to use for fluidsynth playback
        :param num_channels: maximum of midi channels available to this midi part. It's wise to use more when doing
            microtonal playback, since pitch bends are applied per channel.
        :param audio_driver: which audio driver to use for this instrument (defaults to ensemble default)
        :param max_pitch_bend: max pitch bend to use for this instrument
        :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or
            other cc messages. Valuable when using :code:`start_note` instead of :code:`play_note` in music that
            doesn't do any dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on
            separate MIDI channels, since they could potentially change pitch or volume; with this flags, we know they
            won't, so they can share the same MIDI channels, only using an extra one due to microtonality.
        :param default_spelling_policy: the :attr:`~ScampInstrument.default_spelling_policy` for the new part
        :param clef_preference: the :attr:`~ScampInstrument.clef_preference` for the new part
        :return: the newly created ScampInstrument
        """
        # Resolve soundfont and audio driver to ensemble defaults if necessary (these may well be the string
        # "default", in which case it gets resolved to the playback_settings default)
        soundfont = self.default_soundfont if soundfont == "default" else soundfont
        audio_driver = self.default_audio_driver if audio_driver == "default" else audio_driver

        # if preset is auto, try to find a match in the soundfont
        if preset == "auto":
            preset = Ensemble._resolve_preset_from_name(name, soundfont)
        elif isinstance(preset, int):
            preset = (0, preset)

        name = "Track " + str(len(self.instruments) + 1) if name is None else name

        instrument = self.new_silent_part(name, default_spelling_policy=default_spelling_policy,
                                          clef_preference=clef_preference)
        instrument.add_soundfont_playback(preset=preset, soundfont=soundfont, num_channels=num_channels,
                                          audio_driver=audio_driver, max_pitch_bend=max_pitch_bend,
                                          note_on_and_off_only=note_on_and_off_only)

        return instrument

    def new_midi_part(self, name: str = None, midi_output_device: Union[int, str] = "default",
                      num_channels: int = 8, midi_output_name: str = None, max_pitch_bend: int = "default",
                      note_on_and_off_only: bool = False, default_spelling_policy: SpellingPolicy = None,
                      clef_preference="from_name", start_channel: int = 0) -> 'ScampInstrument':
        """
        Creates and returns a new ScampInstrument for this Ensemble that uses a MIDIStreamPlaybackImplementation.
        This means that when notes are played by this instrument, midi messages are sent out to the given device.

        :param name: name used for this instrument in score, etc. for a preset of the appropriate name.
        :param midi_output_device: name or number of the device used to output midi. Call
            get_available_midi_output_devices to check what's available.
        :param num_channels: maximum of midi channels available to this midi part. It's wise to use more when doing
            microtonal playback, since pitch bends are applied per channel.
        :param midi_output_name: name of this part
        :param max_pitch_bend: max pitch bend to use for this instrument
        :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or
            other cc messages. Valuable when using :code:`start_note` instead of :code:`play_note` in music that
            doesn't do any dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on
            separate MIDI channels, since they could potentially change pitch or volume; with this flags, we know they
            won't, so they can share the same MIDI channels, only using an extra one due to microtonality.
        :param default_spelling_policy: the :attr:`~ScampInstrument.default_spelling_policy` for the new part
        :param clef_preference: the :attr:`~ScampInstrument.clef_preference` for the new part
        :param start_channel: the first channel to use. For instance, if start_channel is 4, and num_channels is 5,
            we will use channels (4, 5, 6, 7, 8). NOTE: channel counting in SCAMP starts from 0, so this may show
            up as channels 5-9 in your MIDI software.
        :return: the newly created ScampInstrument
        """
        midi_output_device = self.default_midi_output_device if midi_output_device == "default" else midi_output_device

        name = "Track " + str(len(self.instruments) + 1) if name is None else name

        instrument = self.new_silent_part(name, default_spelling_policy=default_spelling_policy,
                                          clef_preference=clef_preference)
        instrument.add_streaming_midi_playback(midi_output_device=midi_output_device, num_channels=num_channels,
                                               midi_output_name=midi_output_name, max_pitch_bend=max_pitch_bend,
                                               note_on_and_off_only=note_on_and_off_only, start_channel=start_channel)

        return instrument

    def new_osc_part(self, name: str = None, port: int = None, ip_address: str = "127.0.0.1",
                     message_prefix: str = None, osc_message_addresses: dict = "default",
                     default_spelling_policy: SpellingPolicy = None, clef_preference="from_name") -> 'ScampInstrument':
        """
        Creates and returns a new ScampInstrument for this Ensemble that uses a OSCPlaybackImplementation. This means
        that when notes are played by this instrument, osc messages are sent out to the specified address

        :param name: name used for this instrument in score, etc. for a preset of the appropriate name.
        :param port: port osc messages are sent to
        :param ip_address: ip_address osc messages are sent to
        :param message_prefix: prefix used for this instrument in osc messages
        :param osc_message_addresses: dictionary defining the address used for each type of playback message. defaults
            to using "start_note", "end_note", "change_pitch", "change_volume", "change_parameter". The default can
            be changed in playback settings.
        :param default_spelling_policy: the :attr:`~ScampInstrument.default_spelling_policy` for the new part
        :param clef_preference: the :attr:`~ScampInstrument.clef_preference` for the new part
        :return: the newly created ScampInstrument
        """
        name = "Track " + str(len(self.instruments) + 1) if name is None else name

        instrument = self.new_silent_part(name, default_spelling_policy=default_spelling_policy,
                                          clef_preference=clef_preference)
        instrument.add_osc_playback(port=port, ip_address=ip_address, message_prefix=message_prefix,
                                    osc_message_addresses=osc_message_addresses)

        return instrument

    def _get_part_name_count(self, name):
        return sum(i.name == name for i in self.instruments)

    def get_instrument_by_name(self, name: str, which: int = 0):
        """
        Returns the instrument of the given name.

        :param name: name of the instrument to return
        :param which: If there are multiple with the same name, this parameter specifies the one returned. (If none
            match the number given by which, the first name match is returned)
        """
        # if there are multiple instruments of the same name, which determines which one is chosen
        imperfect_match = None
        for instrument in self.instruments:
            if name == instrument.name:
                if which == instrument.name_count:
                    return instrument
                else:
                    imperfect_match = instrument if imperfect_match is None else imperfect_match
        return imperfect_match

    def print_default_soundfont_presets(self) -> None:
        """
        Prints a list of presets available with the default soundfont.
        """
        print_soundfont_presets(self.default_soundfont)

    @staticmethod
    def get_available_midi_output_devices() -> enumerate:
        """
        Returns an enumeration of available ports and devices for midi output.
        """
        return get_available_midi_output_devices()

    @staticmethod
    def print_available_midi_output_devices() -> None:
        """
        Prints a list of available ports and devices for midi output.
        """
        print_available_midi_output_devices()

    @property
    def default_spelling_policy(self) -> 'SpellingPolicy':
        """
        Default spelling policy used for transcriptions made with this Ensemble.
        """
        return self._default_spelling_policy

    @default_spelling_policy.setter
    def default_spelling_policy(self, value: Union[SpellingPolicy, str, tuple]):
        self._default_spelling_policy = SpellingPolicy.interpret(value) if value is not None else None

    def _to_dict(self):
        return {
            "default_soundfont": self.default_soundfont,
            "default_audio_driver": self.default_audio_driver,
            "default_midi_output_device": self.default_midi_output_device,
            "default_spelling_policy": self.default_spelling_policy,
            "instruments": self.instruments
        }

    @classmethod
    def _from_dict(cls, json_dict):
        ensemble = cls(**json_dict)
        for instrument in ensemble.instruments:
            instrument.set_ensemble(ensemble)
        return ensemble

    def __str__(self):
        return "Ensemble({})".format(self.instruments)

    def __repr__(self):
        return "Ensemble._from_dict({})".format(self._to_dict())


class ScampInstrument(SavesToJSON):

    """
    Instrument class that does the playing of the notes. Generally this will be created through one of the
    "new_part" methods of the Session or Ensemble class.

    :param name: name of this instrument (e.g. when printed in a score)
    :param ensemble: Ensemble to which this instrument will belong.
    :param default_spelling_policy: sets :attr:`ScampInstrument.default_spelling_policy`
    :param clef_preference: sets :attr:`ScampInstrument.clef_preference`
    :ivar name: name of this instrument (e.g. when printed in a score)
    :ivar name_count: when there are multiple instruments of the same name within an Ensemble, this variable assigns
        each a unique index (starting with 0), to distinguish them
    :ivar ensemble: Ensemble to which this instrument will belong.
    :ivar playback_implementations: list of PlaybackImplementation(s) used to actually playback notes
    """

    _note_id_generator = itertools.count()
    _change_param_call_counter = itertools.count()

    def __init__(self, name: str = None, ensemble: Ensemble = None, default_spelling_policy: SpellingPolicy = None,
                 clef_preference="from_name"):
        super().__init__()

        self.name = name
        self._clef_preference = None
        self.clef_preference = clef_preference

        self._transcribers_to_notify = []

        self._note_info_by_id = {}
        self.playback_implementations = []

        # A policy for spelling notes used as the default for this instrument. Overrides any broader defaults.
        # (Has a getter and setter method allowing constructor strings to be passed.)
        self._default_spelling_policy = default_spelling_policy

        # this lock stops multiple threads from simultaneously accessing the self._note_info_by_id
        self._note_info_lock = Lock()

        #: used when exporting to json to see if this is the top level object being exported, or part of an ensemble
        self._export_as_stand_alone = False

        self.ensemble = None
        self.name_count = 0
        if ensemble is not None:
            self.set_ensemble(ensemble)

    def set_ensemble(self, ensemble: 'Ensemble') -> None:
        """
        Sets the ensemble that this instrument belongs to. Generally this happens automatically.
        
        :param ensemble: the :class:`Ensemble` that this instrument should belong to.
        """
        if self.ensemble == ensemble:
            # already set to this ensemble
            return
        self.ensemble = ensemble
        # used to help distinguish between identically named instruments in the same ensemble
        self.name_count = ensemble._get_part_name_count(self.name)
        for playback_implementation in self.playback_implementations:
            playback_implementation.set_host_instrument(self)

    def play_note(self, pitch, volume, length, properties: Union[str, dict, Sequence, NoteProperty] = None,
                  blocking: bool = True, clock: Clock = None, silent: bool = False, transcribe: bool = True) -> None:
        """
        Play a note on this instrument, with the given pitch, volume and length.

        :param pitch: either a number, an Envelope, or a list used to create an Envelope. MIDI pitch values are used,
            with 60 representing middle C. However, microtones are allowed; for instance, a pitch of 64.7 produces an
            F4 30 cents flat.
        :param volume: either a number, an Envelope, or a list used to create an Envelope. Volume is scaled from 0 to 1,
            with 0 representing silence and 1 representing max volume.
        :param length: either a number (of beats), or a tuple representing a set of tied segments
        :param properties: Catch-all for a wide range of other playback and notation details that we may want to convey
            about a note. These details can either be given in a dictionary or a string (for greater brevity).
            Recognized dictionary keys are "articulation(s)", "notehead(s)", "notation(s)", "text(s)",
            "playback_adjustment(s)", "key"/"spelling_policy", "voice", and "param_*" (for specifying arbitrary
            extra parameters). For example:

            .. code-block:: python3

                properties={
                     # add  staccato and tenuto articulations
                    "articulations": ["staccato", "tenuto"],
                    # change to an "x" notehead
                    "notehead": "x",
                    # add a 32-note tremolo
                    "notation": "tremolo32",
                    # add this text to the score by the note
                    "text": "Hello there!",
                    # play an octave higher (could also use a NotePlaybackAdjustment object)
                    "playback_adjustment": "pitch + 12",
                    # notate accidentals consistent with the key of Bb major
                    "key": "Bb major",
                    # place the note in voice two (named voices are also allowed)
                    "voice": 2,
                    # sets the "vibrato" parameter to an envelope going from 2 to 6 to 1
                    # (note that extra parameters only effect playback when used with
                    # a playback implementation that recognizes them)
                    "param_vibrato": [2, 6, 1]
                }

            Since this dictionary format can be quite cumbersome, it is also possible to pass a string containing
            shorthand, which gets parsed into a dictionary. For example:

            .. code-block:: python3

                properties="articulations: staccato/tenuto, harmonic, #, volume * 0.7"

            The comma separates different properties, and the forward slash separates multiple entries for the same
            property (with the exception of with the text property, since a slash could be part of the text). Properties
            can either be given with explicit key/value pairs (separated by colon), or a value can simply be given and
            the type of property will be inferred. In the above example, it is inferred that "harmonic" is a notehead,
            that the "#" is a desired spelling, and that "volume * 0.7" is a string to be parsed as a
            :class:`~scamp.playback_adjustments.NotePlaybackAdjustment` using its
            :func:`~scamp.playback_adjustments.NotePlaybackAdjustment.from_string` method.

            Finally, it is also possible to directly pass a :class:`~scamp.spelling.SpellingPolicy`,
            :class:`~scamp.text.StaffText`, or :class:`~scamp.playback_adjustments.NotePlaybackAdjustment`.
        :param blocking: if True, don't return until the note is done playing; if False, return immediately
        :param clock: which clock to use. If None, capture the clock from context.
        :param silent: if True, note is not played back, but is still transcribed when a
            :class:`~scamp.transcriber.Transcriber` is active. (Generally ignored by end user.)
        :param transcribe: if False, note is not transcribed even when a :class:`~scamp.transcriber.Transcriber` is
            active. (Generally ignored by end user.)
        """
        if clock is None:
            # first try to just get the clock operating on the current thread
            clock = current_clock()
            if clock is None:
                # if there's no clock operating on the current thread,,,
                if isinstance(self.ensemble, Clock):
                    # ...but this instrument belongs to a Session (i.e. an ensemble that's also a clock),
                    # then we use that session as our clock
                    clock = self.ensemble
                    # we're also going to not want to block execution, since that will involve a call to wait
                    # on the session that's probably running as a server (and therefore doing its own wait calls)
                    # on a parallel thread
                    blocking = False
                else:
                    # otherwise, just create a clock to run this all on
                    clock = Clock()

        properties = self._standardize_properties(properties)

        if hasattr(pitch, "__len__"):
            properties.temp["parameters_that_came_from_lists"].add("pitch")
            pitch = Envelope.from_list(pitch)

        if hasattr(volume, "__len__"):
            properties.temp["parameters_that_came_from_lists"].add("volume")
            volume = Envelope.from_list(volume)

        ScampInstrument._normalize_envelopes(pitch, volume, length, properties)

        adjusted_pitch, adjusted_volume, adjusted_length, did_an_adjustment = \
            properties.apply_playback_adjustments(pitch, volume, length)

        if did_an_adjustment:
            adjusted_pitch = Envelope.from_list(adjusted_pitch) \
                if hasattr(adjusted_pitch, "__len__") else adjusted_pitch
            adjusted_volume = Envelope.from_list(adjusted_volume) \
                if hasattr(adjusted_volume, "__len__") else adjusted_volume
            # play, but don't transcribe the modified version (though only if the clock is not fast-forwarding)
            if not clock.is_fast_forwarding():
                clock.fork(self._do_play_note, name="DO_PLAY_NOTE",
                           args=(adjusted_pitch, adjusted_volume, adjusted_length, properties),
                           kwargs={"transcribe": False, "silent": silent})
            # transcribe, but don't play the unmodified version
            if blocking:
                self._do_play_note(clock, pitch, volume, length, properties, silent=True, transcribe=transcribe)
            else:
                clock.fork(self._do_play_note, name="DO_PLAY_NOTE",
                           args=(pitch, volume, length, properties), kwargs={"silent": True, "transcribe": transcribe})
        else:
            # No adjustments, so no need to separate transcription from playback
            # (However, if the clock is fast-forwarding, make it silent)
            if blocking:
                self._do_play_note(clock, pitch, volume, length, properties,
                                   silent=clock.is_fast_forwarding() or silent, transcribe=transcribe)
            else:
                clock.fork(self._do_play_note, name="DO_PLAY_NOTE",
                           args=(pitch, volume, length, properties),
                           kwargs={"silent": clock.is_fast_forwarding() or silent, "transcribe": transcribe})

    @staticmethod
    def _normalize_envelopes(pitch, volume, length, properties):
        # length can either be a single number of beats or a list/tuple or segments to be split
        # sum_length will represent the total number of beats in either case
        sum_length = sum(length) if hasattr(length, "__len__") else length

        # normalize envelopes to the duration of the note if the setting say to do so
        if isinstance(pitch, Envelope) and (playback_settings.resize_parameter_envelopes == "always" or
                                            playback_settings.resize_parameter_envelopes == "lists" and
                                            "pitch" in properties.temp["parameters_that_came_from_lists"]):
            pitch.normalize_to_duration(sum_length)
        if isinstance(volume, Envelope) and (playback_settings.resize_parameter_envelopes == "always" or
                                             playback_settings.resize_parameter_envelopes == "lists" and
                                             "volume" in properties.temp["parameters_that_came_from_lists"]):
            volume.normalize_to_duration(sum_length)
        for param, value in properties.iterate_extra_parameters_and_values():
            if isinstance(value, Envelope) and (playback_settings.resize_parameter_envelopes == "always" or
                                                playback_settings.resize_parameter_envelopes == "lists" and
                                                param in properties.temp["parameters_that_came_from_lists"]):
                value.normalize_to_duration(sum_length)

    def _do_play_note(self, clock, pitch, volume, length, properties, silent=False, transcribe=True):
        """
        This runs the actual thread that plays the note, and is scheduled when play_note is called.
        If playback adjustments were made, then we schedule the altered version of _do_play_note to play back, but with
        "transcribe" set to false, and we schedule an unaltered version of _do_play_note to run silently, but with
        "transcribe" set to true. This way the transcription is not affected by performance adjustments.

        :param clock: which clock this plays back on
        :param pitch: either a number, an Envelope
        :param volume: either a number, an Envelope
        :param length: either a number (of beats), or a tuple representing a set of tied segments
        :param properties: a NoteProperties dictionary
        :param silent: if True, don't actually do any of the playback; just go through the motions for transcribing it
        :param transcribe: if False, don't notify Transcribers at the end of the note
        """

        # if we know ahead of time that neither pitch nor volume changes, we can pass
        fixed = not isinstance(pitch, Envelope) and not isinstance(volume, Envelope)

        # start the note. (Note that this will also start the animation of pitch, volume,
        # and any other parameters if they are envelopes.)
        note_flags = []
        if fixed:
            note_flags.append("fixed")
        if silent:
            note_flags.append("silent")
        if not transcribe:
            note_flags.append("no_transcribe")
        note_handle = self.start_note(
            pitch, volume, properties, clock=clock, flags=note_flags,
            max_volume=volume.max_level() if isinstance(volume, Envelope) else volume
        )

        try:
            if hasattr(length, "__len__"):
                for length_segment in length:
                    clock.wait(length_segment)
                    note_handle.split()
            else:
                clock.wait(length)
            note_handle.end()
        except ClockKilledError as e:
            note_handle.end()
            raise e

    def play_chord(self, pitches: Sequence, volume, length, properties: Union[str, dict, Sequence, NoteProperty] = None,
                   blocking: bool = True, clock: Clock = None, silent: bool = False, transcribe: bool = True) -> None:
        """
        Play a chord with the given pitches, volume, and length. Essentially, this is a convenience method that
        bundles together several calls to "play_note" and takes a list of pitches rather than a single pitch

        :param pitches: a list of pitches for the notes of this chord
        :param volume: see :func:`play_note`
        :param length: see :func:`play_note`
        :param properties: see :func:`play_note`. One extra wrinkle to note with chords: if one value is
            given for the "notehead" property then all noteheads are set to that value. If multiple values are given,
            they will be assigned to individual noteheads, and there should be the same number as notes in the chord.
        :param blocking: see description for "play_note"
        :param clock: see description for "play_note"
        :param silent: see description for "play_note"
        :param transcribe: see description for "play_note"
        """
        if not hasattr(pitches, "__len__"):
            raise ValueError("'pitches' must be a list of pitches.")

        properties = self._standardize_properties(properties)

        # we should either be given a number of noteheads equal to the number of pitches or just one notehead for all
        if not (len(properties.noteheads) == len(pitches) or len(properties.noteheads) == 1):
            raise ValueError("Wrong number of noteheads for chord.")

        for i, pitch in enumerate(pitches[:-1]):
            # for all but the last pitch, play it without blocking, so we can start all the others
            # also copy the properties dictionary, and pick out the correct notehead if we've been given several
            properties_copy = deepcopy(properties)
            if len(properties.noteheads) > 1:
                properties_copy.noteheads = [properties_copy.noteheads[i]]
            self.play_note(pitch, volume, length, properties=properties_copy, blocking=False, clock=clock,
                           silent=silent, transcribe=transcribe)

        # for the last pitch, block or not based on the blocking parameter
        # also, if we've been given a list of noteheads, pick out the last one
        if len(properties.noteheads) > 1:
            properties.noteheads = [properties.noteheads[-1]]
        self.play_note(pitches[-1], volume, length, properties=properties, blocking=blocking, clock=clock,
                       silent=silent, transcribe=transcribe)

    def start_note(self, pitch: float, volume: float, properties: Union[str, dict, Sequence, NoteProperty] = None,
                   clock: Clock = None, max_volume: float = 1, flags: Sequence[str] = None) -> 'NoteHandle':
        """
        Start a note with the given pitch, volume, and properties

        :param pitch: the pitch / starting pitch of the note (not an Envelope)
        :param volume: the volume / starting volume of the note (not an Envelope)
        :param properties: see :func:`play_note`
        :param clock: the clock on which to run any animation of pitch, volume, etc. If None, captures the clock from
            context.
        :param max_volume: This is a bit of a pain, but since midi playback requires us to set the velocity at the
            beginning of the note, and thereafter vary volume using expression, and since expression can only make the
            note quieter, we need to start the note with velocity equal to the max desired volume (using expression to
            adjust it down to the actual start volume). The default will be 1, meaning as loud as possible, since unless
            we know in advance what the note is going to do, we need to be prepared to go up to full volume. Using
            play_note, we do actually know in advance how loud the note is going to get, so we can set max volume to the
            peak of the Envelope. Honestly, I wish I could separate this implementation detail from the ScampInstrument
            class, but I don't see how this would be possible.
        :param flags: list of strings that act as flags for how the note should be processed. Should probably be
            ignored by a normal user.
        :return: a NoteHandle with which to later manipulate the note
        """
        if clock is None:
            # first try to just get the clock operating on the current thread
            clock = current_clock()
            if clock is None:
                # if there's no clock operating on the current thread,,,
                if isinstance(self.ensemble, Clock):
                    # ...but this instrument belongs to a Session (i.e. an ensemble that's also a clock),
                    # then we use that session as our clock
                    clock = self.ensemble
                else:
                    # otherwise, just create a clock to run this all on
                    clock = Clock()

        # standardize properties if necessary, turn pitch and volume into lists if necessary
        properties = self._standardize_properties(properties)
        pitch = Envelope.from_list(pitch) if hasattr(pitch, "__len__") else pitch
        volume = Envelope.from_list(volume) if hasattr(volume, "__len__") else volume

        # get the starting values for all the parameters to pass to the playback implementations
        start_pitch = pitch.start_level() if isinstance(pitch, Envelope) else pitch
        start_volume = volume.start_level() if isinstance(volume, Envelope) else volume
        other_param_start_values = {param: value.start_level() if isinstance(value, Envelope) else value
                                    for param, value in properties.iterate_extra_parameters_and_values()}

        with self._note_info_lock:
            # generate a new id for this note, and set up all of its info
            note_id = next(ScampInstrument._note_id_generator)
            self._note_info_by_id[note_id] = {
                "clock": clock,
                "start_time_stamp": TimeStamp(clock),
                "end_time_stamp": None,
                "split_points": [],
                "parameter_start_values": dict(other_param_start_values, pitch=start_pitch, volume=start_volume),
                "parameter_values": dict(other_param_start_values, pitch=start_pitch, volume=start_volume),
                "parameter_change_segments": {},
                "segments_list_lock": Lock(),
                "properties": properties,
                "max_volume": max_volume,
                "flags": [] if flags is None else flags
            }

            if clock.is_fast_forwarding() and "silent" not in self._note_info_by_id[note_id]["flags"]:
                self._note_info_by_id[note_id]["flags"].append("silent")

            if "silent" not in self._note_info_by_id[note_id]["flags"]:
                # otherwise, call all the playback implementation!
                for playback_implementation in self.playback_implementations:
                    playback_implementation.start_note(note_id, start_pitch, start_volume,
                                                       properties, other_param_start_values)

        # we now exit the lock, since otherwise the following calls will not be able to happen
        # create a handle for this note
        handle = NoteHandle(note_id, self)

        # start all the note animation for pitch, volume, and any extra parameters
        # note that, if the note is silent, then start_note has added the silent flag to the note_info dict
        # this will cause unsynchronized animation threads not to fire
        if isinstance(pitch, Envelope):
            handle.change_pitch(pitch.levels[1:], pitch.durations, pitch.curve_shapes, clock)
        if isinstance(volume, Envelope):
            handle.change_volume(volume.levels[1:], volume.durations, volume.curve_shapes, clock)
        for param, value in properties.iterate_extra_parameters_and_values():
            if isinstance(value, Envelope):
                handle.change_parameter(param, value.levels[1:], value.durations, value.curve_shapes, clock)

        return handle

    def start_chord(self, pitches: Sequence[float], volume: float,
                    properties: Union[str, dict, Sequence, NoteProperty] = None,
                    clock: Clock = None, max_volume: float = 1, flags: Sequence[str] = None) -> 'ChordHandle':
        """
        Simple utility for starting chords without starting each note individually.

        :param pitches: a list of pitches (not Envelopes)
        :param volume: see :func:`start_note`
        :param properties: see :func:`play_note`. In general, properties are cloned to all members of the chord.
            However, noteheads can be separately defined using this syntax: "noteheads: diamond / normal / cross"
        :param clock: see start_note
        :param max_volume: see start_note
        :param flags: see start_note
        :return: a ChordHandle, which is used to manipulate the chord thereafter. Pitch change calls on the ChordHandle
            are based on the first note of the chord; all other notes are shifted in parallel
        """
        assert hasattr(pitches, "__len__")

        properties = self._standardize_properties(properties)

        # we should either be given a number of noteheads equal to the number of pitches or just one notehead for all
        assert len(properties.noteheads) == len(pitches) or len(properties.noteheads) == 1, \
            "Wrong number of noteheads for chord."

        note_handles = []

        pitches = [Envelope.from_list(pitch) if hasattr(pitch, "__len__") else pitch for pitch in pitches]

        first_pitch_start_level = pitches[0].start_level() if isinstance(pitches[0], Envelope) else pitches[0]
        intervals = [(pitch.start_level() if isinstance(pitch, Envelope) else pitch) - first_pitch_start_level
                     for pitch in pitches]

        for i, pitch in enumerate(pitches):
            # for all but the last pitch, play it without blocking, so we can start all the others
            # also copy the properties dictionary, and pick out the correct notehead if we've been given several
            properties_copy = deepcopy(properties)
            if len(properties.noteheads) > 1:
                properties_copy.noteheads = [properties_copy.noteheads[i]]
            note_handles.append(self.start_note(pitch, volume, properties=properties_copy, clock=clock,
                                                max_volume=max_volume, flags=flags))

        return ChordHandle(note_handles, intervals)

    def _standardize_properties(self, raw_properties) -> NoteProperties:
        """
        Turns the properties given into the standard form of a NotePropertiesDictionary

        :param raw_properties: can be None, a string, a list, or a dict
        :return: a NotePropertiesDictionary
        """
        if isinstance(raw_properties, NoteProperties):
            return raw_properties

        properties = NoteProperties.from_unknown_format(raw_properties) \
            if not isinstance(raw_properties, NoteProperties) else raw_properties

        # resolve the spelling policy based on defaults (local first, then more global)
        if properties["spelling_policy"] is None:
            # if the note doesn't say how to be spelled, check the instrument
            if self.default_spelling_policy is not None:
                properties.spelling_policy = self.default_spelling_policy
            # if the instrument doesn't have a default spelling policy check the host (probably a Session)
            elif self.ensemble is not None and self.ensemble.default_spelling_policy is not None:
                properties.spelling_policy = self.ensemble.default_spelling_policy
            # if the host doesn't have a default, then don't do anything and it will fall back to playback_settings
        return properties

    def change_note_parameter(self, note_id: Union[int, 'NoteHandle'], param_name: str,
                              target_value_or_values: Union[float, Sequence],
                              transition_length_or_lengths: Union[float, Sequence] = 0,
                              transition_curve_shape_or_shapes: Union[float, Sequence] = 0,
                              clock: Clock = None) -> None:
        """
        Changes the value of parameter of note playback over a given time; can also take a sequence of targets and times

        :param note_id: which note to affect (an id or a NoteHandle)
        :param param_name: name of the parameter to affect. "pitch" and "volume" are special cases
        :param target_value_or_values: target value (or list of values) for the parameter
        :param transition_length_or_lengths: transition time(s) in beats to the target value(s)
        :param transition_curve_shape_or_shapes: curve shape(s) for the transition(s)
        :param clock: which clock all of this happens on; by default, reuses the clock that the note started on.
        """
        with self._note_info_lock:
            note_id = note_id.note_id if isinstance(note_id, NoteHandle) else note_id
            note_info = self._note_info_by_id[note_id]

            if clock is None:
                clock = note_info["clock"]
            assert isinstance(clock, Clock), "Invalid clock argument."

            if "fixed" in note_info["flags"] and param_name in ("pitch", "volume"):
                raise Exception("Cannot change pitch or volume of a note with 'fixed' set to True.")

            # which function do we use to actually carry out the change of parameter? Pitch and volume are special.
            if "silent" in note_info["flags"]:
                # if it's silent, then we don't actually call any of the implementation, so pass a dummy function
                def parameter_change_function(value): note_info["parameter_values"][param_name] = value
                temporal_resolution = None
            elif param_name == "pitch":
                def parameter_change_function(value):
                    for playback_implementation in self.playback_implementations:
                        playback_implementation.change_note_pitch(note_id, value)
                    note_info["parameter_values"][param_name] = value
                temporal_resolution = "pitch-based"
            elif param_name == "volume":
                def parameter_change_function(value):
                    for playback_implementation in self.playback_implementations:
                        playback_implementation.change_note_volume(note_id, value)
                    note_info["parameter_values"][param_name] = value
                temporal_resolution = "volume-based"
            else:
                def parameter_change_function(value):
                    for playback_implementation in self.playback_implementations:
                        playback_implementation.change_note_parameter(note_id, param_name, value)
                    note_info["parameter_values"][param_name] = value
                temporal_resolution = 0.01

            assert param_name in note_info["parameter_values"], \
                "Cannot change parameter {}, as it was undefined at note start.".format(param_name)

            if param_name in note_info["parameter_change_segments"]:
                segments_list = note_info["parameter_change_segments"][param_name]
            else:
                segments_list = note_info["parameter_change_segments"][param_name] = []

            # if there was a previous segment changing this same parameter, and it's not done yet, we should abort it
            if len(segments_list) > 0:
                segments_list[-1].abort_if_running()

            # this helps to keep track of which call to change_note_parameter happened first, since when
            # do_animation_sequence gets forked, order can become indeterminate (see comment there)
            call_priority = next(ScampInstrument._change_param_call_counter)

            if hasattr(target_value_or_values, "__len__"):
                # assume linear segments unless otherwise specified
                transition_curve_shape_or_shapes = [0] * len(target_value_or_values) if \
                    transition_curve_shape_or_shapes == 0 else transition_curve_shape_or_shapes
                assert hasattr(transition_length_or_lengths, "__len__") and \
                       hasattr(transition_curve_shape_or_shapes, "__len__")
                assert len(target_value_or_values) == len(transition_length_or_lengths) == \
                       len(transition_curve_shape_or_shapes), \
                    "List of target values must be accompanied by a equal length list of transition lengths and shapes."

                def do_animation_sequence():
                    for target, length, shape in zip(target_value_or_values, transition_length_or_lengths,
                                                     transition_curve_shape_or_shapes):
                        with note_info["segments_list_lock"]:
                            if len(segments_list) > 0 and segments_list[-1].running:
                                # if two segments are started at the exact same (clock) time, then we want to abort the
                                # one that was called first. Often that will happen in the call to segments_list[-1].
                                # abort_if_running() above. However, it may be that they both make it through that check
                                # before either is added to the segments list. This checks in on that case, and aborts
                                # whichever segment came from the earlier call to change_note_parameter
                                if call_priority > segments_list[-1].call_priority:
                                    # this call to change_note_parameter happened after, abort the other one
                                    segments_list[-1].abort_if_running()
                                else:
                                    # this call to change_note_parameter happened before, abort
                                    return

                            this_segment = _ParameterChangeSegment(
                                parameter_change_function, note_info["parameter_values"][param_name], target,
                                length, shape, clock, call_priority, temporal_resolution=temporal_resolution)

                            segments_list.append(this_segment)
                        # note that these segments are not forked individually: they are chained together and called
                        # directly on a function (do_animation_sequence) that is forked. This means that when we abort
                        # one of them, we kill the clock that do_animation_sequence is running on, thereby aborting all
                        # remaining segments as well. This is exactly what we want: if we call change_note_parameter
                        # while a previous change_note_parameter is running, we want to abort all segments of the
                        # one that's running
                        try:
                            this_segment.run(silent="silent" in note_info["flags"])
                        except Exception as e:
                            raise e

                clock.fork(do_animation_sequence, name="PARAM_ANIMATION_SEQUENCE({})".format(param_name))
            else:
                parameter_change_segment = _ParameterChangeSegment(
                    parameter_change_function, note_info["parameter_values"][param_name], target_value_or_values,
                    transition_length_or_lengths, transition_curve_shape_or_shapes, clock, call_priority,
                    temporal_resolution=temporal_resolution)
                with note_info["segments_list_lock"]:
                    segments_list.append(parameter_change_segment)
                clock.fork(parameter_change_segment.run, name="PARAM_ANIMATION({})".format(param_name),
                           kwargs={"silent": "silent" in note_info["flags"]})

    def change_note_pitch(self, note_id: Union[int, 'NoteHandle'], target_value_or_values: Union[float, Sequence],
                          transition_length_or_lengths: Union[float, Sequence] = 0,
                          transition_curve_shape_or_shapes: Union[float, Sequence] = 0,
                          clock: Clock = None) -> None:
        """
        Change the pitch of an already started note; can also take a sequence of targets and times.

        :param note_id: which note to affect (an id or a NoteHandle)
        :param target_value_or_values: target value (or list of values) for the parameter
        :param transition_length_or_lengths: transition time(s) in beats to the target value(s)
        :param transition_curve_shape_or_shapes: curve shape(s) for the transition(s)
        :param clock: which clock all of this happens on; by default, reuses the clock that the note started on.
        """
        self.change_note_parameter(note_id, "pitch", target_value_or_values, transition_length_or_lengths,
                                   transition_curve_shape_or_shapes, clock)

    def change_note_volume(self, note_id: Union[int, 'NoteHandle'], target_value_or_values: Union[float, Sequence],
                           transition_length_or_lengths: Union[float, Sequence] = 0,
                           transition_curve_shape_or_shapes: Union[float, Sequence] = 0,
                           clock: Clock = None) -> None:
        """
        Change the volume of an already started note; can also take a sequence of targets and times

        :param note_id: which note to affect (an id or a NoteHandle)
        :param target_value_or_values: target value (or list thereof) for the parameter
        :param transition_length_or_lengths: transition time(s) in beats to the target value(s)
        :param transition_curve_shape_or_shapes: curve shape(s) for the transition(s)
        :param clock: which clock all of this happens on; "from_note" simply reuses the clock that the note started on.
        """
        self.change_note_parameter(note_id, "volume", target_value_or_values, transition_length_or_lengths,
                                   transition_curve_shape_or_shapes, clock)

    def split_note(self, note_id: Union[int, 'NoteHandle']) -> None:
        """
        Adds a split point in a note, causing it later to be rendered as tied pieces.

        :param note_id: Which note or NoteHandle to split
        """
        with self._note_info_lock:
            note_id = note_id.note_id if isinstance(note_id, NoteHandle) else note_id
            note_info = self._note_info_by_id[note_id]
            note_info["split_points"].append(TimeStamp(note_info["clock"]))

    def end_note(self, note_id: Union[int, 'NoteHandle'] = None) -> None:
        """
        Ends the note with the given note id. If none is specified, ends oldest note started.
        Note that this only applies to notes started in an open-ended way with :func:`start_note`, notes created using
        :func:`play_note` have their lifecycle controlled automatically.

        :param note_id: either the id itself or a NoteHandle with that id. Default of None ends the oldest note
        """
        with self._note_info_lock:
            # in case we're passed a NoteHandle instead of an actual id number, get the number from the handle
            note_id = note_id.note_id if isinstance(note_id, NoteHandle) else note_id

            if note_id is not None:
                # as specific note_id has been given, so it had better belong to a currently playing note!
                if note_id not in self._note_info_by_id:
                    logging.warning("Tried to end a note that was never started!")
                    return
            elif len(self._note_info_by_id) > 0:
                # no specific id was given, so end the oldest note
                # (note that ids just count up, so the lowest active id is the oldest)
                note_id = min(self._note_info_by_id.keys())
            else:
                logging.warning("Tried to end a note that was never started!")
                return

            note_info = self._note_info_by_id[note_id]

            # resolve the clock to use
            clock = note_info["clock"]

            # end any segments that are still changing
            for param_name in note_info["parameter_change_segments"]:
                if len(note_info["parameter_change_segments"][param_name]) > 0:
                    note_info["parameter_change_segments"][param_name][-1].abort_if_running()

            # transcribe the note, if applicable
            note_info["end_time_stamp"] = TimeStamp(clock)
            if "no_transcribe" not in note_info["flags"]:
                for transcriber in self._transcribers_to_notify:
                    transcriber.register_note(self, note_info)

            # do the sonic implementation of ending the note, as long as it's not silent
            if "silent" not in note_info["flags"]:
                for playback_implementation in self. playback_implementations:
                    playback_implementation.end_note(note_id)

            # remove from active notes and delete the note info
            del self._note_info_by_id[note_id]

    def end_all_notes(self) -> None:
        """
        Ends all notes currently playing
        """
        while len(self._note_info_by_id) > 0:
            self.end_note()

    def num_notes_playing(self) -> int:
        """
        Returns the number of notes currently playing.
        """
        return len(self._note_info_by_id)

    """
    ---------------------------------------- Adding and removing playback ----------------------------------------
    """

    def add_soundfont_playback(self, preset: Union[str, int, Sequence] = "auto", soundfont: str = "default",
                               num_channels: int = 8, audio_driver: str = "default",  max_pitch_bend: int = "default",
                               note_on_and_off_only: bool = False) -> 'ScampInstrument':
        """
        Add a soundfont playback implementation for this instrument.

        :param preset: either a preset number, a tuple of (bank, preset), a string giving a name to search for in the
            soundfont, or the string "auto", in which case the name of this instrument is used to search for a preset.
        :param soundfont: which soundfont to use. This can be either a path to a soundfont or the name of one of the
            soundfonts specified in playback_settings.named_soundfonts. If this instrument belongs to an Ensemble,
            "default" means use the Ensemble default; if not, we will fall back to the default provided in
            playback_settings.
        :param num_channels: how many channels to allocate for managing pitch bends, etc.
        :param audio_driver: which driver to use
        :param max_pitch_bend: max pitch bend to allow
        :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or
            other cc messages. Valuable when using :func:`start_note` instead of :func:`play_note` in music that
            doesn't do any dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on
            separate MIDI channels, since they could potentially change pitch or volume; with this flags, we know they
            won't, so they can share the same MIDI channels, only using an extra one due to microtonality.
        :return: self, for chaining purposes
        """
        soundfont = self.ensemble.default_soundfont \
            if self.ensemble is not None and soundfont == "default" else soundfont

        if isinstance(preset, str):
            preset = Ensemble._resolve_preset_from_name(self.name if preset == "auto" else preset, soundfont)
        elif isinstance(preset, int):
            preset = (0, preset)
        SoundfontPlaybackImplementation(self, bank_and_preset=preset, soundfont=soundfont, num_channels=num_channels,
                                        audio_driver=audio_driver, max_pitch_bend=max_pitch_bend,
                                        note_on_and_off_only=note_on_and_off_only)
        return self

    def remove_soundfont_playback(self) -> 'ScampInstrument':
        """
        Remove the most recent SoundfontPlaybackImplementation from this instrument.

        :return: self, for chaining purposes
        """
        for index in reversed(range(len(self.playback_implementations))):
            if isinstance(self.playback_implementations[index], SoundfontPlaybackImplementation):
                self.playback_implementations.pop(index)
                break
        return self

    def add_streaming_midi_playback(self, midi_output_device: Union[int, str] = "default", num_channels: int = 8,
                                    midi_output_name: str = None, max_pitch_bend: int = "default",
                                    note_on_and_off_only: bool = False, start_channel: int = 0) -> 'ScampInstrument':
        """
        Add a streaming MIDI playback implementation for this instrument.

        :param midi_output_device: name or number of the device to use
        :param num_channels: how many channels to allocate for managing pitch bends, etc.
        :param midi_output_name: name given to the output stream
        :param max_pitch_bend: max pitch bend to allow
        :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or
            other cc messages. Valuable when using :func:`start_note` instead of :func:`play_note` in music that
            doesn't do any dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on
            separate MIDI channels, since they could potentially change pitch or volume; with this flags, we know they
            won't, so they can share the same MIDI channels, only using an extra one due to microtonality.
        :param start_channel: the first channel to use. For instance, if start_channel is 4, and num_channels is 5,
            we will use channels (4, 5, 6, 7, 8). NOTE: channel counting in SCAMP starts from 0, so this may show
            up as channels 5-9 in your MIDI software.
        :return: self, for chaining purposes
        """
        MIDIStreamPlaybackImplementation(self, midi_output_device=midi_output_device, num_channels=num_channels,
                                         midi_output_name=midi_output_name, max_pitch_bend=max_pitch_bend,
                                         note_on_and_off_only=note_on_and_off_only, start_channel=start_channel)
        return self

    def remove_streaming_midi_playback(self) -> 'ScampInstrument':
        """
        Remove the most recent MIDIStreamPlaybackImplementation from this instrument.

        :return: self, for chaining purposes
        """
        for index in reversed(range(len(self.playback_implementations))):
            if isinstance(self.playback_implementations[index], MIDIStreamPlaybackImplementation):
                self.playback_implementations.pop(index)
                break
        return self

    def add_osc_playback(self, port: int, ip_address: str = "127.0.0.1", message_prefix: str = None,
                         osc_message_addresses: dict = "default"):
        """
        Add an OSCPlaybackImplementation for this instrument.

        :param port: port to use
        :param ip_address: ip address to use
        :param message_prefix: the prefix to give to all outgoing osc messages; defaults to the instrument name
            with all spaces removed.
        :param osc_message_addresses: the specifix message addresses to be used for each type of message. Defaults are
            defined in playback_settings
        :return: self, for chaining purposes
        """
        OSCPlaybackImplementation(self, port=port, ip_address=ip_address, message_prefix=message_prefix,
                                  osc_message_addresses=osc_message_addresses)
        return self

    def remove_osc_playback(self) -> 'ScampInstrument':
        """
        Remove the most recent OSCPlaybackImplementation from this instrument.

        :return: self, for chaining purposes
        """
        for index in reversed(range(len(self.playback_implementations))):
            if isinstance(self.playback_implementations[index], OSCPlaybackImplementation):
                self.playback_implementations.pop(index)
                break
        return self

    """
    ------------------------------------------------- Other -----------------------------------------------------
    """

    def set_max_pitch_bend(self, semitones: int) -> None:
        """
        Set the max pitch bend for all midi playback implementations on this instrument
        """
        for playback_implementation in self.playback_implementations:
            playback_implementation.set_max_pitch_bend(semitones)

    def send_midi_cc(self, cc_number: int, value_from_0_to_1: float) -> None:
        """
        Sends a midi cc message to all midi-based playback implementations, affecting all channels this instrument uses.
        This is useful for stuff like pedal messages, that we don't really want to bundle with note playback, and that
        we want to apply to all channels.

        :param cc_number: the cc number from 0 to 127
        :param value_from_0_to_1: the value to send, normalized from 0 to 1
        """
        for playback_implementation in self.playback_implementations:
            if hasattr(playback_implementation, "cc"):
                for chan in range(playback_implementation.num_channels):
                    playback_implementation.cc(chan, cc_number, value_from_0_to_1)

    @property
    def clef_preference(self):
        """
        The clef preference for this instrument. Can be any of:

        - "from_name", which picks clef based on the instrument name
        - "default", which uses the default clef preferences for an unknown instrument
        - the name of a clef
        - the name of an instrument whose clef defaults to use
        - a list of possible clefs. Each of these choices should be either a valid clef name string or a tuple of (valid clef name string, center pitch).

        """
        return self._clef_preference

    @clef_preference.setter
    def clef_preference(self, value):
        old_value = self._clef_preference
        self._clef_preference = value
        try:
            self.resolve_clef_preference()
        except RuntimeError as e:
            self._clef_preference = old_value
            raise e

    def resolve_clef_preference(self) -> Sequence[Union[str, Tuple[str, Real]]]:
        """
        Resolves the clef preference to a sequence of possible clef choices.
        """
        if isinstance(self.clef_preference, str):
            if self.clef_preference == "from_name":
                # base clef preference on instrument name
                if self.name.lower().strip() in engraving_settings.clefs_by_instrument:
                    return engraving_settings.clefs_by_instrument[self.name.lower().strip()]
                else:
                    # instrument name is not found, so revert to default clef preferences
                    return engraving_settings.clefs_by_instrument["default"]
            elif self.clef_preference == "default":
                # just use the default clef preferences
                return engraving_settings.clefs_by_instrument["default"]
            elif self.clef_preference in engraving_settings.clef_pitch_centers:
                # clef preference is the name of a clef
                return [self.clef_preference]
            elif self.clef_preference.lower().strip() in engraving_settings.clefs_by_instrument:
                # clef preference is an instrument name
                return engraving_settings.clefs_by_instrument[self.clef_preference.lower().strip()]
            raise RuntimeError("Clef preference could not be resolved.")
        elif isinstance(self.clef_preference, Sequence):
            # if not a string, clef preference should be a sequence of possible clef choices
            # each of these choices should be either a valid clef name string or a tuple of
            # (valid clef name string, center pitch)
            if all(
                x in engraving_settings.clef_pitch_centers or hasattr(x, "__len__") and
                x[0] in engraving_settings.clef_pitch_centers and isinstance(x[1], Real)
                for x in self.clef_preference
            ):
                return self.clef_preference
            else:
                raise RuntimeError("Clef preference not understood.")
        else:
            raise RuntimeError("Clef preference not understood.")

    @property
    def default_spelling_policy(self):
        """
        The default spelling policy for notes played back by this instrument. (Can be set with either a
        :class:`~scamp.spelling.SpellingPolicy` or a string, which is passed to
        :func:`~scamp.spelling.SpellingPolicy.from_string`)
        """
        return self._default_spelling_policy

    @default_spelling_policy.setter
    def default_spelling_policy(self, value: Union[SpellingPolicy, str]):
        if value is None or isinstance(value, SpellingPolicy):
            self._default_spelling_policy = value
        elif isinstance(value, str):
            self._default_spelling_policy = SpellingPolicy.from_string(value)
        else:
            raise ValueError("Spelling policy not understood.")

    """
    --------------------------------------------- To / from JSON -------------------------------------------------
    """

    def save_to_json(self, file_path: str) -> None:
        self._export_as_stand_alone = True
        super().save_to_json(file_path)
        self._export_as_stand_alone = False

    def json_dumps(self) -> str:
        self._export_as_stand_alone = True
        out = super().json_dumps()
        self._export_as_stand_alone = False
        return out

    def _to_dict(self):
        return {
            "name": self.name,
            "playback_implementations": self.playback_implementations,
            "default_spelling_policy": self.default_spelling_policy,
            "clef_preference": self.clef_preference,
            "standalone": self._export_as_stand_alone
        }

    @classmethod
    def _from_dict(cls, json_dict):
        # "standalone" means that the instrument was not part of an ensemble. Check that key then delete it.
        standalone = json_dict["standalone"]
        del json_dict["standalone"]
        playback_implementations = json_dict["playback_implementations"]
        del json_dict["playback_implementations"]
        # reconstruct the instrument
        instrument = cls(**json_dict)
        instrument.playback_implementations = playback_implementations

        if standalone:
            # if it was a standalone instrument, connect up its playback implementation now
            for playback_implementation in instrument.playback_implementations:
                playback_implementation.set_host_instrument(instrument)
            # if not, this will happen in the ensemble's _from_dict method
        return instrument

    def __str__(self):
        return "ScampInstrument({})".format(self.name)

    def __repr__(self):
        return "ScampInstrument._from_dict({})".format(self._to_dict())


class NoteHandle:
    """
    This handle, which is returned by instrument.start_note, allows us to manipulate the note that we have started,
    (i.e. by changing pitch, volume, or another other parameter, or by ending the note). You would never create
    one of these directly.

    :param note_id: the reference id of the note
    :param instrument: the instrument playing the note
    :ivar note_id: the reference id of the note
    :ivar instrument: the instrument playing the note
    """

    def __init__(self, note_id: int, instrument: ScampInstrument):
        self.note_id: int = note_id
        self.instrument: ScampInstrument = instrument

    def change_parameter(self, param_name: str, target_value_or_values: Union[float, Sequence],
                         transition_length_or_lengths: Union[float, Sequence] = 0,
                         transition_curve_shape_or_shapes: Union[float, Sequence] = 0, clock: Clock = None) -> None:
        """
        Change a custom playback parameter for this note to a given target value or values, over a given duration and
        with a given curve shape.

        :param param_name: name of the parameter to change
        :param target_value_or_values: either a single value or a list of values to which we want to change the
            parameter of interest.
        :param transition_length_or_lengths: the duration (in beats) that we want it to take to reach the target value.
            The default value of 0 represents an instantaneous change. If multiple target values were given, a list of
            durations should be given for each segment.
        :param transition_curve_shape_or_shapes: the curve shape used in transitioning to the new target value.
            The default value of 0 represents an linear change, a value greater than zero represents late change,
            and a value less than 0 represents early change. If multiple target values were given, a list of curve
            shapes should be given (unless it is left as the default 0, in which case all segments are linear).
        :param clock: The clock with which to interpret the transition timings. The default value of "from_note", which
            you likely don't want to change, carries out the timings on the clock on which the note was started.
        """
        self.instrument.change_note_parameter(self.note_id, param_name, target_value_or_values,
                                              transition_length_or_lengths, transition_curve_shape_or_shapes, clock)

    def change_pitch(self, target_value_or_values: Union[float, Sequence],
                     transition_length_or_lengths: Union[float, Sequence] = 0,
                     transition_curve_shape_or_shapes: Union[float, Sequence] = 0, clock: Clock = None) -> None:
        """
        Change the pitch of this note to a given target value or values, over a given duration and with a given
        curve shape.

        :param target_value_or_values: either a single target pitch or a list of target pitches.
        :param transition_length_or_lengths: the duration (in beats) that we want it to take to reach the target pitch.
            The default value of 0 represents an instantaneous change. If multiple target values were given, a list of
            durations should be given for each segment.
        :param transition_curve_shape_or_shapes: the curve shape used in transitioning to the new target pitch.
            The default value of 0 represents an linear change, a value greater than zero represents late change,
            and a value less than 0 represents early change. If multiple target values were given, a list of curve
            shapes should be given (unless it is left as the default 0, in which case all segments are linear).
        :param clock: The clock with which to interpret the transition timings. The default value of "from_note", which
            you likely don't want to change, carries out the timings on the clock on which the note was started.
        """
        self.instrument.change_note_pitch(self.note_id, target_value_or_values, transition_length_or_lengths,
                                          transition_curve_shape_or_shapes, clock)

    def change_volume(self,  target_value_or_values: Union[float, Sequence],
                      transition_length_or_lengths: Union[float, Sequence] = 0,
                      transition_curve_shape_or_shapes: Union[float, Sequence] = 0, clock: Clock = None) -> None:
        """
        Change the volume of this note to a given target value or values, over a given duration and with a given
        curve shape.

        :param target_value_or_values: either a single target volume or a list of target volumes.
        :param transition_length_or_lengths: the duration (in beats) that we want it to take to reach the target volume.
            The default value of 0 represents an instantaneous change. If multiple target values were given, a list of
            durations should be given for each segment.
        :param transition_curve_shape_or_shapes: the curve shape used in transitioning to the new target volume.
            The default value of 0 represents an linear change, a value greater than zero represents late change,
            and a value less than 0 represents early change. If multiple target values were given, a list of curve
            shapes should be given (unless it is left as the default 0, in which case all segments are linear).
        :param clock: The clock with which to interpret the transition timings. The default value of "from_note", which
            you likely don't want to change, carries out the timings on the clock on which the note was started.
        """
        self.instrument.change_note_volume(self.note_id, target_value_or_values, transition_length_or_lengths,
                                           transition_curve_shape_or_shapes, clock)

    def split(self) -> None:
        """
        Adds a split point to this note, causing it later to be rendered as tied pieces.
        """
        self.instrument.split_note(self.note_id)

    def end(self) -> None:
        """
        Ends this note.
        """
        self.instrument.end_note(self.note_id)

    def __repr__(self):
        return "NoteHandle({}, {})".format(self.note_id, self.instrument)


class ChordHandle:
    """
    This handle, returned by instrument.start_chord, allows us to manipulate a chord that we have started,
    (i.e. by changing pitch, volume, or another other parameter, or by ending the note). You would never create
    one of these directly.

    :param note_handles: the handles of the notes that make up this chord
    :param intervals: the original pitch intervals between the chord tones
    :ivar note_handles: the handles of the notes that make up this chord
    """
    def __init__(self, note_handles: Sequence[NoteHandle], intervals: Sequence[float]):
        self.note_handles = tuple(note_handles) if not isinstance(note_handles, tuple) else note_handles
        self._intervals = tuple(intervals) if not isinstance(intervals, tuple) else intervals

    def change_parameter(self, param_name: str, target_value_or_values: Union[float, Sequence],
                         transition_length_or_lengths: Union[float, Sequence] = 0,
                         transition_curve_shape_or_shapes: Union[float, Sequence] = 0, clock: Clock = None) -> None:
        """
        Change a custom playback parameter for all notes in this chord to a given target value or values, over a given
        duration and with a given curve shape.

        :param param_name: name of the parameter to change
        :param target_value_or_values: either a single value or a list of values to which we want to change the
            parameter of interest.
        :param transition_length_or_lengths: the duration (in beats) that we want it to take to reach the target value.
            The default value of 0 represents an instantaneous change. If multiple target values were given, a list of
            durations should be given for each segment.
        :param transition_curve_shape_or_shapes: the curve shape used in transitioning to the new target value.
            The default value of 0 represents an linear change, a value greater than zero represents late change,
            and a value less than 0 represents early change. If multiple target values were given, a list of curve
            shapes should be given (unless it is left as the default 0, in which case all segments are linear).
        :param clock: The clock with which to interpret the transition timings. The default value of "from_note", which
            you likely don't want to change, carries out the timings on the clock on which the note was started.
        """
        for note_handle in self.note_handles:
            note_handle.change_parameter(param_name, target_value_or_values, transition_length_or_lengths,
                                         transition_curve_shape_or_shapes, clock)

    def change_pitch(self, target_value_or_values: Union[float, Sequence],
                     transition_length_or_lengths: Union[float, Sequence] = 0,
                     transition_curve_shape_or_shapes: Union[float, Sequence] = 0, clock: Clock = None) -> None:
        """
        Change the pitches of this chord such that the first note of the chord goes to the given target value or values,
        over a given duration and with a given curve shape.

        :param target_value_or_values: either a single target pitch or a list of target pitches. Note that this is the
            pitch that the first note of the chord gets changed to; all of the other notes in the chord follow suit,
            maintaining the same interval as before with the first note of the chord.
        :param transition_length_or_lengths: the duration (in beats) that we want it to take to reach the target pitch.
            The default value of 0 represents an instantaneous change. If multiple target values were given, a list of
            durations should be given for each segment.
        :param transition_curve_shape_or_shapes: the curve shape used in transitioning to the new target pitch.
            The default value of 0 represents an linear change, a value greater than zero represents late change,
            and a value less than 0 represents early change. If multiple target values were given, a list of curve
            shapes should be given (unless it is left as the default 0, in which case all segments are linear).
        :param clock: The clock with which to interpret the transition timings. The default value of "from_note", which
            you likely don't want to change, carries out the timings on the clock on which the note was started.
        """
        for note_handle, interval in zip(self.note_handles, self._intervals):
            this_note_pitch_targets = [target_value + interval for target_value in target_value_or_values] \
                if hasattr(target_value_or_values, "__len__") else target_value_or_values + interval
            note_handle.change_pitch(this_note_pitch_targets, transition_length_or_lengths,
                                     transition_curve_shape_or_shapes, clock)

    def change_volume(self,  target_value_or_values: Union[float, Sequence],
                      transition_length_or_lengths: Union[float, Sequence] = 0,
                      transition_curve_shape_or_shapes: Union[float, Sequence] = 0, clock: Clock = None) -> None:
        """
        Change the volume for all notes in this chord to a given target value or values, over a given duration and with
        a given curve shape.

        :param target_value_or_values: either a single target volume or a list of target volumes.
        :param transition_length_or_lengths: the duration (in beats) that we want it to take to reach the target volume.
            The default value of 0 represents an instantaneous change. If multiple target values were given, a list of
            durations should be given for each segment.
        :param transition_curve_shape_or_shapes: the curve shape used in transitioning to the new target volume.
            The default value of 0 represents an linear change, a value greater than zero represents late change,
            and a value less than 0 represents early change. If multiple target values were given, a list of curve
            shapes should be given (unless it is left as the default 0, in which case all segments are linear).
        :param clock: The clock with which to interpret the transition timings. The default value of "from_note", which
            you likely don't want to change, carries out the timings on the clock on which the note was started.
        """
        for note_handle in self.note_handles:
            note_handle.change_volume(target_value_or_values, transition_length_or_lengths,
                                      transition_curve_shape_or_shapes, clock)

    def split(self) -> None:
        """
        Adds a split point to this chord, causing it later to be rendered as tied pieces.
        """
        for note_handle in self.note_handles:
            note_handle.split()

    def end(self) -> None:
        """
        Ends all notes in this chord.
        """
        for note_handle in self.note_handles:
            note_handle.end()

    def __repr__(self):
        return "ChordHandle({}, {})".format(self.note_handles, self._intervals)


class _ParameterChangeSegment(EnvelopeSegment):

    """
    Convenience class for handling interruptable transitions of parameter values and storing info on them
    (This is an implementation detail.)

    :param parameter_change_function: since this is for general parameters, we pass the function to be called
    to set the parameter. Generally will call _do_change_note_parameter/pitch/volume for a given note_id
    :param start_value: start value of the parameter in the transition
    :param target_value: target value of the parameter in the transition
    :param transition_length: length of the transition in beats on the clock given
    :param transition_curve_shape: curve shape of the transition
    :param clock: the clock that all of this happens in reference to
    :param call_priority: this is used to determine which call to change_parameter happened first, since once these
    things get spawned in threads, the order gets indeterminate.
    :param temporal_resolution: time resolution of the unsynchronized process. One of the following:
     - just a number (in seconds)
     - the string "pitch-based", in which case we derive it based on trying to get a smooth pitch change
     - the string "volume-based", in which case we derive it based on trying to get a smooth volume change.
    """

    def __init__(self, parameter_change_function, start_value, target_value, transition_length, transition_curve_shape,
                 clock, call_priority, temporal_resolution=0.01):
        # set this up as an envelope
        super().__init__(0, transition_length, start_value, target_value, transition_curve_shape)
        # "do_change_parameter" feels more like an action name
        self.do_change_parameter = parameter_change_function

        self.clock = clock  # the parent clock that this process runs on
        self._run_clock = None  # the sub-clock created by forking this process
        self.running = False  # flag used for aborting the unsynchronized process

        # some of the key data that this envelope holds onto are the time stamps at which it starts and finishes
        # this can be used to construct the appropriate envelope segment on whichever clock we're recording on
        self.start_time_stamp = None
        self.end_time_stamp = None
        self.call_priority = call_priority

        self.temporal_resolution = temporal_resolution

    def run(self, silent=False):
        """
        Runs the segment from start to finish, gradually changing the parameter.
        This function runs as a synchronized clock process (it should be forked), and it starts a parallel,
        unsynchronized process ("_animation_function") to do the actual calls to change parameter

        :param silent: this flag causes none of the animation to actually happen. This is used when we're trying to
        notate a note but not play it back, as in the case of a note that has been adjusted (where we playback -- but
        don't notate -- the adjusted version, while we run -- but don't play back -- the unadjusted version.)
        """
        self.start_time_stamp = TimeStamp(self.clock)

        # if this segment has no duration, no need to do any animation
        # just set it to the final value and return
        if self.duration == 0:
            self.end_time_stamp = TimeStamp(self.clock)
            self.do_change_parameter(self.end_level)
            return

        self.start_time_stamp = TimeStamp(self.clock)
        self.running = True  # used to kill the unsynchronized process when we abort or this synchronized one ends

        # we note down the clock we're running this on. If abort is called, this clock gets killed
        self._run_clock = current_clock()

        # if there's no change, or if we're skipping animation, just wait and finish
        if self.end_level == self.start_level or silent:
            wait(self.duration)
            self.end_time_stamp = TimeStamp(self.clock)
            self.do_change_parameter(self.end_level)
            self.running = False
            return

        # determine the time increment, perhaps by calculating a good one for the given parameter
        if self.temporal_resolution == "pitch-based":
            time_increment = self._get_good_pitch_bend_temporal_resolution()
        elif self.temporal_resolution == "volume-based":
            time_increment = self._get_good_volume_temporal_resolution()
        else:
            time_increment = self.temporal_resolution
        # don't animate faster than 4ms though
        time_increment = max(0.004, time_increment)

        def _animation_function():
            # does the intermediate changing of values; since it's sleeping in small time increments, we fork it
            # as unsynchronized parallel process so that it doesn't gum up the clocks with the overhead of
            # waking and sleeping rapidly
            beats_passed = 0

            while beats_passed < self.duration and self.running:
                start = time.time()
                if beats_passed > 0:  # no need to change the parameter the first time, before we had a chance to wait
                    self.do_change_parameter(self.value_at(beats_passed))
                time.sleep(time_increment)
                # TODO: Absolute_rate would be great, except that it doesn't update between synchronized clock events
                # Is there a way of improving this??
                beats_passed += (time.time() - start) * self.clock.absolute_rate()

        # start the unsynchronized animation function
        self.clock.fork_unsynchronized(_animation_function)
        # waits in a synchronized fashion so that it can save an accurate time stamp at the end
        wait(self.duration)

        # we only get here if it wasn't aborted while running, since that will call kill on the child clock
        self.running = False
        self.end_time_stamp = TimeStamp(self.clock)
        self.do_change_parameter(self.end_level)

    def abort_if_running(self):
        if self.running:
            # if we were running, we save the time stamp at which we aborted as the end time stamp
            self.end_time_stamp = TimeStamp(self.clock)
            self._run_clock.kill()  # kill the clock doing the "run" function
            # since the units of this envelope are beats in self.clock, see how far we got in the envelope by
            # subtracting converting the start and end time stamps to those beats and subtracting
            how_far_we_got = self.end_time_stamp.beat_in_clock(self.clock) - \
                             self.start_time_stamp.beat_in_clock(self.clock)

            # now split there, discarding the rest of the envelope. This makes self.end_level the value we ended up at.
            if self.start_time < how_far_we_got < self.end_time:
                self.split_at(how_far_we_got)
            elif self.start_time == how_far_we_got:
                # this was aborted before it even got going. Later, the transcriber will ignore this nothing segment
                self.end_time = self.start_time
                self.end_level = self.start_level
                self.running = False
                return

            self.do_change_parameter(self.end_level)  # set it to where we should be at this point
        self.running = False  # this will make sure to abort the animation function

    def completed(self):
        # it's not running, but because it finished, not because it never started
        return not self.running and self.end_time_stamp is not None

    def _get_good_pitch_bend_temporal_resolution(self):
        """
        Returns a reasonable temporal resolution, based on this clock's envelope and rate, assuming it's a pitch curve
        """
        max_cents_per_second = self.max_absolute_slope() * 100 * self.clock.absolute_rate()
        # cents / update * updates / sec = cents / sec   =>  updates_freq = cents_per_second / cents_per_update
        # we'll aim for 4 cents per update, since some say the JND is 5-6 cents
        update_freq = max_cents_per_second / 4.0
        return 1 / update_freq

    def _get_good_volume_temporal_resolution(self):
        """
        Returns a reasonable temporal resolution, based on this clock's envelope and rate, assuming it's a volume curve
        """
        max_volume_per_second = self.max_absolute_slope() * self.clock.absolute_rate()
        # based on the idea that for midi volumes, it's quantized from 0 to 127, so there's not much point in updating
        # in between those quantization levels. It's a decent enough rule even if not using midi output.
        update_freq = max_volume_per_second * 127
        return 1 / update_freq

    def __repr__(self):
        return "_ParameterChangeSegment[{}, {}, {}, {}, {}]".format(
            self.start_time_stamp, self.end_time_stamp, self.start_level, self.end_level, self.curve_shape
        )
