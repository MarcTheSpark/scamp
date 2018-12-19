"""
To be run after "load_and_play_performance.py", since this loads up that performance as well as the Ensemble.
"""

from scamp import *

session = Session("default")
session.load_ensemble_from_json(resolve_relative_path("SavedFiles/shakEnsemble.json"))

performance = Performance.load_from_json(resolve_relative_path("SavedFiles/perfShakoboe.json"))

session.master_clock.tempo = 30
session.master_clock.set_tempo_target(150, 40, duration_units="time")

while True:
    performance.play(ensemble=session.ensemble, clock=session.master_clock, blocking=True)
