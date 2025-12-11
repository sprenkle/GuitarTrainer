# Minimal BLE scan test
import asyncio
import aioble

async def test_ble():
    """Test if BLE/aioble works at all"""
    print("Testing aioble...")
    
    try:
        print("Starting scan...")
        count = 0
        async with aioble.scan(3000) as scanner:  # 3 second scan
            async for result in scanner:
                count += 1
                print(f"Found device: {result.name()}")
                if count >= 5:  # Stop after 5 devices
                    break
        
        print(f"Scan complete. Found {count} devices.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ble())
