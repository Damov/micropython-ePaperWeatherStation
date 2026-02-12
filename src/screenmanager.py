# ScreenManager by Frederik Andersen
# Class to manage the ePaper/eInk screen.
# Released under the MIT License (MIT). See LICENSE for details.

import gc
import utime
import machine
from lib.e_ink_lib import EPD_5in65
from lib.easywriter import EasyWriter
from errorhandler import ErrorHandler
import fonts.opensans80, fonts.opensans32, fonts.opensans16

class ScreenManager():
    
    def __init__(self, data_fetcher, time_manager, app_config, lng_config):
        """
        Initializes the ScreenManager with a DataFetcher and TimeManager.

        Parameters:
        data_fetcher (DataFetcher): An instance of the DataFetcher class.
        time_manager (TimeManager): An instance of the TimeManager class.
        app_config (IniConfig): An instance of IniConfig for application configuration.
        lng_config (IniConfig): An instance of IniConfig for language configuration.
        """
        self._app_config  = app_config #........................ Save application configuration
        self._lang_config = lng_config  #....................... Save language configuration

        self.data_fetcher = data_fetcher
        self.time_manager = time_manager
        self.screen_buffer = bytearray(600 * 448 // 2) # buffer for the display, get memory leaks if not global outside the driver.
    
    def clear(self):
        """
        Clears the screen.

        The screen should be cleared every 24 hours. 
        If you plan to store the device, run this method to clear the screen for storage.
        """
        gc.collect()
        epd = EPD_5in65(self.screen_buffer)  # The screen
        epd.EPD_5IN65F_Clear(epd.White)
        epd.Sleep()
        self.time_manager.set_screen_cleaned()
        
    def draw(self):
        """
        Updates and draws the screen with all its content.
        
        This method initializes the screen, draws weather data, date, and lines, 
        then refreshes and puts the screen to sleep to prevent damage.
        """
        ew = self._init_screen()
        ew.device.fill(ew.device.White) # White background.
        
        self._draw_weather_data(ew)
        self._draw_date(ew)
        self._draw_lines(ew)
        self._draw_location(ew)
        
        ew.refresh()
        ew.sleep()  # ALWAYS run this after writing to the screen, may cause physical damage to screen if not.
        
        # Next draw should be in 1 hour. Set that the screen just have been updated.
        self.time_manager.set_screen_updated()
    
    def _init_screen(self):
        """
        Initializes the screen and EasyWriter.

        This method is used to write to the screen multiple times. 
        After the screen goes to sleep, everything needs to be re-initialized.

        Returns:
        EasyWriter: An instance of the EasyWriter class.
        """
        gc.collect()
        try:
            epd = EPD_5in65(self.screen_buffer)  # The screen
            ew = EasyWriter(epd, fonts.opensans16) # EasyWriter for easier use of the writer class
            return ew
        
        except MemoryError:
            print(gc.mem_free())
            print("Soft reset...")
            machine.soft_reset()
            
        
    def _draw_weather_data(self, ew):
        """
        Draws all weather data including text and icons on the display.

        Parameters:
        ew (EasyWriter): An instance of the EasyWriter class used to draw text and images on the display.
        """

        def get_future_time(offset_seconds):
            """
            Help function to get future time after offset in seconds.

            Parameters:
            offset_seconds (int): Number of seconds to add to the current time.

            Returns:
            tuple: A tuple containing (year, month, mday, hour, minute, second, weekday, yearday).
            """
            import time
        #-- current local time as tuple ----------------------------------------
            now = time.localtime()  # (year, month, mday, hour, min, sec, weekday, yearday) [web:2]

        #-- convert to seconds since epoch -------------------------------------
            now_s = time.mktime(now)  # [web:2]

        #-- Get future timestamp -----------------------------------------------
            future_s = now_s + offset_seconds

        #-- back to a time tuple -----------------------------------------------
            future = time.localtime(future_s)  # [web:2]

            year, month, mday, hour, minute, second, weekday, yearday = (
                future[0], future[1], future[2], future[3], future[4], future[5], future[6], future[7]
            )

        #-- Return -------------------------------------------------------------
            return weekday, year, month, mday, hour, minute, second
        
        # Set font for weather data
        ew.change_font(fonts.opensans32) # Change font size

        # --------------------------------------------------------------------------------------------------
        # LEFT SIDE OF THE SCREEN
        # --------------------------------------------------------------------------------------------------
        Y_POS_TIME = 25
        Y_POS_ICON = 100
        Y_POS_INFO = 180

        # [1.1] Print current weather data
        delta_seconds = 0
        _, year, month, day, hour, minute, _ = get_future_time(delta_seconds)
        temp, humidity, icon = self.data_fetcher.get_weather_data(year, month, day, hour, retrieve_image = True, symbol_period = 'next_1_hours')

        minute = f"{minute}" if minute >= 10 else f"0{minute}"
        hour = f"{hour}" if hour >= 10 else f"0{hour}"

        #lng_now_str = self._lang_config.get_section("language_common").get("now")

        dH = 20
        line_height = int(448/2 - 448/4 - 40)
        ew.add_image_vertical_center(
                        image=icon,
                        img_width = 80,
                        img_height = 80,
                        width_pos = Y_POS_ICON,
                        height_start_pos = line_height,
                        height_end_pos = line_height + 90
                    )
        ew.add_text_vertical_center(
                        f"{hour}:{minute}",
                        width_pos = Y_POS_TIME,
                        height_start_pos = line_height,
                        height_end_pos = line_height + 90
                    )
        ew.add_text_vertical_center(
                        f"{temp}°C",
                        width_pos = Y_POS_INFO,
                        height_start_pos = line_height - dH,
                        height_end_pos = line_height + 90 - dH
                    )
        ew.add_text_vertical_center(
                        f"{humidity}%",
                        width_pos = Y_POS_INFO,
                        height_start_pos = line_height + dH,
                        height_end_pos = line_height + 90 + dH
                    )

        # [1.2] Print +4h weather data
        delta_seconds = 4*60*60
        _, year, month, day, hour, minute, _ = get_future_time(delta_seconds)
        temp, humidity, icon = self.data_fetcher.get_weather_data(year, month, day, hour, retrieve_image = True, symbol_period = 'next_1_hours')

        minute = f"{minute}" if minute >= 10 else f"0{minute}"
        hour = f"{hour}" if hour >= 10 else f"0{hour}"

        dH = 20
        line_height = int(448/2 - 40)
        ew.add_image_vertical_center(
                        image=icon,
                        img_width = 80,
                        img_height = 80,
                        width_pos = Y_POS_ICON,
                        height_start_pos = line_height,
                        height_end_pos = line_height + 90
                    )
        ew.add_text_vertical_center(
                        f"{hour}:{minute}",
                        width_pos = Y_POS_TIME,
                        height_start_pos = line_height,
                        height_end_pos = line_height + 90
                    )
        ew.add_text_vertical_center(
                        f"{temp}°C",
                        width_pos = Y_POS_INFO,
                        height_start_pos = line_height - dH,
                        height_end_pos = line_height + 90 - dH
                    )
        ew.add_text_vertical_center(
                        f"{humidity}%",
                        width_pos = Y_POS_INFO,
                        height_start_pos = line_height + dH,
                        height_end_pos = line_height + 90 + dH
                    )

        # [1.3] Print +8h weather data
        delta_seconds = 8*60*60
        _, year, month, day, hour, minute, _ = get_future_time(delta_seconds)
        temp, humidity, icon = self.data_fetcher.get_weather_data(year, month, day, hour, retrieve_image = True, symbol_period = 'next_1_hours')

        minute = f"{minute}" if minute >= 10 else f"0{minute}"
        hour = f"{hour}" if hour >= 10 else f"0{hour}"

        dH = 20
        line_height = int(448/2 + 448/4 - 40)
        ew.add_image_vertical_center(
                        image=icon,
                        img_width = 80,
                        img_height = 80,
                        width_pos = Y_POS_ICON,
                        height_start_pos = line_height,
                        height_end_pos = line_height + 90
                    )
        ew.add_text_vertical_center(
                        f"{hour}:{minute}",
                        width_pos = Y_POS_TIME,
                        height_start_pos = line_height,
                        height_end_pos = line_height + 90
                    )
        ew.add_text_vertical_center(
                        f"{temp}°C",
                        width_pos = Y_POS_INFO,
                        height_start_pos = line_height - dH,
                        height_end_pos = line_height + 90 - dH
                    )
        ew.add_text_vertical_center(
                        f"{humidity}%",
                        width_pos = Y_POS_INFO,
                        height_start_pos = line_height + dH,
                        height_end_pos = line_height + 90 + dH
                    )
        del icon
        gc.collect()

        # --------------------------------------------------------------------------------------------------
        # RIGHT SIDE OF THE SCREEN
        # --------------------------------------------------------------------------------------------------
        Y_POS_WEEK_NAME = 290
        Y_POS_MIDDAY_TMP = 440

        Y_POS_DAY1 = 1 * 65
        Y_POS_DAY2 = 2 * 65
        Y_POS_DAY3 = 3 * 65
        Y_POS_DAY4 = 4 * 65
        Y_POS_DAY5 = 5 * 65
        

        # Fetch future datetimes
        day1_weekday, day1_year, day1_month, day1_day, _, _, _ = get_future_time(1 * 24*60*60)
        day2_weekday, day2_year, day2_month, day2_day, _, _, _ = get_future_time(2 * 24*60*60)
        day3_weekday, day3_year, day3_month, day3_day, _, _, _ = get_future_time(3 * 24*60*60)
        day4_weekday, day4_year, day4_month, day4_day, _, _, _ = get_future_time(4 * 24*60*60)
        day5_weekday, day5_year, day5_month, day5_day, _, _, _ = get_future_time(5 * 24*60*60)

        # Convert weekday to name
        day_converter = {
             0: self._lang_config.get_section('language_short_days').get('name_monday'),
             1: self._lang_config.get_section('language_short_days').get('name_tuesday'),
             2: self._lang_config.get_section('language_short_days').get('name_wednesday'),
             3: self._lang_config.get_section('language_short_days').get('name_thursday'),
             4: self._lang_config.get_section('language_short_days').get('name_friday'),
             5: self._lang_config.get_section('language_short_days').get('name_saturday'),
             6: self._lang_config.get_section('language_short_days').get('name_sunday'),
        }
        
        day1_weekday_name = day_converter[day1_weekday]
        day2_weekday_name = day_converter[day2_weekday]
        day3_weekday_name = day_converter[day3_weekday]
        day4_weekday_name = day_converter[day4_weekday]
        day5_weekday_name = day_converter[day5_weekday]

        #Write days
        ew.add_text_vertical_center(f"{day1_weekday_name}", width_pos=Y_POS_WEEK_NAME, height_start_pos=Y_POS_DAY1, height_end_pos=Y_POS_DAY1 + 60)
        ew.add_text_vertical_center(f"{day2_weekday_name}", width_pos=Y_POS_WEEK_NAME, height_start_pos=Y_POS_DAY2, height_end_pos=Y_POS_DAY2 + 60)
        ew.add_text_vertical_center(f"{day3_weekday_name}", width_pos=Y_POS_WEEK_NAME, height_start_pos=Y_POS_DAY3, height_end_pos=Y_POS_DAY3 + 60)
        ew.add_text_vertical_center(f"{day4_weekday_name}", width_pos=Y_POS_WEEK_NAME, height_start_pos=Y_POS_DAY4, height_end_pos=Y_POS_DAY4 + 60)
        ew.add_text_vertical_center(f"{day5_weekday_name}", width_pos=Y_POS_WEEK_NAME, height_start_pos=Y_POS_DAY5, height_end_pos=Y_POS_DAY5 + 60)

        #Retrieve midday weather data
        day1_midday_temp, _, _ = self.data_fetcher.get_weather_data(day1_year, day1_month, day1_day, 12, retrieve_image = False, symbol_period = 'next_6_hours')
        day2_midday_temp, _, _ = self.data_fetcher.get_weather_data(day2_year, day2_month, day2_day, 12, retrieve_image = False, symbol_period = 'next_6_hours')
        day3_midday_temp, _, _ = self.data_fetcher.get_weather_data(day3_year, day3_month, day3_day, 12, retrieve_image = False, symbol_period = 'next_6_hours')
        day4_midday_temp, _, _ = self.data_fetcher.get_weather_data(day4_year, day4_month, day4_day, 12, retrieve_image = False, symbol_period = 'next_6_hours')
        day5_midday_temp, _, _ = self.data_fetcher.get_weather_data(day5_year, day5_month, day5_day, 12, retrieve_image = False, symbol_period = 'next_6_hours')

        #Retrieve morning weather data
        day1_morn_temp, _, _ = self.data_fetcher.get_weather_data(day1_year, day1_month, day1_day, 6, retrieve_image = False, symbol_period = 'next_6_hours')
        day2_morn_temp, _, _ = self.data_fetcher.get_weather_data(day2_year, day2_month, day2_day, 6, retrieve_image = False, symbol_period = 'next_6_hours')
        day3_morn_temp, _, _ = self.data_fetcher.get_weather_data(day3_year, day3_month, day3_day, 6, retrieve_image = False, symbol_period = 'next_6_hours')
        day4_morn_temp, _, _ = self.data_fetcher.get_weather_data(day4_year, day4_month, day4_day, 6, retrieve_image = False, symbol_period = 'next_6_hours')
        day5_morn_temp, _, _ = self.data_fetcher.get_weather_data(day5_year, day5_month, day5_day, 6, retrieve_image = False, symbol_period = 'next_6_hours')

        #Retrieve symbol for 12 hours
        _, _, day1_icon = self.data_fetcher.get_weather_data(day1_year, day1_month, day1_day, 12, retrieve_image = True, symbol_period = 'next_6_hours')
        _, _, day2_icon = self.data_fetcher.get_weather_data(day2_year, day2_month, day2_day, 12, retrieve_image = True, symbol_period = 'next_6_hours')
        _, _, day3_icon = self.data_fetcher.get_weather_data(day3_year, day3_month, day3_day, 12, retrieve_image = True, symbol_period = 'next_6_hours')
        _, _, day4_icon = self.data_fetcher.get_weather_data(day4_year, day4_month, day4_day, 12, retrieve_image = True, symbol_period = 'next_6_hours')
        _, _, day5_icon = self.data_fetcher.get_weather_data(day5_year, day5_month, day5_day, 12, retrieve_image = True, symbol_period = 'next_6_hours')

        #Plot symbol
        ew.add_image_vertical_center(image=day1_icon, img_width=80, img_height=80, width_pos=Y_POS_WEEK_NAME + 60, height_start_pos=Y_POS_DAY1, height_end_pos=Y_POS_DAY1+80)
        ew.add_image_vertical_center(image=day2_icon, img_width=80, img_height=80, width_pos=Y_POS_WEEK_NAME + 60, height_start_pos=Y_POS_DAY2, height_end_pos=Y_POS_DAY2+80)
        ew.add_image_vertical_center(image=day3_icon, img_width=80, img_height=80, width_pos=Y_POS_WEEK_NAME + 60, height_start_pos=Y_POS_DAY3, height_end_pos=Y_POS_DAY3+80)
        ew.add_image_vertical_center(image=day4_icon, img_width=80, img_height=80, width_pos=Y_POS_WEEK_NAME + 60, height_start_pos=Y_POS_DAY4, height_end_pos=Y_POS_DAY4+80)
        ew.add_image_vertical_center(image=day5_icon, img_width=80, img_height=80, width_pos=Y_POS_WEEK_NAME + 60, height_start_pos=Y_POS_DAY5, height_end_pos=Y_POS_DAY5+80)

        #Plot temp data on diagram
        ew.add_text_vertical_center(f"{day1_midday_temp:4.1f}", width_pos=Y_POS_MIDDAY_TMP, height_start_pos=Y_POS_DAY1, height_end_pos=Y_POS_DAY1 + 60)
        ew.add_text_vertical_center(f"{day2_midday_temp:4.1f}", width_pos=Y_POS_MIDDAY_TMP, height_start_pos=Y_POS_DAY2, height_end_pos=Y_POS_DAY2 + 60)
        ew.add_text_vertical_center(f"{day3_midday_temp:4.1f}", width_pos=Y_POS_MIDDAY_TMP, height_start_pos=Y_POS_DAY3, height_end_pos=Y_POS_DAY3 + 60)
        ew.add_text_vertical_center(f"{day4_midday_temp:4.1f}", width_pos=Y_POS_MIDDAY_TMP, height_start_pos=Y_POS_DAY4, height_end_pos=Y_POS_DAY4 + 60)
        ew.add_text_vertical_center(f"{day5_midday_temp:4.1f}", width_pos=Y_POS_MIDDAY_TMP, height_start_pos=Y_POS_DAY5, height_end_pos=Y_POS_DAY5 + 60)
        
        ew.add_text_vertical_center(f"/", width_pos=Y_POS_MIDDAY_TMP + 60, height_start_pos=Y_POS_DAY1, height_end_pos=Y_POS_DAY1 + 60)
        ew.add_text_vertical_center(f"/", width_pos=Y_POS_MIDDAY_TMP + 60, height_start_pos=Y_POS_DAY2, height_end_pos=Y_POS_DAY2 + 60)
        ew.add_text_vertical_center(f"/", width_pos=Y_POS_MIDDAY_TMP + 60, height_start_pos=Y_POS_DAY3, height_end_pos=Y_POS_DAY3 + 60)
        ew.add_text_vertical_center(f"/", width_pos=Y_POS_MIDDAY_TMP + 60, height_start_pos=Y_POS_DAY4, height_end_pos=Y_POS_DAY4 + 60)
        ew.add_text_vertical_center(f"/", width_pos=Y_POS_MIDDAY_TMP + 60, height_start_pos=Y_POS_DAY5, height_end_pos=Y_POS_DAY5 + 60)

        ew.add_text_vertical_center(f"{day1_morn_temp:4.1}°C", width_pos=Y_POS_MIDDAY_TMP + 70, height_start_pos=Y_POS_DAY1, height_end_pos=Y_POS_DAY1 + 60)
        ew.add_text_vertical_center(f"{day2_morn_temp:4.1}°C", width_pos=Y_POS_MIDDAY_TMP + 70, height_start_pos=Y_POS_DAY2, height_end_pos=Y_POS_DAY2 + 60)
        ew.add_text_vertical_center(f"{day3_morn_temp:4.1}°C", width_pos=Y_POS_MIDDAY_TMP + 70, height_start_pos=Y_POS_DAY3, height_end_pos=Y_POS_DAY3 + 60)
        ew.add_text_vertical_center(f"{day4_morn_temp:4.1}°C", width_pos=Y_POS_MIDDAY_TMP + 70, height_start_pos=Y_POS_DAY4, height_end_pos=Y_POS_DAY4 + 60)
        ew.add_text_vertical_center(f"{day5_morn_temp:4.1}°C", width_pos=Y_POS_MIDDAY_TMP + 70, height_start_pos=Y_POS_DAY5, height_end_pos=Y_POS_DAY5 + 60)

        #Print times
        str_12h = self._lang_config.get_section("language_common").get("time_12h")
        str_6h  = self._lang_config.get_section("language_common").get("time_6h")
        ew.add_text_vertical_center(f"{str_12h:>4}", width_pos=Y_POS_MIDDAY_TMP-20, height_start_pos=30, height_end_pos=60)
        ew.add_text_vertical_center(f"{str_6h:>4}", width_pos=Y_POS_MIDDAY_TMP + 70, height_start_pos=30, height_end_pos=60)
        
        print("Free memory after allocating all content to buffer:", gc.mem_free())

    
    def _draw_date(self, ew):
        """
        Draw date and line under on top of the screen.
        Draw date and time the screen was last updated.
        """
        date_and_time = self.time_manager.get_datetime() # Weekday, day, month, year, hour, minute
        ew.change_font(fonts.opensans16)
        
        #ew.add_text(f"{date_and_time[0]} {date_and_time[1]}.{date_and_time[2]} {date_and_time[3]}", 10, 10)
        #ew.add_text(f"Sist oppdatert: {date_and_time[4]}:{date_and_time[5]}", 440, 417)
        #ew.add_text(f"Last update: {date_and_time[4]}:{date_and_time[5]}", 440, 417)

        lng_last_update_str = self._lang_config.get_section("language_common").get("last_update")
        ew.add_text(
                f"{lng_last_update_str}: "
                f"{date_and_time[0]}, {date_and_time[1]}. {date_and_time[2]} {date_and_time[3]} - "
                f"{date_and_time[4]}:{date_and_time[5]}",
                10,
                417
            )
        
        #ew.add_text(f"Sist oppdatert: {date_and_time[4]}:{date_and_time[5]}", 10, 417)
        
    def _draw_lines(self, ew):
        """
        Draw all lines on screen.
        """
        ew.device.hline(60, int(448/2) - 60, 180, ew.device.Black) # Pos x, Pos Y, lenght, color
        ew.device.hline(60, int(448/2) + 60, 180, ew.device.Black) # Pos x, Pos Y, lenght, color
        ew.device.vline(280, 60, 350, ew.device.Black) # Pos x, Pos Y, lenght, color
    
    def _draw_location(self, ew):
        """
        Draw current location.
        """
        # --------------------------------------------------------------------------------------------------
        # LOCATION NAME ON TOP OF THE SCREEN
        # --------------------------------------------------------------------------------------------------
        location_name = self._app_config.get_section('location').get('name')
        ew.change_font(fonts.opensans16) # Change font size
        ew.add_text_vertical_center(f"{location_name}", width_pos=10, height_start_pos=5, height_end_pos=30)

