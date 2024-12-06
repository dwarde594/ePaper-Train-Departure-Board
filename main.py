import gc
import network
import urequests
import ujson
import micropython

print("Mem before imports: ", gc.mem_alloc())
from utime import sleep
from color_setup import ssd  # Import the ePaper display driver
from gui.core.writer import Writer  # Import Writer class for writing text
from gui.core.nanogui import refresh # Import refresh function that refreshes the contents on the screen
from gui.widgets.label import Label  # Import Label widget to display text
from gui.widgets.textbox import Textbox # Import Textbox widget to display long text
print("Mem after imports: ", gc.mem_alloc())
import gui.fonts.courier20 as courier20  # Import courier20 font
#import gui.fonts.font10 as font10 # Import font10 font
print("Mem after font import: ", gc.mem_alloc())

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
    raise e

# Info to connect to wireless network
ssid = "<YOUR-SSID>"
password = "<YOUR-PASSWORD>"

# Parameters for the API call
leaving_from = config["crs"]
destination = config["filterCrs"]
numRows = config["numRows"]

# URL for the API endpoint with added parameters seen above
url = f"https://api1.raildata.org.uk/1010-live-departure-board-dep/LDBWS/api/20220120/GetDepBoardWithDetails/{leaving_from}?numRows={numRows}&filterCRS={destination}"

# API key from Rail Data Marketplace subscription (Live Departure Board service)
api_key = config["api_key"]

# Holds the delay info text displayed on the board
delayBuffer = ""

# Flag to show if there are no trains to display
noTrains = False

def connect(ssid, password):
    ''' Function that connects to the wireless network using the ssid and password parameters. '''
    wlan = network.WLAN(network.STA_IF)
    
    wlan.active(True)
    
    wlan.connect(ssid, password)
    
    while wlan.isconnected() == False:
        print("Waiting for connection...")
        sleep(1)
    
    print(wlan.ifconfig())


def getData(url : str, api_key : str):
    ''' Function that gets the departure data from the API endpoint, extracts key data and returns as a dictionary. '''

    try:
        req = urequests.get(url, headers={"x-apikey": api_key})
    # If API call fails, print error and output to message screen. Then raise error.
    except Exception as e:
        message = "API call failed:", e
        print(message)
        raise e
    
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
    print(formatted_data)
    gc.collect()
    
    return formatted_data


def initialiseBoard(wri, y_pos: int):
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
        row = [
            Label(wri, y_pos, 0, wri.stringlen("00:00")), # Time
            Label(wri, y_pos, 90, wri.stringlen("Ashford International")), # Destination (Ashford International is the longest station name)
            Label(wri, y_pos, 340, wri.stringlen("Cancelled")) # Expected
        ]
        
        board.append(row)
        
        # Increment y_pos to move down the screen
        y_pos += courier20.height()
    
    print("Mem after board contents:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    # Finally adds the delay information to the bottom of the board
    board.append(Textbox(wri, y_pos + courier20.height(), 0, wri.stringlen("This is the width of the textbox.."), 4, clip=False))
    gc.collect()
    print("Mem after delays box:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    return board


def newUpdateBoard(board, data: dict):
    ''' Adds the data to the display in a readable format. Combined updateBoard and formatData functions to save RAM '''
    global delayBuffer, noTrains
    
    # Flag to show if a delay has already been discovered
    delayFound = False
    
    # Checks if there are no trains in the response dictionary
    if data is None and not noTrains:
        # Add message to textbox
        board[-1].append(message, nlines=4)
        # noTrains is True. Next time the board will only refresh if trains are present
        noTrains = True
        # dataLen set to -1. All rows will be removed in the loop
        dataLen = -1
    # If the no trains message is already displayed
    elif data is None and noTrains:
        # Exit function. Do not need to update board.
        return
    else:
        # Length of data dict
        dataLen = len(data)
        
    for row in range(0, numRows):
        # If there are no more services to be displayed, reset the remaining row values and continue next loop
        if row > dataLen:
            board[row][0].value("") # Time
            board[row][1].value("") # Destination
            board[row][2].value("") # Expected
            continue

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
            delayBuffer = data[row]["std"] + ": " + data[row][delay_key]
            # Adds delay/cancellation message to display. ntrim=4 sets no. of text lines to store in RAM
            board[-1].append(delayBuffer, ntrim=4)
            delayFound = True


def displayError(wri, error: str):
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
    print("Mem after writer:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    refresh(ssd, True)
    
    # Connects to network using supplied ssid and password
    try:
        connect(ssid, password)

    # If connection fails, print error message and display it on screen. Then raise the error
    except Exception as e:
        message = "Wi-Fi connection failed: " + str(e)
        print(message)
        displayError(wri, message)
        raise e
    print("Mem after wifi:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    # Creates a board on display to write train departures on
    board = initialiseBoard(wri, 0)
    print("Mem after board:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    while True:

        try:
            # Call getData function and store in JSON variable
            data = getData(url, api_key)
        except Exception as e:
            message = "API GET request failed: " + str(e)
            displayError(wri, message)
            raise e
        
        print("Mem after API call:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")

        # Update the board with the data
        newUpdateBoard(board, data)
        # Refresh display after board update
        refresh(ssd)
        
        print("Mem after:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free())
        gc.collect()
        print("Mem after g collection:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free())
        print(micropython.mem_info())
        # Wait for 3 minutes (180 seconds) using utime library instead of async (less RAM intensive)
        sleep(180)
        
if __name__ == '__main__':
    main()


