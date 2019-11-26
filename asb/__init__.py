import socket
import time
import cv2
import numpy as np
import threading
from threading import Event
from queue import Queue
import sys
import argparse as ap
import subprocess as sp
from collections import OrderedDict


class ScreenOrientation:
    VERTICAL = 0
    HORIZONTAL = 1

class AndroidScreenBuffer:

    def __init__(self, minicap_port=1313,
                buffer_size=10, scale_ratio=0.1,
                      screen_orientation=ScreenOrientation.HORIZONTAL,
                bitrate=120000):

        self.stop_evt = Event()
        self.buffer = OrderedDict()
        self.buffer_size = buffer_size
        self.queue = Queue()
        self.device_height, self.device_width = self.get_device_screen_shape()
        self.scale_ratio = scale_ratio
        self.bitrate = bitrate
        self.screen_orientation = screen_orientation
        self.minicap_port = minicap_port

    def run(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('localhost', self.minicap_port))

        threading.Thread(target=self.frames_thread).start()
        threading.Thread(target=self.buffer_thread).start()

    def get_device_screen_shape(self):
        wss = sp.check_output(['adb', 'shell', 'wm', 'size'])
        w = str(wss).split('x')[0]
        w = int(w[w.index(":") + 1:])
        h = str(wss).split('x')[1]
        h = int(h[:h.index("\\n")])
        return (h, w)

    def buffer_thread(self):
        while not self.stop_evt.is_set():
            t = time.time()
            frame = self.queue.get()
            self.buffer[str(t)] = frame
            while len(self.buffer) > self.buffer_size:
                del self.buffer[next(iter(self.buffer))]

    def stop(self):
        self.stop_evt.set()
        del self.client_socket

    def get_timelapse_frame(self, timelapse):

        if not len(self.buffer):
            print("Empty buffer")
            return

        k = list(self.buffer.keys())
        for tt in k:
            if float(tt) >= float(timelapse):
                return self.buffer[str(tt)]

    def get_last_frame(self):
        if not len(self.buffer):
            return

        return self.buffer[next(reversed(self.buffer))]

    def frames_thread(self):
        ref_width = self.device_width
        ref_height = self.device_height

        if self.screen_orientation == ScreenOrientation.VERTICAL:
            #print("Using vertical orientation")
            t = ref_width
            ref_width = ref_height
            ref_height = t

        out_with = int(ref_width * self.scale_ratio)
        screen_aspect = ref_height/ref_width
        out_height = int(out_with * screen_aspect)

        flag = False
        readBannerBytes = 0
        bannerLength = 2
        readFrameBytes = 0
        frameBodyLengthRemaining = 0
        frameBody = ''
        banner = {
            'version': 0,
            'length': 0,
            'pid': 0,
            'realWidth': 0,
            'realHeight': 0,
            'virtualWidth': 0,
            'virtualHeight': 0,
            'orientation': 0,
            'quirks': 0
        }
        while not self.stop_evt.is_set():
            chunk = self.client_socket.recv(self.bitrate)
            if len(chunk) == 0:
                continue

            #print(('chunk(length=%d)' % len(chunk)))
            cursor = 0
            while cursor < len(chunk):
                if (readBannerBytes < bannerLength):
                    #print((readBannerBytes, "---", bannerLength))
                    if readBannerBytes == 0:
                        banner['version'] = int(hex(chunk[cursor]), 16)
                    elif readBannerBytes == 1:
                        banner['length'] = bannerLength = int(hex(chunk[cursor]), 16)
                    elif readBannerBytes >= 2 and readBannerBytes <= 5:
                        banner['pid'] = int(hex(chunk[cursor]), 16)
                    elif readBannerBytes == 23:
                        banner['quirks'] = int(hex(chunk[cursor]), 16)

                    cursor += 1
                    readBannerBytes += 1

                    #if readBannerBytes == bannerLength:
                        #print(('banner', banner))

                elif readFrameBytes < 4:
                    frameBodyLengthRemaining += (int(hex(chunk[cursor]), 16) << (readFrameBytes * 8))
                    cursor += 1
                    readFrameBytes += 1
                    #print(('headerbyte%d(val=%d)' % (readFrameBytes, frameBodyLengthRemaining)))

                else:
                    # if this chunk has data of next image
                    if len(chunk) - cursor >= frameBodyLengthRemaining:
                        #print(('bodyfin(len=%d,cursor=%d)' % (frameBodyLengthRemaining, cursor)))
                        frameBody = frameBody + chunk[cursor:(cursor + frameBodyLengthRemaining)]
                        if hex(frameBody[0]) != '0xff' or hex(frameBody[1]) != '0xd8':
                            #print(("Frame body does not strt with JPEG header", frameBody[0], frameBody[1]))
                            exit()
                        img = np.array(bytearray(frameBody))
                        img = cv2.imdecode(img, 1)
                        img = cv2.resize(img, (out_height, out_with))
                        self.queue.put(img)

                        cursor += frameBodyLengthRemaining
                        frameBodyLengthRemaining = 0
                        readFrameBytes = 0
                        frameBody = ''
                    else:
                        # else this chunk is still for the current image
                        #print(('body(len=%d)' % (len(chunk) - cursor), 'remaining = %d' % frameBodyLengthRemaining))
                        frameBody = bytes(list(frameBody) + list(chunk[cursor:len(chunk)]))
                        frameBodyLengthRemaining -= (len(chunk) - cursor)
                        readFrameBytes += len(chunk) - cursor
                        cursor = len(chunk)

if __name__ == "__main__":

    par = ap.ArgumentParser(add_help=True)
    par.add_argument('-p', '--port', help="Minicap port", default=1313)
    par.add_argument('-b', '--bitrate', help="Stream bitrate",
                     default=120000, type=int)
    par.add_argument('-r', '--output-ratio', help="Output ratio, used to" \
                     " estimate output height from specified output width",
                     default=0.1, type=float)

    args = vars(par.parse_args())

    asb = AndroidScreenBuffer(minicap_port=args['port'],
                              scale_ratio=args['output_ratio'],
                              bitrate=args['bitrate']
                              )

    asb.run()

    while True:
        img = asb.get_last_frame()
        if img is not None:
            cv2.imshow('capture', img)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            asb.stop()
            exit(0)
            break
