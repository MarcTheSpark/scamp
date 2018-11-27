# SCAMP (Suite for Composing Algorithmic Music in Python)

A Python interface for playing notes via _fluidsynth_ and saving the result in formats that can be imported to notation programs.


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