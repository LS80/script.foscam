import os

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import foscam
from resources.lib import utils
from resources.lib import gui


user = utils.get_setting('username')
password = utils.get_setting('password')
host = utils.get_setting('host')
port = utils.get_int_setting('port')

# ir_on = foscam.CameraCommand('openInfraLed')
# ir_off = foscam.CameraCommand('closeInfraLed')

def error_dialog(msg):
    xbmcgui.Dialog().ok(utils.get_string(32000), msg, " ", utils.get_string(32102))
    utils.open_settings()
    sys.exit(1)

if not host:
    error_dialog(utils.get_string(32101))
    
success, msg = foscam.CameraCommand.set_url_components(host, port, user, password)  
if not success:
    error_dialog(msg)


VIDEO_URL = foscam.video_url(user, password, host, port)
PTZ_RUN_DURATION = 400


class MoveButton(gui.Button):
    end_cmd = foscam.CameraCommand('ptzStopRun')

    def __init__(self, parent, action, x, y):
        self.action = action.capitalize()
        self.cmd = foscam.CameraMoveCommand(action)
        
    def send_cmd(self, control=None):
        self.cmd.send()
        xbmc.sleep(PTZ_RUN_DURATION)
        return self.end_cmd.send()


class MirrorFlipButton(gui.ToggleButton):
    def __init__(self, parent, action, x, y):
        self.cmd = foscam.MirrorFlipToggleCommand(action)


class CameraControlDialog(xbmcgui.WindowDialog):
    def __enter__(self):
        return self
    
    def start(self):
        utils.log_normal("Starting main view")
        self.playVideo()
        self.setupUi()
        
        mirror_flip = foscam.CameraCommand('getMirrorAndFlipSetting')
        mirror, flip = mirror_flip.send().values()

        self.mirror_button.setSelected(mirror)
        self.flip_button.setSelected(flip)

        self.doModal()

    def playVideo(self):
        self.player = utils.StopResumePlayer()
        self.player.maybe_stop_current()
        self.player.play(VIDEO_URL)

    def setupUi(self):
        Y_OFFSET = 100
        X_OFFSET = 20
        OFFSET1 = 50
        OFFSET2 = 100

        self.buttons = []

        self.up_button = MoveButton(self, 'up', OFFSET1+X_OFFSET, Y_OFFSET)
        self.addControl(self.up_button)

        self.left_button = MoveButton(self, 'left', X_OFFSET, OFFSET1+Y_OFFSET)
        self.addControl(self.left_button)
        
        self.down_button = MoveButton(self, 'down', OFFSET1+X_OFFSET, OFFSET2+Y_OFFSET)
        self.addControl(self.down_button)
        
        self.right_button = MoveButton(self, 'right', OFFSET2+X_OFFSET, OFFSET1+Y_OFFSET)
        self.addControl(self.right_button)

        self.flip_button = MirrorFlipButton(self, 'flip', 30, Y_OFFSET+200)        
        self.addControl(self.flip_button)

        self.mirror_button = MirrorFlipButton(self, 'mirror', 30, Y_OFFSET+260)
        self.addControl(self.mirror_button)
        
        self.close_button = gui.Button(self, 'close', 1280-60, 20)
        self.addControl(self.close_button)
        
        self.settings_button = gui.Button(self, 'settings', 1280-120, 20)
        self.addControl(self.settings_button)       
        
        self.setFocus(self.close_button)

        self.up_button.setNavigation(self.mirror_button, self.down_button, self.left_button, self.right_button)
        self.left_button.setNavigation(self.up_button, self.down_button, self.right_button, self.right_button)
        self.right_button.setNavigation(self.up_button, self.down_button, self.left_button, self.settings_button)
        self.down_button.setNavigation(self.up_button, self.flip_button, self.left_button, self.right_button)

        self.flip_button.controlUp(self.down_button)
        self.flip_button.controlDown(self.mirror_button)
        self.flip_button.controlRight(self.close_button)

        self.mirror_button.controlUp(self.flip_button)
        self.mirror_button.controlRight(self.close_button)
        
        self.settings_button.controlLeft(self.right_button)
        self.settings_button.controlRight(self.close_button)
        
        self.close_button.controlLeft(self.settings_button)

    def getControl(self, control):
        return next(button for button in self.buttons if button == control)
    
    def onControl(self, control):
        if control == self.close_button:
            self.stop()
        elif control == self.settings_button:
            utils.open_settings()
        else:
            button = self.getControl(control)
            response = button.send_cmd(control)
            if not response:
                msg = u"{0}: {1}".format(utils.get_string(32103), response.message)
                utils.notify(msg)

                if isinstance(control, xbmcgui.ControlRadioButton):
                    control.setSelected(not control.isSelected())

    def onAction(self, action):
        if action in (utils.ACTION_PREVIOUS_MENU, utils.ACTION_BACKSPACE,
                      utils.ACTION_NAV_BACK, utils.ACTION_STOP):
            self.stop()

    def stop(self):
        utils.log_normal("Closing main view")
        self.player.stop()
        self.close()
        self.player.maybe_resume_previous()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

with CameraControlDialog() as camera:
    camera.start()

            
            
