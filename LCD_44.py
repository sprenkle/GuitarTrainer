
import board
import busio
import digitalio
import pwmio
import displayio
import fourwire
import terminalio
from adafruit_st7735r import ST7735R
from adafruit_display_text import label
import time


class LCD_1inch44:
    def __init__(self):
        self.width = 128
        self.height = 128
        
        displayio.release_displays()
        
        self.spi = busio.SPI(board.GP10, MOSI=board.GP11)
        display_bus = fourwire.FourWire(
            self.spi,
            command=board.GP8,
            chip_select=board.GP9,
            reset=board.GP12,
            baudrate=10000000
        )
        
        self.display = ST7735R(
            display_bus,
            width=128,
            height=128,
            rotation=270,
            bgr=True
        )
        
        self.splash = displayio.Group()
        self.display.root_group = self.splash

        # Color definitions (RGB565 format converted to RGB888 for displayio)
        self.WHITE  = 0xFFFFFF
        self.BLACK  = 0x000000
        self.GREEN  = 0x00FF00
        self.RED    = 0xFF0000
        self.BLUE   = 0x0000FF
        self.GBLUE  = 0x00FFFF
        self.YELLOW = 0xFFFF00
        
        # Create a reusable bitmap and palette for drawing
        self.bitmap = displayio.Bitmap(self.width, self.height, 16)
        self.palette = displayio.Palette(16)
        # Initialize palette with common colors
        self.palette[0] = self.BLACK
        self.palette[1] = self.WHITE
        self.palette[2] = self.RED
        self.palette[3] = self.GREEN
        self.palette[4] = self.BLUE
        self.palette[5] = self.GBLUE
        self.palette[6] = self.YELLOW
        
        self.tile_grid = displayio.TileGrid(self.bitmap, pixel_shader=self.palette)
        self.splash.append(self.tile_grid)
    
    def _get_color_index(self, color):
        """Map RGB color to palette index"""
        color_map = {
            self.BLACK: 0,
            self.WHITE: 1,
            self.RED: 2,
            self.GREEN: 3,
            self.BLUE: 4,
            self.GBLUE: 5,
            self.YELLOW: 6
        }
        return color_map.get(color, 1)
    
    def fill(self, color):
        """Fill the entire display with a color"""
        color_idx = self._get_color_index(color)
        for y in range(self.height):
            for x in range(self.width):
                self.bitmap[x, y] = color_idx
    
    def fill_rect(self, x, y, w, h, color):
        """Draw a filled rectangle"""
        color_idx = self._get_color_index(color)
        for dy in range(h):
            for dx in range(w):
                if 0 <= x + dx < self.width and 0 <= y + dy < self.height:
                    self.bitmap[x + dx, y + dy] = color_idx
    
    def rect(self, x, y, w, h, color):
        """Draw a rectangle outline"""
        self.hline(x, y, w, color)
        self.hline(x, y + h - 1, w, color)
        self.vline(x, y, h, color)
        self.vline(x + w - 1, y, h, color)
    
    def hline(self, x, y, w, color):
        """Draw a horizontal line"""
        color_idx = self._get_color_index(color)
        for dx in range(w):
            if 0 <= x + dx < self.width and 0 <= y < self.height:
                self.bitmap[x + dx, y] = color_idx
    
    def vline(self, x, y, h, color):
        """Draw a vertical line"""
        color_idx = self._get_color_index(color)
        for dy in range(h):
            if 0 <= x < self.width and 0 <= y + dy < self.height:
                self.bitmap[x, y + dy] = color_idx
    
    def text(self, text_str, x, y, color):
        """Draw text"""
        text_area = label.Label(terminalio.FONT, text=text_str, color=color)
        text_area.x = x
        text_area.y = y + 4  # Offset for better positioning
        self.splash.append(text_area)
    
    def show(self):
        """Update the display - automatically handled by displayio"""
        pass

  
if __name__=='__main__':
    pwm = pwmio.PWMOut(board.GP13, frequency=1000, duty_cycle=32768)#max 65535

    LCD = LCD_1inch44()
    #color BRG
    LCD.fill(LCD.BLACK)
     
    LCD.show()
    
    LCD.fill_rect(15,40,75,12,LCD.YELLOW)
    LCD.rect(15,40,75,12,LCD.YELLOW)
    LCD.text("1in44-LCD",17,42,LCD.WHITE)
    
    LCD.fill_rect(15,60,75,12,LCD.BLUE)
    LCD.rect(15,60,75,12,LCD.BLUE)
    LCD.text("128x128Px ",17,62,LCD.WHITE)
    
    LCD.fill_rect(15,80,75,12,LCD.GREEN)
    LCD.rect(15,80,75,12,LCD.GREEN)
    LCD.text("ST7735S",17,82,LCD.WHITE)

    LCD.hline(5,5,120,LCD.GBLUE)
    LCD.hline(5,125,120,LCD.GBLUE)
    LCD.vline(5,5,120,LCD.GBLUE)
    LCD.vline(125,5,120,LCD.GBLUE)
    
    LCD.show()
   
    key0 = digitalio.DigitalInOut(board.GP15)
    key0.direction = digitalio.Direction.INPUT
    key0.pull = digitalio.Pull.UP
    key1 = digitalio.DigitalInOut(board.GP17)
    key1.direction = digitalio.Direction.INPUT
    key1.pull = digitalio.Pull.UP
    key2 = digitalio.DigitalInOut(board.GP2)
    key2.direction = digitalio.Direction.INPUT
    key2.pull = digitalio.Pull.UP
    key3 = digitalio.DigitalInOut(board.GP3)
    key3.direction = digitalio.Direction.INPUT
    key3.pull = digitalio.Pull.UP
   
    while(1):      
        if(key0.value == False):
            LCD.fill_rect(100,100,20,20,LCD.GBLUE)
        else :
            LCD.fill_rect(100,100,20,20,LCD.BLACK)
            LCD.rect(100,100,20,20,LCD.GBLUE)
            
        if(key1.value == False):
            LCD.fill_rect(100,70,20,20,LCD.GBLUE)
        else :
            LCD.fill_rect(100,70,20,20,LCD.BLACK)
            LCD.rect(100,70,20,20,LCD.GBLUE)
            
        if(key2.value == False):
            LCD.fill_rect(100,40,20,20,LCD.GBLUE)
        else :
            LCD.fill_rect(100,40,20,20,LCD.BLACK)
            LCD.rect(100,40,20,20,LCD.GBLUE)
        if(key3.value == False):
            
            LCD.fill_rect(100,10,20,20,LCD.GBLUE)
        else :
            LCD.fill_rect(100,10,20,20,LCD.BLACK)
            LCD.rect(100,10,20,20,LCD.GBLUE) 
                      
        LCD.show()
    time.sleep(1)
    LCD.fill(0xFFFF)







