from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib
import socket
import threading
import socket
import logging
import json
import os
from datetime import datetime

PORT_HTTP = 3000
UDP_IP = '127.0.0.1'
UDP_PORT = 5000


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='server.log')


# http handler


class HttpHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        print(self.path)
        pr_url = urllib.parse.urlparse(self.path)
        print(pr_url)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())

    def forward_to_socket(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, (UDP_IP, UDP_PORT))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        data = self.rfile.read(content_length)
        print(data)
        self.forward_to_socket(data)
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()


# run http_server


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', PORT_HTTP)
    http = server_class(server_address, handler_class)
    try:
        logging.info(f'Starting HTTP server on port {PORT_HTTP}...')
        http.serve_forever()
    except KeyboardInterrupt:
        logging.info("HTTP server interrupted. Shutting down...")
        http.server_close()
    except Exception as e:
        logging.error(f"Error occurred in HTTP server: {e}")

# socket server


def run_udp_socket_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    sock.bind(server)

    try:
        logging.info(f'Starting UDP socket server on {ip}:{port}...')
        while True:
            try:
                data, address = sock.recvfrom(1024)
                logging.info(f'Received data: {data.decode()} from: {address}')
                sock.sendto(data, address)
                logging.info(f'Send data: {data.decode()} to: {address}')
                try:
                    decoded_data = urllib.parse.unquote_plus(data.decode())
                    data_dict = {key: value for key, value in [
                        el.split('=') for el in decoded_data.split('&')]}

                    logging.info(f'Decoded JSON data: {decoded_data}')
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logging.error(f'Error decoding JSON data: {e}')
                    continue
            except ConnectionResetError:
                logging.error("Connection reset by remote host")
                continue

            existing_data = []
            dir_for_json = "storage"
            if not os.path.exists(dir_for_json):
                os.makedirs(dir_for_json)
            file_path = os.path.join(dir_for_json, 'data.json')
            try:
                with open(file_path, "r") as file:
                    existing_data = json.load(file)

            except FileNotFoundError:
                logging.error("File not found.")

            date = datetime.now()
            new_entry = {str(date): data_dict}
            existing_data.append(new_entry)

            try:
                with open(file_path, "w") as outfile:
                    json.dump(existing_data, outfile, indent=4)

            except Exception as e:
                logging.error(
                    f"Error occurred while writing JSON to file: {e}")

    except KeyboardInterrupt:
        logging.info("UDP socket server interrupted. Shutting down...")
    except Exception as e:
        logging.error(f"Error occurred in UDP socket server: {e}")
    finally:
        sock.close()


if __name__ == '__main__':
    socket_server = threading.Thread(
        target=run_udp_socket_server, args=(UDP_IP, UDP_PORT),  name="socket_server")
    http_server = threading.Thread(target=run_http_server,  name="HTTPServer")

    http_server.start()
    socket_server.start()
    http_server.join()
    socket_server.join()
