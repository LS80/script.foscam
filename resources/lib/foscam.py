import xml.etree.ElementTree as ET

import requests2 as requests
import xbmc

import utils


ALARM_DURATION = 60

def video_url(user, password, host, port):
    return "rtsp://{0}:{1}@{2}:{3}/videoMain".format(user, password, host, port)


class CameraXMLResponse(object):
    ''' A dictionary-like container which parses the XML response to a CGI request '''

    RESULT_MSG = { 0: "Success",
                  -1: "CGI request string format error",
                  -2: "Username or password error",
                  -3: "Access denied",
                  -4: "CGI execute failure",
                  -5: "Timeout"
                  }

    def __init__(self, response):
        self._xml = response.text
        self._xml_root = ET.fromstring(self._xml)

        result = self._xml_root.find('result')
        self._result_value = int(result.text)
        self._xml_root.remove(result)

    def __nonzero__(self):
        return self._result_value == 0
    
    def __str__(self):
        return self._xml

    def __getitem__(self, key):
        return int(self._xml_root.find(key).text)

    def __iter__(self):
        return (element.tag for element in self._xml_root)

    keys = __iter__

    def items(self):
        return ((element.tag, int(element.text)) for element in self._xml_root)

    def values(self):
        return (int(element.text) for element in self._xml_root)

    @property
    def status(self):
        return self._result_value

    @property
    def message(self):
        return self.RESULT_MSG[self._result_value]


class CameraCommand(object):
    ''' Class to handle the sending of the CGI request and the return of a response object '''

    URL_FMT = None
    
    def __init__(self, cmd):
        if self.URL_FMT is None:
            utils.log_error("Camera URL is not set")

        self.cmd_url = self.URL_FMT.format(cmd)

    @classmethod
    def set_url_components(cls, host, port, user, password):
        cls.host = host
        cls.port = port
        cls.user = user
        cls.password = password

        cls.set_url_fmt()

        response = cls('getDevState').send()
        if response:
            msg = response.message
        else:
            msg = "Error connecting to camera."
        return bool(response), msg
        
    @classmethod
    def set_url_fmt(cls):
        cls.URL_FMT = "http://{0}:{1}/cgi-bin/CGIProxy.fcgi?cmd={{0}}&usr={2}&pwd={3}".format(cls.host,
                                                                                              cls.port,
                                                                                              cls.user,
                                                                                              cls.password)
    def send(self):
        utils.log_verbose(self.cmd_url)
        try:
            response = requests.get(self.cmd_url)
        except (requests.RequestException) as e:
            utils.log_error(str(e))
            return False
        else:
            return self._response(response)
            
    def _response(self, response):
        xml_resp = CameraXMLResponse(response)
        utils.log_verbose(xml_resp)
        if not xml_resp:
            utils.log_error(xml_resp.message)
        return xml_resp

    def get(self, element=None):
        response = self.send()
        if response:
            return response[element]
        else:
            return False

    def bytes(self):
        return self.send().bytes()


class CameraDataCommand(CameraCommand):
    def _response(self, response):
        return response.content

    data = CameraCommand.send 


class SetCommand(CameraCommand):
    def __init__(self, cmd):
        self.cmd = cmd
        
        get_cmd = self.cmd.replace("set", "get")
        command = CameraCommand(get_cmd)
        
        self._settings = dict(command.send().items())
        
    def __setitem__(self, key, value):
        self._settings[key] = value

    def send(self):
        qs = "&".join(("{0}={1:d}".format(param, value) for param, value in self._settings.iteritems()))
        
        self.cmd_url = self.URL_FMT.format("{0}&{1}".format(self.cmd, qs))
        return super(SetCommand, self).send()


class ToggleCommand(CameraCommand):
    def __init__(self, cmd, param):
        cmd_fmt = "{0}&{1}={{0:d}}".format(cmd, param)
        self.cmd_url_fmt = self.URL_FMT.format(cmd_fmt)

    def set_enabled(self, enable):
        self.cmd_url = self.cmd_url_fmt.format(enable)
        return super(ToggleCommand, self).send()


class MirrorFlipToggleCommand(ToggleCommand):
    def __init__(self, action):
        cmd = "{0}Video".format(action)
        param = "is{0}".format(action.title())    
        super(MirrorFlipToggleCommand, self).__init__(cmd, param)


class CameraMoveCommand(CameraCommand):
    def __init__(self, direction):
        cmd = "ptzMove{0}".format(direction.title())
        super(CameraMoveCommand, self).__init__(cmd)

