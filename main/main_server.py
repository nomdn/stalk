from os import abort

import flask
import tomli_w
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import tomllib
import traceback

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

# 格式：[[服务器的名字,服务器ip:port（局域网也行）]]

PC_LIST = config["LISTS"]["PC_LIST"]
SERVER_LIST = config["LISTS"]["SERVER_LIST"]
refresh_password = config["PWD"]["refresh_password"]

app = flask.Flask(__name__)
CORS(app, origins=["http://localhost:8080", "http://192.168.0.107:8080" ,"http://192.168.0.105:8080","http://192.168.0.106:8080","http://192.168.0.105:8080","https://ern.wsmdn.top"])
@app.route("/get")
def info():
    type = request.args.get("type")
    id = request.args.get("id")
    if type=="pc":
        for i in PC_LIST:
            if id == i[0]:
                pc_ip=i[1]
                break

        else:
            return '404 Not Found'
        result = requests.get("http://"+pc_ip+"/status").json()
        return jsonify(result)
    elif type=="server":
        for i in SERVER_LIST:
            if id == i[0]:
                server_ip=i[1]
                break
        else:
            return '404 Not Found'
        result = requests.get("http://"+server_ip+"/status").json()
        return jsonify(result)
@app.route("/change")
def change_ips():
    id = request.args.get("id")
    new_ip = request.args.get("ip")
    type= request.args.get("type")
    password = request.args.get("pwd")
    if password == refresh_password:
        try:
            if type=="pc":
                for item in PC_LIST:
                    if item[0] == id:
                        PC_LIST.remove(item)
                        break
                PC_LIST.append([id,new_ip])
                print(PC_LIST)
                config["LISTS"]["PC_LIST"] = PC_LIST
                with open("config.toml", "wb") as f:
                    tomli_w.dump(config, f)
                return PC_LIST
            elif type=="server":
                for item in SERVER_LIST:
                    if item[0] == id:
                        SERVER_LIST.remove(item)
                        break
                SERVER_LIST.append([id, new_ip])
                print(SERVER_LIST)
                config["LISTS"]["SERVER_LIST"] = SERVER_LIST
                with open("config.toml", "wb") as f:
                    tomli_w.dump(config, f)
                return SERVER_LIST
        except Exception as e:

            return str(e)
    else:
        return '403'


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8090)

