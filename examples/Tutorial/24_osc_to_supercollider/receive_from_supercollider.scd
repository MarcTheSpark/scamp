// --------------------------------------------------------------------------------------------------
// Corresponding SuperCollider Code for OSC-to-SuperCollider SCAMP example. Run this before the Python
// script by booting the server and then running the code blocks below in order.
// --------------------------------------------------------------------------------------------------


// If it's not working, make sure the port printed here matches the port that the Python file is sending to
NetAddr.langPort.postln;


(
// ----------------------------- 1) Define vib synth ----------------------------------
SynthDef(\vibSynth, { |out=0, freq=440, gain=0.1, vibFreq=20, vibWidth=0.5, gate=1|
	var envelope = EnvGen.ar(Env.asr(releaseTime:0.5), gate, doneAction: 2);
	var vibHalfSteps = SinOsc.ar(vibFreq) * vibWidth;
	var vibFreqMul = 2.pow(vibHalfSteps / 12);
	var vibSine =  SinOsc.ar(freq * vibFreqMul) * gain;
	Out.ar(out, (envelope * vibSine / 5) ! 2);
}, [\ir, 0.1, 0.1, 0.1, 0.1, \kr]).add;
)


(
// ---------------------------- 2) Set up OSC Receivers -------------------------------

// This dictionary maps the note-id's sent by SCAMP to their associated Synths
~notesPlaying = Dictionary();

// START NOTE
OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], pitch = msg[2], volume = msg[3];
	// Start a new Synth and place it in the ~notesPlaying dictionary under its associated id
	~notesPlaying.put(id, Synth(\vibSynth,
		[\freq, pitch.midicps,
		 \gain, (-40 * (1-volume)).dbamp]
	));
}, '/vibrato/start_note');

// END NOTE
OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1];
	~notesPlaying[id].set(\gate, 0);
}, '/vibrato/end_note');

// CHANGE PITCH
OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], pitch = msg[2];
	~notesPlaying[id].set(\freq, pitch.midicps);
}, '/vibrato/change_pitch');

// CHANGE VOLUME
OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], volume = msg[2];
	~notesPlaying[id].set(\gain,
		(-40 * (1-volume)).dbamp);
}, '/vibrato/change_volume');

// CHANGE VIBRATO FREQUENCY
OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], freq = msg[2];
	~notesPlaying[id].set(\vibFreq, freq);
}, '/vibrato/change_parameter/vibFreq');

// CHANGE VIBRATO WIDTH
OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], width = msg[2];
	~notesPlaying[id].set(\vibWidth, width);
}, '/vibrato/change_parameter/vibWidth');
)
