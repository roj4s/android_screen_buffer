import socket

import cv2
import numpy as np
import threading
from queue import Queue

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 1313))


q = Queue()

def frames_thread(q):
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
    while True:
        #chunk = client_socket.recv(4084)
        chunk = client_socket.recv(12000)
        if len(chunk) == 0:
            continue

        print(('chunk(length=%d)' % len(chunk)))
        cursor = 0
        while cursor < len(chunk):
            if (readBannerBytes < bannerLength):
                print((readBannerBytes, "---", bannerLength))
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

                if readBannerBytes == bannerLength:
                    print(('banner', banner))

            elif readFrameBytes < 4:
                frameBodyLengthRemaining += (int(hex(chunk[cursor]), 16) << (readFrameBytes * 8))
                cursor += 1
                readFrameBytes += 1
                print(('headerbyte%d(val=%d)' % (readFrameBytes, frameBodyLengthRemaining)))

            else:
                # if this chunk has data of next image
                if len(chunk) - cursor >= frameBodyLengthRemaining:
                    print(('bodyfin(len=%d,cursor=%d)' % (frameBodyLengthRemaining, cursor)))
                    frameBody = frameBody + chunk[cursor:(cursor + frameBodyLengthRemaining)]
                    if hex(frameBody[0]) != '0xff' or hex(frameBody[1]) != '0xd8':
                        print(("Frame body does not strt with JPEG header", frameBody[0], frameBody[1]))
                        exit()
                    img = np.array(bytearray(frameBody))
                    img = cv2.imdecode(img, 1)
                    #img = cv2.resize(img, (432, 768))
                    #img = cv2.resize(img, (224, 394))
                    w = 200
                    img = cv2.resize(img, (int(w*(1560/720)), w))
                    q.put(img)
                    
                    cursor += frameBodyLengthRemaining
                    frameBodyLengthRemaining = 0
                    readFrameBytes = 0
                    frameBody = ''
                else:
                    # else this chunk is still for the current image
                    print(('body(len=%d)' % (len(chunk) - cursor), 'remaining = %d' % frameBodyLengthRemaining))
                    frameBody = bytes(list(frameBody) + list(chunk[cursor:len(chunk)]))
                    frameBodyLengthRemaining -= (len(chunk) - cursor)
                    readFrameBytes += len(chunk) - cursor
                    cursor = len(chunk)

threading.Thread(target=frames_thread, args=(q,)).start()
while True:
    img = q.get()
    cv2.imshow('capture', img)
    if cv2.waitKey(25) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        exit(0)

#tryRead()
