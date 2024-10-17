#import uasyncio as asyncio
import gc
import network
import urequests

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

# Info needed to connect to wireless network
ssid = "<YOUR-SSID-HERE>"
password = "<YOUR-PASSWORD-HERE>"

# Parameters for the API call
leaving_from = "<CRS-CODE-HERE>"
destination = "<FILTER-CRS-CODE-HERE>"
numRows = 5 # Number of services to return

# URL for the API endpoint with added parameters seen above
url = f"https://api1.raildata.org.uk/1010-live-departure-board-dep/LDBWS/api/20220120/GetDepBoardWithDetails/{leaving_from}?numRows={numRows}&filterCRS={destination}"

# API key from Rail Data Marketplace subscription (Live Departure Board service)
api_key = "<YOUR-API-KEY-HERE>"

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
    ''' Function that gets the departure data from the API endpoint and returns as JSON. '''
    headers = {
        "x-apikey": api_key
    }
    
    # TO-DO: Fix the memory issues encountered. Useful links:
    # https://stackoverflow.com/questions/74883568/oserror-errno-12-enomem
    # https://github.com/micropython/micropython/issues/9003
    try:
        req = urequests.get(url, headers=headers)
    # If API call fails, print error and output to message screen. Then raise error.
    except Exception as e:
        message = "API call failed:", e
        print(message)
        #displayError(message)
        raise e

    data = req.json()

    # Close once finished (very important!)
    req.close()
    
    gc.collect()
    
    return data

def formatData(data: dict):
    ''' Formats the data, returning the service information as a 2d list of Label objects to be displayed '''
    # 2d list containing data
    services = []
    
    for service in data["trainServices"]:
        # Row to be added to the 2d list
        row = [
            service["std"], # Time
            service["destination"][0]["locationName"], # Destination
            service["etd"] # Expected
        ]
        
        # If the service is delayed or cancelled, add the reason to the row.
        if "delayReason" in service.keys():
            row.append(service["delayReason"])
        elif "cancelReason" in service.keys():
            row.append(service["cancelReason"])
        
        services.append(row)
        
    return services

def initialiseBoard(wri, y_pos: int):
    ''' Function that prepares the display for the train info to be added. '''
    
    # Title identifying the journey
    Label(wri, y_pos, 0, leaving_from + " -> " + destination)
    
    # Set delay_y_pos to 140 below the top (delay info appears below the train times)
    delay_y_pos = y_pos + 160
    
    # Increment y_pos to move down the page
    y_pos += 20
    
    Label(wri, y_pos, 0, "Time")
    Label(wri, y_pos, 90, "Destination")
    Label(wri, y_pos, 340, "Expt")
    
    
    print("Mem after board headers:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    # Train data will be further down the page
    y_pos += 20
    
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
        y_pos += 20
    
    print("Mem after board contents:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    # Finally adds the delay information to the bottom of the board
    board.append(Textbox(wri, delay_y_pos, 0, wri.stringlen("This is the width of the textbox.."), 3, clip=False))
    gc.collect()
    print("Mem after delays box:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    
    return board

def updateBoard(board, services):
    ''' Loops through all items in the 2d board array and updates the labels on the display with their corresponding values '''
    
    for row in range(0, len(services)):
        for col in range(0, 3):
            board[row][col].value(services[row][col])
            
        # Adds delay information at bottom of screen if that train is delayed. board[-1] last element of list which is the delay info item
        try:
            board[-1].append(services[row][0] + ": " + services[row][3])
        except IndexError:
            continue

def displayError(wri, error: str):
    ''' Function that displays an error on the display to help with troubleshooting '''
    # Clear display
    refresh(ssd, True)
    print("Displaying error...")
    # Sets the clip parameters row_clip=False, col_clip=False, wrap=True
    wri.set_clip(False, False, True)
    
    # Draw the error string to the screen at x=0 y=0
    wri.set_textpos(ssd, 0, 0)
    wri.printstring(leaving_from + " -> " + destination + "\n" + error)


    # Refresh to show the text
    refresh(ssd)
    print("Finished displaying error")
    

def main():
    ''' Main function that displays the data on the screen. '''
    # Writer object with courier 20 font
    wri = Writer(ssd, courier20, verbose=False)
    print("Mem after writer:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free(), "bytes")
    # Sets the clip parameters row_clip=False, col_clip=False, wrap=True
    wri.set_clip(False, False, True)
    
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
        
        # Checks if train data is not present in the API response
        if "trainServices" not in data.keys():
            # String containing train information
            message = ""
            
            try:
                nrcc_messages = data["nrccMessages"]
            except KeyError:
                # If there are no messages from the train operators, print a generic statement.
                message = "There are no direct trains between these stations today. Please check the National Rail website for more info."
                print(message)
            # If there are messages from the train operators...
            else:
                # Loop through all train info messages
                for item in nrcc_messages:
                    # Add the message to the string to be displayed
                    message += item["Value"]
            finally:
                # Displays messages using function
                displayError(wri, message)
        
            # OLD: Display the train data on the screen, passing JSON data and starting y position
            #displayData(data, 0)
        else:
            updateBoard(board, formatData(data))
            refresh(ssd)
            

        print("Mem after:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free())
        gc.collect()
        print("Mem after g collection:", gc.mem_alloc(), "bytes  Mem free:", gc.mem_free())
        # Wait for 3 minutes (180 seconds) using utime library instead of async (less RAM intensive)
        sleep(30)
        
if __name__ == '__main__':
    main()


