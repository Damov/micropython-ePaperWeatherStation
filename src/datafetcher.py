# DataFetcher by Frederik Andersen
# Class to handle all data from the MET Weather API and my personal API.
# The MET Weather API requires a unique user agent to use their API, and your email should be included.
# This is stated under the terms of service for the API: https://api.met.no/doc/TermsOfService
# Released under the MIT License (MIT). See LICENSE for details.

import gc
import os
import json
import utime
import network
import lib.mrequests as requests
from lib.configuration import IniConfig 
from machine import RTC
from errorhandler import ErrorHandler

class DataFetcher():
    def __init__(self, app_config, wifi_config):
        """
        Initializes the DataFetcher with a specified location.

        Parameters:
        -----------
        app_config (IniConfig): An instance of IniConfig for application configuration.
        wifi_config (IniConfig): An instance of IniConfig for Wi-Fi configuration.
        """

    #-- Read the configuration files ------------------------------
        self._wifi_config = wifi_config #........................ Save wifi configuration object
        self._app_config  = app_config #......................... Save application configuration

    #-- Set WIFI credentials --------------------------------------
        self._SSID = str(self._wifi_config.get_section("wifi").get("ssid")) #.......... Set SSID
        self._WIFI_TOKEN = str(self._wifi_config.get_section("wifi").get("password")) # Set WIFI password

    #-- Set user agent and location -------------------------------
        usr_agent = self._app_config.get_section("requests").get("user_agent")# ... Get the user agent from config file
        self.USER_AGENT_HEADER = {'User-Agent': usr_agent} #....................... Set the user agent header

        self.location_name      = self._app_config.get_section("location").get("name") #..... Get location name
        self.location_latitude  = self._app_config.get_section("location").get("latitude") #. Get latitude
        self.location_longitude = self._app_config.get_section("location").get("longitude") # Get longitude
        self.location_altitude  = self._app_config.get_section("location").get("altitude") #. Get altitude

        #Check if wifi is enabled
        self._is_wifi_enabled()

    #def _is_wifi_enabled(self):
    #    """
    #    Checks if Wi-Fi is enabled and connects if not.
    #    Ensures Wi-Fi is enabled. If not, attempts to enable it. If connection fails, retries after a delay.
    #    """
    #    wlan = network.WLAN(network.STA_IF)
    #    if wlan.isconnected() == False: # If not connected to wifi.
    #        print("Not connected to wifi...")
    #        try:
    #            self._enable_wifi(wlan) # Connect to wifi.
    #        except Exception as e:
    #            raise e
    #            """
    #            ErrorHandler(e)
    #            
    #            while True:
    #                ErrorHandler.retry_timer() # Flashes led and waits 5 minutes before continuing this loop.
    #                try:
    #                    self._enable_wifi(wlan) # Connect to wifi
    #                except:
    #                    continue
    #            """

    def _is_wifi_enabled(self, retries=3, delay=5):
        wlan = network.WLAN(network.STA_IF)
        for attempt in range(retries):
            if wlan.isconnected():
                return
            try:
                self._enable_wifi(wlan)
                return
            except Exception as e:
                print("Wi-Fi attempt", attempt + 1, "failed:", e)
                utime.sleep(delay)
        raise RuntimeError("Wi-Fi connection failed after retries")

    def _enable_wifi(self, wlan, connection_timeout = 30):
        wlan.active(True)
        wlan.connect(self._SSID, self._WIFI_TOKEN)

        
        while connection_timeout > 0:
            status = wlan.status()
            # break if either finished (>=3) or error (<0)
            if status < 0 or status >= 3:
                break
            connection_timeout -= 1
            print("Waiting for Wi-Fi connection...", status)
            utime.sleep(1)

        status = wlan.status()
        if status != 3:
            # Optional: map status to a readable message
            raise RuntimeError(f"Failed to establish a network connection, status: {status}")
        else:
            print("Connection successful!")
            print("IP address:", wlan.ifconfig()[0])
        return
    
    def _read_file(self, filename, bypass_error=False):
        """
        Read and return data.
        returns data if read is successful else raise exception.
        
        Parameters:
        filename (str): filename without extention.
        bypass_error (bool): used to bypass the error drawing to the screen. Normally False.
        """
        """
        Reads and returns data from a JSON file.

        Parameters:
        filename (str): The name of the file (without extension) to read.
        bypass_error (bool): If True, bypasses error handling. Default is False.

        Returns:
        dict or list: The data read from the file.

        Raises:
        OSError: If there is an error reading the file.
        """
        try:
            with open(f'data/{filename}.json', 'r') as file:
                data = json.load(file)
                return data
            
        except OSError as e:
            if bypass_error == False:
                exception_string = f"Error trying to open file: OSError {e}"
                ErrorHandler(exception_string)
            raise
    
    def _save_file(self, filename, data):
        """
        Saves data to a JSON file.

        Parameters:
        filename (str): The name of the file (without extension) to save.
        data (dict): The data to save.
        """
        with open(f'data/{filename}.json', 'w') as file:
                json.dump(data, file)
        os.sync() # Make sure the filesystem is up to date after the new file is added.
    
    def get_image(self, image_name):
        """
        Retrieves a binary image from flash storage.

        Parameters:
        image_name (str): The name of the image file (without extension).

        Returns:
        bytes: The binary data of the image.

        Raises:
        Exception: If there is an error loading the image.
        """
        try:
            with open(f'images/{image_name}.bin', 'rb') as file:
                image = file.read()
                return image
                
        except Exception as e:
            exception_string = f"Error loading image: {e}"
            ErrorHandler(exception_string)
            raise
        
    def fetch_new_weather_data(self):
        """
        Fetches weather data from the MET Weather API for the specified location.

        Saves the fetched data and headers to JSON files.

        Raises:
        Exception: If there is an error connecting to the MET Weather API.
        """
        lat = self.location_latitude
        lon = self.location_longitude
        alt = self.location_altitude

        self._is_wifi_enabled() # Ensure that wifi is connected.
    
        # GET weather data from MET using mini.json.
        # Can use compact or complete parameter instead of mini.json if more data is needed.
        print(f'https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}&altitude={alt}')

        weather_data = requests.get(
            f'https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}&altitude={alt}', headers=self.USER_AGENT_HEADER, save_headers=True)
        
        if weather_data.status_code != 200:  # 200 = successful connection to MET API, anything else is an error.
            exception_string = f"MET Weather API connection error: {weather_data.status_code}"
            ErrorHandler(exception_string)
            raise Exception(exception_string)
        else:
            file_name_prefix = self._app_config.get_section('requests').get('log_file_name_prefix')
            self._save_file(f'{file_name_prefix}', weather_data.json()) # Save the data from the api
            self._save_file(f'{file_name_prefix}_headers', weather_data.headers) # Save the header.

            #self._data_expire_time = weather_data.headers['Expires']

            weather_data.close()
            gc.collect()
            
    def _get_weather_icon(self, icon_requested):
        """
        Fetches a weather icon from a Frederik API.
        All the weather icons takes up to much space to save it to the flash.
        The solution was to put it on a flask api using pythonanywhere.com.

        Parameters:
        icon_requested (str): The name of the requested weather icon (without extension).

        Returns:
        bytes: The binary data of the weather icon.

        Raises:
        Exception: If there is an error connecting to the Frederik API.
        """
    
        self._is_wifi_enabled() # Ensure that wifi is connected.
        gc.collect()
        icon_recieved = requests.get(
                f'https://frederikapi.pythonanywhere.com/api/?requested-icon={icon_requested}', headers=self.USER_AGENT_HEADER)
        
        if icon_recieved.status_code != 200:  # 200 = successful connection to frederikapi, anything else is an error.
                exception_string = f"Frederik API connection error: {icon_recieved.status_code}, Requested icon: {icon_requested}"
                ErrorHandler(exception_string)
                print(icon_recieved.headers)
                raise Exception(exception_string)

        else:
            data = icon_recieved.content
            icon_recieved.close()
            gc.collect()
            return data
        
        
    def get_weather_data(
                self,
                future_year,
                future_month,
                future_day,
                future_hour,
                retrieve_image=True,
                symbol_period='next_1_hours'
            ):
        """
        Retrieves the temperature and associated weather icon.

        Parameters:
        -----------
        future_year (int): The year of the requested time.
        future_month (int): The month of the requested time.
        future_day (int): The day of the requested time.
        future_hour (int): The hour of the requested time.
        retrieve_image (bool): Whether to retrieve the weather icon. Default is True.
        symbol_period (str): The period for the weather symbol. Default is 'next_1_hours'.
        
        Returns:
        --------
        tuple:
            int: The temperature.
            int: The humidity.
            bytes: The weather icon as binary data.
        """
    
    #-- Read the actual weather data --------------------------------------------------------
        file_name_prefix = self._app_config.get_section('requests').get('log_file_name_prefix')
        weather_data = self._read_file(file_name_prefix) # Read the weather data.

        for data in weather_data['properties']['timeseries']: # Loop trough the data and find correct time.
        #-- Parse the date time of the particular data point --------------------------------
            data_year  = int(data['time'].split("T")[0].split("-")[0])
            data_month = int(data['time'].split("T")[0].split("-")[1])
            data_day   = int(data['time'].split("T")[0].split("-")[2])

            data_hour   = int(data['time'].split("T")[1].replace('Z','').split(':')[0])
            data_minute = int(data['time'].split("T")[1].replace('Z','').split(':')[1])
            data_second = int(data['time'].split("T")[1].replace('Z','').split(':')[2])

            if (future_year == data_year and future_month == data_month and future_day == data_day and future_hour == data_hour):
            #-- Get the temperature --------------------------------------------------------------------------------
                temperature = data['data']['instant']['details']['air_temperature'] # Get the current temperature.
            #-- Get the humidity -----------------------------------------------------------------------------------
                humidity = data['data']['instant']['details']['relative_humidity'] # Get the current relative humidity.

            #-- Retrieve the weather icon --------------------------------------------------------------------------
                if retrieve_image == True:
                    filename = f"{data['data'][symbol_period]['summary']['symbol_code']}_80x80"
                    weather_icon = self.get_image(filename) #........................................... Get 80x80 icon from flash.
                else:
                    weather_icon = None
                break
                    
        return temperature, humidity, weather_icon
    
    
    def get_expiretime_weatherdata(self):
        """
        Retrieves the expiration time for the weather data.

        Returns:
        str: The expiration time as a string.
        """

        try:
            file_name_prefix = self._app_config.get_section('requests').get('log_file_name_prefix')
            headers_list = self._read_file(f"{file_name_prefix}_headers", bypass_error=True) # Bypass error drawing to screen if the file doesnt exist.
            headers_dict = dict(header.split(": ", 1) for header in headers_list)
            
            expire_time = headers_dict['Expires']
            return expire_time
        
        except Exception as e: # The file is not made yet, use fictional http date and time.
            print(e)
            return 'Tue, 14 Jan 2025 12:58:38 GMT'

    