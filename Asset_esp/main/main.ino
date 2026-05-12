#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

const char* ap_ssid = "GateESP";
const char* ap_password = "12345678";

const char* sta_ssid = "TASHINGA";
const char* sta_password = "1234567890";

const char* server_host = "asset-tracking-system-psvg.onrender.com";  // Render-hosted Django app

WiFiClientSecure secureClient;
WebServer server(80);

// ---- LED Pin ----
#define LED_PIN 2   // Built-in LED on many ESP32 boards

// ---- Servo Pin ----
#define SERVO_PIN 33
Servo gateServo;

// ---- Control Pin ----
#define CONTROL_PIN 4  // D4 pin

// Last detected device ID (shown on AP web UI so owner can claim)
String lastDeviceId = "";

unsigned long lastStatusSend = 0;
// How often to send heartbeat/status to server (milliseconds)
const unsigned long STATUS_INTERVAL_MS = 1000; // 1s for faster detection

// Track previous WiFi connected state to detect transitions quickly
bool prevWiFiConnected = false;

// Reconnect pacing when disconnected
unsigned long lastReconnectAttempt = 0;
const unsigned long RECONNECT_INTERVAL_MS = 3000; // try reconnect every 3s

void sendStatus() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = String("https://") + server_host + "/update_status/";
    http.begin(secureClient, url);
    http.addHeader("Content-Type", "application/json");

    IPAddress apIP = WiFi.softAPIP();
    String staIP = WiFi.localIP().toString();
    String apIPStr = apIP.toString();
    String jsonData = "{\"sta_connected\":true, \"ap_ip\":\"" + apIPStr + "\", \"sta_ip\":\"" + staIP + "\"}";
    int httpResponseCode = http.POST(jsonData);

    if (httpResponseCode > 0) {
      Serial.println("✅ Status sent to server: " + String(httpResponseCode));
    } else {
      Serial.println("❌ Failed to send status: " + String(httpResponseCode));
    }
    http.end();
  }
}

bool checkDeviceStatus(String deviceID, String serialNumber = "") {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ No WiFi, cannot check device status");
    return false;
  }

  HTTPClient http;
  String url = String("https://") + server_host + "/check_device_status/";
  if (serialNumber.length() > 0) {
    url += "?serial_number=" + serialNumber;
  } else {
    url += "?device_id=" + deviceID;
  }
  Serial.println("🔎 Querying server: " + url);
  http.begin(secureClient, url);
  int httpResponseCode = http.GET();

  if (httpResponseCode == 200) {
    String payload = http.getString();
    Serial.println("Device status response: " + payload);
    
    bool checkedOut = payload.indexOf("\"checked_out\":true") != -1 || payload.indexOf("\"checked_out\": 1") != -1;
    if (checkedOut) {
      Serial.println("✅ Device is checked out");
      http.end();
      return true;
    } else {
      Serial.println("ℹ️ Device is not checked out");
    }
  } else {
    Serial.println("❌ Failed to check device status: " + String(httpResponseCode));
  }
  http.end();
  return false;
}

void controlGate(bool isRegisteredAndCheckedOut) {
  if (isRegisteredAndCheckedOut) {
    // Move servo to 180 degrees
    Serial.println("🚪 Gate opening (servo to 180°)");
    gateServo.write(180);
    delay(2000);  // Wait 2 seconds
    
    // Move servo back to 0 degrees
    Serial.println("🚪 Gate closing (servo to 0°)");
    gateServo.write(0);
    delay(600);  // Allow return motion to finish
    Serial.println("✅ Servo returned to 0°");
  } else {
    // Just set D4 high
    Serial.println("⚠️ Unregistered or non-allowed device detected - D4 set HIGH");
    digitalWrite(CONTROL_PIN, HIGH);
    delay(1000);  // Keep it high for 1 second
    digitalWrite(CONTROL_PIN, LOW);
    Serial.println("⚠️ D4 set LOW");
  }
}

// Test function to manually control servo via serial input
void testServo() {
  static String inputString = "";
  static bool stringComplete = false;

  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n' || inChar == '\r') {
      if (inputString.length() > 0) {
        stringComplete = true;
      }
    } else {
      inputString += inChar;
    }
  }

  if (stringComplete) {
    int angle = inputString.toInt();
    angle = constrain(angle, 0, 180);
    
    gateServo.write(angle);
    Serial.print("🔧 Test: Moved servo to angle: ");
    Serial.println(angle);
    
    inputString = "";
    stringComplete = false;
  }
}

