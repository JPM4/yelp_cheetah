from __future__ import unicode_literals

import re
from io import StringIO
from tokenize import Number

try:
    # Python2
    from ConfigParser import ConfigParser
except ImportError:
    # Python3
    from configparser import ConfigParser


numberRE = re.compile(Number)


def mergeNestedDictionaries(dict1, dict2):
    """Recursively merge the values of dict2 into dict1.

    This little function is very handy for selectively overriding settings in a
    settings dictionary that has a nested structure.
    """
    for key, val in dict2.items():
        if key in dict1 and isinstance(val, dict) and isinstance(dict1[key], dict):
            dict1[key] = mergeNestedDictionaries(dict1[key], val)
        else:
            dict1[key] = val
    return dict1


def stringIsNumber(s):
    """Return True if theString represents a Python number, False otherwise.
    This also works for complex numbers and numbers with +/- in front.
    """
    s = s.strip()

    if s[0] in '-+' and len(s) > 1:
        s = s[1:].strip()

    match = numberRE.match(s)
    return bool(match) and match.end() == len(s)


def convStringToNum(theString):
    """Convert a string representation of a Python number to the Python version"""
    if not stringIsNumber(theString):
        raise AssertionError(
            theString + ' cannot be converted to a Python number'
        )
    return eval(theString, {}, {})


class ConfigParserCaseSensitive(ConfigParser):
    """A case sensitive version of the standard Python ConfigParser."""

    def optionxform(self, optionstr):
        """Don't change the case as is done in the default implemenation."""
        return optionstr


def convert_value(s):
    if s.lower() == 'none':
        return None
    elif s.lower() == 'true':
        return True
    elif s.lower() == 'false':
        return False
    elif stringIsNumber(s):
        return convStringToNum(s)
    return s


class _SettingsCollector(object):
    """An abstract base class that provides the methods SettingsManager uses to
    collect settings from config files and strings.

    This class only collects settings it doesn't modify the _settings dictionary
    of SettingsManager instances in any way.
    """

    _ConfigParserClass = ConfigParserCaseSensitive

    def readSettingsFromConfigFileObj(self, inFile):
        """Return the settings from a config file that uses the syntax accepted by
        Python's standard ConfigParser module (like Windows .ini files).

        NOTE:
        this method maintains case unlike the ConfigParser module

        All setting values are initially parsed as strings.
        However, the following value conversions are applied:

        * all Python numeric literals will be coverted from string to number
        * The string 'True' will be converted to a Python truth value
        * The string 'False' will be converted to a Python false value
        """
        p = self._ConfigParserClass()
        p.readfp(inFile)
        assert 'globals' in p.sections()

        return dict(
            (k, convert_value(p.get('globals', k)))
            for k in p.options('globals')
        )


class SettingsManager(_SettingsCollector):
    """A mixin class that provides facilities for managing application settings.

    SettingsManager is designed to work well with nested settings dictionaries
    of any depth.
    """

    def __init__(self):
        super(SettingsManager, self).__init__()
        self._settings = {}
        self._initializeSettings()

    def _initializeSettings(self):
        """A hook that allows for complex setting initialization sequences that
        involve references to 'self' or other settings.  For example:
              self._settings['myCalcVal'] = self._settings['someVal'] * 15
        This method should be called by the class' __init__() method when needed.
        The dummy implementation should be reimplemented by subclasses.
        """
        raise NotImplementedError

    # core post startup methods

    def setting(self, name):
        """Get a setting from self._settings, with or without a default value."""
        return self._settings[name]

    def setSetting(self, name, value):
        """Set a setting in self._settings."""
        self._settings[name] = value

    def settings(self):
        """Return a reference to the settings dictionary"""
        return self._settings

    def updateSettings(self, newSettings):
        """Update the settings with a selective merge or a complete overwrite."""
        mergeNestedDictionaries(self._settings, newSettings)

    def updateSettingsFromConfigStr(self, configStr):
        """See the docstring for .updateSettingsFromConfigFile()
        """
        configStr = '[globals]\n' + configStr
        inFile = StringIO(configStr)
        newSettings = self.readSettingsFromConfigFileObj(inFile)
        self.updateSettings(newSettings)
