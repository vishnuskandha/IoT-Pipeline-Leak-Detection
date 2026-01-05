#include <HTTPClient.h>
#include <WiFi.h>


// ------------------- USER CONFIG -------------------
const char *ssid = "Vishnu";
const char *password = "12345678";
const char *serverUrl = "http://192.168.0.3:8000/api/sensor-data"; // Updated IP

void setup() {
  Serial.begin(115200);

  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    // Generate random mock values
    int nodeId = 1; // Testing Node 1
    float tds = random(100, 500) / 1.0;
    float turb = random(0, 200) / 10.0;
    float flow = random(50, 250) / 10.0;
    bool isLeak = (turb > 15.0); // Simple mock condition

    // Create JSON Payload
    String json = "{";
    json += "\"node_id\":" + String(nodeId) + ",";
    json += "\"tds\":" + String(tds) + ",";
    json += "\"turbidity\":" + String(turb) + ",";
    json += "\"flow\":" + String(flow) + ",";
    json += "\"is_leak\":" + String(isLeak ? "true" : "false");
    json += "}";

    Serial.println("Posting: " + json);
    int httpResponseCode = http.POST(json);

    if (httpResponseCode > 0) {
      Serial.println("Server Res: " + String(httpResponseCode));
    } else {
      Serial.print("Error on sending POST: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("WiFi Disconnected");
  }

  delay(3000); // Send every 3 seconds
}
