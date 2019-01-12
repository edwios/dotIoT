import epd2in13
import time
from PIL import Image, ImageDraw, ImageFont

def wipe_screen():

    epd = epd2in13.EPD()
    epd.init(epd.lut_partial_update)

    x=0
    f=True
    while (f):
        bimage = Image.new('1', (epd2in13.EPD_WIDTH, epd2in13.EPD_HEIGHT), 255)  # 255: clear the frame
        bdraw = ImageDraw.Draw(bimage)
        print(x)
        bdraw.rectangle((x, 0, 16+x-1, epd2in13.EPD_HEIGHT-1), fill = 0)
#        bdraw.rectangle((0, 0, 112, epd2in13.EPD_HEIGHT-8), fill = 0)
        epd.clear_frame_memory(0xFF)
        epd.set_frame_memory(bimage, 0, 0)
        epd.display_frame()

        bimage = Image.new('1', (epd2in13.EPD_WIDTH, epd2in13.EPD_HEIGHT), 255)  # 255: clear the frame
        bdraw = ImageDraw.Draw(bimage)
        print(x)
        bdraw.rectangle((x, 0, 16+x-1, epd2in13.EPD_HEIGHT-1), fill = 0)
#        bdraw.rectangle((0, 0, 112, epd2in13.EPD_HEIGHT-8), fill = 0)
        epd.clear_frame_memory(0xFF)
        epd.set_frame_memory(bimage, 0, 0)
        epd.display_frame()

        x += 16
        print("--")
        f=(x<=epd2in13.EPD_WIDTH)
    print("==")

    f=False

if __name__ == '__main__':
    main()
