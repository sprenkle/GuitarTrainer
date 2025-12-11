# Metronome Module

import asyncio
import utime
from config import Colors

class Metronome:
    """Handles metronome timing and visual feedback"""
    
    def __init__(self, bpm):
        self.bpm = bpm
        self.beat_interval_ms = int(60000 / bpm)
        self.running = False
        self.beat_state = {'beat_white': True, 'last_beat_time': utime.ticks_ms()}
        self.ticker_task = None
    
    async def start(self):
        """Start the metronome"""
        self.running = True
        self.beat_state['last_beat_time'] = utime.ticks_ms()
        self.ticker_task = asyncio.create_task(self._ticker())
    
    async def stop(self):
        """Stop the metronome"""
        self.running = False
        if self.ticker_task:
            self.ticker_task.cancel()
    
    async def _ticker(self):
        """Background task to update beat state"""
        while self.running:
            current_time = utime.ticks_ms()
            elapsed_since_beat = utime.ticks_diff(current_time, self.beat_state['last_beat_time'])
            
            # Toggle white/black based on beat timing
            # White for first half of beat, black for second half
            if elapsed_since_beat > self.beat_interval_ms:
                self.beat_state['last_beat_time'] = current_time
                self.beat_state['beat_white'] = True
            elif elapsed_since_beat > self.beat_interval_ms // 2:
                self.beat_state['beat_white'] = False
            else:
                self.beat_state['beat_white'] = True
            
            await asyncio.sleep_ms(20)
    
    def get_beat_color(self):
        """Get the current beat color"""
        return Colors.WHITE if self.beat_state['beat_white'] else Colors.BLACK
    
    def is_beat_white(self):
        """Check if beat should be white"""
        return self.beat_state['beat_white']
