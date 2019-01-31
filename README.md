# Sample Skills

For the Skydio Skills SDK

## Skillset

We've put together a skillset of sample skills that you can use to learn how the Skills SDK works.

### Try these skills in the simulator and control with your Skydio Mobile App

1. [Download](https://github.com/Skydio/sample-skills/archive/master.zip) this repo and unzip it.
1. [Login](https://console.skydio.com) to the Skydio Developer Console using the same email you did/will in the Skydio Mobile App.
1. Create a new [skillset](https://console.skydio.com/skillsets/) with a unique name for your testing.
1. Upload the `skillset` folder from the zip into your newly created skillset. This creates an automatic file sync between our server and your browser tab if using Google Chrome.
1. Open the [simulators page](https://console.skydio.com/simulators) in a new tab, request a simulator from the pool and then select yours from the dropdown.
1. Open the Skydio Mobile App (must be version 4.0+) and [select the matching simulator](https://console.skydio.com/docs/skills/getting_started.html#running-the-skydio-mobile-app) via the Settings tab.
1. Tap `FLY NOW` in your Mobile App Fly tab, and you should start to see streaming video from the simulator in your app and the browser.
1. If your sim vehicle is not already flying, swipe up to takeoff in the Mobile App.
1. Select the `PropertyTour` sample skill from the menu in the app to activate it. You should see a `Go` button on screen. Pressing it will initiate the automated tour.
1. Edit the code for the `property_tour.py` using your favorite code editor. Uncomment line `183` to add a new `OrbitMotion` to the tour.
1. Save the file and your change will be automatically uploaded to the cloud via your open skillset web page (if you are not using Chrome you will have to re-upload).
1. Press the `Synchronize Skills` button in the skill selection menu of the Skydio Mobile App to redeploy your code to the simulator. You will need to re-select your skill, as the system restarts and selects the `Follow` skill by default.
1. If your change worked, you should see a new orbit motion in the tour when you run it. However, if an error occured, the vehicle will not execute the skill. Any errors will appear in the debugging console above the simulator pane. Look out for red text describing the error.

Visit the [Getting Started](https://console.skydio.com/docs/skills/getting_started.html) section of the SDK docs for more information.

### Included Skills

- [Polygon Path](skillset/polygon_path.py): Fly a path in the shape of a user-defined polygon.
- [Property Tour](skillset/property_tour.py): Perform a series of cinematic motions to record a real estate video.
- [Roof Inspection](skillset/roof_inspection.py): Fly a configurable scanning pattern over the roof of a house.
- [Security Bot](skillset/security_bot.py): Follow anyone that gets within range of a home point, then return.
- [Com Link](skillset/com_link.py): Communicate with a Skill from an external client using HTTP. See instructions in [Client](#client) to use with a python client on your desktop.
 - [Party Mode](party_mode.py): Automatically follow subjects for 15 seconds at a time within a defined area.

## Client

Included is a [Skydio Client](client/skydio_client.py) python module which demonstrates how to control
the vehicle and communicate with a skill from your desktop/laptop over wifi without using a Skydio Mobile App.

This demonstration client uses the [Com Link](skillset/com_link.py) Skill
on the vehicle to receive and handle movement controls by the desktop client so be sure to follow
the steps above to create a Skillset for yourself that includes ComLink.

Visit the [Client Readme](client/README.md) for Instructions to use the client with a simulator
