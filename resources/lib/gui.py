import xbmc
import xbmcgui

import utils

class Button(xbmcgui.ControlButton):
    WIDTH = HEIGHT = 32

    def __new__(cls, parent, action, x, y):
        focusTexture = utils.TEXTURE_FMT.format(action + '-focus')
        noFocusTexture = utils.TEXTURE_FMT.format(action)
        self = super(Button, cls).__new__(cls, x, y, cls.WIDTH, cls.HEIGHT, "", focusTexture, noFocusTexture)

        parent.buttons.append(self)
        return self


class ToggleButton(xbmcgui.ControlRadioButton):
    WIDTH = 110
    HEIGHT = 40

    def __new__(cls, parent, action, x, y):
        focusOnTexture = utils.TEXTURE_FMT.format('radio-on')
        noFocusOnTexture = utils.TEXTURE_FMT.format('radio-on')
        focusOffTexture = utils.TEXTURE_FMT.format('radio-off')
        noFocusOffTexture = utils.TEXTURE_FMT.format('radio-off')
        focusTexture = utils.TEXTURE_FMT.format('back')
        noFocusTexture = utils.TEXTURE_FMT.format('trans')
        textOffsetX = 12

        self = super(ToggleButton, cls).__new__(cls, x, y, cls.WIDTH, cls.HEIGHT, action.title(),
                                                focusOnTexture, noFocusOnTexture,
                                                focusOffTexture, noFocusOffTexture,
                                                focusTexture, noFocusTexture,
                                                textOffsetX)

        self.action = action
        
        parent.buttons.append(self)
        return self

    def send_cmd(self, control):
        return self.cmd.set_enabled(control.isSelected())
