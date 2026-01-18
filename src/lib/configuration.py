
class IniConfig:
    """
        Simple INI configuration file parser. Supports sections, key-value pairs,
        comments, and basic type conversion.

        Example INI format:
        ```
        ; This is a comment
        [section1]
        key1 = value1
        key2 = 42 ; integer
        key3 = 3.14 ; float
        key4 = true ; boolean
        [section2]
        keyA = another value
        ```

        Attributes:
        -----------
        - _path (str): Path to the INI configuration file.
        - _data (dict): Nested dictionary holding the parsed configuration data.

        Methods:
        --------
        - load(): Loads and parses the INI file.
        - as_dict(): Returns the entire configuration as a nested dictionary.
        - get_section(section): Retrieves all key-value pairs in a specified section.
        - get(section, key): Retrieves a specific value from a section.

        Raises:
        -------
        - OSError: If the INI file cannot be opened or read.
        
    """
    
    def __init__(self, path, auto_load=True):
        """
        Initializes the IniConfig instance.

        Parameters:
        -----------
        path (str): Path to the INI configuration file.
        auto_load (bool): If True, automatically load the configuration upon initialization.

        Returns:
        --------
        None
            This constructor does not return any value.
        """
    #-- Init -----------------------------------------------------------------
        self._comment_chars = ["#"] #......... Characters indicating comments
        self._path = path #................... Path to the INI file
        self._data = {} #..................... Dictionary to hold the parsed configuration data
        if auto_load:
            self.load() #..................... Load the configuration file
    #-- Return  --------------------------------------------------------------
        return

    def _convert_value(self, value):
        """
        Converts a string value to an appropriate type (int, float, bool, or str).

        Parameters:
        -----------
        value (str): The string value to convert.

        Returns:
        --------
        The converted value in its appropriate type.
        """
    #-- Try int ------------------------------------
        try:
            return int(value)
        except ValueError:
            pass

    #-- Try float ----------------------------------
        try:
            return float(value)
        except ValueError:
            pass

    #-- Try booleans (optional) --------------------
        lower = value.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False

    #-- Fallback: raw string -----------------------
        return value

    def load(self):
        """
        Loads and parses the INI configuration file.

        This method reads the INI file line by line, handling sections, key-value pairs,
        and comments. It populates the internal data dictionary with the parsed values.

        Returns:
        --------
        None
            This method does not return any value.
        """
        self._data = {} #....................................................... Reset data dictionary
        current_section = None #................................................ Current section being processed

        try:
            with open(self._path, "r") as f: #.................................. Open the INI file for reading
                for line in f: #................................................ Read each line in the file
                #-- Remove comments starting with # or ;------------------------
                    for ch in self._comment_chars:
                        idx = line.find(ch)
                        if idx != -1:
                            line = line[:idx]

                #-- Strip leading/trailing whitespace --------------------------
                    line = line.strip() #....................................... Remove leading/trailing whitespace

                #-- Continue, if line is not empty -----------------------------
                    if line:
                    #-- Section header -----------------------------------------
                        if line.startswith("[") and line.endswith("]"):
                            section_name = line[1:-1].strip()
                            if section_name:
                                current_section = section_name
                                if current_section not in self._data:
                                    self._data[current_section] = {}
                            continue

                        # Key-value inside a section
                        if "=" in line and current_section is not None:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = self._convert_value(value.strip())
                            self._data[current_section][key] = value
        except OSError as e:
            self._data = {} #................................................ Reset data dictionary
            raise e #........................................................ Raise the exception
            
    def as_dict(self):
        """
        Returns the entire configuration as a nested dictionary.

        Returns:
        --------
        dict: A dictionary representation of the entire configuration.
        """
        return dict(self._data)

    def get_section(self, section, default=None):
        """
        Retrieves all key-value pairs in a specified section.

        Parameters:
        -----------
        section (str): The section name to retrieve.
        default: The value to return if the section does not exist.
        
        Returns:
        --------
        dict or default: A dictionary of key-value pairs in the section, or the default value if the section is not found.
        """ 
        return self._data.get(section, default)

    def get(self, section, key, default=None):
        """
        Retrieves a specific value from a section.
        
        Parameters:
        -----------
        section (str): The section name.
        key (str): The key name within the section.
        default: The value to return if the section or key does not exist.
        
        Returns:
        -----------
        The value associated with the specified key in the section, or the default value if not found.
        """
        sec = self._data.get(section)
        if sec is None:
            return default
        return sec.get(key, default)
