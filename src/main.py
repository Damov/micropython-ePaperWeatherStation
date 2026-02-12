# ePaperWeatherStation by Frederik Andersen
# v.1.0.0
# Date 2025-02-07
# This project fetches weather data for a specified location using the MET Weather API
# and displays it on a Waveshare 5.65-inch ePaper display. The weather data is updated
# every hour, and the screen is cleared once every 24 hours to prevent ghosting.
# Released under the MIT License (MIT). See LICENSE for details.

import os, sys
import utime
import gc
from datafetcher import DataFetcher
from timemanager import TimeManager
from screenmanager import ScreenManager                                                                    
from lib.configuration import IniConfig 
from errorhandler import ErrorHandler

#Paths to the configuration files
APP_CONFIG_FILE_PATH  = "config/config.ini"
LNG_CONFIG_FILE_PATH  = "config/language.ini"
WIFI_CONFIG_FILE_PATH = "config/wifi.ini"

#Log file configuration
LOG_PATH = "data/exception.log"
MAX_LOG_SIZE = 100 * 1024  # 100 kB

# ============================================================
#  PRINTS EXCEPTIONS TO THE SCREEN
# ============================================================
def write_exception_to_screen(exc):
    """
    Compact top-level handler: clear screen and show exception summary.
    Call from a top-level try/except block with the caught exception.
    """
    import gc, sys
    try:
        import uio as io
    except ImportError:
        import io

    from lib.e_ink_lib import EPD_5in65
    from lib.easywriter import EasyWriter
    import fonts.opensans16

    _SCREEN_W = 600
    _SCREEN_H = 448

    gc.collect()
    screen_buffer = bytearray(600 * 448 // 2)

    # ---- Build traceback text in RAM ---------------------------------
    buf = io.StringIO()
    sys.print_exception(exc, buf)       # prints "Traceback..., File \"x\", line n, ..."[web:8]
    lines = buf.getvalue().splitlines()

    # Extract last "File ..." (file + line) and last line (type + message)
    file_line = ""
    for l in lines:
        if l.startswith("  File "):
            file_line = l
    last_line = lines[-1] if lines else ""

    # ---- Draw on e-paper ---------------------------------------------
    epd = EPD_5in65(screen_buffer)
    ew = EasyWriter(epd, fonts.opensans16)
    ew.device.fill(ew.device.White)

    y = 8
    ew.add_text("ERROR: EXCEPTION", 6, y); y += 22

    if file_line:
        ew.add_text(file_line[:52], 6, y); y += 18  # truncate for safety
    if last_line:
        ew.add_text(last_line[:52], 6, y); y += 18

    # Optional: show a couple more traceback lines if space
    for l in lines[-4:]:
        if y > _SCREEN_H - 18:
            break
        ew.add_text(l[:52], 6, y)
        y += 18

    epd.EPD_5IN65F_Display(epd.buffer)
    epd.Sleep()

    gc.collect()    
    

# ============================================================
#  LOG FILE HANDLER
# ============================================================

def _write_log_header(f):
    try:
        ts = utime.localtime()
        timestr = "%04d-%02d-%02d %02d:%02d:%02d" % (
            ts[0], ts[1], ts[2], ts[3], ts[4], ts[5]
        )
    except Exception:
        timestr = "unknown-time"
    f.write("\n===== EXCEPTION @ %s =====\n" % timestr)


def log_exception(e):
    try:
        size = 0
        try:
            st = os.stat(LOG_PATH)
            size = st[6] if len(st) > 6 else st[0]
        except OSError:
            size = 0

        if size > MAX_LOG_SIZE:
            try:
                with open(LOG_PATH, "r") as f:
                    data = f.read()
                keep = data[-MAX_LOG_SIZE // 2 :]
                with open(LOG_PATH, "w") as f:
                    f.write("=== LOG TRUNCATED, KEPT LAST HALF ===\n")
                    f.write(keep)
            except Exception:
                with open(LOG_PATH, "w") as f:
                    f.write("=== LOG RESET DUE TO ERROR ===\n")

        with open(LOG_PATH, "a") as f:
            _write_log_header(f)
            sys.print_exception(e, f)  # traceback into file[web:21][web:25]
            f.write("===== END EXCEPTION =====\n")
    except Exception:
        pass

# ============================================================
#  MAIN PROGRAM
# ============================================================

def main():
#-- Read configuration files --------------------------------
    app_config  = IniConfig(APP_CONFIG_FILE_PATH) #.... Load application configuration
    lng_config  = IniConfig(LNG_CONFIG_FILE_PATH) #.... Load language configuration
    wifi_config = IniConfig(WIFI_CONFIG_FILE_PATH) #.... Load wifi configuration

    # Write in your location. The location must be defined in datafetcher locations dictionary with latitude, longitude and altitude
    data = DataFetcher(app_config, wifi_config)
    time_manager = TimeManager(data, app_config, lng_config)
    screen_manager = ScreenManager(data, time_manager, app_config, lng_config)
    
    while True:
        time_for_update = time_manager.is_it_time()
        if time_for_update[0] == True: # Time to fetch new weather data?
            print(f'Updating the weather data. Datetime: {time_manager.rtc.datetime()}')
            data.fetch_new_weather_data() # Update the data
            
        else:
            if time_for_update[2] == True: # Time to clear the screen? Should be at night
                print(f'Cleaning the screen. Datetime: {time_manager.rtc.datetime()}')
                screen_manager.clear()
                screen_manager.clear()
                
            elif time_for_update[1] == True: # Time to update the screen?
                print(f'Updating the screen. Datetime: {time_manager.rtc.datetime()}')
                screen_manager.draw() # Draw the screen

        gc.collect() # Free up memory.
        utime.sleep(10)
    


if __name__=='__main__':
    try:
        main()
    except Exception as e:
        # Log and optionally re‑raise or soft‑fail
        log_exception(e)
        # Uncomment if you want the board to reboot after logging:
        # import machine
        # machine.reset()
        ErrorHandler.turn_on_led()

        #Write exception on the ink screen
        write_exception_to_screen(e)
        
