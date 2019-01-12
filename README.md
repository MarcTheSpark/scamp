# SCAMP (Suite for Composing Algorithmic Music in Python)

SCAMP is an algorithmic composition framework in Python that manages the flow of musical time, plays back notes via _fluidsynth_ or over osc, and quantizes and exports the result to music notation. This framework is the distillation of years of practice composing algorithmic music in Python and aims to address pervasive technical challenges while imposing as little as possible on the aesthetic choices of the user. 

Compositional tools always feature some degree of trade-off between functionality and freedom; every feature that is made available to the user steers them in a certain direction. For instance, if a framework provides abstractions for manipulating harmonies, the user may find themselves (perhaps unconsciously) pushed in the direction of particular harmonic languages. This may be a worthwhile trade-off in many cases: much creative work has been done within frameworks that impose even very restrictive limits. However, this is not the goad of SCAMP. Here, the goal is to provide only the basics, with the idea being that users are encouraged to write their own extensions to suit their own compositional inclinations.

Usage:

- For note-based composition, but in a broad sense.

Philosophy:

- Facilitate the compositional feedback loop. Interact with an ensemble not a score.
- Impose on the user's aesthetic approach as little as possible.
- Address common practical issues, rather than uncommon aesthetic issues. SCAMP does not and will not contain modules that model scales, pitch class sets, etc.
- Make code compact by using sensible defaults. Notice that this conflicts a little with not imposing on the user's aesthetic approach. This is unavoidable.
- Modularity, where possible, e.g. with clocks, parameter, xml. This goes along with not imposing; if someone's use case is better addressed by borrowing only certain components, facilitate that.
- Extensibility


Stretch goals:

- Presets
- LinuxSampler / SFZ support
