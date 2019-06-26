from .ensemble import Ensemble
from .transcriber import Transcriber
from .midi_listener import *
from .instruments import ScampInstrument
from clockblocks import Clock, wait, current_clock
from typing import Sequence
from .utilities import SavesToJSON
from threading import Thread, current_thread


class Session(Clock, Ensemble, Transcriber, SavesToJSON):

    def __init__(self, tempo=60, default_soundfont="default", default_audio_driver="default",
                 default_midi_output_device="default"):
        """
        A Session combines the functionality of a master clock, an ensemble, and a transcriber.

        :param tempo: the initial tempo of the master clock
        :param default_soundfont: the default soundfont used by instruments in this session. (Can be overridden at
            instrument creation.)
        :param default_audio_driver: the default driver used by (soundfont) instruments to output audio. (Can be
            overridden at instrument creation.)
        :param default_midi_output_device: the default midi_output_device for outgoing midi streams. (Again, can be
            overridden at instrument creation.)
        """

        # noinspection PyArgumentList
        Clock.__init__(self, name="MASTER", initial_tempo=tempo)
        Ensemble.__init__(self, default_soundfont=default_soundfont, default_audio_driver=default_audio_driver,
                          default_midi_output_device=default_midi_output_device)
        Transcriber.__init__(self)

        # A policy for spelling notes used as the default for the entire session
        # Useful if the entire session is in a particular key, for instance
        self._default_spelling_policy = None

    def run_as_server(self, time_step=0.01):
        """
        Runs this session on a parallel thread so that it can act as a server. This is the approach that should be taken
        if running scamp from an interactive terminal session. Simply type "s = Session().run_as_server()"

        :param time_step: time step for the server loop.
        :return: self
        """
        def run_server():
            current_thread().__clock__ = self
            while True:
                wait(time_step)

        Thread(target=run_server, daemon=True).start()
        # don't have the thread that called this recognize the Session as its clock anymore
        current_thread().__clock__ = None
        return self

    # ----------------------------------- Listeners ----------------------------------

    @staticmethod
    def get_available_midi_ports_and_devices():
        """
        Returns a list of available midi ports and devices.
        """
        return get_available_ports_and_devices()

    @staticmethod
    def print_available_midi_ports_and_devices():
        """
        Prints a list of available midi ports and devices for reference.
        """
        print_available_ports_and_devices()

    def register_midi_callback(self, port_number_or_device_name, callback_function,
                               time_resolution=0.005, synchronous=True):
        """
        Register a callback_function to respond to incoming midi events from port_number_or_device_name

        :param port_number_or_device_name: either the port number to be used, or an device name for which the port
            number will be determined.
        :param callback_function: the callback function used when a new midi event arrives. Should take either one
            argument (the midi message) or two arguments (the midi message, and the dt since the last message)
        :param time_resolution: time resolution used in checking for midi events
        :param synchronous: controls whether this callback operates as a synchronous child clock or as an
            asynchronous parallel thread
        """
        start_midi_listener(port_number_or_device_name, callback_function,
                            clock=self, time_resolution=time_resolution, synchronous=synchronous)

    # --------------------------------- Recording Stuff -------------------------------

    def start_recording(self, instruments: Sequence[ScampInstrument] = None, clock: Clock = None, units="beats"):
        """
        Starts a recording, defaults to using the session (master) clock and all session instruments

        :param instruments: which instruments to record
        :param clock: which clock to record on, i.e. what are all the timings notated relative to
        :param units: one of ["beats", "time"]. Do we use the beats of the clock or the time?
        :return the Performance we will be recording to
        """
        if instruments is None and len(self.instruments) == 0:
            raise ValueError("Can't record with empty ensemble; did you call \"start_recording\" before adding "
                             "parts to the session?")

        return super().start_recording(self.instruments if instruments is None else instruments,
                                       self if clock is None else clock, units=units)

    def to_json(self):
        json_object = Ensemble.to_json(self)
        json_object["tempo"] = self.tempo
        return json_object

    @classmethod
    def from_json(cls, json_dict):
        json_instruments = json_dict.pop("instruments")
        default_spelling_policy = json_dict.pop("default_spelling_policy")
        session = cls(**json_dict)
        session.default_spelling_policy = default_spelling_policy
        session.instruments = [ScampInstrument.from_json(json_instrument, session)
                               for json_instrument in json_instruments]
        return session

    def __repr__(self):
        return "Session.from_json({})".format(self.to_json())
