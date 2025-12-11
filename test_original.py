# Test the original monolithic code to verify hardware works

import asyncio
from guitar_trainer_chords import ChordTrainer

async def main():
    """Test with original code"""
    trainer = ChordTrainer(chord_sequence=[])
    await trainer.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
