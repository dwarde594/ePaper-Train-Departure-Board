import gc
print("Mem before imports: ", gc.mem_alloc())
import network
import urequests
import ujson
import micropython

import utime
from color_setup import ssd  # Import the ePaper display driver
from gui.core.writer import Writer  # Import Writer class for writing text
from gui.core.nanogui import refresh # Import refresh function that refreshes the contents on the screen
from gui.widgets.label import Label  # Import Label widget to display text
from gui.widgets.textbox import Textbox # Import Textbox widget to display long text
print("Mem after imports: ", gc.mem_alloc())
import gui.fonts.courier20 as courier20  # Import courier20 font
print("Mem after font import: ", gc.mem_alloc())

def validate_config(config: dict):
    """ Validate the config dictionary. """
    # Define the expected configuration schema
    expected_config = {
        "ssid": str,
        "password": str,
        "crs": str,
        "filterCrs": str,
        "numRows": int,
        "api_key": str,
    }
    
    for key, expected_type in expected_config.items():
        if key not in config:
            raise ValueError(f"Missing key in config: {key}")
        # Checks if the value is of the expected type using isinstance function
        if not isinstance(config[key], expected_type):
            raise TypeError(f"Invalid type for key '{key}': expected {expected_type.__name__}, got {type(config[key]).__name__}")
        # Additional checks for specific keys
        if key == "numRows" and config[key] <= 0:
            raise ValueError(f"Invalid value for 'numRows': must be a positive integer, got {config[key]}")
    print("Configuration validated successfully.")

# Opens config.json file and implements error handling
try:
    with open("config.json", "r") as file:
        config = ujson.load(file)
        file.close()
except OSError as e:
    print("config.json is not found. Please ensure it is present.")
    raise e
except Exception as e:
    print("Failed to open config.json file. Please ensure it is present and accessible.")

validate_config(config)

# Info to connect to wireless network
ssid = config["ssid"]
password = config["password"]

# Parameters for the API call
leaving_from = config["crs"]
destination = config["filterCrs"]
numRows = config["numRows"]

# API key from Rail Data Marketplace subscription (Live Departure Board service)
api_key = config["api_key"]

# Remove config dictionary to save RAM, and garbage collect
del config
gc.collect()

# URL for the API endpoint with added parameters seen above
url = f"https://api1.raildata.org.uk/1010-live-departure-board-dep/LDBWS/api/20220120/GetDepBoardWithDetails/{leaving_from}?numRows={numRows}&filterCRS={destination}"

# Holds the delay info text displayed on the board
delayBuffer = ""

# Flag to show if there are no trains to display
noTrains = False

# Flag to show if the network is disconnected. Assists with network reconnection during runtime
network_disconnected = True

def connect(ssid: str, password: str, max_retries: int = 8):
    """Function that connects to the wireless network using the ssid and password parameters."""
    wlan = network.WLAN(network.STA_IF)
    # Closes any previous connections
    wlan.disconnect()
    wlan.active(True)

    wlan.connect(ssid, password)

    attempt = 0

    while not wlan.isconnected() and attempt < max_retries:
        print(f"Attempt {attempt + 1} of {max_retries}: Waiting for connection...")
        utime.sleep(1.5)
        attempt += 1

    if wlan.isconnected():
        print("Connected successfully.")
        print("Network configuration:", wlan.ifconfig())
        return wlan
    else:
        print(f"Failed to connect after {attempt} connection attempts.")
        raise Exception(f"Failed to connect after {attempt} connection attempts.")



