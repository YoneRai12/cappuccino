class VideoCapture:
    def __init__(self, path):
        self.path = path
        self._opened = True
    def isOpened(self):
        return True
    def get(self, prop):
        return 0
    def release(self):
        pass

CAP_PROP_FRAME_COUNT = 0
CAP_PROP_FPS = 1
CAP_PROP_FRAME_WIDTH = 2
CAP_PROP_FRAME_HEIGHT = 3
