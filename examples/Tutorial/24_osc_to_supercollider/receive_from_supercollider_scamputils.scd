// --------------------------------------------------------------------------------------------------
// Corresponding SuperCollider Code for OSC-to-SuperCollider SCAMP example. Run this before the Python
// script by booting the server and then running the code blocks below in order.
// --------------------------------------------------------------------------------------------------


// If it's not working, make sure the port printed here matches the port that the Python file is sending to
NetAddr.langPort.postln;


(
// ----------------------------- 1) Define vib synth ----------------------------------
ScampUtils.instrumentFromSynthDef(
	SynthDef(\vibSynth, { |out=0, freq=440, volume=0.1, vibFreq=20, vibWidth=0.5, gate=1|
		var envelope = EnvGen.ar(Env.asr(releaseTime:0.5), gate, doneAction: 2);
		var vibHalfSteps = SinOsc.ar(vibFreq) * vibWidth;
		var vibFreqMul = 2.pow(vibHalfSteps / 12);
		var vibSine =  SinOsc.ar(freq * vibFreqMul) * volume;
		Out.ar(out, (envelope * vibSine / 5) ! 2);
	}, [\ir, 0.1, 0.1, 0.1, 0.1, \kr]);
)
)
