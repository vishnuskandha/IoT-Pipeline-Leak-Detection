#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <HTTPClient.h>
#include <ModbusMaster.h>
#include <WiFi.h>
#include <Wire.h>

// ------------------- USER CONFIG -------------------
const char *ssid = "Vishnu";
const char *password = "12345678";
const char *serverUrl =
    "http://192.168.1.100:8000/api/sensor-data"; // REPLACE WITH YOUR PC IP

// Modbus Pins (RS485)
#define MAX485_DE 4
#define MAX485_RE_NEG 4
#define RX2_PIN 16
#define TX2_PIN 17

// OLED Config
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ------------------- GLOBALS -------------------
ModbusMaster node;

// Leak Thresholds (Adjust based on your environment)
#define THRESHOLD_TDS_MAX 500.0
#define THRESHOLD_TURBIDITY_MAX 10.0
#define THRESHOLD_FLOW_MIN 1.0
#define THRESHOLD_FLOW_MAX 30.0

void preTransmission() {
  digitalWrite(MAX485_DE, 1);
  digitalWrite(MAX485_RE_NEG, 1);
}

void postTransmission() {
  digitalWrite(MAX485_DE, 0);
  digitalWrite(MAX485_RE_NEG, 0);
}

void setup() {
  Serial.begin(115200);

  // RS485 Control Pin
  pinMode(MAX485_DE, OUTPUT);
  pinMode(MAX485_RE_NEG, OUTPUT);
  digitalWrite(MAX485_DE, 0);
  digitalWrite(MAX485_RE_NEG, 0);

  // Serial2 for Modbus (RX=16, TX=17)
  Serial2.begin(9600, SERIAL_8N1, RX2_PIN, TX2_PIN);

  // OLED Init
  // Address 0x3C for 128x64
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for (;;)
      ; // Don't proceed, loop forever
  }
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(F("Modbus Master Init..."));
  display.display();

  // WiFi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    display.print(".");
    display.display();
  }
  Serial.println("\nWiFi connected.");
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println(F("WiFi Connected!"));
  display.display();
  delay(1000);
}

// Helper to scale down integer from Modbus to float
float scaleFromModbus(uint16_t val) { return val / 100.0; }

void updateOLED(int nodeId, float tds, float turb, float flow, bool leak) {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.setTextSize(1);

  display.print("Node: ");
  display.println(nodeId);
  display.drawLine(0, 10, 128, 10, SSD1306_WHITE);

  display.setCursor(0, 15);
  display.print("TDS : ");
  display.print(tds);
  display.println(" ppm");

  display.print("Turb: ");
  display.print(turb);
  display.println(" NTU");

  display.print("Flow: ");
  display.print(flow);
  display.println(" L/m");

  display.setCursor(0, 50);
  if (leak) {
    display.setTextColor(SSD1306_BLACK, SSD1306_WHITE); // Invert for alert
    display.println("!! LEAK DETECTED !!");
    display.setTextColor(SSD1306_WHITE);
  } else {
    display.println("Status: Normal");
  }

  display.display();
}

void sendToBackend(int nodeId, float tds, float turbidity, float flow,
                   bool isLeak) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    String json = "{";
    json += "\"node_id\":" + String(nodeId) + ",";
    json += "\"tds\":" + String(tds) + ",";
    json += "\"turbidity\":" + String(turbidity) + ",";
    json += "\"flow\":" + String(flow) + ",";
    json += "\"is_leak\":" + String(isLeak ? "true" : "false");
    json += "}";

    int httpResponseCode = http.POST(json);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Server Res: " + String(httpResponseCode));
    } else {
      Serial.print("Error on sending POST: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("WiFi Disconnected");
  }
}

void processNode(uint8_t slaveId) {
  node.begin(slaveId, Serial2);
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);

  // Read 3 Holding Registers starting at 40001
  // 0: TDS, 1: Turbidity, 2: Flow
  uint8_t result = node.readHoldingRegisters(0x0000, 3);

  if (result == node.ku8MBSuccess) {
    float tds = scaleFromModbus(node.getResponseBuffer(0));
    float turbidity = scaleFromModbus(node.getResponseBuffer(1));
    float flow = scaleFromModbus(node.getResponseBuffer(2));

    Serial.printf("Node %d -> TDS: %.2f, Turb: %.2f, Flow: %.2f\n", slaveId,
                  tds, turbidity, flow);

    // Simple Leak Detection Logic
    bool isLeak = false;
    if (turbidity > THRESHOLD_TURBIDITY_MAX || flow > THRESHOLD_FLOW_MAX) {
      isLeak = true;
    }

    // Update Display
    updateOLED(slaveId, tds, turbidity, flow, isLeak);

    // Send to Backend
    sendToBackend(slaveId, tds, turbidity, flow, isLeak);
  } else {
    Serial.printf("Failed to read Node %d. Error: %02X\n", slaveId, result);
    display.clearDisplay();
    display.setCursor(0, 0);
    display.print("Node ");
    display.print(slaveId);
    display.println(" Error!");
    display.print("Code: ");
    display.println(result, HEX);
    display.display();
  }
}

void loop() {
  // Poll 3 Slaves
  processNode(1);
  delay(1000);
  processNode(2);
  delay(1000);
  processNode(3);
  delay(1000); // Wait before next cycle
}
