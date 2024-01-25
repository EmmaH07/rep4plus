"""
Author: Barak Gonen and Nir Dweck
EDITOR: Emma Harel
DATE 25.1.24
Description: HTTP server 4+
"""
import os
import re
import socket
import logging

QUEUE_SIZE = 10
IP = '0.0.0.0'
PORT = 80
SOCKET_TIMEOUT = 2
MAX_PACKET = 1
WEB_ROOT = 'webroot'
UPLOAD_FOLDER = 'webroot/uploads'
DEFAULT_URL = '\index.html'
REDIRECTION_DICTIONARY = {"/forbidden": "403 FORBIDDEN", "/error": "500 INTERNAL SERVER ERROR"}
MOVED_URI = '302 MOVED TEMPORARILY'
NOT_FOUND_URI = '404 NOT FOUND'
BAD_REQUEST = "400 BAD REQUEST"
CONTENT_TYPES = {
    '.html': 'text/html;charset=utf-8', '.jpg': 'image/jpeg',  '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.js': 'text/javascript; charset=UTF-8', '.css': 'text/css', '.txt': 'text/plain', '.ico': 'image/x-icon',
    '.gif': 'image/jpeg'
}
PIC404 = '404pic.png'

logging.basicConfig(filename='HTTP_server4plus.log', level=logging.DEBUG)


def get_file_data(file_name):
    """
    Get data from file
    :param file_name: the name of the file.
    :return: the file data in bytes.
    """
    file_path = WEB_ROOT + "\\" + file_name
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        return data
    except FileNotFoundError:
        logging.error(f"Error: File '{file_name}' not found.")
        return None  # Return None to indicate file not found
    except PermissionError:
        logging.error(f"Error: Permission denied to access file '{file_name}'.")
        return None  # Return None to indicate permission error
    except Exception as e:  # Catch any other unexpected errors
        logging.error(f"Error reading file '{file_name}': {str(e)}")
        return None  # Return None to signal an error


def handle_post(resource, client_socket, client_req):
    """
    Check the required resource, generate proper HTTP response and send
    to client
    :param resource: the required resource
    :param client_socket: a socket for the communication with the client.
    :param client_req: the client's request without the body.
    :return: None
    """
    uri = resource
    headers, length_header = client_req.split("Content-Length: ")
    length = str(length_header).split("\r\n")
    length = int(length[0])
    try:
        im_data = client_socket.recv(MAX_PACKET)
        while not len(im_data) == length:
            im_data += client_socket.recv(MAX_PACKET)

        if uri in REDIRECTION_DICTIONARY.keys():
            response = f"HTTP/1.1 {REDIRECTION_DICTIONARY[uri]}\r\n\r\n"

        elif 'upload' in client_req:
            func_name, par = uri.split('?')
            par_name, image_name = par.split("=")
            response = upload(im_data, image_name)

        else:
            response = f"HTTP/1.1 {BAD_REQUEST}\r\n\r\n"

        client_socket.sendall(response.encode())

    except KeyboardInterrupt:
        logging.error('received KeyboardInterrupt')

    except socket.error as err:
        logging.error('received socket exception - ' + str(err))

    finally:
        client_socket.close()


def handle_client_request(resource, client_socket):
    """
    Check the required resource, generate proper HTTP response and send
    to client
    :param resource: the required resource
    :param client_socket: a socket for the communication with the client
    :return: None
    """

    if resource == '/':
        uri = DEFAULT_URL
    else:
        uri = resource

    if uri in REDIRECTION_DICTIONARY.keys():
        response = f"HTTP/1.1 {REDIRECTION_DICTIONARY[uri]}\r\n\r\n"
        data = None

    elif uri == '/moved':
        response = f"HTTP/1.1 {MOVED_URI}\r\nLocation: {DEFAULT_URL}\r\n\r\n"
        data = None

    elif "calculate-next" in uri:
        func_name, par = uri.split('?')
        par_name, val = par.split("=")
        try:
            response_val = calculate_next(int(val))
            if response_val == BAD_REQUEST:
                response = f"HTTP/1.1 {BAD_REQUEST}\r\n\r\n"
                data = None
            else:
                response = (f"HTTP/1.1 200 OK\r\nContent-Type: 'text/plain'\r\nContent-Length: {len(response_val)}"
                            f"\r\n\r\n")
                data = response_val.encode()
        except ValueError as e:
            logging.error("received exception: " + str(e))
            response = f"HTTP/1.1 {BAD_REQUEST}\r\n\r\n"
            data = None

    elif "calculate-area" in uri:
        func_name, par = uri.split('?')
        val1, val2 = par.split("&")
        val1_name, height = val1.split('=')
        val2_name, width = val2.split("=")
        try:
            response_val = calculate_area(int(height), int(width))
            if response_val == BAD_REQUEST:
                response = f"HTTP/1.1 {BAD_REQUEST}\r\n\r\n"
                data = None
            else:
                response = (f"HTTP/1.1 200 OK\r\nContent-Type: 'text/plain'\r\nContent-Length: {len(response_val)}"
                            f"\r\n\r\n")
                data = response_val.encode()
        except ValueError as e:
            logging.error("received exception: " + str(e))
            response = f"HTTP/1.1 {BAD_REQUEST}\r\n\r\n"
            data = None
    elif 'image' in uri:
        func_name, par = uri.split('?')
        par_name, im_name = par.split('=')
        data = open_upload_im(im_name)
        if data is None:
            response = f"HTTP/1.1 {NOT_FOUND_URI}\r\n\r\n"
        else:
            filename, file_extension = im_name.split('.')
            if file_extension in CONTENT_TYPES.keys():
                content_type = CONTENT_TYPES[file_extension]
            else:
                content_type = 'application/octet-stream'  # Default content type

            response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(data)}\r\n\r\n"
    else:
        data = get_file_data(uri)

        if data is None:
            data = get_file_data(PIC404)
            if data is not None:
                response = (f"HTTP/1.1 {NOT_FOUND_URI}\r\nContent-Type: image/png\r\nContent-Length: {len(data)}\r\n"
                            f"Not Found\r\n\r\n")
            else:
                response = f"HTTP/1.1 {NOT_FOUND_URI}\r\nContent-Type: text/plain\r\nNot Found\r\n\r\n"

        else:
            filename, file_extension = os.path.splitext(uri)

            if file_extension in CONTENT_TYPES.keys():
                content_type = CONTENT_TYPES[file_extension]
            else:
                content_type = 'application/octet-stream'  # Default content type

            response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(data)}\r\n\r\n"

    if data is None:
        client_socket.sendall(response.encode())
        client_socket.close()
    else:
        client_socket.sendall(response.encode() + data)
        client_socket.close()


