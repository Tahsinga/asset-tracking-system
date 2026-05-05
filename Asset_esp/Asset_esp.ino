#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "GateESP";  // Main ESP AP SSID
const char* password = "12345678";

String deviceID = "AA12B3423HIT";
// Set these per-device details in the sketch
String ownerName = "N/A";
String createdDate = "N/A"; // YYYY-MM-DD
String ownerPhone = "N/A";
String serialNumber = "ABC123456709";

void setup() {
  Serial.begin(115200);

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
    HTTPClient http;
    // Send device details to MAIN ESP's AP (192.168.4.1) - it will forward to Django
    String serverPath = "http://192.168.4.1/?id=" + deviceID
                        + "&owner=" + ownerName
                        + "&created=" + createdDate
                        + "&phone=" + ownerPhone
                        + "&serial=" + serialNumber;
    http.begin(serverPath);
    int httpResponseCode = http.GET();
    Serial.println("🔄 Proximity confirmed - Device " + deviceID + " still near gate (HTTP: " + String(httpResponseCode) + ")");
    http.end();
  } else {
    Serial.println("❌ Lost connection to gate AP - Device moved away");
    Serial.println("🔄 Attempting to reconnect...");
    WiFi.begin(ssid, password);
  }
  
  delay(1000); // Send every 1 second while near receive/r
}
