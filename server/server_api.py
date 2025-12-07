import platform
import socket

import requests
from flask import Flask, request, jsonify
import psutil
from flask_cors import CORS
mem = psutil.virtual_memory()
app = Flask(__name__)
api_addr = "http://localhost:8090"
port = "8090"
server_id = "ubuntu"
def send_local_ip():

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip
requests.get(api_addr +f"/change?type=pc&id={server_id}&ip={send_local_ip()}:{port}&pwd=nmtxdix1145")

CORS(app, origins=["http://localhost:8080", "http://192.168.0.107:8080" ,"http://192.168.0.105:8080","http://192.168.0.106:8080","http://192.168.0.105:8080","https://ern.wsmdn.top"])
@app.route("/status")
def return_status():
    pc_system=platform.system()
    pc_version = platform.version()
    cpu_cores = psutil.cpu_count(logical=False)
    cpu_used = psutil.cpu_percent(interval=0.5, percpu=False)
    all_mem = round(mem.total/(1024**3),2)
    used_mem = round(mem.used / (1024 ** 3), 2)
    free_mem =round(mem.free/(1024**3),2)
    dk = psutil.disk_usage('/')
    disk_used =round(dk.used / (1024 ** 3), 2)
    disk_free = round(dk.free / (1024 ** 3), 2)
    disk_all = round(dk.total / (1024 ** 3), 2)
    cpu_top_origin = get_top_cpu_usage()
    cpu_top=[]
    for items in cpu_top_origin:
        pid = items[0]
        name = items[1]
        usage = items[2]
        cpu_top.append([pid,name,usage])
    mem_top_origin = get_top_cpu_usage()
    mem_top=[]
    for items in mem_top_origin:
        pid = items[0]
        name = items[1]
        usage = items[2]
        mem_top.append([pid,name,usage])

    status = {
        "system_info":{
            "system":pc_system,
            "version":pc_version
        },
        "cpu_info":{
            "cores":cpu_cores,
            "used":cpu_used
        },
        "mem_info":{
            "all":all_mem,
            "used":used_mem,
            "free":free_mem
        },
        "disk_info":{
            "all":disk_all,
            "used":disk_used,
            "free":disk_free
        },
        "used":{
            "cpu":cpu_top,
            "mem":mem_top

        }

    }

    return jsonify(status)
import psutil
import time

def get_top_cpu_usage(num_processes=5):
    # 第一次遍历：初始化所有进程的 CPU 监控
    procs = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # 触发 cpu_percent() 初始化（返回 0，但启动计时）
            proc.cpu_percent()
            procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 等待采样时间（至少 0.1 秒）
    time.sleep(0.2)

    # 第二次遍历：获取真实 CPU%
    processes = []
    for proc in procs:
        try:
            name = proc.name()
            if not name or name in ('System Idle Process', 'Idle'):
                continue
            cpu = proc.cpu_percent()
            if cpu >= 0:  # 过滤无效值
                processes.append((proc.pid, name, round(cpu, 2)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 排序并返回 Top N
    processes.sort(key=lambda x: x[2], reverse=True)
    processes = [p for p in processes if p[2] > 0.1]
    return processes[:num_processes]


def get_top_mem_usage(num_processes=5):
    processes = []
    ignore_names = {'MemCompression', 'System', 'Registry', 'Idle'}

    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            name = proc.info['name']
            mem_pct = proc.info['memory_percent']
            if not name or name in ignore_names or mem_pct is None:
                continue
            processes.append((proc.info['pid'], name, round(mem_pct, 2)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda x: x[2], reverse=True)
    processes = [p for p in processes if p[2] > 0.1]
    return processes[:num_processes]

if __name__ == "__main__":

    app.run(host="0.0.0.0")