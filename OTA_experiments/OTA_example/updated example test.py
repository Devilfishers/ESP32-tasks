import http.server
import multiprocessing
import os
import re
import socket
import ssl
import sys

import pytest
from pytest_embedded import Dut

server_cert = "-----BEGIN CERTIFICATE-----\n" \
              "MIIDmzCCAoOgAwIBAgIUMz1nBZ5KoZbyC+3O1SFoqc4Ysz0wDQYJKoZIhvcNAQEL\n"\
              "BQAwXTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM\n"\
              "GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDEWMBQGA1UEAwwNMTkyLjE2OC40My42\n"\
              "MjAeFw0yNDAzMjUwNTM3NDdaFw0yNTAzMjUwNTM3NDdaMF0xCzAJBgNVBAYTAkFV\n"\
              "MRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRz\n"\
              "IFB0eSBMdGQxFjAUBgNVBAMMDTE5Mi4xNjguNDMuNjIwggEiMA0GCSqGSIb3DQEB\n"\
              "AQUAA4IBDwAwggEKAoIBAQDXLn+Kh+pTmgh1X0W5tPu6ZcUdTJoLZD6O8RLO5uch\n"\
              "RXaX014AZwuc0mxM2EagpKZsiRyGuyNrBUIV4T3i7mdN6jUOAG4IZNepZ6X6AsvL\n"\
              "GNc3A5Oe8zOpBV970Y0fNsl3PnjbixFY9WG9IdAg3XXh7sJlOIh+c75tyJnjGjIJ\n"\
              "FvK3GEpsWtc9+oEXOjGJDakgMxcfiN0i7kLjgbSVcchCdGC2CxmZWHQ4b4Q5T+6u\n"\
              "Ig8HD5gTi0gQpNAPn024kEd1gz3N+tNVx9127LVnqYQ+UwvL/ntBml3psd2BpOIU\n"\
              "Op2L4pc7lx3SX5CNw8PzSvkx/m5FD6J7K8i+kh7BHWLrAgMBAAGjUzBRMB0GA1Ud\n"\
              "DgQWBBTs+N96EYJ68l5JruvMhyVMFnaDITAfBgNVHSMEGDAWgBTs+N96EYJ68l5J\n"\
              "ruvMhyVMFnaDITAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAA\n"\
              "zHTbhAHul4a1iepi03e6xiVJM9jtU5ghgsEqBAcR0vmIKtLh8DclgvmBaZv/o+os\n"\
              "bBkj8pscMYIgcXSVL2HZRokAZiYIAkowmGKRcJhx1cDJX/sFCx7dETJDnzJHAskl\n"\
              "XKh1DFrJH/Go5/3g9+u9fXXXvI9Il7A0qA9vyvKmFE/AfIgr+zKmhEs6umBfuz11\n"\
              "Sr+ukTXnrvVZCNxcFuKwCAJfWZFb5aQuHWX2IJY84Ow9Ej51i6zPha08EbYGBT/5\n"\
              "69/gepjZjskI3zHMAeLa6+QJhxTUzn/JmPmA0edYsswPXiwpSc+QGuqp4CjYsn8Y\n"\
              "0lYMeNL0eeCG3DHaYcf7\n"\
              "-----END CERTIFICATE-----\n",

