# Guitar Trainer - Chord Upload Tool

Upload custom chord sequences to your Guitar Trainer device wirelessly via Bluetooth.

## Installation

1. Install Python 3.8 or higher
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Power on your Guitar Trainer device
2. Make sure it's in menu mode (not actively practicing)
3. Run the upload tool:
   ```
   python upload_chords.py
   ```

4. The tool will:
   - Scan for your device
   - Connect automatically
   - Show menu of pre-defined chord lists
   - Allow you to upload lists

## Creating Custom Chord Lists

Choose option 'C' in the menu to create a custom chord list:

1. **Name**: Give your list a name (max 20 characters)
2. **Mode**: 
   - `R` = Random (shuffles after each completion)
   - `S` = Sequential (same order every time)
3. **Chords**: Enter comma-separated chord names
   - Example: `C,G,Am,F`
   - Example: `E,A,D,G,B`

## Pre-defined Lists

The tool comes with example lists:
- Pop Progression (C, G, Am, F) - Random
- Blues in E (E7, A7, B7) - Random
- Jazz ii-V-I (Dm7, G7, Cmaj7) - Sequential
- Country Basic (G, C, D, Em) - Random

## Supported Chords

Your Guitar Trainer supports these chords:
- Major: C, D, E, F, G, A, B
- Minor: Am, Bm, Cm, Dm, Em, Fm, Gm
- 7th: A7, B7, C7, D7, E7, F7, G7
- Major 7th: Amaj7, Bmaj7, Cmaj7, Dmaj7, Emaj7, Fmaj7, Gmaj7
- Minor 7th: Am7, Bm7, Cm7, Dm7, Em7, Fm7, Gm7
- And more (check CHORD_MIDI_NOTES_FULL in the main code)

## Notes

- Upload new lists while device is in menu mode
- New lists are stored in RAM (lost on power cycle)
- Keep chord names under 10 characters each
- Maximum 20 chords per list recommended

## Troubleshooting

**Device not found:**
- Make sure device is powered on
- Check that Bluetooth is enabled on your PC
- Device should show "Pico BLE MIDI" name

**Upload fails:**
- Try reconnecting
- Make sure device isn't actively practicing a sequence
- Check that chord names are valid

**Chord not recognized:**
- Use exact chord names from supported list
- Check capitalization (Am not am)
- Some complex chords may not be supported
