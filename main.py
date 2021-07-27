# Two key things to optimise code:
# Put things into functions
# Assign methods to variables, eg blink=LED.Blink()
# Add error handling.

# Try adding error handling from here https://wiki.python.org/moin/HandlingExceptions under 'General Error Catching'

import network, urequests, time, ujson

# Initialise Wifi
station = network.WLAN(network.STA_IF)
station.active(True)
#
post = urequests.post
dumps = ujson.dumps
sleep = time.sleep
loads = ujson.loads

# SWQ = West array
# SW25 = East Array

sol = ["Solax_SW25", "Solax_SWQ"]

def connect_to_inverter(SSID):
    try:
        #connect to the wifi
        print("connecting to " + SSID)
        station.ifconfig(('5.8.8.10', '255.255.255.0', '5.8.8.8', '5.8.8.8'))
        station.connect(SSID, "")
        sleep(5)
        if station.isconnected() == True:
            return(0)
        else:
            return(1)
    except:
        print("something went wrong")
        return(1)


def connect_to_home():
    try:
        print("connecting to IOT Network")
        station.ifconfig(('192.168.0.95', '255.255.255.0', '192.168.0.1', '192.168.0.3'))
        station.connect("ssid", "pass")
        sleep(5)
        if station.isconnected() == True:
            return(0)
        else:
            return(1)
    except:
        print("something went wrong")
        return(1)

def disconnect_network():
    try:
        station.disconnect()
        sleep(1)
        print('disconnected wifi')
    except:
        print("Error disconnecting")
        return 1

def get_solax_data():
    try:
        res = post('http://5.8.8.8/?optType=ReadRealTimeData').text
        return res
    except:
        print("Error retrieving Solax Data")
        return 1

def push_to_node_red(obj):
    try:
        post("http://192.168.0.3:1880/update-sensor", headers = {'content-type': 'application/json'}, data = obj)
    except:
        print("Error Pushing to Node-Red")

def calculate_production(tele):
    obj=loads(tele)
    production = obj["Data"][11] + obj["Data"][12]
    return production

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
