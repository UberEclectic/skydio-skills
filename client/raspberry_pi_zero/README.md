#Connecting a Raspberry Pi Zero W to R1

While the Skills SDK allows you to execute a limited set of python directly
onboard the TX1, you may want to execute your own code in a linux environment
that you can directly control.

One way to accomplish this is by attaching a Raspberry Pi Zero to the R1 via the usb-c port.
The usb port can power your Pi, but you'll need to configure the Pi as a usb network adapter
that treats the Skydio R1 as the host computer.

Boot your Pi and make the following changes.

1. add `dtoverlay=dwc2` to `/boot/config.txt`
2. insert `modules-load=dwc2,g_ether` to `/boot/cmdline.txt` after `root-wait`

Make sure your Pi is set up to connect to a wifi network, so that you can ssh into it later.

Now plug the Pi into the usb-c port of the Skydio R1.
While on, the R1 will provide power over usb-c to run the Pi.

ssh in over your wifi network, and then run the following command:
    ```sh
    sudo modprobe; sudo ifconfig usb0 192.168.13.2 up
    ```

This will assign a static ip address to the Pi. Now Try to ping the R1

    ```sh
    ping 192.168.13.1
    ```

If that works, you're all set! Try copying the `client` folder to your pi and running the examples.
If that didn't work, check the connection to the R1, and try reversing the usb port.

You'll want to create a startup script that executes the ifconfig command on boot,
and whatever other scripts you need.

    ```sh
    cp setup_network.sh ~/
    sudo cp pi_network_config.service /etc/systemd/system/
    sudo systemctl enable pi_network_config
    ```
