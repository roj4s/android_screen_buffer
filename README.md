## Android Screen Buffer

Python package for streaming Android device's screen frames. It might be usefull in case you'd like to make processing or use screen frames in your python code (e.g to create reinforcement learning setups for android games).

## How to install:

 - First install and run [minicap](https://github.com/openstf/minicap) (thats really easy).
 - Then `pip install asb`

## How to use:

    from asb import AndroidScreenBuffer

    buf = AndroidScreenBuffer()
    buf.run()

    img = asb.get_last_frame()

    if img is not None:
        # Use image as you would like
        # e.g cv2.imshow('capture', img)