server_key = "-----BEGIN PRIVATE KEY-----\n"\
             "MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDXLn+Kh+pTmgh1\n"\
             "X0W5tPu6ZcUdTJoLZD6O8RLO5uchRXaX014AZwuc0mxM2EagpKZsiRyGuyNrBUIV\n"\
             "4T3i7mdN6jUOAG4IZNepZ6X6AsvLGNc3A5Oe8zOpBV970Y0fNsl3PnjbixFY9WG9\n"\
             "IdAg3XXh7sJlOIh+c75tyJnjGjIJFvK3GEpsWtc9+oEXOjGJDakgMxcfiN0i7kLj\n"\
             "gbSVcchCdGC2CxmZWHQ4b4Q5T+6uIg8HD5gTi0gQpNAPn024kEd1gz3N+tNVx912\n"\
             "7LVnqYQ+UwvL/ntBml3psd2BpOIUOp2L4pc7lx3SX5CNw8PzSvkx/m5FD6J7K8i+\n"\
             "kh7BHWLrAgMBAAECggEAZOfopkFTOM4QLl41d77vlrq3oyQzTqk9DtHsxHqSI0+M\n"\
             "K+lR+PVZhDpG0AhRom5jnpzzdBjYpIyML293Em5Cok50f7Li5mvHmCjDNAjQoVZu\n"\
             "Qd2bAZxBev7Khmk/eMY71n/EtAs0YNd89HChRXAkogTRQx8uHsJPJ/M8ertjgE/W\n"\
             "MxDzT/z7wSdYczCZYPDbeK5aDsR023wJ9b6eEk6/U4Bl/ZsyjwCPjeJudeVv2ztJ\n"\
             "DVxEfuuEQ+k/eyYg7yTxBx8NoCpCIsvAyaotC9sQ9Jgmka09v6p9aGDuRq9XeIIz\n"\
             "WeuhZtwePfUJL5mjQ2nUoXsfUlta1AXvMpR8+REW0QKBgQD+/AxW896+NuM73Myb\n"\
             "djGhAOGzUYlQOHHLmGwH7LlafQCU1XrWzYx16gFH4xFa0nc4v2VOQN9smNHQ3D2z\n"\
             "rx/Mt1khLMaSHXoUHtaIRF86p1VlRkweEBfK0m4THy/+t3D/h4K6S4FvBClDxtlA\n"\
             "UhpNd8hIKMc5oHaDaeWWDDIvkQKBgQDYCd8nVEfFbV+aRcKzdhzsN3nqzp1SnXws\n"\
             "xoJArKl4pNr6vt8aO1RjLaPQr7E2T7gLw+qHtFvJ0DegroN5h/n2uJUv4e7TixRV\n"\
             "jNtsaF2EyhTm857I/fIahBruT4i9wygwMsF4e6LWSN9UduRK+AzBgfHeteXl686p\n"\
             "rnTrL+BkuwKBgQDiYFN0Pz7aEVDcrMLaoqydDHNVCGaoWfRtlP0UbA6DT8dcW8ub\n"\
             "ORIi/YX1lJqrz38ZWpNOTjoN5/8fNulwxWGuFnmDAoWo45KmmlpM0KbbJASkzSx2\n"\
             "5EK7RueDAoVR1vrzYhOl4bMgJMmd6sSmXj4L2PRvXATEHLobIcE63ckQgQKBgQCz\n"\
             "fNgjA9mxRGKGeOj/UuVKt/iZxdldVyxgwvhapVkTu9uXMdeIIrzEvZl5e06/MdJW\n"\
             "LAqBfq436L8ex37CDN/3RHnmU06qAMX/Icz3r2nrNj3Rd5x3nsxzjUgWsIuKJUcR\n"\
             "bEnjQM0UPW0W7sRTKOzoJH8AKp37vUNxJFlNQPSsmwKBgQDuypqYR9/4GJTW85Oe\n"\
             "qK6e7OPwzerp2b7YcYqYEzKK9wAVojONjBuaqUxE5dvZ4Ck7FwLyjF2LubCvhqc8\n"\
             "daa7ro/ch+maoiA2zextroK8eFvOOwwjIPLcQGWqewFDVKnyEysPB7kIMWNHNz62\n"\
             "aKeERiD//ZKXxMzsD7NximQtHQ==\n"\
             "-----END PRIVATE KEY-----\n",


def get_my_ip():
    s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s1.connect(('8.8.8.8', 80))
    my_ip = s1.getsockname()[0]
    s1.close()
    return my_ip


