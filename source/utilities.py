import json
from abc import ABC, abstractmethod


class SavesToJSON(ABC):

    @abstractmethod
    def _to_json(self):
        pass

    @classmethod
    @abstractmethod
    def _from_json(cls, json_object):
        pass

    def save_to_json(self, file_path):
        with open(file_path, "w") as file:
            json.dump(self._to_json(), file)

    @classmethod
    def load_from_json(cls, file_path):
        with open(file_path, "r") as file:
            return cls._from_json(json.load(file))
