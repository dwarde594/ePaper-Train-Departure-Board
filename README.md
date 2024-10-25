# ePaper-Train-Departure-Board
This is code for a UK train departure board using Waveshare ePaper 3.7" display and Raspberry Pi Pico W. It uses the National Rail API "Darwin" from the Rail Data Marketplace (RDM). The endpoint can be found [here](https://raildata.org.uk/dataProduct/P-9a01dd96-7211-4912-bcbb-c1b5d2e35609/overview). The code uses the MicroPython NanoGUI libraries which can be found in [this repo](https://github.com/waveshareteam/Pico_ePaper_Code). There's also some comprehensive documentation from the author of the NanoGUI modules [here](https://github.com/peterhinch/micropython-nano-gui).
Note: Still a work in progress
## Hardware requirements
- Raspberry Pi Pico W with soldered headers
- Waveshare 3.7" eInk Display (or equivalent)
- Development device (any device with a suitable IDE and USB port to connect with pico)
## Setup
1. Flash the MicroPython firmware onto the Pico. Either use the official firmware release or the uf2 file in this repo which includes the NanoGUI as frozen bytecode. It's recommended to freeze the bytecode as it reduces RAM usage. If you choose not to use the custom uf2 image, you'll need to include the gui folder in the pico's file system.
2. Sign up to Rail Data Marketplace (RDM) [here](https://raildata.org.uk/)
3. Subscribe to the Live Departure Board endpoint in RDM (linked above)
4. Note your consumer secret. This can be found on the subscription page under "Specification"
5. Transfer the color_setup.py, main.py files and drivers folder onto the pico's file system. Easiest to use Thonny IDE to do this
6. Paste your API consumer secret into the api_key variable in main.py
7. Enter your Wi-Fi SSID and password in the main.py file to connect to the network
8. Customise the other options in the main.py file, such as numRows (number of services displayed), leaving_from and destination stations
9. Test the program by running main.py and you should see the train info appear on the screen
## Freezing bytecode
If you want to create your own uf2 image file, [this GitHub issue](https://github.com/orgs/micropython/discussions/13019) provides a comprehensive method for doing this. It's also detailed in [Peter Hinch's NanoGUI repo](https://github.com/peterhinch/micropython-nano-gui?tab=readme-ov-file#appendix-1-freezing-bytecode).
   
