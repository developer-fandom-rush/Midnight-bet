# Dhika Episode 01 Director Board

Static GitHub Pages UI for Episode 01 source review.

What it does:

- Loads `00_DHIKA_COMPLETE_RAW.txt` in the browser with a file picker or paste box.
- Extracts Episode 01 by the `EPISODE 1` and `EPISODE 2` markers.
- Assigns source refs as `E01-L###`.
- Breaks Episode 01 into character/relationship blocks.
- Marks director claims as `locked` or `ask author`.
- Shows carry-forward events for Episode 02 with exact refs.

The RAW story text is not bundled in this folder. The UI renders exact RAW only after the author loads the local source file.
