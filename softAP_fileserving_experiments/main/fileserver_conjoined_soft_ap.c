/*  WiFi softAP Example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/
#include <stdlib.h>
#include <sys/param.h>
#include <stdio.h>
#include <string.h>
#include <sys/param.h>
#include <sys/unistd.h>
#include <sys/stat.h>
#include <dirent.h>

#include "esp_err.h"
#include "esp_vfs.h"
#include "esp_spiffs.h"
#include "esp_http_server.h"
#include "esp_netif.h"
//#include "esp_eth.h"
#include "esp_tls_crypto.h"
#include <esp_http_server.h>
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"

#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "nvs_flash.h"

#include "lwip/err.h"
#include "lwip/sys.h"
#include "protocol_examples_common.h"
#include "file_serving_example_common.h"

static const char *TAG = "wifi softAP";

//WIFI EXAMPLE ile gelen define'ler
#define EXAMPLE_ESP_WIFI_SSID      CONFIG_ESP_WIFI_SSID
#define EXAMPLE_ESP_WIFI_PASS      CONFIG_ESP_WIFI_PASSWORD
#define EXAMPLE_ESP_WIFI_CHANNEL   CONFIG_ESP_WIFI_CHANNEL
#define EXAMPLE_MAX_STA_CONN       CONFIG_ESP_MAX_STA_CONN

#define FILE_PATH_MAX (ESP_VFS_PATH_MAX + CONFIG_SPIFFS_OBJ_NAME_LEN)

/* Max size of an individual file. Make sure this
 * value is same as that set in upload_script.html */
#define MAX_FILE_SIZE   (200*1024) // 200 KB
#define MAX_FILE_SIZE_STR "200KB"

/* Scratch buffer size */
#define SCRATCH_BUFSIZE  8192

struct file_server_data {
    /* Base path of file storage */
    char base_path[ESP_VFS_PATH_MAX + 1];

    /* Scratch buffer for temporary storage during file transfer */
    char scratch[SCRATCH_BUFSIZE];
};

static const char *html_code = "<!DOCTYPE html>\
<table class=\"fixed\" border=\"0\">\
    <col width=\"1000px\" /><col width=\"500px\" />\
    <tr><td>\
        <h2>ESP32 File Server</h2>\
    </td><td>\
        <table border=\"0\">\
            <tr>\
                <td>\
                    <label for=\"newfile\">Upload a file</label>\
                </td>\
                <td colspan=\"2\">\
                    <input id=\"newfile\" type=\"file\" onchange=\"setpath()\" style=\"width:100%;\">\
                </td>\
            </tr>\
            <tr>\
                <td>\
                    <label for=\"filepath\">Set path on server</label>\
                </td>\
                <td>\
                    <input id=\"filepath\" type=\"text\" style=\"width:100%;\">\
                </td>\
                <td>\
                    <button id=\"upload\" type=\"button\" onclick=\"upload()\">Upload</button>\
                </td>\
            </tr>\
        </table>\
    </td></tr>\
</table>\
<script>\
function setpath() {\
    var default_path = document.getElementById(\"newfile\").files[0].name;\
    document.getElementById(\"filepath\").value = default_path;\
}\
function upload() {\
    var filePath = document.getElementById(\"filepath\").value;\
    var upload_path = \"/upload/\" + filePath;\
    var fileInput = document.getElementById(\"newfile\").files;\
\
    var MAX_FILE_SIZE = 200*1024;\
    var MAX_FILE_SIZE_STR = \"200KB\";\
\
    if (fileInput.length == 0) {\
        alert(\"No file selected!\");\
    } else if (filePath.length == 0) {\
        alert(\"File path on server is not set!\");\
    } else if (filePath.indexOf(' ') >= 0) {\
        alert(\"File path on server cannot have spaces!\");\
    } else if (filePath[filePath.length-1] == '/') {\
        alert(\"File name not specified after path!\");\
    } else if (fileInput[0].size > 200*1024) {\
        alert(\"File size must be less than 200KB!\");\
    } else {\
        document.getElementById(\"newfile\").disabled = true;\
        document.getElementById(\"filepath\").disabled = true;\
        document.getElementById(\"upload\").disabled = true;\
\
        var file = fileInput[0];\
        var xhttp = new XMLHttpRequest();\
        xhttp.onreadystatechange = function() {\
            if (xhttp.readyState == 4) {\
                if (xhttp.status == 200) {\
                    document.open();\
                    document.write(xhttp.responseText);\
                    document.close();\
                } else if (xhttp.status == 0) {\
                    alert(\"Server closed the connection abruptly!\");\
                    location.reload();\
                } else {\
                    alert(xhttp.status + \" Error!\\n\" + xhttp.responseText);\
                    location.reload();\
                }\
            }\
        };\
        xhttp.open(\"POST\", upload_path, true);\
        xhttp.send(file);\
    }\
}\
</script>";

