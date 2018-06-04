from playcorder import Playcorder, Performance
from playcorder.quantization import QuantizationScheme, MeasureQuantizationScheme

pc = Playcorder("default")
pc.load_ensemble_from_json("shakEnsemble.json")

performance = Performance.load_from_json("perfShakoboe.json")
assert isinstance(performance, Performance)

# performance = performance.quantized(QuantizationScheme([MeasureQuantizationScheme.from_time_signature("4/4", max_divisor=16)]))

pc.master_clock.tempo = 30
pc.master_clock.set_tempo_target(150, 40, duration_units="time")
while True:
    performance.play(ensemble=pc.ensemble, clock=pc.master_clock, blocking=True)