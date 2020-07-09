#include <nRF24L01.h>
#include <RF24_config.h>
#include <RF24.h>
#include <DHT.h>
#include <stdint.h>

#define IRQ_TRIGGER_PIN 2                // The interrupt pin of the NRF24l01
#define HFS_TRIGGER_PIN 3                // The pin at which the out signal of the HFS sensor will be read (5v high signal (voltage divide to 3.3))
#define DHTPIN 4                         // The data pin of the dht22 temp sensor
#define CE 7                             // The CE pin of the NRF24l01
#define CSN 8                            // The CSN pin of the NRF24l01
#define HFS_ENABLE_DELAY 1 * 60000  // delay in milli seconds before processing interrupts from HFS when the sensor is enabled
#define Ping_Delay 5 * 1000              // the delay in milliseconds for ping packets which include the same info as GETSTATUS command respons
#define STARTUP_DELAY 20 * 1000          // delay before running the sketch to avoid hfs being high on startup
#define powerbankResetPin 5              // the pin at which the powerbank button will be connected
#define powerBankResetInterval 20 * 1000 // how often to trigger the powerBank reset
#define powerButtonClickDelay 500        // time in milliseconds for how long the powerbuttonreset press is
enum commandType
{
  NOCOMMAND = 0,
  DisableDetection,
  StartDetection,  // this should set the sensor state to waiting until the enable delay is over
  EnableDetection, // this should start the processing of the sensor output immediatly
  GETSTATUS        // used to get info and as a ping command
};

enum HFSState
{
  NONE = 33,           // ASCII "!"
  SensorDisabled = 68, // ACII "D"
  SensorEnabled = 69,  // ASCII "E"
  SensorWaiting = 87   // ASCII "W"
};

typedef struct
{
  bool isAlarm;
  float temp;
  // float humidity;
  char state;
} infoPacket;

volatile commandType commandToExcute;     // the command received from the main unit to excute
volatile bool isHfsTriggered = true;      // used to indicate for the loop function if the sensor has been triggered.
int payloadSize = sizeof(infoPacket);     // dynamic payloads are not supported in micropython (used on the other end)
unsigned long hfsEnableTime = 0;          // stores millis() since last time the hfs was enabled
unsigned long PingTime = 0;               // stores millis() since last time a ping was sent
HFSState currentHFSState = SensorDisabled ; // the current state of the HFS sensor
bool isAlarm = false;                     // if alarm sending failed the ping packet will indicate the alarm until success
unsigned long powerbankResetTime = 0;     // stores millis() since last time the powerbank reset was triggered

RF24 radio(CE, CSN);
uint8_t pipes[][6] = {"Pipe0", "Pipe1"};

// float humidity = NAN;
float temp = NAN;

DHT dht(DHTPIN, DHT22);

void setup()
{
  // setup the pins mode
  pinMode(HFS_TRIGGER_PIN, INPUT);
  pinMode(IRQ_TRIGGER_PIN, INPUT);

  // setup the NRF24l01
  radio.begin();
  radio.setChannel(85);
  radio.setAutoAck(1); // Ensure autoACK is enabled
  radio.setPayloadSize(payloadSize);
  radio.setDataRate(RF24_250KBPS);            // 0 = RF24_1MBPS / 1 =RF24_1MBPS / 2 = RF24_250KBPS 
  radio.setPALevel(RF24_PA_MAX);  //Set power level to high
  radio.setRetries(15, 15);        // Smallest time between retries, max no. of retries //(delay is in multiples of 250us, max is 15. 0 means 250us, 15 means 4000us.)
  radio.maskIRQ(1, 1, 0);          // mask all IRQ triggers except for receive (1 is mask, 0 is no mask)
  radio.openWritingPipe(pipes[1]); // Both radios listen on the same pipes by default, and switch when writing
  radio.openReadingPipe(1, pipes[0]);
  radio.startListening(); // start listening

  // setup serial
  Serial.begin(9600);
  

  //attach interrupts to the 2 interrupt pins of the arduino
  attachInterrupt(digitalPinToInterrupt(HFS_TRIGGER_PIN), HFSTrigger, RISING);  // attach interrupt to the output signal of the HFS sensor
  attachInterrupt(digitalPinToInterrupt(IRQ_TRIGGER_PIN), NRFTrigger, FALLING); // attach interrupt to the output signal of the NRF transmitter (pin is low on trigger)

  //start the temp sensor
  dht.begin();
  Serial.println("Setting things up");
  // Enable the sensor
  Serial.print("Enabling the sensor, status:");
  if (radio.isChipConnected() == 1)
  {
    Serial.println("connected");
  }
  else
  {
    Serial.println("unavailable");
  }
  isHfsTriggered = false;
}

