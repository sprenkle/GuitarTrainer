"""Unit tests for MenuSystem and BLEConnectionManagerDualCore

Tests cover:
- SharedMIDIMessageQueue thread-safe operations
- MenuSystem MIDI parsing and menu navigation
- BLE connection manager initialization
"""

import unittest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from menu_system import MenuSystem
from ble_connection_dual_core import SharedMIDIMessageQueue, BLEConnectionManagerDualCore
from config import PRACTICE_OPTIONS, BPM_OPTIONS, SELECTION_NOTES, Colors


class TestSharedMIDIMessageQueue(unittest.TestCase):
    """Test cases for SharedMIDIMessageQueue"""
    
    def setUp(self):
        """Create a fresh queue for each test"""
        self.queue = SharedMIDIMessageQueue(max_size=10)
    
    def test_queue_initialization(self):
        """Test queue initializes with correct parameters"""
        self.assertEqual(self.queue.max_size, 10)
        self.assertEqual(self.queue.dropped_count, 0)
        self.assertTrue(self.queue.is_empty())
    
    def test_put_and_get_single_message(self):
        """Test adding and retrieving a single message"""
        msg = [0x90, 0x3C, 0x64]  # Note On, Middle C, velocity 100
        result = self.queue.put(msg)
        
        self.assertTrue(result)
        self.assertEqual(self.queue.size(), 1)
        
        retrieved = self.queue.get()
        self.assertEqual(retrieved, msg)
        self.assertTrue(self.queue.is_empty())
    
    def test_put_multiple_messages(self):
        """Test FIFO ordering with multiple messages"""
        messages = [
            [0x90, 0x3C, 0x64],  # Note On
            [0x80, 0x3C],        # Note Off
            [0x90, 0x3E, 0x64],  # Another Note On
        ]
        
        for msg in messages:
            self.queue.put(msg)
        
        self.assertEqual(self.queue.size(), 3)
        
        # Verify FIFO order
        for expected_msg in messages:
            retrieved = self.queue.get()
            self.assertEqual(retrieved, expected_msg)
    
    def test_queue_overflow(self):
        """Test queue handles overflow correctly"""
        # Fill queue to capacity
        for i in range(10):
            msg = [0x90, i, 0x64]
            result = self.queue.put(msg)
            self.assertTrue(result)
        
        # Try to add beyond capacity
        result = self.queue.put([0x90, 99, 0x64])
        self.assertFalse(result)
        self.assertEqual(self.queue.dropped_count, 1)
        self.assertEqual(self.queue.size(), 10)
    
    def test_queue_clear(self):
        """Test clearing the queue"""
        for i in range(5):
            self.queue.put([0x90, i, 0x64])
        
        self.assertEqual(self.queue.size(), 5)
        self.queue.clear()
        self.assertTrue(self.queue.is_empty())
        self.assertEqual(self.queue.dropped_count, 0)
    
    def test_queue_get_stats(self):
        """Test queue statistics"""
        for i in range(3):
            self.queue.put([0x90, i, 0x64])
        
        stats = self.queue.get_stats()
        self.assertEqual(stats['size'], 3)
        self.assertEqual(stats['max_size'], 10)
        self.assertEqual(stats['dropped'], 0)
        self.assertEqual(stats['usage_percent'], 30.0)
    
    def test_queue_get_empty_returns_none(self):
        """Test getting from empty queue returns None"""
        result = self.queue.get()
        self.assertIsNone(result)


class TestMenuSystemParsing(unittest.TestCase):
    """Test cases for MenuSystem MIDI parsing"""
    
    def setUp(self):
        """Create mock display and BLE managers"""
        self.mock_display = Mock()
        self.mock_ble = Mock()
        self.menu = MenuSystem(self.mock_display, self.mock_ble)
    
    def test_parse_note_on_message(self):
        """Test parsing a valid Note On message"""
        # Format: [status, string_number, note]
        data = [0x90, 0x01, 0x50]  # Note On, channel 0, note 80
        result = self.menu._parse_midi(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'note_on')
        self.assertEqual(result[1], 0x01)  # string_number
        self.assertEqual(result[2], 0x50)  # note
    
    def test_parse_note_off_message(self):
        """Test parsing a valid Note Off message"""
        data = [0x80, 0x50]  # Note Off, note 80
        result = self.menu._parse_midi(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'note_off')
        self.assertEqual(result[1], 0x50)
    
    def test_parse_incomplete_message(self):
        """Test parsing incomplete message returns None"""
        data = [0x90]  # Incomplete
        result = self.menu._parse_midi(data)
        self.assertIsNone(result)
    
    def test_parse_empty_data(self):
        """Test parsing empty data returns None"""
        result = self.menu._parse_midi(None)
        self.assertIsNone(result)
        
        result = self.menu._parse_midi([])
        self.assertIsNone(result)
    
    def test_parse_unknown_status_byte(self):
        """Test parsing unknown status byte returns None"""
        data = [0x50, 0x3C, 0x64]  # Invalid status
        result = self.menu._parse_midi(data)
        self.assertIsNone(result)


