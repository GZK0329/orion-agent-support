#!/usr/bin/env python3
"""
简单的文件上传服务，支持流式写入大文件。
用法: python3 upload_server.py [端口] [目标目录]
"""

import http.server
import os
import re
import sys
import urllib.parse
import html

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
UPLOAD_DIR = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.getcwd()
CHUNK = 65536


def _fmt_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return "{:.1f} {}".format(size, unit)
        size /= 1024
    return "{:.1f} TB".format(size)


def _stream_upload(rfile, content_type, content_length, upload_dir):
    """流式解析 multipart，边读边写磁盘，不占内存。"""
    m = re.search(r'boundary=(?:"([^"]+)"|([^;\s]+))', content_type)
    if not m:
        return False
    boundary = m.group(1) or m.group(2)
    delim = b'--' + boundary.encode()
    delim_end = delim + b'--'

    remaining = content_length
    buf = b''
    file_written = False

    def _read_until(delimiter):
        """读到 delimiter 为止，返回之前的内容。"""
        nonlocal buf, remaining
        while True:
            idx = buf.find(delimiter)
            if idx != -1:
                data = buf[:idx]
                buf = buf[idx + len(delimiter):]
                return data
            if remaining <= 0:
                data = buf
                buf = b''
                return data
            chunk = rfile.read(min(CHUNK, remaining))
            if not chunk:
                data = buf
                buf = b''
                return data
            remaining -= len(chunk)
            buf += chunk

    # 跳过 preamble
    _read_until(delim)

    while True:
        # 读头部
        header_raw = _read_until(b'\r\n\r\n')
        if not header_raw:
            break
        headers_text = header_raw.decode(errors='replace')
        fn_match = re.search(r'filename="([^"]*)"', headers_text)
        if not fn_match:
            # 跳过非文件字段的内容
            _read_until(delim)
            continue

        filename = os.path.basename(fn_match.group(1))
        dest = os.path.join(upload_dir, filename)

        with open(dest + '.tmp', 'wb') as f:
            while True:
                idx = buf.find(delim)
                if idx != -1:
                    f.write(buf[:idx])
                    # 去掉末尾的 \r\n
                    buf = buf[idx:]
                    break
                f.write(buf)
                buf = b''
                if remaining <= 0:
                    break
                chunk = rfile.read(min(CHUNK, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                buf += chunk

        if os.path.getsize(dest + '.tmp') > 0:
            os.rename(dest + '.tmp', dest)
            print("[UPLOAD] {} ({})".format(filename, _fmt_size(os.path.getsize(dest))))
            file_written = True
        else:
            os.remove(dest + '.tmp')

        # 检查是否是结束 boundary
        if buf.startswith(delim_end) or buf.startswith(delim) and buf[len(delim):].startswith(b'--'):
            break
        # 跳过末尾的 \r\n
        if buf.startswith(b'\r\n'):
            buf = buf[2:]

    return file_written


class UploadHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print("[{}] {}".format(self.client_address[0], fmt % args))

    def _page(self):
        files = []
        for f in os.listdir(UPLOAD_DIR):
            fp = os.path.join(UPLOAD_DIR, f)
            if os.path.isfile(fp):
                files.append((f, _fmt_size(os.path.getsize(fp))))

        rows = ""
        if files:
            for name, size in files:
                rows += """<tr>
                    <td><a href="/download?name={name}">{name}</a></td>
                    <td>{size}</td>
                    <td><form method="post" action="/delete" style="display:inline">
                        <input type="hidden" name="name" value="{name}">
                        <button type="submit" style="color:red">删除</button>
                    </form></td>
                </tr>""".format(name=html.escape(name), size=size)
        else:
            rows = '<tr><td colspan="3" style="text-align:center;color:#999">暂无文件</td></tr>'

        return """<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>文件上传</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  * {{ box-sizing:border-box; margin:0; padding:0 }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:#f5f5f5; padding:20px }}
  .container {{ max-width:800px; margin:0 auto; background:#fff; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,.1); padding:24px }}
  h1 {{ font-size:20px; margin-bottom:16px }}
  .upload-box {{ border:2px dashed #ddd; border-radius:6px; padding:24px; text-align:center; margin-bottom:20px }}
  .upload-box.dragover {{ border-color:#007aff; background:#f0f7ff }}
  input[type=file] {{ margin:8px 0 }}
  button {{ background:#007aff; color:#fff; border:none; padding:8px 20px; border-radius:4px; cursor:pointer; font-size:14px }}
  button:hover {{ background:#005bbf }}
  table {{ width:100%; border-collapse:collapse }}
  th,td {{ text-align:left; padding:10px 8px; border-bottom:1px solid #eee }}
  th {{ font-size:13px; color:#666 }}
  .dir {{ font-size:12px; color:#999; margin-bottom:12px }}
  .msg {{ padding:10px 14px; border-radius:4px; margin-bottom:12px; display:none }}
  .msg.ok {{ background:#d4edda; color:#155724; display:block }}
  .msg.err {{ background:#f8d7da; color:#721c24; display:block }}
</style></head>
<body>
<div class="container">
  <h1>📂 文件上传</h1>
  <div class="dir">目标目录：<code>{dir}</code></div>
  <div id="msg" class="msg"></div>
  <div class="upload-box" id="dropZone">
    <form method="post" action="/upload" enctype="multipart/form-data" id="uploadForm">
      <input type="file" name="file" multiple required id="fileInput">
      <br><button type="submit">上传</button>
    </form>
  </div>
  <table><thead><tr><th>文件名</th><th>大小</th><th>操作</th></tr></thead><tbody>{rows}</tbody></table>
</div>
<script>
  const dz = document.getElementById('dropZone');
  const msg = document.getElementById('msg');
  dz.addEventListener('dragover', e => {{ e.preventDefault(); dz.classList.add('dragover') }});
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => {{ e.preventDefault(); dz.classList.remove('dragover');
    const dt = e.dataTransfer; const fi = dt.files;
    if (fi.length) {{ document.getElementById('fileInput').files = fi; document.getElementById('uploadForm').submit() }}
  }});
  (function() {{
    const s = new URLSearchParams(window.location.search);
    const v = s.get('status');
    if (v === 'ok') {{ msg.className = 'msg ok'; msg.textContent = '✅ 上传成功！'; setTimeout(() => msg.style.display='none', 3000); }}
    else if (v === 'err') {{ msg.className = 'msg err'; msg.textContent = '❌ 上传失败，请重试'; setTimeout(() => msg.style.display='none', 3000); }}
  }})();
</script>
</body></html>""".format(dir=html.escape(UPLOAD_DIR), rows=rows)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/download":
            qs = urllib.parse.parse_qs(parsed.query)
            name = qs.get("name", [None])[0]
            if name and ".." not in name and "/" not in name:
                fp = os.path.join(UPLOAD_DIR, name)
                if os.path.isfile(fp):
                    self.send_response(200)
                    self.send_header("Content-Disposition",
                                     'attachment; filename="{}"'.format(name))
                    self.send_header("Content-Length", str(os.path.getsize(fp)))
                    self.end_headers()
                    with open(fp, "rb") as f:
                        while True:
                            chunk = f.read(CHUNK)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                    return
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html;charset=utf-8")
        self.end_headers()
        self.wfile.write(self._page().encode())

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        ctype = self.headers.get("Content-Type", "")
        clen = int(self.headers.get("Content-Length", 0) or 0)

        if parsed.path == "/upload" and "multipart/form-data" in ctype:
            ok = _stream_upload(self.rfile, ctype, clen, UPLOAD_DIR)
            self._redirect("/?status=ok" if ok else "/?status=err")

        elif parsed.path == "/delete":
            body = self.rfile.read(min(clen, 4096))
            qs = urllib.parse.parse_qs(body.decode())
            name = qs.get("name", [None])[0]
            if name and ".." not in name and "/" not in name:
                fp = os.path.join(UPLOAD_DIR, name)
                if os.path.isfile(fp):
                    os.remove(fp)
                    print("[DELETE] {}".format(name))
            self._redirect("/")

        else:
            self.send_response(405)
            self.end_headers()

    def _redirect(self, path):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()


if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    server = http.server.HTTPServer(("0.0.0.0", PORT), UploadHandler)
    print("🚀 文件上传服务已启动")
    print("   地址: http://0.0.0.0:{}".format(PORT))
    print("   目录: {}".format(UPLOAD_DIR))
    print("   按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()
