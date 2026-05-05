#include <TinyGPSPlus.h>

// Use ESP32 Hardware Serial 2
static const int RXPin = 16;
static const int TXPin = 17;
static const uint32_t GPSBaud = 9600;

TinyGPSPlus gps;
HardwareSerial ss(2);   // Use UART2 on ESP32

void setup()
{
  Serial.begin(115200);
  delay(1000);

  ss.begin(GPSBaud, SERIAL_8N1, RXPin, TXPin);

  Serial.println("ESP32 GPS Test");
  Serial.print("TinyGPSPlus library v. ");
  Serial.println(TinyGPSPlus::libraryVersion());
  Serial.println();
}

void loop()
{
  while (ss.available() > 0)
  {
    if (gps.encode(ss.read()))
    {
      displayInfo();
    }
  }

  if (millis() > 5000 && gps.charsProcessed() < 10)
  {
    Serial.println("No GPS detected: check wiring.");
    while (true);
  }
}

void displayInfo()
{
  Serial.println("Google Maps link:");

  if (gps.location.isValid())
  {
    Serial.print("http://www.google.com/maps/place/");
    Serial.print(gps.location.lat(), 6);
    Serial.print(",");
    Serial.println(gps.location.lng(), 6);
  }
  else
  {
    Serial.println("Location: INVALID");
  }

  Serial.print("Date/Time: ");

  if (gps.date.isValid())
  {
    Serial.print(gps.date.month());
    Serial.print("/");
    Serial.print(gps.date.day());
    Serial.print("/");
    Serial.print(gps.date.year());
  }
  else
  {
    Serial.print("INVALID");
  }

  Serial.print(" ");

  if (gps.time.isValid())
  {
    if (gps.time.hour() < 10) Serial.print("0");
    Serial.print(gps.time.hour());
    Serial.print(":");

    if (gps.time.minute() < 10) Serial.print("0");
    Serial.print(gps.time.minute());
    Serial.print(":");

    if (gps.time.second() < 10) Serial.print("0");
    Serial.print(gps.time.second());
  }
  else
  {
    Serial.print("INVALID");
  }

  Serial.println();
  Serial.println();
}