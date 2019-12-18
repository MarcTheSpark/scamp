from .ensemble import Ensemble
from .transcriber import Transcriber
from .midi_listener import *
from .instruments import ScampInstrument
from clockblocks import Clock, wait
from typing import Sequence
from .utilities import SavesToJSON
from ._dependencies import pynput
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

    def register_midi_callback(self, port_number_or_device_name, callback_function, time_resolution=0.005):
        """
        Register a callback_function to respond to incoming midi events from port_number_or_device_name

        :param port_number_or_device_name: either the port number to be used, or an device name for which the port
            number will be determined.
        :param callback_function: the callback function used when a new midi event arrives. Should take either one
            argument (the midi message) or two arguments (the midi message, and the dt since the last message)
        :param time_resolution: time resolution used in checking for midi events
        """
        start_midi_listener(port_number_or_device_name, callback_function, clock=self, time_resolution=time_resolution)

    def register_keyboard_callback(self, on_press=None, on_release=None, suppress=False, **kwargs):
        """
        Register a callback_function to respond to incoming keyboard events

        :param on_press: function taking two arguments: key name (string) and key number (int) called on key down
        :param on_release: function taking two arguments: key name (string) and key number (int) called on key up
        :param suppress: if true, keyboard events are consumed and not passed on to other processes
        """
        if pynput is None:
            raise ImportError("Cannot use keyboard input because package pynput was not found. "
                              "Install pynput and try again.")

        keys_down = []
        if on_press is not None:
            # if on_press is defined, place a wrapper around it that wakes up the the Session when it's called
            def on_press_wrapper(key_argument):
                self.rouse_and_hold()
                threading.current_thread().__clock__ = self
                name, number = Session.name_and_number_from_key(key_argument)
                if name not in keys_down:
                    keys_down.append(name)
                    on_press(name, number)
                threading.current_thread().__clock__ = None
                self.release_from_suspension()
        else:
            on_press_wrapper = None
        if on_release is not None:
            # if on_release is defined, place a wrapper around it that wakes up the the Session when it's called
            def on_release_wrapper(key_argument):
                self.rouse_and_hold()
                threading.current_thread().__clock__ = self
                name, number = Session.name_and_number_from_key(key_argument)
                if name in keys_down:
                    keys_down.remove(name)
                on_release(name, number)
                threading.current_thread().__clock__ = None
                self.release_from_suspension()
        else:
            # otherwise, in case we defined on_press, we need to make sure to remove the key from key down anyway
            def on_release_wrapper(key_argument):
                name, number = Session.name_and_number_from_key(key_argument)
                if name in keys_down:
                    keys_down.remove(name)

        listener = pynput.keyboard.Listener(on_press=on_press_wrapper, on_release=on_release_wrapper,
                                            suppress=suppress, **kwargs)
        listener.start()

    @staticmethod
    def name_and_number_from_key(key_or_key_code):
        # converts the irritating system within pynput to a simple key name and key number
        # TODO: FIX KEY CODES? Why is 'o' the same as space?
        if key_or_key_code is None:
            name = number = None
        elif isinstance(key_or_key_code, pynput.keyboard.Key):
            name = key_or_key_code.name
            number = key_or_key_code.value.vk
        else:
            # it's KeyCode
            name = key_or_key_code.char
            number = key_or_key_code.vk
        return name, number

    def register_mouse_callback(self, on_move=None, on_press=None, on_release=None, on_scroll=None,
                                suppress=False, relative_coordinates=False, **kwargs):
        """
        Register a callback_function to respond to incoming mouse events

        :param on_move: callback function taking two arguments (x, y) called when the mouse is moved
        :param on_press: callback function taking three arguments: (x, y, button), where button is one of
            "left", "right", or "middle"
        :param on_release: callback function taking three arguments: (x, y, button), where button is one of
            "left", "right", or "middle"
        :param on_scroll: callback function taking four arguments: (x, y, dx, dy)
        :param relative_coordinates: if True (requires tkinter library), x and y values are normalized to screen width
            and height and are floating point. Otherwise they are ints in units of pixels.
        :param suppress: if true, mouse events are consumed and not passed on to other processes
        """
        if pynput is None:
            raise ImportError("Cannot use mouse input because package pynput was not found. "
                              "Install pynput and try again.")

        if relative_coordinates:
            try:
                import tkinter as tk
            except ImportError:
                raise ImportError("Cannot use relative coordinates, since the tkinter library is required for"
                                  "determining the screen size.")
            root = tk.Tk()
            x_scale = 1 / root.winfo_screenwidth()
            y_scale = 1 / root.winfo_screenheight()
        else:
            x_scale = y_scale = 1

        # on_move and on_scroll are surrounded with a very simple wrapper that rouses the session and defines it as
        # the current clock on the thread of the callback function
        if on_move is not None:
            def on_move_wrapper(x, y):
                self.rouse_and_hold()
                threading.current_thread().__clock__ = self
                on_move(x * x_scale, y * y_scale)
                threading.current_thread().__clock__ = None
                self.release_from_suspension()
        else:
            on_move_wrapper = None

        if on_scroll is not None:
            def on_scroll_wrapper(x, y, dx, dy):
                self.rouse_and_hold()
                threading.current_thread().__clock__ = self
                on_scroll(x * x_scale, y * y_scale, dx, dy)
                threading.current_thread().__clock__ = None
                self.release_from_suspension()
        else:
            on_scroll_wrapper = None

        # for on_press and on_release, pynput actually uses an on_click function with that takes a pressed argument
        # that seems kind of like a pain; I separate them into two different methods. I also turn button into a
        # string rather than an enum that you have to go find in the pynput package.
        if on_press is not None or on_release is not None:
            def on_click_wrapper(x, y, button, pressed):
                self.rouse_and_hold()
                threading.current_thread().__clock__ = self
                if pressed:
                    on_press(x * x_scale, y * y_scale, button.name)
                else:
                    on_release(x * x_scale, y * y_scale, button.name)
                threading.current_thread().__clock__ = None
                self.release_from_suspension()
        else:
            on_click_wrapper = None

        listener = pynput.mouse.Listener(on_move=on_move_wrapper, on_click=on_click_wrapper,
                                         on_scroll=on_scroll_wrapper, suppress=suppress, **kwargs)
        listener.start()

    # --------------------------------- Transcription Stuff -------------------------------

    def start_transcribing(self, instruments: Sequence[ScampInstrument] = None, clock: Clock = None, units="beats"):
        """
        Starts a transcription, defaults to using the session (master) clock and all session instruments

        :param instruments: which instruments to transcribe
        :param clock: which clock to record on, i.e. what are all the timings notated relative to
        :param units: one of ["beats", "time"]. Do we use the beats of the clock or the time?
        :return the Performance we will be transcribing to
        """
        if instruments is None and len(self.instruments) == 0:
            raise ValueError("Can't record with empty ensemble; did you call \"start_transcribing\" before adding "
                             "parts to the session?")

        return super().start_transcribing(self.instruments if instruments is None else instruments,
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
