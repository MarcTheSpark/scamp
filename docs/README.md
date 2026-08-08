# Building the docs

The documentation is built with Sphinx. From the `scamp/` package root:

```
scripts/documentation/build_docs.sh
```

This regenerates the API reference from docstrings, runs Sphinx into `docs_build/`,
and opens the result in a browser.

- `--rebuild-examples` also regenerates the Examples gallery from `examples/`.
  (Example pages are otherwise reused, and rebuilt automatically on a fresh checkout.)

The audio and score media embedded in the example pages are rendered separately — a
slow, real-time job that only needs rerunning when examples change:

```
scripts/documentation/render_example_media.py
```

It records each example's playback to mp3 and any score it shows to SVG, under
`docs/_static/media/`. Hand-authored videos and per-example media ordering live in
`docs/example_media.toml`.

Requirements: `scamp` importable and `sphinx` for the docs; `ffmpeg` on PATH and
`verovio` for the media.
