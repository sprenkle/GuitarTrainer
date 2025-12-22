# BLE Connection Manager

import asyncio
import aioble
import network
from config import MIDI_SERVICE_UUID, MIDI_CHAR_UUID


class MIDIMessageQueue:
    """Simple FIFO queue for MIDI messages with size limit"""
    
    def __init__(self, max_size=128):
        """Initialize the message queue
        
        Args:
            max_size: Maximum number of messages to buffer (default 128)
        """
        self.messages = []
        self.max_size = max_size
        self.dropped_count = 0  # Track dropped messages
    
    def put(self, message):
        """Add a message to the queue
        
        Args:
            message: MIDI message data (bytes)
            
        Returns:
            True if message was queued, False if queue was full and message was dropped
        """
        if len(self.messages) >= self.max_size:
            self.dropped_count += 1
            print(f"WARNING: MIDI message queue full! Dropped message #{self.dropped_count}")
            return False
        
        self.messages.append(message)
        return True
    
    def get(self):
        """Get the next message from the queue
        
        Returns:
            Message data if available, None if queue is empty
        """
        if len(self.messages) > 0:
            return self.messages.pop(0)
        return None
    
    def size(self):
        """Get current queue size"""
        return len(self.messages)
    
    def is_empty(self):
        """Check if queue is empty"""
        return len(self.messages) == 0
    
    def clear(self):
        """Clear all messages from the queue"""
        self.messages = []
        self.dropped_count = 0
    
    def get_stats(self):
        """Get queue statistics"""
        return {
            'size': len(self.messages),
            'max_size': self.max_size,
            'dropped': self.dropped_count,
            'usage_percent': (len(self.messages) / self.max_size) * 100
        }


class BLEConnectionManager:
    """Manages BLE connections to MIDI devices"""
    
    def __init__(self, display_manager):
        self.display = display_manager
        self.connection = None
        self.midi_characteristic = None
        self.connected = False
        self.message_queue = MIDIMessageQueue(max_size=128)  # Create message queue
        self.background_task = None  # Task for reading MIDI in background
    
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
                            
                            # Start background MIDI reader task
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
            # Note: traceback module not available in MicroPython
        
        print(f"Scan completed. Found {found_count} devices total")
        print("Aeroband guitar not found")
        return False
    
    async def disconnect(self):
        """Disconnect from device"""
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
            self.connected = False
            self.midi_characteristic = None
        
        self.message_queue.clear()
    
    async def _background_midi_reader(self):
        """Background task that continuously reads MIDI messages and queues them
        
        This task runs in the background and reads from the MIDI characteristic,
        parsing BLE MIDI notifications and adding each individual MIDI message 
        to the message queue. This prevents messages from being lost when the main 
        loop is processing other tasks.
        """
        while self.connected and self.midi_characteristic:
            try:
                # Use a short timeout to allow other tasks to run
                try:
                    data = await asyncio.wait_for(self.midi_characteristic.notified(), timeout=1000)
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
                        
                        hex_str = ' '.join(f'{b:02x}' for b in data)
                        print(f"[BLE] Received notification with {len(messages)} MIDI message(s): {hex_str}")
                        
                        # Optionally log queue status when messages are dropped
                        stats = self.message_queue.get_stats()
                        if stats['dropped'] > 0:
                            print(f"MIDI Queue: {stats['size']}/{stats['max_size']} messages, "
                                  f"{stats['dropped']} dropped")
            except Exception as e:
                # Log error but continue running
                print(f"MIDI reader error: {e}")
                # await asyncio.sleep_ms(10)
    
    def start_background_reader(self):
        """Start the background MIDI reader task"""
        if not self.background_task:
            self.background_task = asyncio.create_task(self._background_midi_reader())
            print("Background MIDI reader started")
    
    @staticmethod
    def _count_midi_messages(data):
        """Count how many MIDI messages are in a BLE notification
        
        BLE MIDI format: [header, timestamp, midi_status, midi_data1, midi_data2, ...]
        A single notification can contain multiple MIDI messages
        """
        if len(data) < 3:
            return 0
        
        message_count = 0
        i = 2  # Skip BLE header and timestamp
        
        while i < len(data):
            midi_status = data[i]
            
            # Note On: 0x90-0x9F
            if 0x90 <= midi_status <= 0x9F:
                if i + 2 < len(data):
                    message_count += 1
                    i += 3
                else:
                    break
            
            # Note Off: 0x80-0x8F
            elif 0x80 <= midi_status <= 0x8F:
                if i + 1 < len(data):
                    message_count += 1
                    i += 2
                else:
                    break
            
            # Other MIDI messages - skip unknown status bytes
            else:
                i += 1
        
        return message_count
    
    @staticmethod
    def _parse_midi_messages(data):
        """Parse BLE MIDI notification and extract individual MIDI messages
        
        BLE MIDI format: [header, timestamp, midi_status, midi_data1, midi_data2, ...]
        A single notification can contain multiple MIDI messages
        Returns a list of individual MIDI messages (as bytes)
        """
        messages = []
        
        if len(data) < 3:
            return messages
        
        i = 2  # Skip BLE header and timestamp
        
        while i < len(data):
            midi_status = data[i]
            
            # Note On: 0x90-0x9F
            if 0x90 <= midi_status <= 0x9F:
                if i + 2 < len(data):
                    # Extract a 3-byte Note On message
                    msg = bytes([data[i], data[i+1], data[i+2]])
                    messages.append(msg)
                    i += 3
                else:
                    break
            
            # Note Off: 0x80-0x8F
            elif 0x80 <= midi_status <= 0x8F:
                if i + 1 < len(data):
                    # Extract a 2-byte Note Off message
                    msg = bytes([data[i], data[i+1]])
                    messages.append(msg)
                    i += 2
                else:
                    break
            
            # Other MIDI messages - skip unknown status bytes
            else:
                i += 1
        
        return messages
    
    def wait_for_queued_midi(self, timeout_ms=100):
        """Get the next queued MIDI message (non-blocking)
        
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
            #print(f"DEBUG BLE: Wait timeout")
            return None
