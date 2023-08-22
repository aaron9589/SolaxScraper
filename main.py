# Two key things to optimise code:
# Put things into functions
# Assign methods to variables, eg blink=LED.Blink()
# Add error handling.

# Try adding error handling from here https://wiki.python.org/moin/HandlingExceptions under 'General Error Catching'

import network, time, ujson, socket, ubinascii, machine
from machine import WDT
from umqttsimple import MQTTClient

# Initialise Wifi
station = network.WLAN(network.STA_IF)
station.active(True)

dumps = ujson.dumps
sleep = time.sleep
loads = ujson.loads

# Initialise Watchdog
wdt = WDT(timeout=30000) # 30s inactivity

#Array Wifi SSIDs
sol = ["Your_Array_SSID", "Your_Array_SSID"]

#MQTT Broker Info
broker = '192.168.0.2'
client_id = ubinascii.hexlify(machine.unique_id())
topic = b'/home/solar/espData'

def solax_json():
    wdt.feed()
    try:
        # Set the inverter config - shouldn't change
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
        del client_socket

        # Print the JSON string
        return json_data

    except Exception as error:
        print("An error occurred:", type(error).__name__) 
        return



def connect_to_inverter(SSID):
    wdt.feed()
    try:
        #station.active(True)
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
        print("connecting to IOT Network")
        #Found a Static IP works better
        station.ifconfig(('192.168.0.166', '255.255.255.0', '192.168.0.1', '192.168.0.2'))
        # connecting/DCing to this wifi with a password seems to be fraight with issues. have a
        # SSID with MAC filtering which keeps it accessible to this device only. YMMV
        station.connect("solar_in", "")
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
        #station.active(False)
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

def calculate_production(tele):
    wdt.feed()
    try:
        obj=loads(tele)
        production = obj["Data"][11] + obj["Data"][12]
        return production
    except Exception as error:
        print("An error occurred:", type(error).__name__)
        return 0
    
def post_array_via_mqtt(client_id, broker, topic, array):
    wdt.feed()
    try:
        # Connect to MQTT broker
        client = MQTTClient(client_id, broker, keepalive=30)
        client.connect()
        sleep(1)

        # Convert to byte array
        payload = bytes(array, 'utf-8')

        # Publish the JSON string to the specified topic
        client.publish(topic, payload)
        
        # Sleep for a bit before disconnecting
        sleep(5)

        # Disconnect from MQTT broker
        client.disconnect()
        del client
        print("Array posted via MQTT successfully.")
    except Exception as e:
        print("Error posting array via MQTT:", str(e))


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
            if len(arr) == 2 and type(arr[0]) == str and type(arr[1]) == str: # Calculate total production
                production = calculate_production(arr[0]) + calculate_production(arr[1])
                data = {
                    "SN" : "totalproduction",
                    "data": production
                    }
                arr.append(data)
            post_array_via_mqtt(client_id, broker, topic, dumps(arr))
        else:
            print("Connection Failed - Skipping")
        disconnect_network()
    else:
        # theres a good change both inverters are off. Sleep for 5 minutes, then push an empty value
        print("nothing to send - sleeping for 5 mins")
        count = 0
        while not count == 300:
            sleep(1)
            wdt.feed()
            count = count + 1
        con = connect_to_home()
        sleep(3) # give it time to connect
        if con == 0:
            # push the results to node-red
            print("pushing to node-red")
            data = [{
                "SN" : "status",
                "data": "offline"
                }]
            post_array_via_mqtt(client_id, broker, topic, dumps(data))
        else:
            print("Connection Failed - Skipping")
        disconnect_network()
        