def validate_http_request(request):
    """
    Check if request is a valid HTTP request and returns TRUE / FALSE and
    the requested URL
    :param request: the request which was received from the client
    :return: a tuple of (True/False - depending on if the request is valid),
    the requested resource, and the type of the request (GET / POST)
    """
    http_pattern1 = r"^GET (.*) HTTP/1.1"
    http_pattern2 = r"^POST (.*) HTTP/1.1"  # Pattern to match the GET request and URL
    match = re.search(http_pattern1, request)

    if match:
        requested_url = match.group(1)
        return True, requested_url, 'GET'
    else:
        match = re.search(http_pattern2, request)
        if match:
            requested_url = match.group(1)
            return True, requested_url, 'POST'
    return False, BAD_REQUEST, 'NOT VALID'


def handle_client(client_socket):
    """
    Handles client requests: verifies client's requests are legal HTTP, calls
    function to handle the requests
    :param client_socket: the socket for the communication with the client
    :return: None
    """
    logging.debug('Client connected')
    try:
        while True:
            client_request = client_socket.recv(MAX_PACKET).decode()
            while not client_request.endswith("\r\n\r\n"):
                client_request += client_socket.recv(MAX_PACKET).decode()

                if client_request == '':
                    break
            valid_http, resource, req_type = validate_http_request(client_request)

            if valid_http:
                logging.debug('Got a valid HTTP request')
                if req_type == 'GET':
                    handle_client_request(resource, client_socket)
                elif req_type == 'POST':
                    handle_post(resource, client_socket, client_request)

            else:
                logging.error('Error: Not a valid HTTP request')
                response = f"HTTP/1.1 {BAD_REQUEST}\r\n\r\n"
                client_socket.sendall(response.encode())
                logging.debug('Closing connection')
                break

        if client_request == '':
            client_socket.close()

    except KeyboardInterrupt:
        logging.error('received KeyboardInterrupt')

    except socket.error as err:
        logging.error('received socket exception - ' + str(err))


def calculate_next(num):
    """
    The function calculates and returns the next number.
    :param num:
    :return: the next number
    """
    if type(num) == int:
        return_str = str(num+1)
    else:
        return_str = BAD_REQUEST
    return return_str


def calculate_area(height, width):
    """
    The function calculates and returns the triangle's area.
    :param height: the height of the triangle.
    :param width: the width of the triangle.
    :return: the triangle's area.
    """
    if type(height) == int and type(width) == int:
        return_str = str(height*width/2.0)
    else:
        return_str = BAD_REQUEST

    return return_str


def upload(file_bytes, file_name):
    """
    The function gets a file's data and name and saves it to the upload folder.
    :param file_bytes: the file's bytes.
    :param file_name: the name of the file
    :return: a 200OK response if the upload succeeded and a 400 BAD REQUEST otherwise.
    """
    try:
        file_path = UPLOAD_FOLDER + '//' + file_name
        with open(file_path, "wb") as binary_file:
            # Write bytes to file
            binary_file.write(file_bytes)
        return_str = f"HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        logging.error("received socket exception: " + str(e))
        return_str = f"HTTP/1.1 {BAD_REQUEST}\r\n\r\n"

    return return_str


def open_upload_im(im_name):
    """
    The function gets and returns an image from the upload folder.
    :param im_name: the name of the file.
    :return: the file's bytes if it is found or None if not.
    """
    file_path = UPLOAD_FOLDER + "//" + im_name
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        return data
    except FileNotFoundError:
        logging.error(f"Error: File '{im_name}' not found.")
        return None  # Return None to indicate file not found
    except PermissionError:
        logging.error(f"Error: Permission denied to access file '{im_name}'.")
        return None  # Return None to indicate permission error
    except Exception as e:  # Catch any other unexpected errors
        logging.error(f"Error reading file '{im_name}': {str(e)}")
        return None  # Return None to signal an error


# Main function
def main():
    """Starts the server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.bind((IP, PORT))
        server_socket.listen(QUEUE_SIZE)
        logging.debug("Listening for connections on port %d" % PORT)

        while True:
            client_socket, client_address = server_socket.accept()
            try:
                logging.debug('New connection received')
                client_socket.settimeout(SOCKET_TIMEOUT)
                handle_client(client_socket)
            except socket.error as err:
                logging.error('received socket exception - ' + str(err))
    except socket.error as err:
        logging.error('received socket exception - ' + str(err))
    finally:
        server_socket.close()


if __name__ == "__main__":
    assert validate_http_request("Get Falafel") == (False, "400 BAD REQUEST", 'NOT VALID')
    assert get_file_data('cyber') is None
    main()