def get_server_status(host_ip, server_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_status = sock.connect_ex((host_ip, server_port))
    sock.close()
    if server_status == 0:
        return True
    return False


def start_https_server(ota_image_dir, server_ip, server_port, server_file=None, key_file=None):
    os.chdir(ota_image_dir)

    if server_file is None:
        server_file = os.path.join(ota_image_dir, 'server_cert.pem')
        cert_file_handle = open(server_file, 'w+')
        cert_file_handle.write(server_cert)
        cert_file_handle.close()

    if key_file is None:
        key_file = os.path.join(ota_image_dir, 'server_key.pem')
        key_file_handle = open('server_key.pem', 'w+')
        key_file_handle.write(server_key)
        key_file_handle.close()

    httpd = http.server.HTTPServer((server_ip, server_port), http.server.SimpleHTTPRequestHandler)

    httpd.socket = ssl.wrap_socket(httpd.socket,
                                   keyfile=key_file,
                                   certfile=server_file, server_side=True)
    httpd.serve_forever()


def check_sha256(sha256_expected, sha256_reported):
    print('sha256_expected: %s' % (sha256_expected))
    print('sha256_reported: %s' % (sha256_reported))
    if sha256_reported not in sha256_expected:
        raise ValueError('SHA256 mismatch')
    else:
        print('SHA256 expected and reported are the same')


def calc_all_sha256(dut):
    bootloader_path = os.path.join(dut.app.binary_path, 'bootloader', 'bootloader.bin')
    output = dut.image_info(bootloader_path)
    sha256_bootloader = re.search(r'Validation Hash:\s+([a-f0-9]+)', output).group(1)
    print('bootloader SHA256: %s' % sha256_bootloader)

    app_path = os.path.join(dut.app.binary_path, 'simple_ota.bin')
    output = dut.image_info(app_path)
    sha256_app = re.search(r'Validation Hash:\s+([a-f0-9]+)', output).group(1)
    print('app SHA256: %s' % sha256_app)

    return sha256_bootloader, sha256_app


@pytest.mark.esp32
@pytest.mark.esp32c3
@pytest.mark.esp32s3
@pytest.mark.wifi_high_traffic
def test_examples_protocol_simple_ota_example(env, extra_data):
    """
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut('simple_ota_example', 'examples/system/ota/simple_ota_example', dut_class=ttfw_idf.ESP32DUT)
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, 'simple_ota.bin')
    bin_size = os.path.getsize(binary_file)
    #ttfw_idf.log_performance('simple_ota_bin_size', '{}KB'.format(bin_size // 1024))
    sha256_bootloader, sha256_app = calc_all_sha256(dut1)
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, 8000) is False):
        thread1 = multiprocessing.Process(target=start_https_server, args=(dut1.app.binary_path, host_ip, 8000))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect('Loaded app from partition at offset 0x10000', timeout=30)
    check_sha256(sha256_bootloader, dut1.expect(re.compile(r'SHA-256 for bootloader:\s+([a-f0-9]+)'))[0])
    check_sha256(sha256_app, dut1.expect(re.compile(r'SHA-256 for current firmware:\s+([a-f0-9]+)'))[0])
    try:
        ip_address = dut1.expect(re.compile(r' sta ip: ([^,]+),'), timeout=30)
        print('Connected to AP with IP: {}'.format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
        thread1.terminate()
    dut1.expect('Starting OTA example', timeout=30)

    print('writing to device: {}'.format('https://' + host_ip + ':8000/simple_ota.bin'))
    dut1.write('https://' + host_ip + ':8000/simple_ota.bin')
    dut1.expect('Loaded app from partition at offset 0x110000', timeout=60)
    dut1.expect('Starting OTA example', timeout=30)
    thread1.terminate()


@pytest.mark.esp32
@pytest.mark.ethernet_ota
@pytest.mark.parametrize('config', ['spiram',], indirect=True)
def test_examples_protocol_simple_ota_example_ethernet_with_spiram_config(env, extra_data):
    """
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut('simple_ota_example', 'examples/system/ota/simple_ota_example', dut_class=ttfw_idf.ESP32DUT, app_config_name='spiram')
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, 'simple_ota.bin')
    bin_size = os.path.getsize(binary_file)
    #ttfw_idf.log_performance('simple_ota_bin_size', '{}KB'.format(bin_size // 1024))
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, 8000) is False):
        thread1 = multiprocessing.Process(target=start_https_server, args=(dut1.app.binary_path, host_ip, 8000))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect('Loaded app from partition at offset 0x10000', timeout=30)
    try:
        ip_address = dut1.expect(re.compile(r' eth ip: ([^,]+),'), timeout=30)
        print('Connected to AP with IP: {}'.format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
        thread1.terminate()
    dut1.expect('Starting OTA example', timeout=30)

    print('writing to device: {}'.format('https://' + host_ip + ':8000/simple_ota.bin'))
    dut1.write('https://' + host_ip + ':8000/simple_ota.bin')
    dut1.expect('Loaded app from partition at offset 0x110000', timeout=60)
    dut1.expect('Starting OTA example', timeout=30)
    thread1.terminate()


def test_examples_protocol_simple_ota_example_with_flash_encryption(env, extra_data):
    """
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut('simple_ota_example', 'examples/system/ota/simple_ota_example', dut_class=ttfw_idf.ESP32DUT, app_config_name='flash_enc')
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, 'simple_ota.bin')
    bin_size = os.path.getsize(binary_file)
    #ttfw_idf.log_performance('simple_ota_bin_size', '{}KB'.format(bin_size // 1024))
    # erase flash on the device
    print('Erasing the flash in order to have an empty NVS key partiton')
    dut1.erase_flash()
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, 8000) is False):
        thread1 = multiprocessing.Process(target=start_https_server, args=(dut1.app.binary_path, host_ip, 8000))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect('Loaded app from partition at offset 0x20000', timeout=30)
    dut1.expect('Flash encryption mode is DEVELOPMENT (not secure)', timeout=10)
    try:
        ip_address = dut1.expect(re.compile(r' eth ip: ([^,]+),'), timeout=30)
        print('Connected to AP with IP: {}'.format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
        thread1.terminate()
    dut1.expect('Starting OTA example', timeout=30)

    print('writing to device: {}'.format('https://' + host_ip + ':8000/simple_ota.bin'))
    dut1.write('https://' + host_ip + ':8000/simple_ota.bin')
    dut1.expect('Loaded app from partition at offset 0x120000', timeout=60)
    dut1.expect('Flash encryption mode is DEVELOPMENT (not secure)', timeout=10)
    dut1.expect('Starting OTA example', timeout=30)
    thread1.terminate()


@pytest.mark.esp32
@pytest.mark.esp32c3
@pytest.mark.flash_encryption_wifi_high_traffic
@pytest.mark.nightly_run
@pytest.mark.parametrize('config', ['flash_enc_wifi',], indirect=True)
@pytest.mark.parametrize('skip_autoflash', ['y'], indirect=True)
def test_examples_protocol_simple_ota_example_with_flash_encryption_wifi(env, extra_data):
    """
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut('simple_ota_example', 'examples/system/ota/simple_ota_example', app_config_name='flash_enc_wifi')
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, 'simple_ota.bin')
    bin_size = os.path.getsize(binary_file)
    #ttfw_idf.log_performance('simple_ota_bin_size', '{}KB'.format(bin_size // 1024))
    # erase flash on the device
    print('Erasing the flash in order to have an empty NVS key partiton')
    dut1.erase_flash()
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, 8000) is False):
        thread1 = multiprocessing.Process(target=start_https_server, args=(dut1.app.binary_path, host_ip, 8000))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect('Loaded app from partition at offset 0x20000', timeout=30)
    dut1.expect('Flash encryption mode is DEVELOPMENT (not secure)', timeout=10)
    try:
        ip_address = dut1.expect(re.compile(r' sta ip: ([^,]+),'), timeout=30)
        print('Connected to AP with IP: {}'.format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
        thread1.terminate()
    dut1.expect('Starting OTA example', timeout=30)

    print('writing to device: {}'.format('https://' + host_ip + ':8000/simple_ota.bin'))
    dut1.write('https://' + host_ip + ':8000/simple_ota.bin')
    dut1.expect('Loaded app from partition at offset 0x120000', timeout=60)
    dut1.expect('Flash encryption mode is DEVELOPMENT (not secure)', timeout=10)
    dut1.expect('Starting OTA example', timeout=30)
    thread1.terminate()


@pytest.mark.esp32
@pytest.mark.ethernet_ota
@pytest.mark.parametrize('config', ['on_update_no_sb_ecdsa',], indirect=True)
def test_examples_protocol_simple_ota_example_with_verify_app_signature_on_update_no_secure_boot_ecdsa(env, extra_data):
    """
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut('simple_ota_example', 'examples/system/ota/simple_ota_example', dut_class=ttfw_idf.ESP32DUT,
                       app_config_name='on_update_no_sb_ecdsa')
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, 'simple_ota.bin')
    bin_size = os.path.getsize(binary_file)
    #ttfw_idf.log_performance('simple_ota_bin_size', '{}KB'.format(bin_size // 1024))
    sha256_bootloader, sha256_app = calc_all_sha256(dut1)
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, 8000) is False):
        thread1 = multiprocessing.Process(target=start_https_server, args=(dut1.app.binary_path, host_ip, 8000))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect('Loaded app from partition at offset 0x20000', timeout=30)
    check_sha256(sha256_bootloader, dut1.expect(re.compile(r'SHA-256 for bootloader:\s+([a-f0-9]+)'))[0])
    check_sha256(sha256_app, dut1.expect(re.compile(r'SHA-256 for current firmware:\s+([a-f0-9]+)'))[0])
    try:
        ip_address = dut1.expect(re.compile(r' eth ip: ([^,]+),'), timeout=30)
        print('Connected to AP with IP: {}'.format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
        thread1.terminate()
    dut1.expect('Starting OTA example', timeout=30)

    print('writing to device: {}'.format('https://' + host_ip + ':8000/simple_ota.bin'))
    dut1.write('https://' + host_ip + ':8000/simple_ota.bin')
    dut1.expect('Writing to partition subtype 16 at offset 0x120000', timeout=20)

    dut1.expect('Verifying image signature...', timeout=60)

    dut1.expect('Loaded app from partition at offset 0x120000', timeout=20)
    dut1.expect('Starting OTA example', timeout=30)
    thread1.terminate()


@pytest.mark.esp32
@pytest.mark.ethernet_ota
@pytest.mark.parametrize('config', ['on_update_no_sb_rsa',], indirect=True)
def test_examples_protocol_simple_ota_example_with_verify_app_signature_on_update_no_secure_boot_rsa(env, extra_data):
    """
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut('simple_ota_example', 'examples/system/ota/simple_ota_example', dut_class=ttfw_idf.ESP32DUT,
                       app_config_name='on_update_no_sb_rsa')
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, 'simple_ota.bin')
    bin_size = os.path.getsize(binary_file)
    #ttfw_idf.log_performance('simple_ota_bin_size', '{}KB'.format(bin_size // 1024))
    sha256_bootloader, sha256_app = calc_all_sha256(dut1)
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, 8000) is False):
        thread1 = multiprocessing.Process(target=start_https_server, args=(dut1.app.binary_path, host_ip, 8000))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect('Loaded app from partition at offset 0x20000', timeout=30)
    check_sha256(sha256_bootloader, dut1.expect(re.compile(r'SHA-256 for bootloader:\s+([a-f0-9]+)'))[0])
    check_sha256(sha256_app, dut1.expect(re.compile(r'SHA-256 for current firmware:\s+([a-f0-9]+)'))[0])
    try:
        ip_address = dut1.expect(re.compile(r' eth ip: ([^,]+),'), timeout=30)
        print('Connected to AP with IP: {}'.format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
        thread1.terminate()
    dut1.expect('Starting OTA example', timeout=30)

    print('writing to device: {}'.format('https://' + host_ip + ':8000/simple_ota.bin'))
    dut1.write('https://' + host_ip + ':8000/simple_ota.bin')
    dut1.expect('Writing to partition subtype 16 at offset 0x120000', timeout=20)

    dut1.expect('Verifying image signature...', timeout=60)
    dut1.expect('#0 app key digest == #0 trusted key digest', timeout=10)
    dut1.expect('Verifying with RSA-PSS...', timeout=10)
    dut1.expect('Signature verified successfully!', timeout=10)

    dut1.expect('Loaded app from partition at offset 0x120000', timeout=20)
    dut1.expect('Starting OTA example', timeout=30)
    thread1.terminate()


if __name__ == '__main__':
    if sys.argv[2:]:    # if two or more arguments provided:
        # Usage: example_test.py <image_dir> <server_port> [cert_di>]
        this_dir = os.path.dirname(os.path.realpath(__file__))
        bin_dir = os.path.join(this_dir, sys.argv[1])
        port = int(sys.argv[2])
        cert_dir = bin_dir if not sys.argv[3:] else os.path.join(this_dir, sys.argv[3])  # optional argument
        print('Starting HTTPS server at "https://:{}"'.format(port))
        start_https_server(bin_dir, '', port,
                           server_file=os.path.join(cert_dir, 'server.crt'),
                           key_file=os.path.join(cert_dir, 'server.key'))
    else:
        test_examples_protocol_simple_ota_example()
        test_examples_protocol_simple_ota_example_ethernet_with_spiram_config()
        test_examples_protocol_simple_ota_example_with_flash_encryption()
        test_examples_protocol_simple_ota_example_with_flash_encryption_wifi()
        test_examples_protocol_simple_ota_example_with_verify_app_signature_on_update_no_secure_boot_ecdsa()
        test_examples_protocol_simple_ota_example_with_verify_app_signature_on_update_no_secure_boot_rsa()