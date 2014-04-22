import os
from functools import partial

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import foscam
from resources.lib import utils
from resources.lib import gui



class MoveButton(gui.Button):
    def send_cmd(self, control=None):
        return self.parent.camera.move(self.action)


class MirrorFlipButton(gui.ToggleButton):
    def send_cmd(self, control=None):
        return self.parent.camera.toggle_mirror_flip(self.action, control.isSelected())
  

class CameraControlDialog(xbmcgui.WindowDialog):
    def __enter__(self):
        return self
    
    def start(self):
        utils.log_normal("Starting main view")

        self.player = utils.StopResumePlayer() #once
        self.player.maybe_stop_current() #once

        self.setupUi()
        self.startCamera()

        self.doModal()

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
        
        self.num_cameras = utils.get_int_setting('num_cameras')
        utils.log("Number of cameras = {0}".format(self.num_cameras))

        if self.num_cameras > 1:
            height = (self.num_cameras + 1) * 35
            self.camera_select = xbmcgui.ControlList(10, 720 - height, 100, height,
                                                     selectedColor="0xFF00FF00",
                                                     buttonFocusTexture=utils.TEXTURE_FMT.format('select-focus'))
            self.addControl(self.camera_select)
            self.camera_select.addItems([str(i+1) for i in range(self.num_cameras)])

            label = xbmcgui.ControlLabel(20, 720 - height - 30, 100, 20, "Camera") 
            self.addControl(label)

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

        if self.num_cameras > 1:
            self.camera_select.controlUp(self.mirror_button)
            self.mirror_button.controlDown(self.camera_select)
            self.setFocus(self.camera_select)
        else:
            self.setFocus(self.close_button)

    def startCamera(self):
        self.setupCamera()
        self.player.play(self.camera.video_url)

    def setupCamera(self):
        self.selected_camera = utils.get_int_setting('selected_camera')
        if self.selected_camera is None:
            self.selected_camera = 0

        user = utils.get_setting('username_{0}'.format(self.selected_camera))
        password = utils.get_setting('password_{0}'.format(self.selected_camera))
        host = utils.get_setting('host_{0}'.format(self.selected_camera))
        port = utils.get_int_setting('port_{0}'.format(self.selected_camera))

        if not host:
            utils.error_dialog(utils.get_string(32101))

        self.camera = foscam.Camera(host, port, user, password)
        success, msg = self.camera.test()
        if not success:
            utils.log_error("Could not connect to {0}".format(self.camera.video_url))
            utils.error_dialog(msg)
        else:
            mirror, flip = self.camera.get_mirror_and_flip()

        self.mirror_button.setSelected(mirror)
        self.flip_button.setSelected(flip)

        if self.num_cameras > 1:
            self.camera_select.getListItem(self.selected_camera).select(True)
            self.camera_select.selectItem(self.selected_camera)

    def getControl(self, control):
        return next(button for button in self.buttons if button == control)
    
    def onControl(self, control):
        utils.log(control)
        if control == self.close_button:
            self.stop()
        elif control == self.settings_button:
            utils.open_settings()
        elif control == self.camera_select:
            utils.log(self.selected_camera)
            if self.selected_camera is not None:
                control.getListItem(self.selected_camera).select(False)
            control.getSelectedItem().select(True)
            self.selected_camera = control.getSelectedPosition()
            utils.set_setting('selected_camera', self.selected_camera)
            self.start()
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

with CameraControlDialog() as camera_dialog:
    camera_dialog.start()

            
            
