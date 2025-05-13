from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import signal
import sys

# 故意忽略SIGTERM信号
def ignore_sigterm(signum, frame):
    print("收到SIGTERM信号，但故意忽略")
    sys.stdout.flush()

signal.signal(signal.SIGTERM, ignore_sigterm)

class LongRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 记录请求开始
        request_id = self.headers.get('X-Request-ID', 'unknown')
        print(f"开始处理请求 {request_id}")
        sys.stdout.flush()

        # 模拟长时间处理 - 30秒
        time.sleep(30)

        # 返回结果
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"请求 {request_id} 成功完成".encode())
        print(f"完成处理请求 {request_id}")
        sys.stdout.flush()

httpd = HTTPServer(('', 8080), LongRequestHandler)
print("cpu_load_app 服务已启动在端口 8080")
sys.stdout.flush()
httpd.serve_forever()