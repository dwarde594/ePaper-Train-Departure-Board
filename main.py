import gc
import network
import urequests
import ujson
import utime
from color_setup import ssd  # Import the ePaper display driver
from gui.core.writer import Writer  # Import Writer class for writing text
from gui.core.nanogui import refresh # Import refresh function that refreshes the contents on the screen
from gui.widgets.label import Label  # Import Label widget to display text
from gui.widgets.textbox import Textbox # Import Textbox widget to display long text
import gui.fonts.courier20 as courier20  # Import courier20 font


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

# Flag to show if the network is connected. Assists with network reconnection during runtime
network_connected = True

def connect(ssid: str, password: str, max_retries: int = 10):
    """Function that connects to the wireless network using the ssid and password parameters."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # Closes any previous connections
    wlan.disconnect()

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



def get_data(url: str, api_key: str, max_retries: int = 6):
    ''' Function that gets the departure data from the API endpoint, extracts key data and returns as a dictionary. '''
    gc.collect()
    
    attempts = 0
    
    req = None
    data = None
    raw_text = None
    
    # API connection loop
    while attempts <= max_retries:
        print(f"API connection attempt {attempts} of {max_retries}")
        try:
            req = urequests.get(url, headers={"x-apikey": api_key}, timeout=8)
            raw_text = req.text
        except Exception as e:
            print("API connection failed: " + str(e))
            try:
                if req:
                    req.close()
            except:
                pass
            req = None
            gc.collect()
            if attempts == max_retries:
                raise Exception(f"API call failed after {attempts} attempts.")
            utime.sleep(2)
            attempts += 1
            continue
        else:
            try:
                if req:
                    req.close()
            except:
                pass
            
            req = None
            gc.collect()
            
            break
    
    
    attempts = 0
    
    # JSON parsing loop
    while attempts <= max_retries:
        print(f"JSON parsing attempt {attempts} of {max_retries}")
        # Parses response to JSON. Very RAM intensive ATM, need to look at this.
        try:
            data = ujson.loads(raw_text)
        except Exception as e:
            print("JSON parsing failed: " + str(e))
            gc.collect()
            if attempts == max_retries:
                raise Exception("JSON parsing failed: " + str(e))
            utime.sleep(2)
            attempts += 1
            continue
        else:
            break
    
    del raw_text
    gc.collect()
    
    # If there are no train services, return None
    if "trainServices" not in data:
        return None
    
    # Dictionary that holds only the required departure info
    formatted_data = []
    
    # Stores the train services records from the API response
    train_services = data["trainServices"]
    
    for service in train_services:
        
        # Contains departure info about the service
        service_info = {
            "std": service["std"], # Time
            "destination": service["destination"][0]["locationName"], # Destination
            "etd": service["etd"] # Expected
        }
        
        # Checks if the service contains a delay or cancellation message
        delay_message = service.get("delayReason") or service.get("cancelReason")
        
        if delay_message is not None:
            service_info["delayMessage"] = delay_message
            
        formatted_data.append(service_info)

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

    # Finally adds the delay information to the bottom of the board
    board.append(Textbox(wri, y_pos + courier20.height(), 0, wri.stringlen("This is the width of the textbox.."), 4, clip=False))
    gc.collect()
    
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
    # If there are now train services upcoming, clear the textbox
    elif data is not None and noTrains:
        board[-1].clear()
        dataLen = len(data)
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

        # If service is delayed or cancelled, add delay message to the textbox on board
        if "delayMessage" in data[row]:
            delayBuffer = data[row]["std"]
            # Adds delay/cancellation message to display. ntrim=4 sets no. of text lines to store in RAM
            board[-1].append(data[row]["std"] + ": " + data[row]["delayMessage"], ntrim=4)
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
    global network_connected
    
    # Writer object with courier 20 font
    wri = Writer(ssd, courier20, verbose=False)
    
    refresh(ssd, True)
    
    # Initialise wlan variable
    wlan = None
    
    # Connects to network using supplied ssid and password
    try:
        wlan = connect(ssid, password)
    # If connection fails, print a message then continue.
    except Exception as e:
        print("Wi-Fi connection failed: " + str(e))
        network_connected = False
    # If connection is successful, set network_connected to True
    else:
        network_connected = True
    
    # Creates a board on display to write train departures on
    board = initialise_board(wri, 0)
    
    while True:
        
        if wlan is None or not wlan.isconnected() or not network_connected:
            print("Wi-Fi connection lost. Attempting to reconnect...")
            
            # Cleanup the old wlan object
            if wlan is not None:
                del wlan
            
            # If Wi-Fi has only just disconnected...
            if network_connected:
                # Set connected flag to False as we have now disconnected
                network_connected = False
            
            # Add a disconnection message to textbox. ntrim=4 sets no. of text lines to store in RAM
            board[-1].append("Wi-Fi connection lost. Attempting to reconnect...", ntrim=4)
            refresh(ssd)
                
            try:
                wlan = connect(ssid, password)
            except Exception as e:
                # If reconnection failed, print a message and sleep for 10 seconds
                print("Wi-Fi reconnection failed: " + str(e))
                gc.collect()
                utime.sleep(10)
                continue  # Skip to the next iteration
            else:
                if wlan.isconnected():  # Only reinitialize if reconnection is successful
                    print("Wi-Fi reconnected...")
                    network_connected = True
                    # Adds a message to indicate Wi-Fi reconnection
                    board[-1].append("Wi-Fi reconnected successfully.", ntrim=4)
                    refresh(ssd)
                    gc.collect()

        try:
            # Call get_data function and store in JSON variable
            data = get_data(url, api_key)
        except Exception as e:
            message = "API GET request failed: " + str(e)
            print(message)
            # Assume network has disconnected if we can't reach API
            network_connected = False

        try:
            # Update the board with the data
            update_board(board, data)
        except Exception as e:
            message = "Display update failed: " + str(e)
            display_error(wri, message)
            raise e
        
        if data is not None:
            del data
        
        # Refresh display after board update
        refresh(ssd)
        
        gc.collect()

        # Wait for 3 minutes (180 seconds) using utime library instead of async (less RAM intensive)
        utime.sleep(180)
        
if __name__ == '__main__':
    main()