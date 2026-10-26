const int button1Pin = 2; 
const int button2Pin = 4; 

int lastButton1State = HIGH; 
int lastButton2State = HIGH;

void setup() {
  // Включаем внутреннюю подтяжку к питанию
  pinMode(button1Pin, INPUT_PULLUP);
  pinMode(button2Pin, INPUT_PULLUP);
  
  // Открываем порт для связи с ПК
  Serial.begin(9600);
}

void loop() {
  // --- Проверка первой кнопки ---
  int currentState1 = digitalRead(button1Pin);
  if (currentState1 == LOW && lastButton1State == HIGH) {
    Serial.println("CLICK1"); // Отправляем команду 1
    delay(50); // Защита от дребезга
  }
  lastButton1State = currentState1;

  // --- Проверка второй кнопки ---
  int currentState2 = digitalRead(button2Pin);
  if (currentState2 == LOW && lastButton2State == HIGH) {
    Serial.println("CLICK2"); // Отправляем команду 2
    delay(50); 
  }
  lastButton2State = currentState2;
}
