Skydio confidential pre-release software. DO NOT DISTRIBUTE


Sample Skills
=============

For the Skydio Skills SDK

This repo shows you how to programmatically move the R1,
detect and follow subjects,
and receive telemetry.

## Try these skills in the simulator
1. [Download](https://github.com/Skydio/sample-skills/archive/master.zip) this repo and unzip it.
1. [Sign up](https://console.skydio.com) to be a Skydio developer.
1. Create a new [skillset](https://console.skydio.com/skillsets/).
1. Upload the unzipped sample folder into your newly created skillset.
1. Click `author-staged` mode in the web interface.
1. Open the Skydio App (must be version 4.0+) and connect to a simulator via the Settings tab.
1. Tap `fly now` in in Fly tab, and you should see streaming video from the simulator.
1. If your sim vehicle is not already flying, swipe up to takeoff.
1. Select one of sample skills from the menu in the app to activate.
1. Edit the code for the skill using your favorite code editor.
1. When you save file in the synced folder, the code will be uploaded to the cloud via your console web page.
1. Press the `Refresh` button in the Skydio app to reload the code actively running in the simulator. You may need to re-select your skill, as the system restarts and selects the `Follow` skill by default.

## Table of Contents

 - [Polygon Path](polygon_path.py): Fly a path in the shape of a user-defined polygon.
 - [Security Bot](security_bot.py): Follow anyone that gets within range of a home point, then return.
