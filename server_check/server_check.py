import requests,socket

def check_internet_connection():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except (socket.error, requests.ConnectionError):
        return False
    

def check_server_status():
    try:
        response = requests.get("http://192.168.68.80:3001")
        if response.status_code in (201, 200) :
            return True
        else:
            return False
    except requests.ConnectionError:
        return False
