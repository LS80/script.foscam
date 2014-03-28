import os

import xbmc
import xbmcgui
import xbmcaddon

from resources.lib import foscam
from resources.lib import utils
from resources.lib import gui


class Main(object):
    def __init__(self):
        utils.log_normal("Starting service")
        self.video_url = ""
        self.motion_detected = False
        self.duration_shown = 0

        self.apply_settings()

        self.monitor = utils.Monitor(updated_settings_callback=self.apply_settings)
        
        self.path = os.path.join(xbmc.translatePath(utils.addon_info('profile')), "snapshots")
        try:
            os.makedirs(self.path)
        except:
            pass

        while not xbmc.abortRequested:
            self.motion_check()

            if self.motion_detected:
                sleep = foscam.MOTION_DURATION - self.duration_shown + self.trigger_interval
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
                preview = gui.CameraPreview(self.duration, self.snapshot_interval, self.path,
                                            self.scaling, self.position,
                                            foscam.CameraDataCommand('snapPicture2').data)
                preview.show()
                self.duration_shown = preview.start()
                del(preview)
            elif alarm < 2:
                self.motion_detected = False
                utils.log_verbose("No motion detected")


if __name__ == "__main__":
    Main()

