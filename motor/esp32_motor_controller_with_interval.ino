#define RXD2 16
#define TXD2 17

HardwareSerial MotorSerial(2);

const int MSTEP = 16;
const int MOTOR_STEPS = 200;
const uint16_t ACC_VALUE = 0x0080;

uint8_t checksum8(const uint8_t *data, int len) {
  uint8_t sum = 0;
  for (int i = 0; i < len; i++) sum += data[i];
  return sum;
}

void setAcceleration(uint16_t acc) {
  uint8_t cmd[5];
  cmd[0] = 0xE0;
  cmd[1] = 0xA4;
  cmd[2] = (acc >> 8) & 0xFF;
  cmd[3] = acc & 0xFF;
  cmd[4] = checksum8(cmd, 4);

  MotorSerial.write(cmd, 5);
  MotorSerial.flush();
  delay(100);
}

uint32_t angleToPulse(float angle) {
  return (uint32_t)round((MOTOR_STEPS * MSTEP) * angle / 360.0);
}

void moveAngle(float degree, int speed, bool reverse) {
  uint32_t pulses = angleToPulse(degree);
  speed = constrain(speed, 1, 127);

  uint8_t speedByte = (uint8_t)speed;
  if (reverse) speedByte |= 0x80;

  uint8_t cmd[8];
  cmd[0] = 0xE0;
  cmd[1] = 0xFD;
  cmd[2] = speedByte;
  cmd[3] = (pulses >> 24) & 0xFF;
  cmd[4] = (pulses >> 16) & 0xFF;
  cmd[5] = (pulses >> 8) & 0xFF;
  cmd[6] = pulses & 0xFF;
  cmd[7] = checksum8(cmd, 7);

  MotorSerial.write(cmd, 8);
  MotorSerial.flush();
}

unsigned long estimateMoveMs(float degree, int speed) {
  speed = max(speed, 1);
  float ms = (degree / 90.0) * (16000.0 / speed);
  if (ms < 400) ms = 400;
  return (unsigned long)ms + 500;
}

void shakeMotor(float angle, int count, int speed, unsigned long intervalMs) {
  Serial.println("SHAKE START");

  for (int i = 0; i < count; i++) {
    moveAngle(angle, speed, false); // D
    delay(estimateMoveMs(angle, speed));
    delay(intervalMs);

    moveAngle(angle, speed, true);  // A
    delay(estimateMoveMs(angle, speed));
    delay(intervalMs);
  }

  Serial.println("SHAKE END");
}

void runSequence(float mainAngle, int mainSpeed,
                 float shakeAngle, int shakeCount,
                 int shakeSpeed, unsigned long shakeIntervalMs) {

  Serial.println("RUN START");
  setAcceleration(ACC_VALUE);

  Serial.println("MAIN D");
  moveAngle(mainAngle, mainSpeed, false);
  delay(estimateMoveMs(mainAngle, mainSpeed));

  shakeMotor(shakeAngle, shakeCount, shakeSpeed, shakeIntervalMs);

  delay(300);

  Serial.println("RETURN A");
  moveAngle(mainAngle, mainSpeed, true);
  delay(estimateMoveMs(mainAngle, mainSpeed));

  Serial.println("DONE");
}

void processCommand(String line) {
  line.trim();

  if (line.startsWith("RUN,")) {
    // RUN,90,2,10,5,20,300
    float mainAngle = 90;
    int mainSpeed = 2;
    float shakeAngle = 10;
    int shakeCount = 5;
    int shakeSpeed = 20;
    unsigned long shakeIntervalMs = 300;

    int p1 = line.indexOf(',');
    int p2 = line.indexOf(',', p1 + 1);
    int p3 = line.indexOf(',', p2 + 1);
    int p4 = line.indexOf(',', p3 + 1);
    int p5 = line.indexOf(',', p4 + 1);
    int p6 = line.indexOf(',', p5 + 1);

    if (p1 > 0 && p2 > p1 && p3 > p2 &&
        p4 > p3 && p5 > p4 && p6 > p5) {

      mainAngle = line.substring(p1 + 1, p2).toFloat();
      mainSpeed = line.substring(p2 + 1, p3).toInt();
      shakeAngle = line.substring(p3 + 1, p4).toFloat();
      shakeCount = line.substring(p4 + 1, p5).toInt();
      shakeSpeed = line.substring(p5 + 1, p6).toInt();
      shakeIntervalMs = line.substring(p6 + 1).toInt();

      mainAngle = constrain(mainAngle, 1.0f, 360.0f);
      mainSpeed = constrain(mainSpeed, 1, 127);
      shakeAngle = constrain(shakeAngle, 1.0f, 45.0f);
      shakeCount = constrain(shakeCount, 1, 20);
      shakeSpeed = constrain(shakeSpeed, 1, 127);
      shakeIntervalMs = constrain(shakeIntervalMs, 0UL, 3000UL);

      runSequence(
        mainAngle, mainSpeed,
        shakeAngle, shakeCount,
        shakeSpeed, shakeIntervalMs
      );
    }
  }

  else if (line.startsWith("JOG,")) {
    int p1 = line.indexOf(',');
    int p2 = line.indexOf(',', p1 + 1);
    int p3 = line.indexOf(',', p2 + 1);

    if (p1 > 0 && p2 > p1 && p3 > p2) {
      String dir = line.substring(p1 + 1, p2);
      float angle = line.substring(p2 + 1, p3).toFloat();
      int speed = line.substring(p3 + 1).toInt();

      bool reverse = (dir == "A");
      moveAngle(angle, speed, reverse);
      Serial.println("JOG DONE");
    }
  }
}

void setup() {
  Serial.begin(115200);
  MotorSerial.begin(38400, SERIAL_8N1, RXD2, TXD2);

  delay(1000);
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    processCommand(line);
  }
}
