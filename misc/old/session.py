from .performance import Performance
from .ensemble import Ensemble
from .instruments import ScampInstrument
from .midi_listener import *
from .spelling import SpellingPolicy
from clockblocks import Clock


class Session(Clock):

    def __init__(self, soundfonts="default", audio_driver=None, midi_output_device=None):
        """
        :param soundfonts: the names / paths of the soundfonts this scamp will use
        :param audio_driver: the driver used to output audio (if none, defaults to whatever fluidsynth chooses)
        :param midi_output_device: the default midi_output_device for outgoing midi streams. These can also be
        specified on a per-instrument basis, but this sets a global default. Defaults to creating virtual devices.
        """

        self._ensemble = None
        self.set_ensemble(Ensemble(soundfonts, audio_driver, midi_output_device))

        # Clock keeps track of time and can spawn subordinate clocks
        super().__init__("MASTER")
        self._recording_clock = None
        self._recording_start_time = None

        # A policy for spelling notes used as the default for the entire session
        # Useful if the entire session is in a particular key, for instance
        self._default_spelling_policy = None

        # The Performance object created when we record
        self.performance: Performance = None

    # ----------------------------------- Listeners ----------------------------------

    @staticmethod
    def get_available_ports_and_devices():
        return get_available_ports_and_devices()

    @staticmethod
    def print_available_ports_and_devices():
        print_available_ports_and_devices()

    def register_midi_callback(self, port_number_or_device_name, callback_function,
                               time_resolution=0.005, synchronous=False):
        start_midi_listener(port_number_or_device_name, callback_function,
                            clock=self, time_resolution=time_resolution, synchronous=synchronous)

    # --------------------------------- Ensemble Stuff -------------------------------

    @property
    def ensemble(self):
        return self._ensemble

    @ensemble.setter
    def ensemble(self, ensemble: Ensemble):
        self.set_ensemble(ensemble)

    def set_ensemble(self, ensemble: Ensemble):
        self._ensemble = ensemble
        self._ensemble.host_session = self

    def get_instruments_with_substring(self, word, avoid=None, soundfont_index=0):
        return self._ensemble.get_instruments_with_substring(word, avoid=avoid, soundfont_index=soundfont_index)

    def iter_presets(self, soundfont_id=None):
        return self._ensemble.iter_presets(soundfont_index=soundfont_id)

    def print_all_soundfont_presets(self):
        self._ensemble.print_all_soundfont_presets()

    def add_part(self, instrument):
        assert isinstance(instrument, ScampInstrument)
        return self._ensemble.add_part(instrument)

    def add_midi_part(self, name=None, preset="auto", soundfont_index=None, num_channels=8,
                      midi_output_device=None, midi_output_name=None):
        assert isinstance(self._ensemble, Ensemble)
        return self._ensemble.add_midi_part(name, preset, soundfont_index, num_channels,
                                            midi_output_device, midi_output_name)

    def add_silent_part(self, name=None):
        return self._ensemble.add_silent_part(name)

    def add_osc_part(self, port, name=None, ip_address="127.0.0.1", message_prefix=None,
                     osc_message_addresses="default"):
        """
        Constructs an OSCScampInstrument, adds it to the Ensemble, and returns it
        :param port: The port to send OSC Messages to (required)
        :param name: The name of the instrument
        :param ip_address: IP Address to send to; defaults to localhost
        :param message_prefix: the first part of the message address. Defaults to name or "unnamed" if name is None.
        If two instruments have the same name, this can be used to give them distinct messages
        :param osc_message_addresses: A dictionary defining the strings used in the address of different kinds of
        messages. The defaults are defined in playbackSettings.json, and you probably would never change them. But
        just in case you have no control over which messages you listen for, the option is there.
        :rtype : OSCScampInstrument
        """
        return self._ensemble.add_osc_part(port, name=name, ip_address=ip_address, message_prefix=message_prefix,
                                           osc_message_addresses=osc_message_addresses)

    def save_ensemble_to_json(self, filepath):
        self._ensemble.save_to_json(filepath)

    def load_ensemble_from_json(self, filepath):
        self.set_ensemble(Ensemble.load_from_json(filepath))

    # ----------------------------- Modifying MIDI Settings --------------------------

    @property
    def audio_driver(self):
        return self._ensemble.audio_driver

    @audio_driver.setter
    def audio_driver(self, audio_driver):
        self._ensemble.audio_driver = audio_driver

    @property
    def default_midi_output_device(self):
        return self._ensemble.default_midi_output_device

    @default_midi_output_device.setter
    def default_midi_output_device(self, device):
        self._ensemble.default_midi_output_device = device

    def load_soundfont(self, soundfont):
        self._ensemble.load_soundfont(soundfont)

    # --------------------------------- Recording Stuff -------------------------------

    def start_recording(self, which_parts=None, clock="master"):
        if isinstance(clock, str) and clock == "master":
            clock = self
        assert clock == "absolute" or isinstance(clock, Clock)
        self._recording_clock = clock
        self._recording_start_time = self.time() if clock == "absolute" else clock.beat()
        which_parts = self._ensemble.instruments if which_parts is None else which_parts
        self.performance = Performance()
        # set a performance_part for each instrument
        for instrument in which_parts:
            new_part = self.performance.new_part(instrument)
            instrument._performance_part = new_part

    def is_recording(self):
        return self._recording_start_time is not None

    def get_recording_beat(self):
        if self._recording_clock == "absolute":
            return self.time() - self._recording_start_time
        else:
            return self._recording_clock.beat() - self._recording_start_time

    def stop_recording(self, tempo_envelope_tolerance=0.001):
        """
        Stop recording and save the recording as a Performance
        :type tempo_envelope_tolerance: when we record on a child clock and we extract the absolute tempo curve,
        this is the degree of error in tempo that we allow in simplifying the curve. You should probably
        not be worrying about this, honestly.
        """
        for part in self.performance.parts:
            instrument = part.instrument
            instrument.end_all_notes()
            instrument._performance_part = None
        if isinstance(self._recording_clock, Clock):
            self.performance.tempo_envelope = self._recording_clock.extract_absolute_tempo_envelope(
                self._recording_start_time, tolerance=tempo_envelope_tolerance
            )
        self._recording_start_time = None
        return self.performance

    @property
    def default_spelling_policy(self):
        return self._default_spelling_policy

    @default_spelling_policy.setter
    def default_spelling_policy(self, value):
        if value is None or isinstance(value, SpellingPolicy):
            self._default_spelling_policy = value
        elif isinstance(value, str):
            self._default_spelling_policy = SpellingPolicy.from_string(value)
        else:
            raise ValueError("Spelling policy not understood.")
