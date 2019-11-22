import socket

import cv2
import numpy as np
import threading
from threading import Event
from queue import Queue
import sys
import argparse as ap
import subprocess as sp


class ScreenOrientation:
    VERTICAL = 0
    HORIZONTAL = 1

def get_device_screen_shape():
    wss = sp.check_output(['adb', 'shell', 'wm', 'size'])
    w = str(wss).split('x')[0]
    w = int(w[w.index(":") + 1:])
    h = str(wss).split('x')[1]
    h = int(h[:h.index("\\n")])
    return (h, w)

def frames_thread(queue_pool, evt, minicap_port=1313, ref_width=720,
                  ref_height=1560, scale_ratio=0.1,
                  screen_orientation=ScreenOrientation.HORIZONTAL, bitrate=120000,
                  ):

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('localhost', minicap_port))

    if screen_orientation == ScreenOrientation.VERTICAL:
        print("Using vertical orientation")
        t = ref_width
        ref_width = ref_height
        ref_height = t

    out_with = int(ref_width * scale_ratio)
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
    while not evt.is_set():
        chunk = client_socket.recv(bitrate)
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
                    for q in queue_pool:
                        q.put(img)

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
    par.add_argument('-w', '--reference-width', help="Device width",
                     default=720)
    par.add_argument('-j', '--reference-height', help="Device height",
                     default=1560)
    par.add_argument('-s', '--width', help="Output width",
                     default=200)
    par.add_argument('-r', '--output-ratio', help="Output ratio, used to" \
                     " estimate output height from specified output width",
                     default=0.1, type=float)

    args = vars(par.parse_args())


    queue_pool = [Queue(), Queue()]
    evt = Event()
    threading.Thread(target=frames_thread, args=(queue_pool, evt),
                     kwargs={
                         'minicap_port': args['port'],
                         'screen_orientation': ScreenOrientation.HORIZONTAL,
                             'ref_width': args['reference_width'],
                             'ref_height': args['reference_height'],
                             'scale_ratio': args['output_ratio'],
                             }).start()
    q = queue_pool[0]
    while True:
        img = q.get()
        cv2.imshow('capture', img)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            evt.set()
            exit(0)
            break
