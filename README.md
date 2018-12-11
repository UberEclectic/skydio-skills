Skydio Skills SDK
=================

This repo shows you how to programmatically move the R1,
detect and follow subjects,
and receive telemetry.

## Try these skills in the simulator
1. [Download](https://github.com/Skydio/sample-skills/archive/master.zip) this repo and unzip it.
1. [Sign up](https://console.skydio.com) to be a Skydio developer. (Note: this is currently invite-only.)
1. Create a new [skillset](https://console.skydio.com/skillsets/).
1. Upload the unzipped sample folder into your newly created skillset. This creates an automatic file sync between our server and your browser tab.
1. Open the [simulator view](https://console.skydio.com/simulators) in a new tab and select yours from the dropdown.
1. Open the Skydio App (must be version 4.0+) and [select the matching simulator](https://console.skydio.com/docs/skills/getting_started.html#running-the-skydio-mobile-app) via the Settings tab.
1. Tap `FLY NOW` in in Fly tab, and you should see streaming video from the simulator.
1. If your sim vehicle is not already flying, swipe up to takeoff.
1. Select the `PropertyTour` sample skill from the menu in the app to activate it. You should see a `Go` button on screen. Pressing it will initiate the automated tour.
1. Edit the code for the `property_tour.py` using your favorite code editor. Uncomment line 183 to add a new `OrbitMotion` to the tour.
1. Save the file and your change will be automatically uploaded to the cloud via your open skillset web page.
1. Press the `Synchronize skills` button in the skill selection menu of the Skydio app to redeploy your code to the simulator. You will need to re-select your skill, as the system restarts and selects the `Follow` skill by default.
1. If your change worked, you should see a new orbit motion in the tour when you run it. However, if an error occured, the vehicle will not execute the skill. Any errors will appear in the debugging console above the simulator pane. Look out for red text describing the error.

Visit the [Getting Started](https://console.skydio.com/docs/skills/getting_started.html) section of the SDK docs for more information.

## Table of Contents

 - [Polygon Path](polygon_path.py): Fly a path in the shape of a user-defined polygon.
 - [Property Tour](property_tour.py): Perform a series of cinematic motions to record a real estate video.
 - [Roof Inspection](roof_inspection.py): Fly a configurable scanning pattern over the roof of a house.
 - [Security Bot](security_bot.py): Follow anyone that gets within range of a home point, then return.
 - [Com Link](com_link.py): Communicate with a Skill using HTTP. Client code is in [skydio_client.py](skydio_client.py).