void handleRoot() {
  // If a device hits the AP with a device identifier, save the ID and forward immediately
  String deviceID = "";
  if (server.hasArg("id")) {
    deviceID = server.arg("id");
  } else if (server.hasArg("device_id")) {
    deviceID = server.arg("device_id");
  }

  String serialValue = "";
  if (server.hasArg("serial_number")) {
    serialValue = server.arg("serial_number");
  } else if (server.hasArg("serial")) {
    serialValue = server.arg("serial");
  }

  if (deviceID.length() == 0 && serialValue.length() > 0) {
    deviceID = serialValue;
  }

  if (deviceID.length() > 0) {
    lastDeviceId = deviceID;
    String owner = server.hasArg("owner") ? server.arg("owner") : "";
    String created = server.hasArg("created") ? server.arg("created") : "";
    String phone = server.hasArg("phone") ? server.arg("phone") : "";
    String serial = serialValue.length() ? serialValue : (server.hasArg("serial") ? server.arg("serial") : "");

    Serial.println("📡 Device reported -> " + deviceID + " owner:" + owner + " phone:" + phone + " serial:" + serial);
    Serial.println("🎯 ASSET DEVICE DETECTED AT GATE - Proximity confirmed!");

    // Only move the servo for the checked-out asset with ID AA12B3423HIT.
    bool isAllowedDevice = (deviceID == "AA12B3423HIT");
    bool isRegisteredAndCheckedOut = false;
    if (isAllowedDevice) {
      if (serialValue.length() > 0) {
        Serial.println("ℹ️ Checking checkout status using serial: " + serialValue);
      }
      isRegisteredAndCheckedOut = checkDeviceStatus(deviceID, serialValue);
    } else {
      Serial.println("ℹ️ Device " + deviceID + " is not AA12B3423HIT; servo will not move.");
    }
    controlGate(isRegisteredAndCheckedOut);

    // Forward to Django server (structured JSON)
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      String url = String("https://") + server_host + "/receive/";
      http.begin(secureClient, url);
      http.addHeader("Content-Type", "application/json");

      String jsonData = "{";
      jsonData += "\"device_id\":\"" + deviceID + "\",";
      if (owner.length()) jsonData += "\"owner_name\":\"" + owner + "\",";
      if (phone.length()) jsonData += "\"owner_contact\":\"" + phone + "\",";
      if (serial.length()) jsonData += "\"serial_number\":\"" + serial + "\",";
      if (created.length()) jsonData += "\"created_date\":\"" + created + "\",";
      jsonData += "\"notes\":\"Device reported at gate\"}";

      Serial.println("📤 Sending to server: " + jsonData);

      int httpResponseCode = http.POST(jsonData);

      if (httpResponseCode > 0) {
        Serial.println("✅ Sent to server: " + String(httpResponseCode));
      } else {
        Serial.println("❌ Failed to send: " + String(httpResponseCode));
      }
      http.end();
    } else {
      Serial.println("❌ No WiFi, cannot send to server");
    }

    // Respond with a small HTML page that directs an owner to the claim page
    String html = String("<html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"></head><body>");
    html += "<h3>Device ";
    html += deviceID;
    html += " detected</h3>";
    html += "<p>Owner? <a href=\"/\">Tap here to claim this device</a></p>";
    html += "</body></html>";
    server.send(200, "text/html", html);
    return;
  }

  // Default: serve the AP claim page that shows the latest detected device and a claim form
  String page = String("<html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"></head><body>");
  page += "<h2>Gate Receiver</h2>";
  page += "<p>Latest detected device: <strong>";
  page += (lastDeviceId.length() ? lastDeviceId : "(none)");
  page += "</strong></p>";
  page += "<form method=\"POST\" action=\"/claim\">";
  page += "<input type=\"hidden\" name=\"device_id\" value=\"";
  page += lastDeviceId;
  page += "\">";
  page += "<div><label>Name: <input name=\"owner_name\" required></label></div>";
  page += "<div><label>Contact: <input name=\"owner_contact\"></label></div>";
  page += "<div><button type=\"submit\">Claim Device</button></div>";
  page += "</form></body></html>";
  server.send(200, "text/html", page);
}

// Handle form POST when an owner claims a detected device
void handleClaim() {
  String deviceID = server.arg("device_id");
  String owner = server.arg("owner_name");
  String contact = server.arg("owner_contact");

  Serial.println("🖊️ Claim received for " + deviceID + " by " + owner + " (" + contact + ")");

  // Build notes string and forward to Django server
  String notes = "Claimed by: " + owner;
  if (contact.length()) notes += " (" + contact + ")";

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = String("https://") + server_host + "/receive/";
    http.begin(secureClient, url);
    http.addHeader("Content-Type", "application/json");

    String jsonData = "{\"device_id\":\"" + deviceID + "\", \"notes\":\"" + notes + "\"}";
    int httpResponseCode = http.POST(jsonData);

    if (httpResponseCode > 0) {
      Serial.println("✅ Claim forwarded to server: " + String(httpResponseCode));
    } else {
      Serial.println("❌ Failed to forward claim: " + String(httpResponseCode));
    }
    http.end();
  } else {
    Serial.println("❌ No WiFi — claim stored locally (not implemented)");
  }

  String resp = String("<html><body><h3>Thanks, ");
  resp += owner;
  resp += "</h3><p>Device ";
  resp += deviceID;
  resp += " claimed.</p></body></html>";
  server.send(200, "text/html", resp);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);   // OFF at startup

  // Initialize servo
  gateServo.setPeriodHertz(50);
  gateServo.attach(SERVO_PIN, 500, 2400);
  gateServo.write(0);  // Start at 0 degrees
  delay(500);          // Give the servo time to reach the start position
  Serial.println("🔧 Servo initialized on pin 33 and moved to 0°");

  // Initialize control pin
  pinMode(CONTROL_PIN, OUTPUT);
  digitalWrite(CONTROL_PIN, LOW);  // Start LOW
  Serial.println("🔧 Control pin D4 initialized");

  Serial.println();
  Serial.println("🚀 Starting GATE RECEIVER ESP32");

  Serial.println("Before WiFi.mode");
  WiFi.mode(WIFI_AP_STA);
  Serial.println("After WiFi.mode");

  Serial.println("Before WiFi.begin");
  WiFi.begin(sta_ssid, sta_password);
  Serial.println("After WiFi.begin");

  secureClient.setInsecure();
  Serial.println("\nConnecting to main WiFi network...");

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Connected to main WiFi");
    Serial.print("📡 STA IP: ");
    Serial.println(WiFi.localIP());

    digitalWrite(LED_PIN, HIGH);   // ⭐ LED ON = Internet connected
  } else {
    Serial.println("\n❌ Failed to connect to WiFi (AP mode only)");
    digitalWrite(LED_PIN, LOW);    // LED OFF = No internet
  }

  // ----- Access Point -----
  WiFi.softAP(ap_ssid, ap_password);

  IPAddress apIP = WiFi.softAPIP();
  Serial.println("\n📶 ACCESS POINT STARTED");
  Serial.print("AP SSID: ");
  Serial.println(ap_ssid);
  Serial.print("AP IP: ");
  Serial.println(apIP);

  // Send status to server
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
      String url = String("https://") + server_host + "/update_status/";
      http.begin(secureClient, url);
    String staIP = WiFi.localIP().toString();
    String apIPStr = apIP.toString();
    String jsonData = "{\"sta_connected\":true, \"ap_ip\":\"" + apIPStr + "\", \"sta_ip\":\"" + staIP + "\"}";
    int httpResponseCode = http.POST(jsonData);

    if (httpResponseCode > 0) {
      Serial.println("✅ Status sent to server: " + String(httpResponseCode));
    } else {
      Serial.println("❌ Failed to send status: " + String(httpResponseCode));
    }
    http.end();
  }
  lastStatusSend = millis();
    // initialize previous connection state
    prevWiFiConnected = (WiFi.status() == WL_CONNECTED);
  // ----- Web Server -----
  server.on("/", handleRoot);
  server.on("/claim", HTTP_POST, handleClaim);
  server.begin();
  Serial.println("\n🌐 HTTP server started");
  Serial.println("Senders should send:");
  Serial.println("http://" + apIP.toString() + "/?id=DEVICE_SERIAL\n");
  Serial.println("🔧 Manual servo test: Enter angle (0-180) in Serial Monitor");
}

void loop() {
  server.handleClient();

  // Test servo manually via serial input
  testServo();

  // Continuously monitor Wi-Fi connection and react to transitions
  bool connected = (WiFi.status() == WL_CONNECTED);

  // Detect transition events (connected <-> disconnected)
  if (connected != prevWiFiConnected) {
    prevWiFiConnected = connected;
    if (connected) {
      Serial.println("↗ WiFi reconnected — sending immediate status");
      digitalWrite(LED_PIN, HIGH);
      sendStatus();                 // immediate heartbeat on reconnect
      lastStatusSend = millis();
    } else {
      Serial.println("↘ WiFi disconnected");
      digitalWrite(LED_PIN, LOW);
    }
  }

  // Periodic heartbeat while connected (shorter interval for faster detection)
  if (connected && (millis() - lastStatusSend > STATUS_INTERVAL_MS)) {
    sendStatus();
    lastStatusSend = millis();
  }

  // If disconnected, occasionally attempt to reconnect to speed recovery
  if (!connected && (millis() - lastReconnectAttempt > RECONNECT_INTERVAL_MS)) {
    Serial.println("Attempting WiFi reconnect...");
    WiFi.reconnect();
    lastReconnectAttempt = millis();
  }
}
