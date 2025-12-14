import platform
import socket
import asyncio
import httpx
import uvicorn
from fastapi import FastAPI, Request, HTTPException
import psutil
from fastapi.middleware.cors import CORSMiddleware
import tomllib
from concurrent.futures import ThreadPoolExecutor
import time
import os

# =============== 全局配置 ===============
with open("config.toml", "rb") as f:
    config = tomllib.load(f)

GLOBAL = config["GLOBAL"]
CONFIG = config["CONFIG"]
POST_CONFIG = config.get("POST_CONFIG", {})

# 从配置中读取（注意：你的配置里 server_id 在 [CONFIG] 下！）
server_id = CONFIG["server_id"]
password = GLOBAL["password"]
api_addr = GLOBAL["api_addr"]

# =============== CORS 来源 ===============
# 你可以自定义，这里先允许所有（或从配置读）
origins = ["*"]  # 或从 config 读取

app = FastAPI(title="Stalk PC Status API", description="视奸PC客户端（Windows）")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============== 功能开关（注意：你的配置值是字符串 "True"/"False"）===============
copy_enabled = str(GLOBAL.get("copy", "False")).lower() == "true"
active_enabled = str(GLOBAL.get("active", "False")).lower() == "true"

# =============== 工具函数 ===============
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

# =============== Windows 特有功能（必须在 Windows 上运行）===============
def get_foreground_window():
    try:
        import win32gui
        import win32process
    except ImportError:
        return {'name': 'win32 not installed', 'title': '', 'exe': ''}

    hwnd = win32gui.GetForegroundWindow()
    if hwnd == 0:
        return {'name': 'None', 'title': '', 'exe': ''}
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        process = psutil.Process(pid)
        return {
            'name': process.name(),
            'title': win32gui.GetWindowText(hwnd),
            'exe': process.exe()
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {'name': 'Unknown', 'title': win32gui.GetWindowText(hwnd), 'exe': ''}

def get_clipboard():
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return data
    except:
        return "无法读取剪贴板"

def get_status_sync():
    """同步获取 PC 状态（可在 executor 中运行）"""
    mem = psutil.virtual_memory()
    pc_system = platform.system()
    pc_version = platform.version()
    cpu_cores = psutil.cpu_count(logical=False)
    all_mem = round(mem.total / (1024 ** 3), 2)
    used_mem = round(mem.used / (1024 ** 3), 2)
    free_mem = round(mem.free / (1024 ** 3), 2)

    status = {
        "pc_info": {
            "system": pc_system,
            "version": pc_version
        },
        "cpu_info": {
            "cores": cpu_cores
        },
        "mem_info": {
            "all": all_mem,
            "used": used_mem,
            "free": free_mem
        }
    }

    if active_enabled:
        fg = get_foreground_window()
        status["running_window"] = {
            "name": fg["name"],
            "title": fg["title"],
            "path": fg["exe"]
        }

    if copy_enabled:
        status["clipboard"] = get_clipboard()

    return status

# =============== 路由 ===============
executor = ThreadPoolExecutor(max_workers=2)

@app.get("/status")
async def return_status():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, get_status_sync)
    return result

# =============== 主动上报任务（POST 模式）===============
async def post_status_background():
    cooldown = int(POST_CONFIG.get("cooldown", 10))
    headers = {
        "password": password,
        "id": server_id,
        "type": "pc"
    }

    while True:
        try:
            loop = asyncio.get_running_loop()
            status = await loop.run_in_executor(executor, get_status_sync)

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url=f"{api_addr}/post",
                    json=status,
                    headers=headers
                )
                resp.raise_for_status()
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] PC status posted successfully.")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to post PC status: {e}")

        await asyncio.sleep(cooldown)

# =============== 启动入口 ===============
if __name__ == '__main__':
    config_enable = str(CONFIG.get("enable", "False")).lower() == "true"
    post_enable = str(POST_CONFIG.get("enable", "False")).lower() == "true"

    if config_enable and post_enable:
        print("WARN: Both CONFIG.enable and POST_CONFIG.enable are True. Running as server + reporter.")

    if config_enable:
        port = int(CONFIG.get("port", 8090))
        print(f"Starting PC API server on http://0.0.0.0:{int(port)}/status")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    elif post_enable:
        print(f"Starting PC status reporter for '{server_id}'...")
        print(f"Posting to: {api_addr}/post every {POST_CONFIG.get('cooldown', 10)} seconds")
        asyncio.run(post_status_background())

    else:
        print("ERROR: Both CONFIG.enable and POST_CONFIG.enable are False.")
        print("Please set one of them to \"True\" in config.toml")