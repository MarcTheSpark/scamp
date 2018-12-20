# expenvelope

_Expenvelope_ is a python library for managing piecewise exponential curves, original intended as a tool for algorithmic music composition. Curves are simple to make, expressive, and useful for controlling dynamics, tempo, and other higher-level parameters.

The central `Envelope` class bears some relation to SuperCollider's _Env_ object, and is represented behind the scenes as a contiguous set of `EnvelopeSegments`. There are a number of different class methods available for constructing envelopes, including:

```python
Envelope.from_levels
Envelope.from_levels_and_durations
Envelope.from_points
Envelope.release
Envelope.ar
Envelope.asr
Envelope.adsr
Envelope.from_function

```

In addition to the `value_at` function, utilities have been included to append and insert new points, insert a new interpolated control point without changing the curve. Envelopes (and EnvelopeSegments) can be added, subtracted, multiplied and divided, with these operations yielding new Envelopes that are close approximations to the resulting function using piecewise exponential curves.

_expenvelope_ a key dependency of the `clockblocks` package for managing the flow of musical time, as well as of `scamp`, a Suite for Composing Algorithmic Music in Python. All three packages are being developed concurrently. 