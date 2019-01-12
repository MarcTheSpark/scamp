from .utilities import resolve_relative_path, SavesToJSON
from .simple_rtmidi_wrapper import SimpleRtMidiOut
from .settings import playback_settings
from .dependencies import fluidsynth, Sf2File
import logging
from collections import namedtuple


ScampMidiPreset = namedtuple("ScampMidiPreset", "name preset soundfont_index")


class CombinedMidiPlayer(SavesToJSON):

    def __init__(self, soundfonts=None, audio_driver=None, rtmidi_output_device=None):

        if audio_driver is None:
            audio_driver = playback_settings.default_audio_driver

        if rtmidi_output_device is None:
            rtmidi_output_device = playback_settings.default_midi_output_device

        self.used_channels = 0  # how many channels have we already assigned to various instruments

        self.soundfonts = [] if soundfonts is None else soundfonts

        # we need audio_driver to be a property, since every time it's changed we need to restart fluidsynth
        self._audio_driver = audio_driver
        self.rtmidi_output_device = rtmidi_output_device

        self.synth = None
        self.soundfont_ids = []  # the ids of loaded soundfonts
        self.soundfont_instrument_lists = []

        if soundfonts is not None:
            if fluidsynth is not None:
                self.initialize_fluidsynth(audio_driver)

            for soundfont in soundfonts:
                self.load_soundfont(soundfont)

    def add_instrument(self, num_channels, bank_and_preset, soundfont=0,
                       midi_output_device=None, midi_output_name=None):
        midi_output_device = self.rtmidi_output_device if self.rtmidi_output_device is not None \
            else midi_output_device
        return CombinedMidiInstrument(self, num_channels, bank_and_preset, soundfont_id=self.soundfont_ids[soundfont],
                                      midi_output_device=midi_output_device, midi_output_name=midi_output_name)

    def initialize_fluidsynth(self, driver):
        if fluidsynth is not None:
            self.synth = fluidsynth.Synth()
            self.synth.start(driver=driver)
            self._audio_driver = driver

    @property
    def audio_driver(self):
        return self._audio_driver

    @audio_driver.setter
    def audio_driver(self, driver):
        if self.synth is not None:
            self.synth.delete()
        self.initialize_fluidsynth(driver)
        self._audio_driver = driver
        for soundfont in self.soundfonts:
            self.load_soundfont(soundfont)

    def load_soundfont(self, soundfont):
        if fluidsynth is None:
            logging.warning("Attempting to load soundfont, but fluidsynth library was not loaded successfully.")
            return
        elif self.synth is None:
            self.initialize_fluidsynth(self._audio_driver)

        named_soundfonts = playback_settings.get_named_soundfonts()
        if soundfont in named_soundfonts:
            soundfont_path = named_soundfonts[soundfont]
            if soundfont_path.startswith("./"):
                soundfont_path = resolve_relative_path("soundfonts/" + soundfont_path[2:])
            elif not soundfont_path.startswith("/"):
                soundfont_path = resolve_relative_path("soundfonts/" + soundfont_path)
        else:
            soundfont_path = soundfont

        if Sf2File is not None:
            # if we have sf2utils, load up the preset info from the soundfonts
            with open(soundfont_path, "rb") as sf2_file:
                sf2 = Sf2File(sf2_file)
                self.soundfont_instrument_lists.append(sf2.presets)

        self.soundfont_ids.append(self.synth.sfload(soundfont_path))

    def get_instruments_with_substring(self, word, avoid=None, soundfont_index=0):
        if 0 <= soundfont_index < len(self.soundfont_instrument_lists):
            instrument_list = self.soundfont_instrument_lists[soundfont_index]
            return [inst for i, inst in enumerate(instrument_list) if word.lower() in inst.name.lower() and
                    (avoid is None or avoid.lower() not in inst.name.lower())]
        return None

    def iter_presets(self):
        for soundfont_id, soundfont_instrument_list in enumerate(self.soundfont_instrument_lists):
            for sf2_preset in soundfont_instrument_list:
                try:
                    yield ScampMidiPreset(sf2_preset.name, (sf2_preset.bank, sf2_preset.preset), soundfont_id)
                except AttributeError:
                    pass
        raise StopIteration

    def print_all_soundfont_presets(self):
        for i in range(len(self.soundfonts)):
            print("PRESETS FOR {}".format(self.soundfonts[i]))
            for preset in self.soundfont_instrument_lists[i]:
                print("   {}".format(preset))

    def to_json(self):
        return {"soundfonts": self.soundfonts, "audio_driver": self._audio_driver,
                "rtmidi_output_device": self.rtmidi_output_device}

    @classmethod
    def from_json(cls, json_dict):
        return cls(**json_dict)


