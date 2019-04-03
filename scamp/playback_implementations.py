from abc import ABC, abstractmethod


class PlaybackImplementation(ABC):

    def __init__(self):
        self.note_info_dict = None

    def get_note_info(self, note_id):
        if self.note_info_dict is None:
            raise Exception("PlaybackImplementation not registered with a ScampInstrument.")
        elif note_id not in self.note_info_dict:
            raise KeyError("No note found for id {}".format(note_id))
        else:
            return self.note_info_dict[note_id]

    @abstractmethod
    def start_note(self, note_id, pitch, volume, properties, other_parameter_values: dict = None):
        pass

    @abstractmethod
    def end_note(self, note_id):
        pass

    @abstractmethod
    def change_note_pitch(self, note_id, new_pitch):
        pass

    @abstractmethod
    def change_note_volume(self, note_id, new_volume):
        pass

    @abstractmethod
    def change_note_parameter(self, note_id, parameter_name, new_value):
        pass


class MidiPlaybackImplementation(PlaybackImplementation):

    def start_note(self, note_id, pitch, volume, properties, other_parameter_values: dict = None):
        print("Midi Starting Note", note_id, pitch, volume)

    def end_note(self, note_id):
        print("Midi Ending Note", note_id)

    def change_note_pitch(self, note_id, new_pitch):
        print("Midi Changing Pitch", note_id, new_pitch)

    def change_note_volume(self, note_id, new_volume):
        print("Midi Changing Volume", note_id, new_volume)

    def change_note_parameter(self, note_id, parameter_name, new_value):
        print("Midi Changing Parameter", note_id, parameter_name, new_value)
