"""
Easily start different types of streaming pipelines.

This is useful for viewing the RTP strema from R1 with no-lag

# How to install Gstreamer

    on Mac:
    ```
    brew install gstreamer \
            gst-plugins-base \
            gst-plugins-good \
            gst-plugins-bad
    ```

    on Linux:
    ```
    apt-get install gstreamer1.0-libav \
            gstreamer1.0-plugins-base \
            gstreamer1.0-plugins-good \
            gstreamer1.0-plugins-bad
    ```

"""
from __future__ import print_function
import argparse
import os
import platform


def start_stream(stream_format, port=55004, system=None):

    # Determine the rtp source based on the format
    if stream_format == 'h264':
        rtp_elements = '! application/x-rtp,payload=96 ! rtph264depay ! h264parse'.split()
    else:
        rtp_elements = '! application/x-rtp,payload=26 ! rtpjpegdepay'.split()

    # Determine the display window based on the operating system.
    if system is None:
        system = platform.system()
    if system == 'Darwin':
        display_elements = '! glimagesink sync=false'.split()
    elif system == 'Linux':
        display_elements = '! xvimagesink sync=false'.split()
    elif system == 'Windows':
        display_elements = '! d3dvideosink sync=false'.split()
    else:
        raise RuntimeError('Unknown system {}'.format(system))

    cmd = (
        ['gst-launch-1.0', 'udpsrc', 'port={}'.format(port)]
        + rtp_elements
        + '! decodebin ! videoconvert'.split()
        + display_elements
    )
    print(' '.join(cmd))

    # Replace the current python process with a gstreamer process
    os.execvp(cmd[0], cmd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', choices=['h264', 'jpeg'], default='h264',
                        help='which type of stream to expect')
    parser.add_argument('--port', type=int, default=55004,
                        help='local port from which to listen for RTP packets')
    args = parser.parse_args()
    start_stream(args.format, args.port)


if __name__ == '__main__':
    main()
