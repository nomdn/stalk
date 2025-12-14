import platform
import socket


import asyncio
import httpx
import uvicorn

from fastapi import FastAPI
import psutil
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "*"
]
import psutil
import time
http_client = httpx.AsyncClient()



app = FastAPI(title="Stalk Server Status API",
description="视奸服务器Server部分")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
import tomllib

with open("config.toml","rb") as f:
    config = tomllib.load(f)
server_id = config["GLOBAL"]["server_id"]

async def send_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip
async def send_public_ip(type):
    ip=""
    try:
        if type=="ipv6":
            ip = await http_client.get("https://api6.ipify.org/").text.strip()
            ip = "["+ip+"]"
        elif type=="ipv4":
            ip = await http_client.get('https://checkip.amazonaws.com').text.strip()

    except:
        ip = ""

    return ip
async def synchronize():
    api_addr = config["GLOBAL"]["api_addr"]
    server_id = config["GLOBAL"]["server_id"]
    port = config["CONFIG"]["port"]
    password = config["GLOBAL"]["password"]
    try:
        if config["CONFIG"]["public_network"] == "True":
            if config["CONFIG"]["domain_enable"] == "True":
                await http_client.get(api_addr + f"/change?type=pc&id={server_id}&ip={config["CONFIG"]["domain"]}&pwd={password}")
            else:
                ip_type = config["CONFIG"]["ip"]
                await http_client.get(api_addr +f"/change?type=pc&id={server_id}&ip={await send_public_ip(ip_type)}:{port}&pwd={password}")
        elif config["CONFIG"]["public_network"] == "False":
            if config["CONFIG"]["domain_enable"] == "True":
                await http_client.get(api_addr + f"/change?type=pc&id={server_id}&ip={config["CONFIG"]["domain"]}&pwd={password}")
            else:
                await http_client.get(api_addr + f"/change?type=pc&id={server_id}&ip={await send_local_ip()}:{port}&pwd={password}")
    except Exception as e:
        return f"ERROR:同步失败！{e}"
    return "OK"
def get_status():
    mem = psutil.virtual_memory()
    pc_system = platform.system()
    pc_version = platform.version()
    cpu_cores = psutil.cpu_count(logical=False)
    cpu_used = psutil.cpu_percent(interval=0.5, percpu=False)
    all_mem = round(mem.total / (1024 ** 3), 2)
    used_mem = round(mem.used / (1024 ** 3), 2)
    free_mem = round(mem.free / (1024 ** 3), 2)
    dk = psutil.disk_usage('/')
    disk_used = round(dk.used / (1024 ** 3), 2)
    disk_free = round(dk.free / (1024 ** 3), 2)
    disk_all = round(dk.total / (1024 ** 3), 2)
    cpu_top_origin = get_top_cpu_usage()
    cpu_top = []
    for items in cpu_top_origin:
        pid = items[0]
        name = items[1]
        usage = items[2]
        cpu_top.append([pid, name, usage])
    mem_top_origin = get_top_mem_usage()
    mem_top = []
    for items in mem_top_origin:
        pid = items[0]
        name = items[1]
        usage = items[2]
        mem_top.append([pid, name, usage])

    status = {
        "system_info": {
            "system": pc_system,
            "version": pc_version
        },
        "cpu_info": {
            "cores": cpu_cores,
            "used": cpu_used
        },
        "mem_info": {
            "all": all_mem,
            "used": used_mem,
            "free": free_mem
        },
        "disk_info": {
            "all": disk_all,
            "used": disk_used,
            "free": disk_free
        },
        "used": {
            "cpu": cpu_top,
            "mem": mem_top

        }

    }
    return status
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
@app.get("/status")
async def return_status():

    return get_status()
async def post_status():
    api_addr = config["GLOBAL"]["api_addr"]
    cooldown = config["POST_CONFIG"]["cooldown"]
    headers = {
        "password": config["GLOBAL"]["password"],
        "id": server_id,
        "type": "server"
    }

    while True:
        try:
            # 每次新建 client 或复用（这里用 with 确保关闭）
            async with httpx.AsyncClient(timeout=10.0) as client:
                status = get_status()  # ← 实时获取！
                resp = await client.post(
                    url=f"{api_addr}/post",
                    json=status,
                    headers=headers
                )
                resp.raise_for_status()
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status posted successfully.")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to post status: {e}")

        await asyncio.sleep(cooldown)

if __name__ == '__main__':
    if config["CONFIG"]["enable"] == "True":
        port = config["CONFIG"]["port"]
        asyncio.run(synchronize())
        uvicorn.run("server_api:app", host="0.0.0.0", port=int(port), log_level="info")
    elif config["POST_CONFIG"]["enable"] == "True":
        asyncio.run(post_status())
