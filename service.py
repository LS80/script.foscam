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
        self.alarm_active = False
        self.duration_shown = 0
        
        self.configured = self.apply_basic_settings()
        if self.configured:
            self.init_settings()
            self.apply_other_settings()

        self.monitor = utils.Monitor(updated_settings_callback=self.settings_changed)
        
        self.path = os.path.join(xbmc.translatePath(utils.addon_info('profile')), "snapshots")
        try:
            os.makedirs(self.path)
        except:
            pass

        while not xbmc.abortRequested:
            if self.configured:
                self.alarm_check()

            if self.alarm_active:
                sleep = foscam.ALARM_DURATION - self.duration_shown + self.trigger_interval
            else:
                sleep = self.check_interval
            utils.log_verbose("Sleeping for {0} seconds".format(sleep))

            for i in range(sleep):
                if not xbmc.abortRequested:
                    xbmc.sleep(1000)
    
    def init_settings(self):
        utils.log_normal("Initialising settings from the camera")

        response = foscam.CameraCommand('getMotionDetectConfig').send()
        utils.set_setting('motion_sensitivity', str(response['sensitivity']))
        utils.set_setting('motion_trigger_interval', str(response['triggerInterval']))
        
        response = foscam.CameraCommand('getAudioAlarmConfig').send()
        utils.set_setting('sound_sensitivity', str(response['sensitivity']))
        utils.set_setting('sound_trigger_interval', str(response['triggerInterval']))
    
    def settings_changed(self):
        utils.log_normal("Applying settings")
        self.configured = self.apply_basic_settings()
        if self.configured:
            self.apply_other_settings()
        
    def apply_basic_settings(self):
        user = utils.get_setting('username')
        password = utils.get_setting('password')
        host = utils.get_setting('host')
        port = utils.get_int_setting('port')

        if not host:
            utils.log_normal("No host specified")
            return False

        success, msg = foscam.CameraCommand.set_url_components(host, port, user, password)
        if not success:
            utils.log_error(msg)
            return False

        self.video_url = foscam.video_url(user, password, host, port)
        return True

    def apply_other_settings(self):            
        self.motion_enable = utils.get_bool_setting('motion_enable')
        self.sound_enable = utils.get_bool_setting('sound_enable')

        self.check_interval = utils.get_int_setting('check_interval')
        self.duration = utils.get_int_setting('preview_duration')
        self.snapshot_interval = utils.get_int_setting('snapshot_interval')
        self.scaling = utils.get_float_setting('preview_scaling')
        self.position = utils.get_setting('preview_position').lower()

        motion_trigger_interval = utils.get_int_setting('motion_trigger_interval')
        sound_trigger_interval = utils.get_int_setting('sound_trigger_interval')
        
        if self.motion_enable and self.sound_enable:
            self.trigger_interval = min(motion_trigger_interval, sound_trigger_interval)
        elif self.motion_enable:
            self.trigger_interval = motion_trigger_interval
        elif self.sound_enable:
            self.trigger_interval = sound_trigger_interval
        
        if self.motion_enable:
            command = foscam.SetCommand('setMotionDetectConfig')
            command['isEnable'] = True
            command['sensitivity'] = utils.get_int_setting('motion_sensitivity')
            command['triggerInterval'] = motion_trigger_interval
            self.send_command(command)
            
        if self.sound_enable:
            command = foscam.SetCommand('setAudioAlarmConfig')
            command['isEnable'] = True
            command['sensitivity'] = utils.get_int_setting('sound_sensitivity')
            command['triggerInterval'] = sound_trigger_interval
            
            for iday in range(7):
                command['schedule{0:d}'.format(iday)] = 2**48 - 1
            
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

    def alarm_check(self):
        if self.motion_enable or self.sound_enable:
            player = xbmc.Player()
            if player.isPlaying() and player.getPlayingFile() == self.video_url:
                return

            self.alarm_active = False
            dev_state = foscam.CameraCommand('getDevState').send()

            for alarm, enabled in (('motionDetect', self.motion_enable),
                                   ('sound', self.sound_enable)):
                if enabled:
                    param = "{0}Alarm".format(alarm)
                    alarm_status = dev_state[param]
                    utils.log_verbose("{0:s} = {1:d}".format(param, alarm_status))
                    if alarm_status == 2:
                        self.alarm_active = True
                        utils.log_normal("Alarm detected")
                        break

            if self.alarm_active:
                preview = gui.CameraPreview(self.duration, self.snapshot_interval, self.path,
                                            self.scaling, self.position,
                                            foscam.CameraDataCommand('snapPicture2').data)
                preview.show()
                self.duration_shown = preview.start()
                del(preview)


if __name__ == "__main__":
    Main()

