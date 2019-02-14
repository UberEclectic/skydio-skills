"""
Proxy an RTP stream from one local port to a remote host/port.

This is useful for using an onboard raspberry pi to proxy the stream over WiFi to another computer.

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-port', type=int, default=55004,
                        help='local port from which to listen for RTP packets')
    parser.add_argument('--remote-port', type=int, default=55005,
                        help='remote port to send packets')
    parser.add_argument('--remote-host', default='localhost',
                        help='remote host ip address')
    args = parser.parse_args()
    cmd = [
        'gst-launch-1.0',
        'udpsrc',
        'port={}'.format(args.local_port),
        '!',
        'udpsink',
        'host={}'.format(args.remote_host),
        'port={}'.format(args.remote_port),
    ]
    print(' '.join(cmd))
    os.execvp(cmd[0], cmd)


if __name__ == '__main__':
    main()
