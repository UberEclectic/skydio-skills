# Example Computer Clients

This folder contains several client scripts that can communicate with and/or control R1 from a computer.

## ComLink Demo

The first example is [com_link_demo.py](com_link_demo.py).
While you are flying with a phone as the primary device,
your computer can fetch info from the vehicle and send basic commands with this script.

Be sure to follow the steps from the repo [README](../README.md) to create a Skillset for yourself that includes ComLink.

### Using a simulator

1.  Follow the instructions in the repo [README](../README.md) for creating and uploading the example skillset
1.  Use your phone to takeoff and switch into the ComLink skill. You may need to `Refresh` first in order to get the skill to appear.
1.  Once you've requested and selected a simulator in the Developer Console click the key icon
    and grab the `Simulator URI` and download the `Simulator Auth Token` file to your computer
1.  On your computer `cd` into the `client` directory
1.  Run the `com_link_demo.py` script using python (2):

    - `--baseurl` equal to `Simulator URI` from the Developer Console
    - `--token-file` pointing to the downloaded `Simulator Auth Token` file
    - `--skill-key` equal to the key of the ComLink skill which is `[your_skillset_name].com_link.ComLink`

    ```sh
    python com_link_demo.py --baseurl https://simX-X.sim.skydio.com \
        --token-file ~/Downloads/simX_token.txt \
        --skill-key my_skillset.com_link.ComLink \
        --forward 3 --loop
    ```

    The first time you run this script it will prompt you for a login code sent to your email to auth
    with the Skydio Cloud API servers so it can download your skillset.


### Using a real R1

1. Connect to the vehicle from your phone, takeoff and switch into ComLink skill.
1. Connect your computer to your R1 over WiFi
1.  Run the `com_link_demo.py` script using python (2):

    - `--skill-key` equal to the key of the ComLink skill which is `[your_skillset_name].com_link.ComLink`

    ```sh
    python com_link_demo.py \
        --skill-key my_skillset.com_link.ComLink \
        --forward 3 --loop
    ```

## Remote Control Demo

This second example replaces your phone and controls R1 entirely from a computer over WiFi with a USB gamepad.

Be sure to follow the steps from the repo [README](../README.md) to create a Skillset for yourself that includes Gamepad.


### Use the computer client with a real R1 and a video stream

1. Install dependencies  for your operating system.
    `pip install inputs opencv-python protobuf requests`

1. Connect your computer to the R1's WiFi. Confirm by visiting http://192.168.10.1/ from a web browser.

1. Run the client script to launch R1 and request an h264 stream
    - `--skill-key` equal to the key of the ComLink skill which is `[your_skillset_name].com_link.ComLink`

    ```sh
    python rc_demo.py \
        --skill-key my_skillset.remote.RemoteControl \
        --stream jpeg
    ```

1. If you are ready to takeoff, pass the `--takeoff` argument.
    ```sh
    python rc_demo.py \
        --skill-key my_skillset.remote.RemoteControl \
        --stream jpeg \
        --takeoff
    ```

1. When you want to land, re-run with the `--land` argument
    ```sh
    python rc_demo.py \
        --skill-key my_skillset.remote.RemoteControl \
        --land
    ```

1. By default the script uses your keyboard as input, but if you have a USB gamepad, pass the `--gamepad` argument.
    ```sh
    python rc_demo.py \
        --skill-key my_skillset.remote.RemoteControl \
        --stream jpeg \
        --takeoff \
        --gamepad
    ```

1.  If you adjust the [RemoteControl skill](../skillset/remote.py) and re-upload to the Developer Console you will have to sync that
code to the vehicle again.
    - Option A: connect with your phone and press `Synchronize Skills`
    - Option B: pass the `--update-skillsets-email` argument to the `rc_demo.py` script,
    while your computer is connected to the Internet and R1 at the same time.

1. Note that the RTP stream does not work from the simulator due to firewalls.


## Raspberry Pi Demo

The USB-C port on top of R1 is able to power and communicate with a properly configured Raspberry Pi
Zero. This setup enables you to execute arbitrary scripts on the pi, and proxy data from R1 over
your own custom wifi network.

### Proxying a video stream to a different computer on your own wifi network using a Pi

1. Install gstreamer dependencies on your Pi and any computer you want to use to view the stream.

    on Mac:
    ```sh
    brew install gstreamer \
            gst-plugins-base \
            gst-plugins-good \
            gst-plugins-bad
    ```

    on Linux:
    ```sh
    apt-get install gstreamer1.0-libav \
            gstreamer1.0-plugins-base \
            gstreamer1.0-plugins-good \
            gstreamer1.0-plugins-bad
    ```

2. Set up your Pi to act as a usb ethernet gadget. Complete the instructions
    [here](raspberry_pi_zero/README.md). This should allow the pi to get power over USB-C.

3. Copy this folder to your Pi and execute the `enterprise mode` script to allow takeoff with the
    USB-C port in use.

    ```sh
    python enable_enterprise_mode.py
    ```

4. Start the stream proxy, so that RTP packets will get forwarded to your destination.

    ```sh
    python gstreamer_proxy.py --remote-host <destination-computer-ip> --remote-port 55005
    ```

5. In a separate terminal (or tmux) run the pi demo.
    By default, this starts streaming but does not launch the R1.

    ```sh
    python pi_proxy_demo.py
    ```

6. On your destination computer, use gstreamer to view the stream.

    ```sh
    python gstreamer_viewer.py --format jpeg --port 55005
