"""
SCAMP Example: SuperCollider made easy

This example requires the scamp_extensions Python package, which offers a simple way of doing the sound synthesis in
SuperCollider while scripting in SCAMP. Note that, for this to work, sclang must be added to your path (if you open a
terminal and type "sclang", it should act like it knows what you mean).
"""

from scamp import *
import random
from scamp_extensions.supercollider import add_sc_extensions

add_sc_extensions()

s = Session()

# this will start up an instance of supercollider (assuming it's installed and that we can run sclang from the
# command line), compile the SynthDef and use it for playback.
vib = s.new_supercollider_part("vibrato", r"""
SynthDef(\vibSynth, { |out=0, freq=440, volume=0.1, vibFreq=20, vibWidth=0.5, gate=1|
    var envelope = EnvGen.ar(Env.asr(releaseTime:0.5), gate, doneAction: 2);
    var vibHalfSteps = SinOsc.ar(vibFreq) * vibWidth;
    var vibFreqMul = 2.pow(vibHalfSteps / 12);
    var vibSine =  SinOsc.ar(freq * vibFreqMul) * volume / 10;
    Out.ar(out, (envelope * vibSine) ! 2);
}, [\ir, 0.1, 0.1, 0.1, 0.1, \kr])
""")

s.start_transcribing()

# any property entries starting or ending
# with "param" will be treated as extra
# playback parameters
while s.beat() < 20:
    # glissando between three random values
    pitch_env = [random.randint(60, 82) for _ in range(3)]
    volume_env = random.choice([
        # percussive envelope
        Envelope.ar(0.1, 1.2),
        # fp crescendo envelope
        Envelope.from_levels_and_durations([1, 0.2, 1], [0.1, 1], curve_shapes=[-2, 3])
    ])
    vib_width_env = [random.uniform(0, 5) for _ in range(2)]
    vib_freq_env = [random.uniform(3, 13) for _ in range(2)]
    vib.play_note(
        pitch_env, volume_env, random.uniform(0.3, 3),
        {"vibWidth_param": vib_width_env,
         "vibFreq_param": vib_freq_env},
        blocking=False
    )
    wait(random.uniform(0.5, 3))

performance = s.stop_transcribing()
engraving_settings.max_voices_per_part = 1
performance.to_score().show()
