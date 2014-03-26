import os
import time

import xbmc
import xbmcgui
import xbmcaddon

from resources.lib import foscam
from resources.lib import utils
from resources.lib import gui


gui.Button.WIDTH = 16
gui.Button.HEIGHT = 16


class Main(object):
    def __init__(self):
        utils.log_normal("Starting service")
        self.video_url = ""
        self.motion_detected = False

        self.apply_settings()

        self.monitor = MyMonitor(updated_settings_callback=self.apply_settings)
        
        self.path = os.path.join(xbmc.translatePath(utils.addon_info('profile')), "snapshots")
        try:
            os.makedirs(self.path)
        except:
            pass

        while not xbmc.abortRequested:
            self.motion_check()

            if self.motion_detected:
                sleep = foscam.MOTION_DURATION + self.trigger_interval
            else:
                sleep = self.check_interval
            utils.log_verbose("Sleeping for {0} seconds".format(sleep))

            for i in range(sleep):
                if not xbmc.abortRequested:
                    xbmc.sleep(1000)

    def apply_settings(self):
        utils.log_normal("Applying settings")

        self.motion_enable = utils.get_bool_setting('motion_enable')

        self.check_interval = utils.get_int_setting('check_interval')
        self.duration = utils.get_int_setting('preview_duration')
        self.snapshot_interval = utils.get_int_setting('snapshot_interval')
        self.trigger_interval = utils.get_int_setting('trigger_interval')
        self.scaling = utils.get_float_setting('preview_scaling')
        self.position = utils.get_setting('preview_position').lower()

        user = utils.get_setting('username')
        password = utils.get_setting('password')
        host = utils.get_setting('host')
        port = utils.get_int_setting('port')

        self.configured = True
        if not host:
            utils.log_normal("No host specified")
            self.configured = False
            return

        success, msg = foscam.CameraCommand.set_url_components(host, port, user, password)  
        if not success:
            utils.log_normal(msg)
            self.configured = False
        elif success and self.motion_enable:
            self.video_url = foscam.video_url(user, password, host, port)

            command = foscam.SetCommand('setMotionDetectConfig')
            command['isEnable'] = True
            command['sensitivity'] = utils.get_int_setting('motion_sensitivity')
            command['triggerInterval'] = self.trigger_interval
            self.send_command(command)
                
            command = foscam.SetCommand('setSnapConfig')
            command['snapPicQuality'] = utils.get_int_setting('snapshot_quality')
            response = command.send()
            self.send_command(command)
            
    def send_command(self, command):
        response = command.send()
        if not response:
            msg = u"{0}: {1}".format(utils.get_string(32104), response.message)
            utils.notify(msg)

    def motion_check(self):
        if self.motion_enable and self.configured:
            player = xbmc.Player()
            if player.isPlaying() and player.getPlayingFile() == self.video_url:
                return

            alarm = foscam.CameraCommand('getDevState').get('motionDetectAlarm')
            if alarm == 2:
                self.motion_detected = True
                utils.log_normal("Motion detected")
                preview = CameraPreview(self.duration, self.snapshot_interval, self.path,
                                        self.scaling, self.position)
                preview.show()
                preview.start()
                del(preview)
            elif alarm < 2:
                self.motion_detected = False
                utils.log_verbose("No motion detected")


class SnapShot(object):
    def __init__(self, path, interval):
        self.time = time.time()

        self.interval = interval
        self.filename = os.path.join(path, "{0}.jpg".format(self.time))
        
        with open(self.filename, 'wb') as output:
            utils.log_verbose("Snapshot {0}".format(self.filename)) 
            output.write(foscam.CameraDataCommand('snapPicture2').data())      
        
    def __enter__(self):
        return self.filename

    def __exit__(self, exc_type, exc_value, traceback):
        current_time = time.time()
        elapsed = current_time - self.time
        utils.log_verbose("Retrieving snapshot took {0:.2f} seconds".format(elapsed))
        remaining = int(self.interval - elapsed*1000)
        sleep = max(200, remaining)
        utils.log_verbose("Sleeping for {0} milliseconds".format(sleep))
        xbmc.sleep(sleep)
        
        try:
            os.remove(self.filename)
        except:
            pass
        else:
            utils.log_verbose("Deleted {0}".format(self.filename))


class CameraPreview(xbmcgui.WindowDialog):
    def __init__(self, duration, interval, path, scaling, position):
        utils.log_normal("Showing preview")
        
        self.buttons = []
        
        self.duration = duration
        self.interval = interval
        self.path = path
        
        self.setProperty('zorder', "99")
        
        WIDTH = 320
        HEIGHT = 180

        width = int(WIDTH * scaling)
        height = int(HEIGHT * scaling)

        if "bottom" in position:
            y = 720 - height
        else:
            y = 0

        if "left" in position:
            x = 0
            start = - width
        else:
            x = 1280 - width
            start = width

        animations = [('WindowOpen',
                       "effect=slide start={0:d} time=2000 tween=cubic easing=out".format(start)),
                      ('WindowClose',
                       "effect=slide end={0:d} time=2000 tween=cubic easing=in".format(start))]

        self.closing = False

        with SnapShot(self.path, self.interval) as snapshot:
            self.image = xbmcgui.ControlImage(x, y, width, height, snapshot)
            self.addControl(self.image)
            self.image.setAnimations(animations)

            self.close_button = gui.Button(self, 'close', x + width - gui.Button.WIDTH - 10, y + 10)
            self.addControl(self.close_button)
            self.close_button.setAnimations(animations)
            
            trans = utils.TEXTURE_FMT.format('trans')
            self.select_button = xbmcgui.ControlButton(x, y, width, height, "", trans, trans)
            self.addControl(self.select_button)
            self.select_button.setAnimations(animations)

    def start(self):
        start_time = time.time()
        current_time = start_time
        while (current_time - start_time) <= self.duration:
            with SnapShot(self.path, self.interval) as snapshot:
                self.image.setImage(snapshot, useCache=False)

            if self.closing:
                break
            
            current_time = time.time()
        self.close()

    def onControl(self, control):
        if control == self.close_button:
            self.stop()
        elif control == self.select_button:
            self.run()
            
    def onAction(self, action):
        if action in (utils.ACTION_PREVIOUS_MENU, utils.ACTION_BACKSPACE, utils.ACTION_NAV_BACK):
            self.stop()
        elif action == utils.ACTION_SELECT_ITEM:
            self.run()
            
    def run(self):
        xbmc.executebuiltin("RunAddon({0})".format(utils.addon_info('id')))
        self.stop()
            
    def stop(self):
        utils.log_normal("Closing preview")
        self.removeControl(self.close_button)
        self.closing = True
        self.close()


class MyMonitor(xbmc.Monitor):
    def __init__(self, updated_settings_callback):
        xbmc.Monitor.__init__(self)
        self.updated_settings_callback = updated_settings_callback

    def onSettingsChanged(self):
        self.updated_settings_callback()
    

if __name__ == "__main__":
    Main()