class CombinedMidiInstrument:

    def __init__(self, combined_midi_player, num_channels, bank_and_preset, soundfont_id=0,
                 midi_output_device=None, midi_output_name=None):
        assert isinstance(combined_midi_player, CombinedMidiPlayer)
        self.combined_midi_player = combined_midi_player
        self.channels = list(range(self.combined_midi_player.used_channels,
                                   self.combined_midi_player.used_channels + num_channels))
        self.num_channels = num_channels
        self.combined_midi_player.used_channels += num_channels
        self.bank_and_preset = bank_and_preset
        self.soundfont_id = soundfont_id

        self.max_pitch_bend = 2

        # since rtmidi can only have 16 output channels, we need to create several output devices if we are using more
        if num_channels <= 16:
            self.rt_simple_outs = [SimpleRtMidiOut(midi_output_device, midi_output_name)]
        else:
            chan = 0
            self.rt_simple_outs = []
            while chan < num_channels:
                self.rt_simple_outs.append(SimpleRtMidiOut(midi_output_device,
                                                           midi_output_name + " chans {}-{}".format(chan, chan + 15)))
                chan += 16

        if fluidsynth is not None:
            self.set_to_preset(*bank_and_preset)

    def set_to_preset(self, bank, preset):
        for i in self.channels:
            self.combined_midi_player.synth.program_select(i, self.soundfont_id, bank, preset)

    def get_rt_simple_out_and_channel(self, chan):
        assert chan < self.num_channels
        adjusted_chan = chan % 16
        rt_simple_out = self.rt_simple_outs[(chan - adjusted_chan) // 16]
        return rt_simple_out, adjusted_chan

    def note_on(self, chan, pitch, volume_from_0_to_1):
        """
        NB: for this and following commands, since a single instance of fluidsynth is running for all instruments,
        it we need to use the absolute channel when we call it 9I.. Each rt_midi output, on the other hand is local
        to the instrument, so no such conversion is necessary.
        """
        rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
        velocity = int(volume_from_0_to_1 * 127)
        if self.combined_midi_player.synth is not None:
            absolute_channel = self.channels[chan]
            self.combined_midi_player.synth.noteon(absolute_channel, pitch, velocity)
        rt_simple_out.note_on(chan, pitch, velocity)

    def note_off(self, chan, pitch):
        rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
        if self.combined_midi_player.synth is not None:
            absolute_channel = self.channels[chan]
            self.combined_midi_player.synth.noteon(absolute_channel, pitch, 0)  # note on call of 0 velocity implementation
            self.combined_midi_player.synth.noteoff(absolute_channel, pitch)  # note off call implementation
        rt_simple_out.note_off(chan, pitch)

    def pitch_bend(self, chan, bend_in_semitones):
        rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
        directional_bend_value = int(bend_in_semitones / self.max_pitch_bend * 8192)

        if directional_bend_value > 8192 or directional_bend_value < -8192:
            logging.warning("Attempted pitch bend beyond maximum range (default is 2 semitones). Call set_max_"
                            "pitch_bend on your MidiScampInstrument to expand the range.")
        # we can't have a directional pitch bend popping up to 8192, because we'll go one above the max allowed
        # on the other hand, -8192 is fine, since that will add up to zero
        # However, notice above that we don't send a warning about going beyond max pitch bend for a value of exactly
        # 8192, since that's obnoxious and confusing. Better to just quietly clip it to 8191
        directional_bend_value = max(-8192, min(directional_bend_value, 8191))
        if self.combined_midi_player.synth is not None:
            absolute_channel = self.channels[chan]
            # for some reason, pyFluidSynth takes a value from -8192 to 8191 and then adds 8192 to it
            self.combined_midi_player.synth.pitch_bend(absolute_channel, directional_bend_value)
        # rt_midi wants the normal value having added in 8192
        rt_simple_out.pitch_bend(chan, directional_bend_value + 8192)

    def set_max_pitch_bend(self, max_bend_in_semitones):
        """
        Sets the maximum pitch bend to the given number of semitones up and down for all tracks associated
        with this instrument. Note that, while this will definitely work with fluidsynth, the output of rt_midi
        must be being recorded already for this to affect subsequent pitch bend, which is slightly awkward.
        Also, in my experience, even then it may be ignored.
        :type max_bend_in_semitones: int
        :return: None
        """
        if max_bend_in_semitones != int(max_bend_in_semitones):
            logging.warning("Max pitch bend must be an integer number of semitones. "
                            "The value of {} is being rounded up.".format(max_bend_in_semitones))
            max_bend_in_semitones = int(max_bend_in_semitones) + 1

        for chan in range(self.num_channels):
            rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)

            if self.combined_midi_player.synth is not None:
                absolute_channel = self.channels[chan]
                self.combined_midi_player.synth.cc(absolute_channel, 101, 0)
                self.combined_midi_player.synth.cc(absolute_channel, 100, 0)
                self.combined_midi_player.synth.cc(absolute_channel, 6, max_bend_in_semitones)
                self.combined_midi_player.synth.cc(absolute_channel, 100, 127)

            rt_simple_out.cc(chan, 101, 0)
            rt_simple_out.cc(chan, 100, 0)
            rt_simple_out.cc(chan, 6, max_bend_in_semitones)
            rt_simple_out.cc(chan, 100, 127)
            self.max_pitch_bend = max_bend_in_semitones

    def expression(self, chan, expression_from_0_to_1):
        rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
        expression_val = int(expression_from_0_to_1 * 127)
        if self.combined_midi_player.synth is not None:
            absolute_channel = self.channels[chan]
            self.combined_midi_player.synth.cc(absolute_channel, 11, expression_val)
        rt_simple_out.expression(chan, expression_val)