void loop()
{
  if (millis() >= STARTUP_DELAY)
  {
    if (millis() - powerbankResetTime >= powerBankResetInterval)
    {
      powerbankResetTime = millis();
      Serial.println("triggering powerbank reset");
      triggerPowerbankButton();
      Serial.println("triggering done");
    }
    if (radio.isChipConnected())
    {
      if (radio.rxFifoFull())
      {
        Serial.println("rx full...flushing");
        radio.flush_rx();
      }
      // Check for triggers
      if (isHfsTriggered) // on trigger
      {
        currentHFSState = SensorDisabled; // disable the sensor
        Serial.println("Sending alarm...");
        isHfsTriggered = false; // set trigger to false
        if (sendInfoPacket(true))
        {
          Serial.println("Alarm sent successfully!!!");
          isAlarm = false;
        }
        else
        {
          Serial.println("Alarm sending failed");
          isAlarm = true;
        }
      }
      // Check if the sensor should be enabled
      if (currentHFSState == SensorWaiting)
      {
        if (millis() - hfsEnableTime >= HFS_ENABLE_DELAY)
        {
          currentHFSState = SensorEnabled;
          hfsEnableTime = millis();
          Serial.println("sensor enabled after waiting");
          if (sendInfoPacket(isAlarm))
          {
            Serial.println("sensor state update packet sent");
            if (isAlarm)
            {
              isAlarm = false;
            }
          }
          else
          {
            Serial.println("failed to send update packet");
          }
        }
      }
      // Check if there is a new command
      if (commandToExcute != NOCOMMAND)
      {
        Serial.print("Command Recived:");
        Serial.println(commandToExcute);
        switch (commandToExcute)
        {
        case DisableDetection:
          currentHFSState = SensorDisabled;
          break;
        case StartDetection:
          /* here it's set that StartDetection will always have a delay and also will reset the delay if the same command is received.
      depending on what implmenation is used on the other side
            it might be more suitable to enable the sensor without a delay if the command is sent while already waiting */
          if (currentHFSState == SensorDisabled || currentHFSState == NONE)
          {
            currentHFSState = SensorWaiting;
            hfsEnableTime = millis();
            Serial.println("Starting up the sensor");
          }
          else if (currentHFSState == SensorWaiting)
          {
            hfsEnableTime = millis();
            Serial.println("Starting up the sensor (delay reset)");
          }
          break;
        case EnableDetection:
          currentHFSState = SensorEnabled;
          hfsEnableTime = 0; // not necessary but it could be good as it indicates that the sensor has been enabled.
          Serial.println("Enabling the sensor");
          break;
        case GETSTATUS:
        {
          if (sendInfoPacket(isAlarm))
          {
            Serial.println("GetStatus packet sent");
            if (isAlarm)
            {
              isAlarm = false;
            }
            PingTime = millis();
          }
          else
          {
            Serial.println("GetStatus packet failed");
          }
          break;
        }
        default:
          break;
        }
        Serial.println("Command done");
        if (commandToExcute != GETSTATUS)
        {
          commandToExcute = GETSTATUS;
        }
        else
        {
          commandToExcute = NOCOMMAND;
        }
      }
      if (millis() - PingTime >= Ping_Delay)
      {
        if (commandToExcute != GETSTATUS)
        {
          PingTime = millis();
          if (sendInfoPacket(isAlarm))
          {
            Serial.println("Ping sent");
            if (isAlarm)
            {
              isAlarm = false;
            }
          }
          else
          {
            Serial.println("Ping failed");
          }
        }
        else
        {
          PingTime = millis();
        }
      }
    }
    else
    {
      Serial.println("Chip not connected");
    }
  }
}

void HFSTrigger()
{
  if (currentHFSState == SensorEnabled && !isHfsTriggered)
  {
    isHfsTriggered = true;
  }
}

void NRFTrigger()
{
  commandType commandReceived = NOCOMMAND; // set the command to be no command
  if (radio.available())                   // check if there is a packet
  {
    byte payload[payloadSize];
    radio.read(&payload, sizeof(payloadSize)); // read the command and store it in the variable created
    radio.flush_rx();
    commandReceived = (commandType)payload[0];
  }
  commandToExcute = commandReceived; // set the global command variable to the command received
}

float readTemp()
{
  temp = dht.readTemperature(); // Read temperature as Celsius (the default)
  if (isnan(temp))              // check if temp is not a number (reading failed)
  {
    // set value to -1 to indicate failuer
    temp = -1;
    // humidity = -1;
  }
  return temp;
}

// float readHumidity()
// {
//   humidity = dht.readHumidity();
//   if (isnan(humidity)) // check if temp is not a number (reading failed)
//   {
//     // set value to -1 to indicate failuer
//     temp = -1;
//   }
//   return humidity;
// }

bool sendInfoPacket(bool isAlarm)
{
  bool isSuccess = false;
  // ! Reading temperature or humidity takes about 250 milliseconds!
  // ! Sensor readings may also be up to 2 seconds 'old' (its a very slow sensor)
  // infoPacket infoPacketToSend = {isAlarm, readTemp(), readHumidity(), currentHFSState};
  infoPacket infoPacketToSend = {isAlarm, readTemp(), currentHFSState};
  Serial.print("Sizeof infopacket: ");
  Serial.println(sizeof(infoPacket));
  radio.stopListening();
  if (radio.write(&infoPacketToSend, sizeof(infoPacket)))
  {
    isSuccess = true;
    Serial.println("Info Packet has been sent! the info sent was:");
  };
  radio.startListening(); // start listening again
  Serial.println("Listning again...");
  return isSuccess;
}

// this function is specific to my use case and specific to the powerbank i am using. Do you research and use at your own risk.
// of course the code itself is harmless but the application is risky
void triggerPowerbankButton()
{
  digitalWrite(powerbankResetPin, LOW);
  pinMode(powerbankResetPin, OUTPUT); // Pull the signal low to activate the power button
  delay(powerButtonClickDelay);       // Wait half a second (the only delay in code since any problems here would at best cause a reset...and at worst would cause an explosion :D )
  pinMode(powerbankResetPin, INPUT);  // Release the power button.
}