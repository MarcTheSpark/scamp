NetAddr.langPort;  // Run this line to get the port to send to from Python
MarcUtilities.setOutputLimiter(0.1, 0.1)
( // Define the Synths

// Simple FM Sine thing
SynthDef(\testSynth, { |out=0, freq=440, gain=0.1, modulationFreq=20, gate=1|
	var synth = EnvGen.ar(Env.asr(releaseTime:0.5), gate, doneAction: 2) * (SinOsc.ar(freq) * SinOsc.ar(modulationFreq) * gain);
	Out.ar(out, synth ! 2);
}).add;

// (from https://sccode.org/1-54H)
SynthDef("hihat", {arg out = 0, gain = 0.5, att = 0.01, rel = 0.2, ffreq = 6000;
	var env, snd;
	env = Env.perc(att, rel, gain).kr(doneAction: 2);
	snd = WhiteNoise.ar;
	snd = HPF.ar(in: snd, freq: ffreq, mul: env);
	Out.ar(out, snd ! 2);
}).add;
)

( // Set up the OSC Listeners

// -------------------- FM SINES -----------------------

~notesPlaying = Dictionary();

// START NOTE
o = OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], pitch = msg[2], volume = msg[3];
	~notesPlaying.put(id, Synth(\testSynth, [\freq, pitch.midicps, \gain, (-40 * (1-volume)).dbamp]));
	"starting ".post; id.postln;
}, '/fm_sines/start_note');

// END NOTE
o = OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1];
	~notesPlaying[id].set(\gate, 0);
	"ending ".post; id.postln;
	~notesPlaying.removeAt(id);
}, '/fm_sines/end_note');

// CHANGE PITCH
o = OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], pitch = msg[2];
	~notesPlaying[id].set(\freq, pitch.midicps);
}, '/fm_sines/change_pitch');

// CHANGE VOLUME
o = OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], volume = msg[2];
	~notesPlaying[id].set(\gain, (-40 * (1-volume)).dbamp);
}, '/fm_sines/change_volume');

// CHANGE THE MODULATION FREQUENCY
o = OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], fm = msg[2];
	~notesPlaying[id].set(\modulationFreq, fm);
}, '/fm_sines/change_parameter/fm');


// -------------------- HiHat -----------------------

// START NOTE
o = OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], pitch = msg[2], volume = msg[3];
	~notesPlaying.put(id, Synth(\hihat, [\ffreq, pitch.midicps, \gain, (-40 * (1-volume)).dbamp]));
}, '/hihat/start_note');

// CHANGE PITCH
o = OSCFunc({ arg msg, time, addr, recvPort;
	var id = msg[1], pitch = msg[2];
	~notesPlaying[id].set(\ffreq, pitch.midicps);
}, '/hihat/change_pitch');
)
