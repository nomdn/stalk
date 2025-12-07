import platform

from IPython.core.hooks import clipboard_get
from flask import Flask, request, jsonify
import psutil
from flask_cors import CORS
import requests
mem = psutil.virtual_memory()
app = Flask(__name__)
import socket

api_addr = "http://api.wsmdn.top"
port = "5000"
pcid = "pc"
# 要开启剪贴板这个危险服务吗？
copy = False
# 要开启活动窗口这个危险服务吗？
active = True
def send_local_ip():

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip
requests.get(api_addr +f"/change?type=pc&id={pcid}&ip={send_local_ip()}:{port}&pwd=nmtxdix1145")

CORS(app, origins=["http://localhost:8080", "http://192.168.0.107:8080" ,"http://192.168.0.105:8080","http://192.168.0.106:8080","http://192.168.0.105:8080","https://ern.wsmdn.top"])
@app.route("/status")
def return_status():
    pc_system=platform.system()
    pc_version = platform.version()
    cpu_cores = psutil.cpu_count(logical=False)
    all_mem = round(mem.total/(1024**3),2)
    used_mem = round(mem.used / (1024 ** 3), 2)
    free_mem =round(mem.free/(1024**3),2)
    foreground_window=get_foreground_window()
    clipboard="啥也木有"
    if copy:
        clipboard=get_clipboard()
    status = {
        "pc_info":{
            "system":pc_system,
            "version":pc_version
        },
        "cpu_info":{
            "cores":cpu_cores
        },
        "mem_info":{
            "all":all_mem,
            "used":used_mem,
            "free":free_mem
        },
        "running_window":{
            "name":foreground_window["name"],
            "title":foreground_window["title"],
            "path":foreground_window["exe"]
        },
        "clipboard":clipboard
    }
    if not copy:
        status.pop("clipboard")
    if not active:
        status.pop("running_window")

    return jsonify(status)

def get_foreground_window():
    import win32gui
    import win32process

    hwnd = win32gui.GetForegroundWindow()
    if hwnd == 0:
        return None
    _,pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        process = psutil.Process(pid)
        return {
            'pid': pid,
            'name': process.name(),
            'exe': process.exe(),
            'title': win32gui.GetWindowText(hwnd)
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {'pid': pid, 'name': 'Unknown', 'title': win32gui.GetWindowText(hwnd)}

def get_clipboard():
    import win32clipboard
    win32clipboard.OpenClipboard()
    text = win32clipboard.GetClipboardData()
    win32clipboard.CloseClipboard()
    return text





if __name__ == "__main__":

    app.run(host="0.0.0.0")

