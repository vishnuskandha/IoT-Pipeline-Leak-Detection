#include <ModbusRTU.h>

// ------------------- USER CONFIG -------------------
// CHANGE THIS ID FOR EACH BOARD (1, 2, 3)
#define SLAVE_ID 1

// Modbus Pins (RS485)
#define MAX485_DE 4
#define MAX485_RE_NEG 4
#define RX2_PIN 16
#define TX2_PIN 17

// Sensor Pins
#define PIN_TURBIDITY 34
#define PIN_TDS 35
#define PIN_FLOW 14 // Pulse output from flow sensor

// ------------------- GLOBALS -------------------
ModbusRTU mb;

volatile int flowPulseCount = 0;
float flowRate = 0.0;
unsigned long oldTime = 0;

void IRAM_ATTR pulseCounter() { flowPulseCount++; }

void setup() {
  Serial.begin(115200);

  // RS485
  Serial2.begin(9600, SERIAL_8N1, RX2_PIN, TX2_PIN);
  mb.begin(&Serial2, MAX485_DE, MAX485_RE_NEG);
  mb.slave(SLAVE_ID);

  // Register Holding Registers
  // 0: TDS, 1: Turbidity, 2: Flow
  mb.addHreg(0, 0);
  mb.addHreg(1, 0);
  mb.addHreg(2, 0);

  // Sensor Setup
  pinMode(PIN_FLOW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), pulseCounter, FALLING);

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
}

void updateSensors() {
  // --- FLOW SENSOR ---
  if ((millis() - oldTime) > 1000) {
    detachInterrupt(digitalPinToInterrupt(PIN_FLOW));
    // Calibration factor (e.g., 7.5) depends on your specific sensor
    flowRate = ((1000.0 / (millis() - oldTime)) * flowPulseCount) / 7.5;
    oldTime = millis();
    flowPulseCount = 0;
    attachInterrupt(digitalPinToInterrupt(PIN_FLOW), pulseCounter, FALLING);
  }

  // --- TURBIDITY ---
  // Example formula from user request
  int adcTurbX = analogRead(PIN_TURBIDITY);
  float voltageT = adcTurbX * (3.3 / 4095.0);
  float ntu = -1120.4 * voltageT * voltageT + 5742.3 * voltageT - 4352.9;
  if (ntu < 0)
    ntu = 0;

  // --- TDS --- (Placeholder logic, needs specific sensor library usually)
  int adcTds = analogRead(PIN_TDS);
  float voltageTds = adcTds * (3.3 / 4095.0);
  float tdsValue = (133.42 * voltageTds * voltageTds * voltageTds -
                    255.86 * voltageTds * voltageTds + 857.39 * voltageTds) *
                   0.5; // Calibration factor approximation

  // Update Modbus Registers
  // We multiply by 100 to store 2 decimal places in an integer register
  mb.Hreg(0, (uint16_t)(tdsValue * 100));
  mb.Hreg(1, (uint16_t)(ntu * 100));
  mb.Hreg(2, (uint16_t)(flowRate * 100));

  // Debug
  // Serial.printf("TDS: %.2f, NTU: %.2f, Flow: %.2f\n", tdsValue, ntu,
  // flowRate);
}

void loop() {
  mb.task();
  updateSensors();
  yield();
}
