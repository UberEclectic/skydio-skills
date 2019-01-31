# Example Desktop Client

Included is a [Client](skydio_client.py) python module which demonstrates how to control
the vehicle and communicate with a skill from your desktop/laptop over wifi without using a Skydio Mobile App.

This demonstration client uses the [ComLink](../skillset/com_link.py) Skill
on the vehicle to receive and handle movement controls by the desktop client so be sure to follow
the steps from the repo [README](../README.md) to create a Skillset for yourself that includes ComLink.

### Use the desktop client with the simulator

1.  Follow the instructions in the repo [README](../README.md) for creating and uploading the example skillset until you get to opening the simulator page in your browser
1.  Once you've requested and selected a simulator in the Developer Console click the key icon
    and grab the `Simulator URI` and download the `Simulator Auth Token` file to your desktop
1.  On your desktop `cd` into the `client` directory
1.  Run the `skydio_client.py` script using python (2):

    - `--baseurl` equal to `Simulator URI` from the Developer Console
    - `--token-file` pointing to the downloaded `Simulator Auth Token` file
    - `--update-skillsets-email` equal to the email you signed in to the Developer Console with
    - `--skill-key` equal to the key of the ComLink skill which is `[your_skillset_name].com_link.ComLink`

    ```sh
    python skydio_client.py --baseurl https://simX-X.sim.skydio.com --token-file ~/Downloads/simX_token.txt --update-skillsets-email johndoe@blah.com --skill-key my_skillset.com_link.ComLink --pilot --takeoff --loop --forward
    ```

    The first time you run this script it will prompt you for a login code sent to your email to auth
    with the Skydio Cloud API servers so it can download your skillset.

1.  If you adjust the ComLink skill and re-upload to the Developer Console you will have to rerun
    the client so that it retrieves the latest skillset code and uploads it to the simulator vehicle.
