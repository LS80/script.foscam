import os
import time
import glob

import xbmc
import xbmcaddon
import xbmcgui

import requests


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

INVALID_PASSWORD_CHARS = ('{', '}', ':', ';', '!', '?', '@', '\\', '/')
INVALID_USER_CHARS = ('@',)


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
    try:
        return int(get_setting(ident))
    except ValueError:
        return None

def get_float_setting(ident):
    return float(get_setting(ident))

def set_setting(ident, value):
    __addon__.setSetting(ident, value)

def open_settings(callback=None):
    if callback is not None:
        callback()
    __addon__.openSettings()

def invalid_char(credential, chars, stringid, show_dialog):
    for char in chars:
        if char in credential:
            if show_dialog:
                xbmcgui.Dialog().ok(get_string(32000), get_string(stringid),
                                    " ", " ".join(chars))
            return char
    return False

def invalid_password_char(password, show_dialog=False):
    return invalid_char(password, INVALID_PASSWORD_CHARS, 32105, show_dialog)

def invalid_user_char(user, show_dialog=False):
    return invalid_char(user, INVALID_USER_CHARS, 32106, show_dialog)

def error_dialog(msg):
    xbmcgui.Dialog().ok(get_string(32000), msg, " ", get_string(32102))
    open_settings()


class SnapShot(object):
    def __init__(self, path, interval, get_data):
        self.time = time.time()

        self.interval = interval
        self.filename = os.path.join(path, "{0}.jpg".format(self.time))

        self.get_data = get_data

    def __enter__(self):
        return self

    def save(self):
        with open(self.filename, 'wb') as output:
            log_verbose("Snapshot {0}".format(self.filename))
            data = self.get_data()
            if data:
                output.write(data)
                return self.filename
            else:
                return ""

    def __exit__(self, exc_type, exc_value, traceback):
        current_time = time.time()
        elapsed = current_time - self.time
        log_verbose("Retrieving snapshot took {0:.2f} seconds".format(elapsed))
        remaining = int(self.interval - elapsed*1000)
        sleep = max(200, remaining)
        log_verbose("Sleeping for {0} milliseconds".format(sleep))
        xbmc.sleep(sleep)
        
        try:
            os.remove(self.filename)
        except:
            pass
        else:
            log_verbose("Deleted {0}".format(self.filename))


def get_mjpeg_frame(stream):
    try:
        stream.readline()
        stream.readline()
        content_length = stream.readline()
        bytes = int(content_length.split(':')[-1])
        stream.readline()
        return stream.read(bytes)
    except requests.RequestException as e:
        utils.log_error(str(e))
        return None

class ExtractMJPEGFrames(object):
    def __init__(self, path, duration, stream, callback, *args):
        self.path = path
        self.duration = duration
        self.stream = stream
        self.callback = callback
        self.callback_args = args

        self._stop = False

    def __enter__(self):
        return self

    def stop(self):
        self._stop = True

    def start(self):
        start_time = time.time()
        current_time = start_time
        frames = 0
        while current_time < start_time + self.duration and not self._stop:
            xbmc.sleep(1)
            frame = get_mjpeg_frame(self.stream)
            if frame:
                filename = os.path.join(self.path, "snapshot.{0}.jpg".format(time.time()))
                open(filename, 'w').write(frame)
                self.callback(filename, *self.callback_args)
                log_verbose("Snapshot {0}".format(filename))
            current_time = time.time()
            frames += 1
        duration = current_time - start_time
        log_normal("Average fps: {0:.2f}".format(frames / duration))
        return int(duration)

    def __exit__(self, exc_type, exc_value, traceback):
        self.stream.close()
        for jpg in glob.glob(os.path.join(self.path, "snapshot.*.jpg")):
            try:
                os.remove(jpg)
            except:
                log_verbose("Unable to delete {0}".format(jpg))
            else:
                log_verbose("Deleted {0}".format(jpg))


class Monitor(xbmc.Monitor):
    def __init__(self, updated_settings_callback):
        xbmc.Monitor.__init__(self)
        self.updated_settings_callback = updated_settings_callback

    def onSettingsChanged(self):
        self.updated_settings_callback()


class StopResumePlayer(xbmc.Player):
    def maybe_stop_current(self):
        if self.isPlaying():
            self.resume_time = self.getTime()
            self.previous_file = self.getPlayingFile()
            self.stop()
            log_normal("Stopped {0}".format(self.previous_file))
        else:
            self.previous_file = None

    def maybe_resume_previous(self):
        if self.previous_file is not None:
            resume_time_str = "{0:.1f}".format(self.resume_time - 10.)
            log_normal("Resuming {0} at {1}".format(self.previous_file, resume_time_str))
            listitem = xbmcgui.ListItem()
            listitem.setProperty('StartOffset', resume_time_str)
            self.play(self.previous_file, listitem)