/* The examples use WiFi configuration that you can set via project configuration menu.

   If you'd rather not, just change the below entries to strings with
   the config you want - ie #define EXAMPLE_WIFI_SSID "mywifissid"
*/


#define IS_FILE_EXT(filename, ext) \
    (strcasecmp(&filename[strlen(filename) - sizeof(ext) + 1], ext) == 0)

/* Set HTTP response content type according to file extension */
static esp_err_t set_content_type_from_file(httpd_req_t *req, const char *filename)
{
    if (IS_FILE_EXT(filename, ".pdf")) {
        return httpd_resp_set_type(req, "application/pdf");
    } else if (IS_FILE_EXT(filename, ".html")) {
        return httpd_resp_set_type(req, "text/html");
    } else if (IS_FILE_EXT(filename, ".jpeg")) {
        return httpd_resp_set_type(req, "image/jpeg");
    } 
    
    /* This is a limited set only */
    /* For any other type always set as plain text */
    return httpd_resp_set_type(req, "text/plain");
}

static const char* get_path_from_uri(char *dest, const char *base_path, const char *uri, size_t destsize)
{
    const size_t base_pathlen = strlen(base_path);
    size_t pathlen = strlen(uri);

    const char *quest = strchr(uri, '?');
    if (quest) {
        pathlen = MIN(pathlen, quest - uri);
    }
    const char *hash = strchr(uri, '#');
    if (hash) {
        pathlen = MIN(pathlen, hash - uri);
    }

    if (base_pathlen + pathlen + 1 > destsize) {
       
        return NULL;
    }

    strcpy(dest, base_path);
    strlcpy(dest + base_pathlen, uri, pathlen + 1);

    return dest + base_pathlen;
}


static esp_err_t upload_handler(httpd_req_t *req)
{
    char filepath[FILE_PATH_MAX];
    FILE *fd = NULL;
    struct stat file_stat;

   
    const char *filename = get_path_from_uri(filepath, ((struct file_server_data *)req->user_ctx)->base_path,
                                             req->uri + sizeof("/upload") - 1, sizeof(filepath));
    if (!filename) {
        
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Filename too long");
        return ESP_FAIL;
    }

   
    if (filename[strlen(filename) - 1] == '/') {
        ESP_LOGE(TAG, "Invalid filename : %s", filename);
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Invalid filename");
        return ESP_FAIL;
    }

    if (stat(filepath, &file_stat) == 0) {
        ESP_LOGE(TAG, "File already exists : %s", filepath);
       
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "File already exists");
        return ESP_FAIL;
    }

   
    if (req->content_len > MAX_FILE_SIZE) {
        ESP_LOGE(TAG, "File too large : %d bytes", req->content_len);
        
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST,
                            "File size must be less than "
                            MAX_FILE_SIZE_STR "!");
        
        return ESP_FAIL;
    }

    fd = fopen(filepath, "w");
    if (!fd) {
        ESP_LOGE(TAG, "Failed to create file : %s", filepath);
        
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Failed to create file");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Receiving file : %s...", filename);

    
    char *buf = ((struct file_server_data *)req->user_ctx)->scratch;
    int received;

    int remaining = req->content_len;

    while (remaining > 0) {

        ESP_LOGI(TAG, "Remaining size : %d", remaining);
        
        if ((received = httpd_req_recv(req, buf, MIN(remaining, SCRATCH_BUFSIZE))) <= 0) {
            if (received == HTTPD_SOCK_ERR_TIMEOUT) {
                
                continue;
            }

            
            fclose(fd);
            unlink(filepath);

            ESP_LOGE(TAG, "File reception failed!");
            
            httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Failed to receive file");
            return ESP_FAIL;
        }

        if (received && (received != fwrite(buf, 1, received, fd))) {
          
            fclose(fd);
            unlink(filepath);

            ESP_LOGE(TAG, "File write failed!");
        
            httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Failed to write file to storage");
            return ESP_FAIL;
        }

        remaining -= received;
    }

    fclose(fd);
    ESP_LOGI(TAG, "File reception complete");

    httpd_resp_set_status(req, "303 See Other");
    httpd_resp_set_hdr(req, "Location", "/");
#ifdef CONFIG_EXAMPLE_HTTPD_CONN_CLOSE_HEADER
    httpd_resp_set_hdr(req, "Connection", "close");
