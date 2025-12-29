# BLE Connection Manager - Dual Core Version (Shared Queue for Inter-core Communication)
# Note: BLE operations must remain on CPU0 (asyncio is CPU0-only)
# This version uses a SharedMIDIMessageQueue for thread-safe communication

import asyncio
import aioble
import network
import _thread
import time
from config import MIDI_SERVICE_UUID, MIDI_CHAR_UUID


class SharedMIDIMessageQueue:
    """Thread-safe FIFO queue for MIDI messages with size limit
    
    This queue is designed to be shared between two CPU cores.
    Uses locks to ensure thread-safe access.
    """
    
    def __init__(self, max_size=256):
        """Initialize the message queue
        
        Args:
            max_size: Maximum number of messages to buffer (default 256)
        """
        self.messages = []
        self.max_size = max_size
        self.dropped_count = 0
        self._lock = _thread.allocate_lock()
    
    def put(self, message):
        """Add a message to the queue (thread-safe)
        
        Args:
            message: MIDI message data (bytes)
            
        Returns:
            True if message was queued, False if queue was full and message was dropped
        """
        with self._lock:
            if len(self.messages) >= self.max_size:
                self.dropped_count += 1
                print(f"WARNING: MIDI message queue full! Dropped message #{self.dropped_count}")
                return False
            
            self.messages.append(message)
            return True
    
    def get(self):
        """Get the next message from the queue (thread-safe)
        
        Returns:
            Message data if available, None if queue is empty
        """
        with self._lock:
            if len(self.messages) > 0:
                return self.messages.pop(0)
            return None
    
    def size(self):
        """Get current queue size"""
        with self._lock:
            return len(self.messages)
    
    def is_empty(self):
        """Check if queue is empty"""
        with self._lock:
            return len(self.messages) == 0
    
    def clear(self):
        """Clear all messages from the queue"""
        with self._lock:
            self.messages = []
            self.dropped_count = 0
    
    def get_stats(self):
        """Get queue statistics"""
        with self._lock:
            return {
                'size': len(self.messages),
                'max_size': self.max_size,
                'dropped': self.dropped_count,
                'usage_percent': (len(self.messages) / self.max_size) * 100
            }


