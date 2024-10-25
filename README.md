# ePaper-Train-Departure-Board
UK train departure board using Waveshare ePaper 3.7" display and Raspberry Pi Pico W. It uses the National Rail API "Darwin" from the Rail Data Marketplace (RDM). The endpoint can be found [here] (https://raildata.org.uk/dataProduct/P-9a01dd96-7211-4912-bcbb-c1b5d2e35609/overview).
Note: Still a work in progress
## Hardware requirements
- Raspberry Pi Pico W
- Waveshare 3.7" eInk Display (or equivalent)
- Development device (any device with a suitable IDE)
## Setup
1. Sign up to Rail Data Marketplace (RDM) [here](https://raildata.org.uk/)
2. Subscribe to the Live Departure Board endpoint in RDM (linked above)
3. Note your consumer ID and consumer secret. These can be found on the subscription page under "Specification".
