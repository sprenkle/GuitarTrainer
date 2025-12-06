# Guitar Trainer Chord JSON Format

## File Structure

The JSON file contains an array of chord lists. Each chord list is an array with:
1. Name (string)
2. Configuration array starting with mode, followed by content

## Modes

### R - Random Practice
Plays chords in random order after each completion.

**Format:** `["List Name", ["R", "Chord1", "Chord2", "Chord3", ...]]`

**Example:**
```json
["Pop Progression", ["R", "C", "G", "Am", "F"]]
```

### S - Sequential Practice
Plays chords in fixed order (no randomization).

**Format:** `["List Name", ["S", "Chord1", "Chord2", "Chord3", ...]]`

**Example:**
```json
["Jazz ii-V-I", ["S", "Dm7", "G7", "Cmaj7"]]
```

### M - Metronome with Pattern
Visual metronome with specific chord changes and strum directions.

**Format:** `["List Name", ["M", ["Chord", "Dir"], ["Chord", "Dir"], ...]]`

Each beat is `["Chord", "Direction"]` where:
- `Chord`: The chord to display (e.g., "C", "Em", "D6/9")
- `Direction`: 
  - `"D"` = Down strum (shown as green down arrow)
  - `"U"` = Up strum (shown as blue up arrow)
  - `null` or `"R"` = Rest (shown as gray X)

**Example:**
```json
["Horse With NN", ["M", 
  ["Em", "D"], ["Em", "D"], ["Em", "U"], ["Em", "U"],
  ["Em", "D"], ["Em", "U"],
  ["D6/9", "D"], ["D6/9", "D"], ["D6/9", "U"], ["D6/9", "U"],
  ["D6/9", "D"], ["D6/9", "U"]
]]
```

This creates a 12-beat pattern alternating between Em and D6/9 chords with specific strum patterns.

## Complete Example

```json
[
  ["Pop Progression", ["R", "C", "G", "Am", "F"]],
  ["Blues in E", ["R", "E7", "A7", "B7"]],
  ["Jazz ii-V-I", ["S", "Dm7", "G7", "Cmaj7"]],
  ["Simple Down Up", ["M", 
    ["C", "D"], ["C", "U"], 
    ["G", "D"], ["G", "U"],
    ["Am", "D"], ["Am", "U"],
    ["F", "D"], ["F", "U"]
  ]]
]
```

## Uploading

```bash
python upload_chords.py your_chords.json
```

The entire file replaces the current chord lists on the device and persists across reboots.
