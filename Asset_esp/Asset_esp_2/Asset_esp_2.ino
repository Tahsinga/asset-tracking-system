#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "GateESP";  // Main ESP AP SSID
const char* password = "12345678";

String deviceID = "Asset_002";
// Set these per-device details in the sketch
String ownerName = "Tashinga";
String createdDate = "2025-12-29"; // YYYY-MM-DD
String ownerPhone = "0786395484";
String serialNumber = "XDDHS253572746";

void setup() {
  Serial.begin(115200);
  pinMode(2, OUTPUT);

  WiFi.begin(ssid, password);
  Serial.println("Connecting to Gate ESP...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.println("🎯 DEVICE DETECTED - Now close to gate/receiver!");
  Serial.println("📤 Sending device details to main ESP...");
  
  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    // Send device details to AP so the receiver can record owner/device fields
    String serverPath = "http://192.168.4.1/?id=" + deviceID
                        + "&owner=" + ownerName
                        + "&created=" + createdDate
                        + "&phone=" + ownerPhone
                        + "&serial=" + serialNumber;
    http.begin(serverPath);
    int httpResponseCode = http.GET();
    Serial.println("✅ Device details sent! HTTP Response: " + String(httpResponseCode));
    Serial.println("📋 Details sent: ID=" + deviceID + ", Owner=" + ownerName + ", Serial=" + serialNumber);
    http.end();
  }
}

void loop() {
  // Keep sending device info while connected to AP (near the receiver)
  if(WiFi.status() == WL_CONNECTED){
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);

    HTTPClient http;
    // Send device details to AP so the receiver can record owner/device fields
    String serverPath = "http://192.168.4.1/?id=" + deviceID
                        + "&owner=" + ownerName
                        + "&created=" + createdDate
                        + "&phone=" + ownerPhone
                        + "&serial=" + serialNumber;
    http.begin(serverPath);
    int httpResponseCode = http.GET();
    Serial.println("🔄 Proximity confirmed - Device " + deviceID + " still near gate");
    http.end();
  } else {
    digitalWrite(2, LOW);
    Serial.println("❌ Lost connection to gate AP - Device moved away");
    Serial.println("🔄 Attempting to reconnect...");
    WiFi.begin(ssid, password);
  }
  
  delay(1000); // Send every 1 second while near receiver
}
