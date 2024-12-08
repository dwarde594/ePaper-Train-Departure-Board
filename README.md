# ePaper-Train-Departure-Board
This is code for a UK train departure board using Waveshare ePaper 3.7" display and Raspberry Pi Pico W. It uses the National Rail API "Darwin" from the Rail Data Marketplace (RDM). The endpoint can be found [here](https://raildata.org.uk/dataProduct/P-9a01dd96-7211-4912-bcbb-c1b5d2e35609/overview). The code uses the MicroPython NanoGUI libraries which can be found in [this repo](https://github.com/waveshareteam/Pico_ePaper_Code). There's also some comprehensive documentation from the author of the NanoGUI modules [here](https://github.com/peterhinch/micropython-nano-gui).
Note: Still a work in progress
## Hardware requirements
- Raspberry Pi Pico W with soldered headers
- Waveshare 3.7" eInk Display (or equivalent)
- Development device (any device with a suitable IDE and USB port to connect with pico)
## Setup
1. Flash the MicroPython firmware onto the Pico using [this method](https://www.raspberrypi.com/documentation/microcontrollers/micropython.html). Either use the official firmware release or the uf2 file in the `firmware` folder of repo which includes the NanoGUI as frozen bytecode. It's recommended to freeze the NanoGUI code files as bytecode as it reduces RAM usage. If you choose not to use the custom uf2 image, you'll need to include the `gui` folder from [this repo](https://github.com/peterhinch/micropython-nano-gui/tree/master) in the Pico's file system.
2. Sign up to Rail Data Marketplace (RDM) [here](https://raildata.org.uk/)
3. Subscribe to the Live Departure Board endpoint in RDM linked [here](https://raildata.org.uk/dataProduct/P-9a01dd96-7211-4912-bcbb-c1b5d2e35609/overview)
4. Note your consumer key for the API requests. Select Subscriptions tab, then select the Live Departure Board subscription. Go to Specification tab and scroll down to API access credentials. Note the Consumer key.
5. Transfer the `color_setup.py`, `main.py`, `config.json` files and `drivers` folder onto the pico's file system. Easiest to use [Thonny IDE](https://thonny.org/) to do this. If you're using the vanilla MicroPython firmware without frozen NanoGUI, make sure to include the `gui` folder in the file system as specified in step 1
6. Paste your API consumer key into the `api_key` value in `config.json`
7. Enter your Wi-Fi SSID and password in the values in `config.json` file to connect to the network
8. Customise the other options in the `config.json` file, such as `numRows` (number of services displayed), `crs` (station leaving from) and `filterCrs` (destination) stations. These should be CRS codes in all capitals e.g. BFR (London Blackfriars). An explanation of CRS codes can be found [here](https://www.rail-record.co.uk/railway-location-codes/) along with a tool to identify a station's code.
9. Test the program by running `main.py` and you should see the train info appear on the display
## Freezing bytecode
If you want to create your own uf2 image file, [this GitHub issue](https://github.com/orgs/micropython/discussions/13019) provides a comprehensive method for doing this. It's also detailed in [Peter Hinch's NanoGUI repo](https://github.com/peterhinch/micropython-nano-gui?tab=readme-ov-file#appendix-1-freezing-bytecode).
   
