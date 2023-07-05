
import network, time, ujson, socket, json, urequests
from machine import WDT

# Initialise Wifi
station = network.WLAN(network.STA_IF)
#station.active(True)


post = urequests.post
dumps = ujson.dumps
sleep = time.sleep
loads = ujson.loads

wdt = WDT(timeout=60000) # 1 min inactivity

# SWQ = West array
# SW25 = East Array

sol = ["Solax_123456", "Solax_987654"]

def solax_json():
    wdt.feed()
    try:
        # Example usage
        host = "5.8.8.8"
        port = 80
        path = "/?optType=ReadRealTimeData"


        # Create a TCP socket
        client_socket = socket.socket()

        # Connect to the server
        addr = socket.getaddrinfo(host, port)[0][-1]
        client_socket.connect(addr)

        # Construct the HTTP request
        request = "POST /?optType=ReadRealTimeData HTTP/1.1\r\n" \
                  "Host: 5.8.8.8\r\n" \
                  "Content-Length: 0\r\n" \
                  "\r\n"

        # Send the request
        client_socket.send(request)

        # Receive the response
        response = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response += chunk

        # Close the socket
        client_socket.close()


        # Print the response

        resp = response.decode("utf-8")

        # Extract JSON data from response
        json_start = resp.find("{")  # Find the starting index of the JSON data
        json_data = resp[json_start:]  # Extract the JSON portion


        # Print the JSON string
        return json_data

    except Exception as error:
        print("An error occurred:", type(error).__name__)
        return

def connect_to_inverter(SSID):
    wdt.feed()
    try:
        station.active(True)
        #connect to the wifi
        print("connecting to " + SSID)
        station.ifconfig(('5.8.8.10', '255.255.255.0', '5.8.8.8', '5.8.8.8'))
        station.connect(SSID, "")
        print("Waiting for connection...")
        count = 0
        while not station.isconnected():
            sleep(1)
            print(station.status())
            count = count + 1
            if count==20:
                print("failed after 20 connects")
                return(1)
        print ("connected to inverter")
        return(0)
    except Exception as error:
        print("An error occurred:", type(error).__name__)
        return(1)


def connect_to_home():
    wdt.feed()
    try:
        station.active(True)
        print("connecting to IOT Network")
        station.ifconfig(('192.168.0.189', '255.255.255.0', '192.168.0.1', '192.168.0.2'))
        station.connect("home_ssid", "home_password")
        count = 0
        while not station.isconnected():
            sleep(1)
            print(station.status())
            count = count + 1
            if count==20:
                print("failed after 20 connects")
                return(1)
        print ("connected to home")
        return(0)
    except Exception as error:
        print("An error occurred:", type(error).__name__)
        return(1)

def disconnect_network():
    wdt.feed()
    try:
        station.disconnect()
        while station.isconnected():
            sleep(1)
        station.active(False)
        print('disconnected wifi')
        return(0)
    except:
        print("Error disconnecting")
        return(1)

def get_solax_data():
    wdt.feed()
    try:
        sleep(3)
        res = solax_json()
        print("Retrieved Data from Inverter")
        return res
    except Exception as error:
        print("An error occurred:", type(error).__name__)
        return(1)


def push_to_node_red(obj):
    wdt.feed()
    try:
        res = post("http://192.168.0.2:1880/update-sensor", headers = {'content-type': 'application/json'}, data = obj)
        print("Data Pushed to Node-Red")
        res.close()
    except Exception as error:
      print("An error occurred:", type(error).__name__)


def calculate_production(tele):
    wdt.feed()
    try:
        obj=loads(tele)
        production = obj["Data"][11] + obj["Data"][12]
        return production
    except Exception as error:
        print("An error occurred:", type(error).__name__)
        return 0

while True:
    arr = []
    for inv in sol:
        con = connect_to_inverter(inv)
        if con == 0:
            data = get_solax_data()
            if sol != 1:
                arr.append(data)
        else:
            print("Connection Failed - Skipping")
        disconnect_network()

    # connect to the iot network
    if len(arr) > 0:
        con = connect_to_home()
        sleep(3) # give it time to connect
        if con == 0:
            # push the results to node-red
            print("pushing to node-red")
            for entry in arr:
                push_to_node_red(entry)
                sleep(1)

            if len(arr) == 2 and type(arr[0]) == str and type(arr[1]) == str: # Calculate total production
                production = calculate_production(arr[0]) + calculate_production(arr[1])
                data = {
                    "SN" : "totalproduction",
                    "data": production
                    }
                push_to_node_red(dumps(data))
        else:
            print("Connection Failed - Skipping")
        disconnect_network()
    else:
        print("nothing to send")