class TestMenuSystemDisplay(unittest.TestCase):
    """Test cases for MenuSystem display methods"""
    
    def setUp(self):
        """Create mock display and BLE managers"""
        self.mock_display = Mock()
        self.mock_ble = Mock()
        self.menu = MenuSystem(self.mock_display, self.mock_ble)
    
    def test_display_menu_first_page(self):
        """Test displaying the first page of the menu"""
        self.menu._display_menu(page=0, items_per_page=4)
        
        # Verify display methods were called
        self.mock_display.clear.assert_called_once()
        self.mock_display.show.assert_called_once()
        
        # Verify text was written for title and items
        text_calls = self.mock_display.text.call_count
        self.assertGreater(text_calls, 4)  # At least title + 4 items
    
    def test_display_menu_second_page(self):
        """Test displaying a subsequent page"""
        # With 4 items per page and assuming 5+ practice options
        if len(PRACTICE_OPTIONS) > 4:
            self.menu._display_menu(page=1, items_per_page=4)
            
            self.mock_display.clear.assert_called_once()
            self.mock_display.show.assert_called_once()
    
    def test_display_menu_pagination(self):
        """Test that pagination info is displayed when multiple pages exist"""
        items_per_page = 4
        if len(PRACTICE_OPTIONS) > items_per_page:
            self.menu._display_menu(page=0, items_per_page=items_per_page)
            
            # Verify pagination text was included
            text_calls = [call[0][0] for call in self.mock_display.text.call_args_list]
            pagination_found = any('Page' in str(text) for text in text_calls)
            self.assertTrue(pagination_found)


class TestBLEConnectionManagerInit(unittest.TestCase):
    """Test cases for BLEConnectionManager initialization"""
    
    def setUp(self):
        """Create mock display manager"""
        self.mock_display = Mock()
    
    def test_ble_manager_initialization_with_new_queue(self):
        """Test BLE manager creates its own queue if none provided"""
        ble = BLEConnectionManagerDualCore(self.mock_display)
        
        self.assertIsNotNone(ble.message_queue)
        self.assertIsInstance(ble.message_queue, SharedMIDIMessageQueue)
        self.assertFalse(ble.connected)
    
    def test_ble_manager_initialization_with_shared_queue(self):
        """Test BLE manager uses provided shared queue"""
        shared_queue = SharedMIDIMessageQueue(max_size=512)
        ble = BLEConnectionManagerDualCore(self.mock_display, shared_queue=shared_queue)
        
        self.assertIs(ble.message_queue, shared_queue)
    
    def test_ble_manager_properties(self):
        """Test BLE manager initializes all properties correctly"""
        ble = BLEConnectionManagerDualCore(self.mock_display)
        
        self.assertIsNone(ble.connection)
        self.assertIsNone(ble.midi_characteristic)
        self.assertFalse(ble.connected)
        self.assertIs(ble.display, self.mock_display)


class TestBLEMIDIParsing(unittest.TestCase):
    """Test cases for BLE MIDI message parsing"""
    
    def test_parse_midi_messages_note_on(self):
        """Test parsing BLE MIDI notification with Note On"""
        # BLE MIDI format: [header, timestamp, status, note, velocity]
        data = bytes([0x80, 0x80, 0x90, 0x3C, 0x64])  # Header, timestamp, Note On, C, velocity 100
        
        messages = BLEConnectionManagerDualCore._parse_midi_messages(data)
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0][0], 0x90)  # Note On status
        self.assertEqual(messages[0][1], 0x3C)  # Note
        self.assertEqual(messages[0][2], 0x64)  # Velocity
    
    def test_parse_midi_messages_multiple(self):
        """Test parsing multiple MIDI messages in one notification"""
        # Two Note On messages
        data = bytes([0x80, 0x80, 0x90, 0x3C, 0x64, 0x90, 0x3E, 0x64])
        
        messages = BLEConnectionManagerDualCore._parse_midi_messages(data)
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0][0], 0x90)
        self.assertEqual(messages[1][0], 0x90)
    
    def test_parse_midi_messages_empty_data(self):
        """Test parsing with insufficient data"""
        data = bytes([0x80])
        messages = BLEConnectionManagerDualCore._parse_midi_messages(data)
        
        self.assertEqual(len(messages), 0)


