# wsgi.py
from pc_api import app  # 假设你的 Flask 实例叫 app，在 main_server.py 中

if __name__ == "__main__":
    from waitress import serve
    # 监听所有 IP，端口 8090
    serve(app, host="0.0.0.0", port=5000, threads=4)