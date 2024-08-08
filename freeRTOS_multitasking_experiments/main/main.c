#include <stdio.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_err.h"

TaskHandle_t xTask1=NULL;
TaskHandle_t xTask2=NULL;
TaskHandle_t xTask3=NULL;
TaskHandle_t xTask4=NULL;

SemaphoreHandle_t xSemaphore = NULL;

QueueHandle_t que;

void task1(void *pvParameters){
    char string[]="deneniyor";
    char data[50];
    que = xQueueCreate(10, sizeof (char [50]));

    for (int i = 0; string[i] != '\0'; i++){
        
        xSemaphoreTake(xSemaphore,portMAX_DELAY);

        sprintf(data,"%c",string[i]);
        xQueueSend(que, &data, portMAX_DELAY);
        vTaskDelay(1000 / portTICK_RATE_MS);

        xSemaphoreGive(xSemaphore);      
    }

    vTaskDelete(NULL);                            //eklenmezse que assertion hatası veriyor

}

void task2(void * pvParameters){
char data[50];

while(1){

    vTaskDelay(1000 / portTICK_RATE_MS);
    if (xQueueReceive(que, &data,portMAX_DELAY)){
        
        printf("%s\n",data);
                              //bu print içindeki string çok dolarsa LoadProhibited hatası alınıyor ama neden bilmiyorum
    }                 
} 

}

void task3(void *pvParameters){

    while(1){
        vTaskDelay(1000 / portTICK_RATE_MS);
        printf("task3\n");
}
}

void task4(void * pvParameters){
int c;

while(1){
    c=xTaskGetTickCount();       //semaphore aktif olsa bile tickcount ilerliyor yani c counter'ı bu duruma göre güncellenmeli

    vTaskDelay(1000 / portTICK_RATE_MS);
    printf("task4\n"); 

    if(c==1200){
        vTaskSuspend(xTask3);
        printf("task3 is suspended\n");
    }

    if(c==1500){
        vTaskResume(xTask3);
        printf("task3 resumes\n");
    }
    if(c==1800){
        printf("task3 and task4 have been terminated\n");
        vTaskDelete(xTask3);
        vTaskDelete(NULL);
    }                                                    
}
}

void app_main(void)
{
    xSemaphore=xSemaphoreCreateMutex();

    xTaskCreate(task2, "task2", 1024, NULL, 3, &xTask2);
    xTaskCreate(task1, "task1", 1024, NULL, 4, &xTask1);

    vTaskDelay(500 / portTICK_RATE_MS);             //delay verilmezse semaphore'u direkt task3'e atıyor ancak biz task 1'de istiyoruz 

    xSemaphoreTake(xSemaphore,portMAX_DELAY);

    xTaskCreate(task3, "task3", 1024, NULL, 2, &xTask3);
    xTaskCreate(task4, "task4", 1024, NULL, 1, &xTask4);

    xSemaphoreGive(xSemaphore);
    
}
    