class TestWaitForQueuedMIDI(unittest.IsolatedAsyncioTestCase):
    """Test cases for async wait_for_queued_midi method"""
    
    async def asyncSetUp(self):
        """Set up for async tests"""
        self.mock_display = Mock()
        self.ble = BLEConnectionManagerDualCore(self.mock_display)
    
    async def test_wait_for_queued_midi_with_message(self):
        """Test retrieving a message from the queue"""
        msg = [0x90, 0x3C, 0x64]
        self.ble.message_queue.put(msg)
        
        result = await self.ble.wait_for_queued_midi()
        
        self.assertEqual(result, msg)
    
    async def test_wait_for_queued_midi_empty_queue(self):
        """Test with empty queue returns None"""
        result = await self.ble.wait_for_queued_midi()
        
        self.assertIsNone(result)
    
    async def test_wait_for_queued_midi_fifo_order(self):
        """Test FIFO order when retrieving messages"""
        messages = [
            [0x90, 0x3C, 0x64],
            [0x80, 0x3C],
            [0x90, 0x3E, 0x64],
        ]
        
        for msg in messages:
            self.ble.message_queue.put(msg)
        
        for expected_msg in messages:
            result = await self.ble.wait_for_queued_midi()
            self.assertEqual(result, expected_msg)


class TestConfigHelperMethods(unittest.TestCase):
    """Test cases for config helper methods"""
    
    def test_get_note_from_string_fret_open_strings(self):
        """Test getting note from open strings"""
        from config import get_note_from_string_fret, OPEN_STRING_NOTES
        
        for string_num in range(1, 7):
            note = get_note_from_string_fret(string_num, 0)
            expected = OPEN_STRING_NOTES[string_num - 1]
            self.assertEqual(note, expected)
    
    def test_get_note_from_string_fret_with_fret(self):
        """Test getting note with fret offset"""
        from config import get_note_from_string_fret, OPEN_STRING_NOTES
        
        string_num = 1
        fret_num = 5
        note = get_note_from_string_fret(string_num, fret_num)
        expected = OPEN_STRING_NOTES[0] + 5
        self.assertEqual(note, expected)
    
    def test_get_note_invalid_string(self):
        """Test invalid string number raises error"""
        from config import get_note_from_string_fret
        
        with self.assertRaises(ValueError):
            get_note_from_string_fret(0, 0)
        
        with self.assertRaises(ValueError):
            get_note_from_string_fret(7, 0)
    
    def test_get_note_invalid_fret(self):
        """Test invalid fret number raises error"""
        from config import get_note_from_string_fret
        
        with self.assertRaises(ValueError):
            get_note_from_string_fret(1, -1)
        
        with self.assertRaises(ValueError):
            get_note_from_string_fret(1, 25)
    
    def test_get_fret_from_string_note_open_strings(self):
        """Test getting fret from open string notes"""
        from config import get_fret_from_string_note, OPEN_STRING_NOTES
        
        for string_num in range(1, 7):
            note = OPEN_STRING_NOTES[string_num - 1]
            fret = get_fret_from_string_note(string_num, note)
            self.assertEqual(fret, 0)
    
    def test_get_fret_from_string_note_with_fret(self):
        """Test getting fret from note with offset"""
        from config import get_fret_from_string_note, OPEN_STRING_NOTES
        
        string_num = 1
        note = OPEN_STRING_NOTES[0] + 5
        fret = get_fret_from_string_note(string_num, note)
        self.assertEqual(fret, 5)
    
    def test_get_fret_out_of_range(self):
        """Test fret out of range returns None"""
        from config import get_fret_from_string_note, OPEN_STRING_NOTES
        
        # Note too high for this string
        note = OPEN_STRING_NOTES[0] + 25
        fret = get_fret_from_string_note(1, note)
        self.assertIsNone(fret)
        
        # Note too low for this string
        note = OPEN_STRING_NOTES[0] - 5
        fret = get_fret_from_string_note(1, note)
        self.assertIsNone(fret)


if __name__ == '__main__':
    unittest.main()