class BLEConnectionManagerDualCore:
    """Manages BLE connections to MIDI devices using shared queue for inter-core communication
    
    BLE operations must run on CPU0 (asyncio requirement)
    SharedMIDIMessageQueue enables thread-safe MIDI message passing to other tasks/cores
    CPU0 main loop reads messages at its own pace via the queue
    """
    
    def __init__(self, display_manager, shared_queue=None):
        self.display = display_manager
        self.connection = None
        self.midi_characteristic = None
        self.connected = False
        
        # Use provided queue or create a new one
        if shared_queue is None:
            self.message_queue = SharedMIDIMessageQueue(max_size=256)
        else:
            self.message_queue = shared_queue
        
        self.background_task = None
    
    async def scan_and_connect(self, timeout_ms=5000):
        """Scan for and connect to Aeroband guitar"""
        self.display.clear()
        self.display.text("Scanning for", 70, 100)
        self.display.text("Aeroband...", 75, 120)
        self.display.show()
        
        print("Initializing Bluetooth...")
        
        # Disable WLAN to allow BLE to work
        try:
            wlan = network.WLAN(network.STA_IF)
            if wlan.active():
                print("Disabling WLAN for BLE...")
                wlan.active(False)
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"WLAN disable warning: {e}")
        
        self.display.clear()
        self.display.text("Scanning for", 70, 100)
        self.display.text("Aeroband...", 75, 120)
        self.display.show()
        
        print("Scanning for Aeroband guitar...")
        
        found_count = 0
        try:
            print("Entering scan context...")
            async with aioble.scan(timeout_ms, interval_us=30000, window_us=30000, active=True) as scanner:
                print("Scan started, waiting for devices...")
                async for result in scanner:
                    found_count += 1
                    name = result.name()
                    print(f"Found device #{found_count}: {name}")
                    
                    has_midi_service = MIDI_SERVICE_UUID in result.services()
                    has_aeroband_name = name and ("aeroband" in name.lower() or "pocketdrum" in name.lower() or "midi" in name.lower())
                    
                    if has_midi_service or has_aeroband_name:
                        print(f"Connecting to: {name}")
                        
                        try:
                            self.display.clear()
                            self.display.text("Connecting...", 70, 120)
                            self.display.show()
                            
                            print("Connecting...")
                            self.connection = await result.device.connect()
                            print("Connected!")
                            
                            print("Discovering services...")
                            midi_service = await self.connection.service(MIDI_SERVICE_UUID)
                            
                            if midi_service is None:
                                print("MIDI service not found")
                                await self.connection.disconnect()
                                continue
                            
                            print("Getting MIDI characteristic...")
                            self.midi_characteristic = await midi_service.characteristic(MIDI_CHAR_UUID)
                            
                            if self.midi_characteristic is None:
                                print("MIDI characteristic not found")
                                await self.connection.disconnect()
                                continue
                            
                            # Subscribe to notifications
                            print("Subscribing to MIDI notifications...")
                            try:
                                await self.midi_characteristic.subscribe(notify=True)
                                print("Successfully subscribed to notifications")
                            except Exception as e:
                                print(f"Failed to subscribe: {e}")
                            
                            self.connected = True
                            
                            # Start background MIDI reader task on CPU0 (async)
                            self.start_background_reader()
                            
                            self.display.clear()
                            self.display.text("Connected!", 75, 110)
                            self.display.show()
                            await asyncio.sleep(1)
                            
                            print("MIDI service ready!")
                            return True
                            
                        except Exception as e:
                            print(f"Connection failed: {e}")
                            if self.connection:
                                try:
                                    await self.connection.disconnect()
                                except:
                                    pass
                            continue
        
        except Exception as e:
            print(f"Scan failed: {e}")
        
        print(f"Scan completed. Found {found_count} devices total")
        print("Aeroband guitar not found")
        return False
    
    async def disconnect(self):
        """Disconnect from device"""
        self.connected = False
        
        if self.background_task:
            try:
                self.background_task.cancel()
            except:
                pass
            self.background_task = None
        
        if self.connection:
            try:
                await self.connection.disconnect()
            except:
                pass
            self.midi_characteristic = None
        
        self.message_queue.clear()
    
    async def _background_midi_reader(self):
        """Background task that continuously reads MIDI messages and queues them
        
        This task runs in the background on CPU0 and reads from the MIDI characteristic,
        parsing BLE MIDI notifications and adding each individual MIDI message 
        to the shared queue. This prevents messages from being lost when the main 
        loop is processing other tasks.
        """
        print("[CPU0] Background MIDI reader started")
        message_count = 0
        
        while self.connected and self.midi_characteristic:
            try:
                # Use a short timeout to allow other tasks to run
                try:
                    data = await asyncio.wait_for(self.midi_characteristic.notified(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Normal timeout, yield to other tasks
                    await asyncio.sleep_ms(1)
                    continue
                
                # Check if data is valid before processing
                if data and len(data) > 0:
                    # Parse notification and extract individual MIDI messages
                    messages = self._parse_midi_messages(data)
                    
                    if messages:
                        # Queue each individual MIDI message
                        for msg in messages:
                            self.message_queue.put(msg)
                            message_count += 1
                        
                        hex_str = ' '.join(f'{b:02x}' for b in data)
                        print(f"[CPU0] #{message_count} Received notification with {len(messages)} MIDI message(s): {hex_str}")
                        
                        # Optionally log queue status when messages are dropped
                        stats = self.message_queue.get_stats()
                        if stats['dropped'] > 0 or message_count <= 5:  # Log first few messages
                            print(f"[CPU0] Queue: {stats['size']}/{stats['max_size']} messages, "
                                  f"{stats['dropped']} dropped")
            except Exception as e:
                # Log error but continue running
                print(f"[CPU0] MIDI reader error: {type(e).__name__}: {e}")
                await asyncio.sleep_ms(1)
        
        print(f"[CPU0] Background MIDI reader stopped (received {message_count} total messages)")
    
    def start_background_reader(self):
        """Start the background MIDI reader task"""
        if not self.background_task:
            self.background_task = asyncio.create_task(self._background_midi_reader())
            print("[CPU0] Background MIDI reader task created")
    
    @staticmethod
    def _parse_midi_messages(data):
        """Parse BLE MIDI notification and extract individual MIDI messages
        
        BLE MIDI format: [header, timestamp, midi_status, midi_data1, midi_data2, ...]
        A single notification can contain multiple MIDI messages
        Returns a list of individual MIDI messages (as bytes)
        """
        messages = []
        
        # Convert to bytes if it's a generator or other iterable
        if not isinstance(data, (bytes, bytearray)):
            data = bytes(data)
        
        if len(data) < 3:
            return messages
        
        i = 2  # Skip BLE header and timestamp
        
        while i < len(data):
            midi_status = data[i]
            command = midi_status & 0xF0
            string_number = midi_status & 0x0F
            # 3-byte messages: Note On (0x90-0x9F), Control Change (0xB0-0xBF), Pitch Wheel (0xE0-0xEF)
            if (0x80 == command or
                0x90 == command or
                0xA0 == command or 
                0xB0 == command or 
                0xE0 == command):
                if i + 2 < len(data):
                    msg = [command, string_number, data[i+1], data[i+2]]
                    messages.append(msg)
                    i += 3
                else:
                    break
            
            # 2-byte messages: Note Off (0x80-0x8F), Program Change (0xC0-0xCF), Channel Pressure (0xD0-0xDF)
            elif (0xC0 == command or 
                  0xD0 == command):
                if i + 1 < len(data):
                    msg = [command, string_number, data[i+1]]
                    messages.append(msg)
                    i += 2
                else:
                    break
            
            # System messages and other status bytes
            else:
                print(f"Unknown MIDI status byte: {midi_status:02x}, skipping")
                i += 1
        
        return messages
    
    def wait_for_queued_midi(self, timeout_ms=100):
        """Get the next queued MIDI message (non-blocking, thread-safe)
        
        Args:
            timeout_ms: Timeout in milliseconds (currently not used, returns immediately)
            
        Returns:
            MIDI message data if available, None if queue is empty
        """
        return self.message_queue.get()
    
    async def wait_for_midi(self, timeout=0.5):
        """Wait for MIDI data with timeout (legacy, use wait_for_queued_midi instead)"""
        if not self.midi_characteristic:
            print("DEBUG BLE: midi_characteristic not set!")
            raise RuntimeError("Not connected to MIDI device")
        
        try:
            data = await asyncio.wait_for(self.midi_characteristic.notified(), timeout=timeout)
            print(f"DEBUG BLE: Received notification: {data}")
            return data
        except asyncio.TimeoutError:
            return None
