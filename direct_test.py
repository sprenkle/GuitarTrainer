# Direct GC9A01 Hardware Test
import machine
import time
import struct

# Pin definitions
SCK_PIN = 18
MOSI_PIN = 19
DC_PIN = 6
CS_PIN = 5
RST_PIN = 9

# Initialize SPI
spi = machine.SPI(0, 
                  baudrate=10000000,  # Lower speed for testing
                  polarity=0, 
                  phase=0,
                  sck=machine.Pin(SCK_PIN), 
                  mosi=machine.Pin(MOSI_PIN))

# Initialize pins
dc = machine.Pin(DC_PIN, machine.Pin.OUT)
cs = machine.Pin(CS_PIN, machine.Pin.OUT)
rst = machine.Pin(RST_PIN, machine.Pin.OUT)

def write_cmd(cmd):
    cs.value(0)
    dc.value(0)
    spi.write(bytes([cmd]))
    cs.value(1)

def write_data(data):
    cs.value(0)
    dc.value(1)
    if isinstance(data, int):
        spi.write(bytes([data]))
    else:
        spi.write(data)
    cs.value(1)

print("Resetting display...")
# Hardware reset
cs.value(1)
rst.value(1)
time.sleep_ms(10)
rst.value(0)
time.sleep_ms(10)
rst.value(1)
time.sleep_ms(150)

print("Initializing display...")
# Minimal init sequence
write_cmd(0xEF)  # Inter register enable 2
write_cmd(0xEB)
write_data(0x14)

write_cmd(0x84)
write_data(0x40)

write_cmd(0x85)
write_data(0xFF)

write_cmd(0x86)
write_data(0xFF)

write_cmd(0x87)
write_data(0xFF)

write_cmd(0x8E)
write_data(0xFF)

write_cmd(0x8F)
write_data(0xFF)

write_cmd(0x88)
write_data(0x0A)

write_cmd(0x89)
write_data(0x21)

write_cmd(0x8A)
write_data(0x00)

write_cmd(0x8B)
write_data(0x80)

write_cmd(0x8C)
write_data(0x01)

write_cmd(0x8D)
write_data(0x01)

write_cmd(0xB6)
write_data(bytes([0x00, 0x20]))

write_cmd(0x36)  # Memory Access Control
write_data(0x08)

write_cmd(0x3A)  # Pixel Format
write_data(0x05)  # 16-bit color

write_cmd(0x90)
write_data(bytes([0x08, 0x08, 0x08, 0x08]))

write_cmd(0xBD)
write_data(0x06)

write_cmd(0xBC)
write_data(0x00)

write_cmd(0xFF)
write_data(bytes([0x60, 0x01, 0x04]))

write_cmd(0xC3)
write_data(0x13)
write_cmd(0xC4)
write_data(0x13)

write_cmd(0xC9)
write_data(0x22)

write_cmd(0xBE)
write_data(0x11)

write_cmd(0xE1)
write_data(bytes([0x10, 0x0E]))

write_cmd(0xDF)
write_data(bytes([0x21, 0x0c, 0x02]))

# Gamma
write_cmd(0xF0)
write_data(bytes([0x45, 0x09, 0x08, 0x08, 0x26, 0x2A]))

write_cmd(0xF1)
write_data(bytes([0x43, 0x70, 0x72, 0x36, 0x37, 0x6F]))

write_cmd(0xF2)
write_data(bytes([0x45, 0x09, 0x08, 0x08, 0x26, 0x2A]))

write_cmd(0xF3)
write_data(bytes([0x43, 0x70, 0x72, 0x36, 0x37, 0x6F]))

write_cmd(0xED)
write_data(bytes([0x1B, 0x0B]))

write_cmd(0xAE)
write_data(0x77)

write_cmd(0xCD)
write_data(0x63)

write_cmd(0x70)
write_data(bytes([0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03]))

write_cmd(0xE8)
write_data(0x34)

write_cmd(0x62)
write_data(bytes([0x18, 0x0D, 0x71, 0xED, 0x70, 0x70, 0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70]))

write_cmd(0x63)
write_data(bytes([0x18, 0x11, 0x71, 0xF1, 0x70, 0x70, 0x18, 0x13, 0x71, 0xF3, 0x70, 0x70]))

write_cmd(0x64)
write_data(bytes([0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07]))

write_cmd(0x66)
write_data(bytes([0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0x00, 0x00, 0x00]))

write_cmd(0x67)
write_data(bytes([0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98]))

write_cmd(0x74)
write_data(bytes([0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00]))

write_cmd(0x98)
write_data(bytes([0x3e, 0x07]))

write_cmd(0x35)  # Tearing effect line ON
write_cmd(0x21)  # Display inversion ON

write_cmd(0x11)  # Sleep out
time.sleep_ms(120)

write_cmd(0x29)  # Display ON
time.sleep_ms(20)

print("Display initialized!")

# Test: Fill with RED
print("Filling screen with RED...")
write_cmd(0x2A)  # Column address set
write_data(struct.pack('>HH', 0, 239))

write_cmd(0x2B)  # Row address set
write_data(struct.pack('>HH', 0, 239))

write_cmd(0x2C)  # Memory write

# Write RED color (0xF800) for entire screen
red_bytes = struct.pack('>H', 0xF800)
buffer = red_bytes * 512

cs.value(0)
dc.value(1)
for _ in range((240 * 240) // 512):
    spi.write(buffer)
cs.value(1)

print("Done! Screen should be RED")
time.sleep(2)

# Test: Fill with GREEN
print("Filling screen with GREEN...")
write_cmd(0x2A)
write_data(struct.pack('>HH', 0, 239))
write_cmd(0x2B)
write_data(struct.pack('>HH', 0, 239))
write_cmd(0x2C)

green_bytes = struct.pack('>H', 0x07E0)
buffer = green_bytes * 512

cs.value(0)
dc.value(1)
for _ in range((240 * 240) // 512):
    spi.write(buffer)
cs.value(1)

print("Done! Screen should be GREEN")
