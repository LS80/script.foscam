import os

import xbmc
import xbmcaddon
import xbmcgui


__addon__ = xbmcaddon.Addon()

__id__ = __addon__.getAddonInfo('id')
__icon__  = __addon__.getAddonInfo('icon').decode("utf-8")
__version__ = __addon__.getAddonInfo('version')

addon_name = __addon__.getLocalizedString(32000)

TEXTURE_FMT = os.path.join(__addon__.getAddonInfo('path'), 'resources', 'media', '{0}.png')

ACTION_PREVIOUS_MENU = 10
ACTION_BACKSPACE = 110
ACTION_NAV_BACK = 92
ACTION_STOP = 13
ACTION_SELECT_ITEM = 7


def log(message, level=xbmc.LOGNOTICE):
    xbmc.log("{0} v{1}: {2}".format(__id__, __version__, message), level=level)
       
def log_normal(message):
    if int(__addon__.getSetting('debug')) > 0:
        log(message)
    
def log_verbose(message):
    if int(__addon__.getSetting('debug')) == 2:
        log(message)
        
def log_error(message):
    log(message, xbmc.LOGERROR)        

def notify(msg, time=10000):
    xbmcgui.Dialog().notification(addon_name, msg, __icon__, time)

def addon_info(info):
    return __addon__.getAddonInfo(info)

def get_string(ident):
    return __addon__.getLocalizedString(ident)

def get_setting(ident):
    return __addon__.getSetting(ident)

def get_bool_setting(ident):
    return get_setting(ident) == "true"

def get_int_setting(ident):
    return int(get_setting(ident))

def get_float_setting(ident):
    return float(get_setting(ident))

def open_settings():
    __addon__.openSettings()


class StopResumePlayer(xbmc.Player):
    def maybe_stop_current(self):
        if self.isPlaying():
            self.seek_time = self.getTime()
            self.previous_file = self.getPlayingFile()
            self.stop()
            utils.log_normal("Stopped {0}".format(self.previous_file))
        else:
            self.previous_file = None

    def maybe_resume_previous(self):
        if self.previous_file is not None:
            utils.log_normal("Resuming {0}".format(self.previous_file))
            self.play(self.previous_file)
            xbmc.sleep(1000) # wait for file to actually play before we can seek
            self.seekTime(self.seek_time - 2.)