#endif
    httpd_resp_sendstr(req, "File uploaded successfully");
    return ESP_OK;
}


esp_err_t web_server_handler(httpd_req_t *req)
{
    // Set the Content-Type header to "text/html"
    httpd_resp_set_type(req, "text/html");

    // Send the HTML code as the HTTP response
    httpd_resp_send(req, html_code, HTTPD_RESP_USE_STRLEN);

    return ESP_OK;
}

static const httpd_uri_t web_server = {
    .uri       = "/web_server",
    .method    = HTTP_GET,
    .handler   = web_server_handler,
    /* Let's pass response string in user
     * context to demonstrate it's usage */
    .user_ctx  = &html_code
};


static httpd_handle_t start_webserver(const char *base_path)
{
    static struct file_server_data *server_data = NULL;
    server_data = calloc(1, sizeof(struct file_server_data));
    strlcpy(server_data->base_path, base_path,
            sizeof(server_data->base_path));
    httpd_handle_t server = NULL;
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.uri_match_fn = httpd_uri_match_wildcard;

    // Start the httpd server
    ESP_LOGI(TAG, "Starting server on port: '%d'", config.server_port);
    if (httpd_start(&server, &config) == ESP_OK) {
        // Set URI handlers
        httpd_uri_t file_upload = {
            .uri       = "/upload/*",   // Match all URIs of type /upload/path/to/file
            .method    = HTTP_POST,
            .handler   = upload_handler,
            .user_ctx  = server_data    // Pass server data as context
        };

       
        ESP_LOGI(TAG, "Registering URI handlers");
        httpd_register_uri_handler(server, &web_server);
        httpd_register_uri_handler(server, &file_upload);
        
        #if CONFIG_EXAMPLE_BASIC_AUTH
        httpd_register_basic_auth(server);
        #endif
        return server;
    }

    ESP_LOGI(TAG, "Error starting server!");
    return NULL;
}



static void connect_handler(void* arg, esp_event_base_t event_base,
                            int32_t event_id, void* event_data)
{
    const char *base_path="/data";
    httpd_handle_t* server = (httpd_handle_t*) arg;
    if (*server == NULL) {
        ESP_LOGI(TAG, "Starting webserver");
        *server = start_webserver(base_path);
    }
}


static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                    int32_t event_id, void* event_data)
{
    if (event_id == WIFI_EVENT_AP_STACONNECTED) {
        wifi_event_ap_staconnected_t* event = (wifi_event_ap_staconnected_t*) event_data;
        ESP_LOGI(TAG, "station "MACSTR" join, AID=%d",
                 MAC2STR(event->mac), event->aid);
    } else if (event_id == WIFI_EVENT_AP_STADISCONNECTED) {
        wifi_event_ap_stadisconnected_t* event = (wifi_event_ap_stadisconnected_t*) event_data;
        ESP_LOGI(TAG, "station "MACSTR" leave, AID=%d",
                 MAC2STR(event->mac), event->aid);
    }
}



void wifi_init_softap(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        NULL));

    wifi_config_t wifi_config = {
        .ap = {
            .ssid = EXAMPLE_ESP_WIFI_SSID,
            .ssid_len = strlen(EXAMPLE_ESP_WIFI_SSID),
            .channel = EXAMPLE_ESP_WIFI_CHANNEL,
            .password = EXAMPLE_ESP_WIFI_PASS,
            .max_connection = EXAMPLE_MAX_STA_CONN,
            .authmode = WIFI_AUTH_WPA_WPA2_PSK
        },
    };
    if (strlen(EXAMPLE_ESP_WIFI_PASS) == 0) {
        wifi_config.ap.authmode = WIFI_AUTH_OPEN;
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "wifi_init_softap finished. SSID:%s password:%s channel:%d",
             EXAMPLE_ESP_WIFI_SSID, EXAMPLE_ESP_WIFI_PASS, EXAMPLE_ESP_WIFI_CHANNEL);
}



void app_main(void)
{
    
    static httpd_handle_t server = NULL;
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }

    ESP_ERROR_CHECK(ret);

    ESP_LOGI(TAG, "ESP_WIFI_MODE_AP");
    wifi_init_softap();
    ESP_ERROR_CHECK(esp_netif_init());

    const char* base_path = "/data";
    ESP_ERROR_CHECK(example_mount_storage(base_path));

    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_AP_STAIPASSIGNED, &connect_handler, &server)); //IP_EVENT_STA_GOT_IP yerine IP_EVENT_AP_STAIPASSIGNED yazıldı 
    
}

