"""本地演示服务器：一个端口同时服务界面与更新包，并带上 CORS 头。

   /             -> hoyo-launcher-clone/src      （启动器界面）
   /sim/         -> update-sim               （v1 / v2 / dist 更新包）

带 CORS 是因为真实部署里 chunk 通常放在 CDN/R2 上，跨源必须发
Access-Control-Allow-Origin；这里先把这个前提模拟出来，
免得本地测试通过、上线才发现拉不到包。

用法: python serve.py [端口]
"""

import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899

SRC = r"F:\新建文件夹\hoyo-launcher-clone\src"
SIM = r"F:\新建文件夹\update-sim"

# 无缓存 + CORS + 支持 Range（大文件断点续传要用）
class H(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Range")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        SimpleHTTPRequestHandler.end_headers(self)

    def translate_path(self, path):
        # 注意：这里的 path 带着查询串（如 /?game=hk4e_cn），
        # 原生 http.server 会剥掉，自己实现就得手动剥，
        # 否则 ?page=hub 这类带参数的地址整个 404。
        path = path.split("?", 1)[0].split("#", 1)[0]
        # /sim/... 走更新包目录，其余走界面目录
        if path.startswith("/sim/"):
            return os.path.join(SIM, path[len("/sim/"):].replace("/", os.sep))
        return os.path.join(SRC, path.lstrip("/").replace("/", os.sep))

    def log_message(self, fmt, *args):
        # 静音，避免刷屏；需要排查时把下面这行注释掉
        pass


if __name__ == "__main__":
    os.chdir(SRC)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"界面   http://127.0.0.1:{PORT}/            -> {SRC}")
    print(f"更新包 http://127.0.0.1:{PORT}/sim/dist/   -> {SIM}")
    print("按 Ctrl+C 停止")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
