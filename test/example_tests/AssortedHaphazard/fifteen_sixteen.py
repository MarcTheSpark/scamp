"""
A rhythm quantized with a 15/16 time signature
"""

from scamp import *

MeasureQuantizationScheme.from_time_signature("15/16")
# engraving_settings.allow_duple_tuplets_in_compound_time = False
dur_list=[1.0, 0.5, 0.5, 0.75, 0.75, 1.5, 1.5, 0.75, 0.75, 1.0, 1.25]

time_sig_list=['7/8', '15/16', '3/4']
s = Session()
s.fast_forward_in_time(1000)
piano1 = s.new_part("Piano1")
s.start_transcribing()
for d in dur_list:
    piano1.play_note(67, 1, d)
s.wait_for_children_to_finish()
performance = s.stop_transcribing()

s.kill()


def test_results():
    return (
        performance,
        performance.to_score(time_signature=time_sig_list, simplicity_preference=2)
    )