def get_data(url: str, api_key: str, max_retries: int = 4):
    ''' Function that gets the departure data from the API endpoint, extracts key data and returns as a dictionary. '''
    gc.collect()
    
    attempts = 1
    success = False
    
    while attempts <= max_retries:
        print(f"API connection attempt {attempts} of {max_retries}")
        try:
            req = urequests.get(url, headers={"x-apikey": api_key})
            print("Response code:", req.status_code)
        except Exception as e:
            print(str(e))
            gc.collect()
            print("Attempt failed. Retrying...")
            utime.sleep(2)
            attempts += 1
        else:
            print("API connection successful.")
            success = True
            break

    
    # If API call fails, print error and output to screen. Then raise error.
    if not success:
        message = f"API call failed after {attempts} attempts. Please check your Wi-Fi connection and try again."
        print(message)
        raise Exception(message)
    
    print("Mem after API call:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    # Parses response to JSON. Very RAM intensive ATM, need to look at this.
    data = req.json()
    
    print("Mem after parsed API response:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    # Close once finished (very important!)
    req.close()
    
    # If there are no train services, garbage collect and return None
    if "trainServices" not in data.keys():
        gc.collect()
        return None
    
    # Dictionary that holds only the required departure info
    formatted_data = []
    
    for row in range(0, len(data["trainServices"])):
        # Contains departure info about the service
        service_info = {
            "std": data["trainServices"][row]["std"], # Time
            "destination": data["trainServices"][row]["destination"][0]["locationName"], # Destination
            "etd": data["trainServices"][row]["etd"] # Expected
        }
        
        # Gets the dictionary keys of the train service for identification of delay/cancellation messages
        service_keys = data["trainServices"][row].keys()
        
        # Checks if the service is delayed or cancelled. If so, add to the reason to the output dictionary
        if "delayReason" in service_keys:
            service_info["delayReason"] = data["trainServices"][row]["delayReason"]
        
        elif "cancelReason" in service_keys:
            service_info["cancelReason"] = data["trainServices"][row]["cancelReason"]
            
        formatted_data.append(service_info)
    
    print("Mem after formatted API response:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")

    gc.collect()
    
    return formatted_data


def initialise_board(wri, y_pos: int):
    ''' Function that prepares the display for the train info to be added. '''
    
    # Title identifying the journey
    Label(wri, y_pos, 0, leaving_from + " -> " + destination)
    
    # Increment y_pos to move down the page
    y_pos += courier20.height()
    
    Label(wri, y_pos, 0, "Time")
    Label(wri, y_pos, 90, "Destination")
    Label(wri, y_pos, 340, "Expt")
    
    
    print("Mem after board headers:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    # Increment y_pos. Train data will be further down the page
    y_pos += courier20.height()
    
    # 2d list to store the departure details
    board = []
    
    for i in range(0, numRows):
        
        # Row to be added to the 2d list
        row = (
            Label(wri, y_pos, 0, wri.stringlen("00:00")), # Time
            Label(wri, y_pos, 90, wri.stringlen("Ashford International")), # Destination (Ashford International is the longest station name)
            Label(wri, y_pos, 340, wri.stringlen("Cancelled")) # Expected
        )
        
        board.append(row)
        
        # Increment y_pos to move down the screen
        y_pos += courier20.height()
    
    print("Mem after board contents:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    # Finally adds the delay information to the bottom of the board
    board.append(Textbox(wri, y_pos + courier20.height(), 0, wri.stringlen("This is the width of the textbox.."), 4, clip=False))
    gc.collect()
    print("Mem after delays box:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    return board


def update_board(board, data: dict):
    ''' Adds the data to the display in a readable format. Combined updateBoard and formatData functions to save RAM '''
    global delayBuffer, noTrains
    
    # Flag to show if a delay has already been discovered
    delayFound = False
    
    # Checks if there are no trains in the response dictionary
    if data is None and not noTrains:
        message = "There are no direct trains between these stations within the next 2 hours. Please check the National Rail website for more info."
        # Add message to textbox
        board[-1].append(message, ntrim=4)
        # noTrains is True. Next time the board will only refresh if trains are present
        noTrains = True
        # dataLen set to -1. All rows will be removed in the loop
        dataLen = -1
    # If the no trains message is already displayed
    elif data is None and noTrains:
        # Exit function. Do not need to update board.
        return
    else:
        # Trains are available, so set noTrains to False
        noTrains = False
        dataLen = len(data)
        
    for row in range(0, numRows):
        # If there are no more services to be displayed, reset the remaining row values and continue next loop
        if row >= dataLen:
            board[row][0].value("") # Time
            board[row][1].value("") # Destination
            board[row][2].value("") # Expected
            continue
        
        # Validate required keys. Must contain std, destination and etd keys
        if not all(k in data[row] for k in ["std", "destination", "etd"]):
            print(f"Skipping invalid entry: {data[row]}")  # Log missing data
            continue  # Skip this entry

        # Rows to be added to the board
        board[row][0].value(data[row]["std"]) # Time
        board[row][1].value(data[row]["destination"]) # Destination
        board[row][2].value(data[row]["etd"]) # Expected
        
        # If train is on time, no need to display delay info
        if data[row]["etd"] == "On time":
            continue
        
        # If delay info is already displayed for this service, or a delay is already found, skip to next service.
        if data[row]["std"] in delayBuffer or delayFound:
            continue
        
        # Iterates through dictionary keys and produces any cancellation or delay messages
        delay_gen = (key for key in ["delayReason", "cancelReason"] if key in data[row])
        try:
            delay_key = next(delay_gen)
        # Once end of generator is reached, return no delay info
        except StopIteration:
            delay_key = None
            continue
        
        # If service is delayed or cancelled, add delay message to the textbox on board
        if delay_key in ["delayReason", "cancelReason"]:
            delayBuffer = data[row]["std"]
            # Adds delay/cancellation message to display. ntrim=4 sets no. of text lines to store in RAM
            board[-1].append(data[row]["std"] + ": " + data[row][delay_key], ntrim=4)
            delayFound = True


def display_error(wri, error: str):
    ''' Function that displays an error on the display to help with troubleshooting '''
    # Clear display
    refresh(ssd, True)
    print("Displaying error...")
    # Sets the clip parameters row_clip=False, col_clip=False, wrap=True
    wri.set_clip(False, False, True)
    
    # Draw the error string to the screen at x=0 y=0
    wri.set_textpos(ssd, 0, 0)
    wri.printstring(leaving_from + " -> " + destination + "\n" + error + "\n" + "Mem alloc:" + str(gc.mem_alloc()) + " bytes\n" "Mem free: " + str(gc.mem_free()) + " bytes")

    # Refresh to show the text
    refresh(ssd)
    print("Finished displaying error")
    

def main():
    ''' Main function that displays the data on the screen. '''
    # Writer object with courier 20 font
    wri = Writer(ssd, courier20, verbose=False)
    
    refresh(ssd, True)
    
    # Connects to network using supplied ssid and password
    try:
        wlan = connect(ssid, password)
    # If connection fails, print error message and display it on screen. Then raise the error
    except Exception as e:
        message = "Wi-Fi connection failed: " + str(e)
        print(message)
        display_error(wri, message)
        raise e
    # If connection is successful, set network_disconnected to False
    else:
        network_disconnected = False
    
    print("Mem after wifi:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    # Creates a board on display to write train departures on
    board = initialise_board(wri, 0)
    print("Mem after board:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    while True:
        
        if not wlan.isconnected():
            print("Wi-Fi lost. Attempting to reconnect...")
            # If Wi-Fi has not disconnected before this...
            if not network_disconnected:
                # Add a disconnection message to textbox. ntrim=4 sets no. of text lines to store in RAM
                board[-1].append("Wi-Fi connection lost. Attempting to reconnect...", ntrim=4)
                refresh(ssd)
                # Set disconnected flag to True as we have now disconnected
                network_disconnected = True
                
            try:
                wlan = connect(ssid, password)
            except Exception as e:
                # If reconnection failed, print a message a sleep for 10 seconds
                print("Wi-Fi reconnection failed: " + str(e))
                utime.sleep(10)
                continue  # Skip to the next iteration
            else:
                if wlan.isconnected():  # Only reinitialize if reconnection is successful
                    print("Wi-Fi reconnected...")
                    network_disconnected = False
                    # Adds a message to indicate Wi-Fi reconnection
                    board[-1].append("Wi-Fi reconnected successfully.", ntrim=4)
                    refresh(ssd)
                    gc.collect()

        try:
            # Call get_data function and store in JSON variable
            data = get_data(url, api_key)
        except Exception as e:
            message = "API GET request failed: " + str(e)
            display_error(wri, message)
            raise e
        
        print("Mem after API call:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")

        try:
            # Update the board with the data
            update_board(board, data)
        except Exception as e:
            message = "Display update failed: " + str(e)
            display_error(wri, message)
            raise e
        
        # Refresh display after board update
        refresh(ssd)
        
        print("Mem after:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free())
        gc.collect()
        print(micropython.mem_info())
        # Wait for 3 minutes (180 seconds) using utime library instead of async (less RAM intensive)
        utime.sleep(180)
        
if __name__ == '__main__':
    main()


