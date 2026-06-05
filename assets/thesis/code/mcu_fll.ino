//// FREQUENCY-LOCKING MCU CODE ////
// Institution: California State University Northridge
// Author: Svarun Soda
// Thesis Advisor: Jeffrey Wiegley, Ph.D.
// Degree: Master of Science in Computer Science
// Thesis Date: May 2026
// Language: C++
// Target System: "Teensy 4.1" by PJRC

//// IDEAL FLL OPERATING TARGET CYCLE RANGES ////
// 150 MHz: 200000 - 400000 cycles
// 600 MHz: 1000000 - 1400000 cycles
// 1.008 GHz: 1800000 - 2200000 cycles

//// INCLUDES ////

#include <SD.h>

//// GLOBAL VARIABLES ////

const uint8_t OscillatorNum = 6;                                          // number of total used oscillator modules in the system

const uint8_t PINS_FLL_ENABLE[OscillatorNum] = {29, 30, 31, 32, 36, 33};  // pins for enabling duty cycle control of the oscillator modules (digital outputs from MCU)
const uint8_t PINS_FLL_SET_A[OscillatorNum] = {23, 18, 41, 0, 5, 24};     // pins for changing the high duty cycles of the oscillator modules (digital outputs from MCU)
const uint8_t PINS_FLL_DIR_A[OscillatorNum] = {21, 16, 39, 2, 7, 26};     // pins for determining the high duty cycle change direction of the oscillator modules (digital outputs from MCU)
const uint8_t PINS_FLL_SET_B[OscillatorNum] = {22, 17, 40, 1, 6, 25};     // pins for changing the low duty cycles of the oscillator modules (digital outputs from MCU)
const uint8_t PINS_FLL_DIR_B[OscillatorNum] = {20, 15, 38, 3, 8, 27};     // pins for determining the low duty cycle change direction of the oscillator modules (digital outputs from MCU)
const uint8_t PINS_SIGNAL[OscillatorNum] = {19, 14, 37, 4, 9, 28};        // pins for reading the clock signals produced by the oscillator modules (digital inputs to MCU)
const uint8_t PINS_PAUSE[OscillatorNum] = {10, 11, 12, 13, 34, 35};       // pins for reading the instantaneous pause states of the oscillator modules (digital inputs to MCU)

const uint32_t OscillatorOperatingCycles = 1200000;                       // target duration for a single duty cycle used by the frequency-locking algorithm (measured in CPU cycles)
const uint32_t OscillatorOperatingCyclesTolerance = 0;                    // frequency-locking algorihtm tolerance (measured in CPU cycles)
const uint32_t FLLIters = 2000;                                           // iteration timeout for frequency-locking algorithm
const uint32_t FLLIterBatches = 1000000000;                                    // number of frequency-locking loops
const uint32_t FLLRollingAverage = 1;                                     // number of rolling averages taken for all duty cycle or phase difference measurements
const bool FLLSaveLogs = false;                                           // toggle for frequency duty cycle logging after every frequency-locking loop

// DO NOT EDIT

#define SDCardConfig SdioConfig(FIFO_SDIO)
FsFile LogFile;

//// MAIN FUNCTIONS ////

// function called upon MCU startup
// initializes digital pins, serial lines, initializes FLL conditions & the clock cycle counter register
FLASHMEM void setup() 
{
  // initializing serial line to computer...
  Serial.begin(9600);

  // initializing all digital pins...
  for (uint8_t i = 0; i < OscillatorNum; i++)
  {
    DigitalPinInit(PINS_FLL_ENABLE[i], OUTPUT);
    DigitalPinInit(PINS_FLL_SET_A[i], OUTPUT);
    DigitalPinInit(PINS_FLL_SET_B[i], OUTPUT);
    DigitalPinInit(PINS_FLL_DIR_A[i], OUTPUT);
    DigitalPinInit(PINS_FLL_DIR_B[i], OUTPUT);
    DigitalPinInit(PINS_SIGNAL[i], INPUT);
    DigitalPinInit(PINS_PAUSE[i], INPUT);
  }

  // initializing FLL conditions...
  for (uint8_t i = 0; i < OscillatorNum; i++)
  {
    OscillatorDutyControlDisable(i);
    OscillatorHighDutyIncrease(i, 1);
    OscillatorLowDutyIncrease(i, 1);
  }

  // initializing CPU cycle counter register...
  Serial.println("initializing CPU cycle counter register...");
  CPUCyclesInit();
  delay(1000);

  // waiting with initial FLL conditions...
  Serial.println("waiting with initial FLL conditions...");
  delay(5000);
}

// function called repeatedly during MCU operation
// contains topmost-level frequency-locking logic
FLASHMEM void loop()
{
  Serial.println("\n---- FREQUENCY-LOCKING STARTED ----\n");

  // enabling duty cycle control for all oscillators...
  for (uint8_t i = 0; i < OscillatorNum; i++)
  {
    OscillatorDutyControlEnable(i);
  }
  delay(1000);

  // running frequency-locking algorithm...
  FLLRun(FLLIters, FLLIterBatches, OscillatorOperatingCycles, OscillatorOperatingCyclesTolerance, FLLRollingAverage, FLLSaveLogs);
  
  // disabling duty cycle control for all oscillators...
  for (uint8_t i = 0; i < OscillatorNum; i++)
  {
    OscillatorDutyControlDisable(i);
  }
  Serial.println("\n---- FREQUENCY-LOCKING FINISHED ----");
  while (true) {delay(1000);}
}

//// FREQUENCY-LOCKING FUNCTIONS ////

// function that executes a series of frequency-locking algorithm loops
inline void FLLRun(const uint32_t iters, const uint32_t batches, const uint32_t operatingCycles, const uint32_t operatingCyclesTolerance, const uint32_t rollingAverage, const bool saveLogs) //@\label{line:fllMcu_FLLRun_Start}@
{
  uint32_t startTimeMicros;
  String data;

  // buffers for duty cycle measurements...
  uint32_t timestampBuff[OscillatorNum][iters];
  uint32_t cycleBuff[OscillatorNum][2][iters];
  bool pauseBuff[OscillatorNum][2][iters];

  Serial.println("running frequency-locking loop:\n" + FLLToString(iters, batches, operatingCycles, operatingCyclesTolerance, rollingAverage) + "\n...");

  // executing for each FLL loop...
  for (uint32_t j = 0; j < batches; j++)
  {
    //Serial.println("\n-- FLL BATCH #" + String(j + 1) + " --");
    // running frequency-locking closed-loop for a pre-determined amount of iterations...
    startTimeMicros = micros();
    for (uint32_t k = 0; k < iters; k++)
    {
      // iterating over each oscillator...
      for (uint8_t i = 0; i < OscillatorNum; i++)
      {
        // running frequency-locking iteration for current oscillator in sequence...
        FLLRunIter(i, k, startTimeMicros, operatingCycles, operatingCyclesTolerance, rollingAverage, (saveLogs ? timestampBuff[i] : nullptr), (saveLogs ? cycleBuff[i][0] : nullptr), (saveLogs ? pauseBuff[i][0] : nullptr), (saveLogs ? cycleBuff[i][1] : nullptr), (saveLogs ? pauseBuff[i][1] : nullptr));
      }
    }

    // saving the measured duty cycles for all oscillators...
    if (saveLogs)
    {
      SDCardInit();
      SDLogFileNew("log_freq_" + String(operatingCycles) + "_" + String(j + 1) + ".txt");
      for (uint32_t i = 0; i < iters; i++)
      {
        for (uint8_t k = 0; k < OscillatorNum; k++)
        {
          data = String(operatingCycles) + "|" + 
                        String(k) + "|0|" + 
                        String(pauseBuff[k][0][i]) + "|" + 
                        String(i) + "|" + 
                        String(timestampBuff[k][i]) + "|" + 
                        String(cycleBuff[k][0][i]);
          SDLogFileWriteLn(data);

          data = String(operatingCycles) + "|" + 
                        String(k) + "|1|" + 
                        String(pauseBuff[k][1][i]) + "|" + 
                        String(i) + "|" + 
                        String(timestampBuff[k][i]) + "|" + 
                        String(cycleBuff[k][1][i]);
          SDLogFileWriteLn(data);
        }
      }
      SDLogFileClose();
      SDCardClose();
    }
  }
} //@\label{line:fllMcu_FLLRun_End}@

// function that executes a single frequency-locking closed-loop iteration for a single oscillator
inline void FLLRunIter(const uint8_t oscillatorIdx, const uint32_t iter, const uint32_t startTimeMicros, const uint32_t operatingCycles, const uint32_t operatingCyclesTolerance, const uint32_t rollingAverage, uint32_t* timestampBuff, uint32_t* cycleBuffHigh, bool* pauseBuffHigh, uint32_t* cycleBuffLow, bool* pauseBuffLow) //@\label{line:fllMcu_FLLRunIter_Start}@
{
  uint32_t measuredCycles;

  // if the operating target cycles is 0, we don't run the iteration for the current oscillator...
  if (operatingCycles == 0)
    return;

  if (timestampBuff != nullptr)
    timestampBuff[iter] = micros() - startTimeMicros;

  // measuring & adjusting the current oscillator's high duty cycle duration...
  {
    measuredCycles = OscillatorGetCyclesHigh(oscillatorIdx, operatingCycles, rollingAverage, true, iter, cycleBuffHigh, pauseBuffHigh);
    
    if (UnsignedGetDifference(measuredCycles, operatingCycles) > operatingCyclesTolerance)
    {
      if (measuredCycles < operatingCycles)
        OscillatorHighDutyIncrease(oscillatorIdx, 1);
      else if (measuredCycles > operatingCycles)
        OscillatorHighDutyDecrease(oscillatorIdx, 1);
    }
  }

  // measuring & adjusting the current oscillator's low duty cycle duration...
  {
    measuredCycles = OscillatorGetCyclesLow(oscillatorIdx, operatingCycles, rollingAverage, true, iter, cycleBuffLow, pauseBuffLow);
    
    if (UnsignedGetDifference(measuredCycles, operatingCycles) > operatingCyclesTolerance)
    {
      if (measuredCycles < operatingCycles)
        OscillatorLowDutyIncrease(oscillatorIdx, 1);
      else if (measuredCycles > operatingCycles)
        OscillatorLowDutyDecrease(oscillatorIdx, 1);
    }
  }
} //@\label{line:fllMcu_FLLRunIter_End}@

// functon that converts a set of frequency-locking algorithm parameters to a printable string
inline String FLLToString(const uint32_t iters, const uint32_t batches, const uint32_t operatingCycles, const uint32_t operatingCyclesTolerance, const uint32_t rollingAverage) //@\label{line:fllMcu_FLLToString_Start}@
{
  return "\titerations: " + String(iters) + 
         "\n\tbatches: " + String(batches) +
         "\n\toperating cycles: " + String(operatingCycles) +
         "\n\toperating cycles tolerance: " + String(operatingCyclesTolerance) +
         "\n\trolling average: " + String(rollingAverage);
} //@\label{line:fllMcu_FLLToString_End}@

//// OSCILLATOR FUNCTIONS ////

inline uint32_t OscillatorGetCyclesHigh(const uint8_t oscillatorIdx, const uint32_t operatingCycles, const uint32_t rollingAverage, const bool subtractPauses, const uint32_t buffIdx, uint32_t* cycleBuff, bool* pauseBuff)
{
  return OscillatorGetCycles(oscillatorIdx, operatingCycles, false, rollingAverage, subtractPauses, buffIdx, cycleBuff, pauseBuff);
}

inline uint32_t OscillatorGetCyclesLow(const uint8_t oscillatorIdx, const uint32_t operatingCycles, const uint32_t rollingAverage, const bool subtractPauses, const uint32_t buffIdx, uint32_t* cycleBuff, bool* pauseBuff)
{
  return OscillatorGetCycles(oscillatorIdx, operatingCycles, true, rollingAverage, subtractPauses, buffIdx, cycleBuff, pauseBuff);
}

// function that measures a single duty cycle duration for a given oscillator
FASTRUN __attribute__((noinline)) uint32_t OscillatorGetCycles(const uint8_t oscillatorIdx, const uint32_t operatingCycles, const bool invert, const uint32_t rollingAverage, const bool subtractPauses, const uint32_t buffIdx, uint32_t* cycleBuff, bool* pauseBuff) //@\label{line:fllMcu_OscillatorGetCycles_Start}@
{
  String str;
  uint32_t startCycles, elapsedCycles, measuredCycles, averaged;
  volatile bool checkState, prevCheckState;
  bool pauseStarted, pauseEncountered;

  measuredCycles = 0;
  averaged = 0;
  pauseEncountered = false;
  
  // measuring the duty cycle for number of rolling averages...
  for (uint32_t i = 0; i < rollingAverage; i++)
  {
    pauseStarted = false;

    // waiting for rising edge...
    checkState = OscillatorGetState(oscillatorIdx, invert);
    do
    {
      prevCheckState = checkState;
      checkState = OscillatorGetState(oscillatorIdx, invert);
    } while (!(checkState && (prevCheckState != checkState)));

    // waiting for falling edge, while measuring cycles...
    startCycles = CPUCyclesGet();
    checkState = OscillatorGetState(oscillatorIdx, invert);
    do
    {
      // if we are subtracting pauses, and we detect an active pausing action on the oscillator that's being measured, we skip this oscillator...
      if (subtractPauses)
      {
        if (OscillatorGetPause(oscillatorIdx))
        {
          pauseStarted = true;
          break;
        }
      }

      prevCheckState = checkState;
      checkState = OscillatorGetState(oscillatorIdx, invert);
    } while (!(!checkState && (prevCheckState != checkState)));

    if (pauseStarted)
    {
      pauseEncountered = true;
      continue;
    }

    // measuring the elapsed cycles...
    elapsedCycles = CPUCyclesGet() - startCycles;
    if (averaged == 0)
      measuredCycles = elapsedCycles;
    else
      measuredCycles = (measuredCycles + elapsedCycles) / 2;
    averaged++;
  }

  if (cycleBuff != nullptr)
    cycleBuff[buffIdx] = measuredCycles;
  if (pauseBuff != nullptr)
    pauseBuff[buffIdx] = pauseEncountered;

  return measuredCycles;
} //@\label{line:fllMcu_OscillatorGetCycles_End}@

// function that retrieves the current instantaneous pause state for a given oscillator
FASTRUN __attribute__((noinline)) volatile bool OscillatorGetPause(const uint8_t oscillatorIdx) //@\label{line:fllMcu_OscillatorGetPause_Start}@
{
  return !DigitalPinGet(PINS_PAUSE[oscillatorIdx]);
} //@\label{line:fllMcu_OscillatorGetPause_End}@

// function that reads the instantaneous output state of a given oscillator
FASTRUN __attribute__((noinline)) volatile bool OscillatorGetState(const uint8_t oscillatorIdx, const bool invert) //@\label{line:fllMcu_OscillatorGetState_Start}@
{
  return invert ? !DigitalPinGet(PINS_SIGNAL[oscillatorIdx]) : DigitalPinGet(PINS_SIGNAL[oscillatorIdx]);
} //@\label{line:fllMcu_OscillatorGetState_End}@

// function that increments the high duty cycle duration of a given oscillator
FASTRUN __attribute__((noinline)) void OscillatorHighDutyIncrease(const uint8_t oscillatorIdx, const uint32_t iters) //@\label{line:fllMcu_OscillatorHighDutyIncrease_Start}@
{
  for (uint32_t i = 0; i < iters; i++)
  {
    // incrementing the current resistance of FCR A module...
    DigitalPinSet(PINS_FLL_DIR_A[oscillatorIdx], HIGH);
    delayNanoseconds(10);
    DigitalPinSet(PINS_FLL_SET_A[oscillatorIdx], HIGH);
    delayNanoseconds(100);
    DigitalPinSet(PINS_FLL_SET_A[oscillatorIdx], LOW);
  }
} //@\label{line:fllMcu_OscillatorHighDutyIncrease_End}@

// function that increments the low duty cycle duration of a given oscillator
FASTRUN __attribute__((noinline)) void OscillatorLowDutyIncrease(const uint8_t oscillatorIdx, const uint32_t iters) //@\label{line:fllMcu_OscillatorLowDutyIncrease_Start}@
{
  for (uint32_t i = 0; i < iters; i++)
  {
    // incrementing the current resistance of FCR B module...
    DigitalPinSet(PINS_FLL_DIR_B[oscillatorIdx], HIGH);
    delayNanoseconds(10);
    DigitalPinSet(PINS_FLL_SET_B[oscillatorIdx], HIGH);
    delayNanoseconds(100);
    DigitalPinSet(PINS_FLL_SET_B[oscillatorIdx], LOW);
  }
} //@\label{line:fllMcu_OscillatorLowDutyIncrease_End}@

// function that decrements the high duty cycle duration of a given oscillator
FASTRUN __attribute__((noinline)) void OscillatorHighDutyDecrease(const uint8_t oscillatorIdx, const uint32_t iters) //@\label{line:fllMcu_OscillatorHighDutyDecrease_Start}@
{
  for (uint32_t i = 0; i < iters; i++)
  {
    // decrementing the current resistance of FCR A module...
    DigitalPinSet(PINS_FLL_DIR_A[oscillatorIdx], LOW);
    delayNanoseconds(10);
    DigitalPinSet(PINS_FLL_SET_A[oscillatorIdx], HIGH);
    delayNanoseconds(100);
    DigitalPinSet(PINS_FLL_SET_A[oscillatorIdx], LOW);
  }
} //@\label{line:fllMcu_OscillatorHighDutyDecrease_End}@

// function that decrements the low duty cycle duration of a given oscillator
FASTRUN __attribute__((noinline)) void OscillatorLowDutyDecrease(const uint8_t oscillatorIdx, const uint32_t iters) //@\label{line:fllMcu_OscillatorLowDutyDecrease_Start}@
{
  for (uint32_t i = 0; i < iters; i++)
  {
    // decrementing the current resistance of FCR B module...
    DigitalPinSet(PINS_FLL_DIR_B[oscillatorIdx], LOW);
    delayNanoseconds(10);
    DigitalPinSet(PINS_FLL_SET_B[oscillatorIdx], HIGH);
    delayNanoseconds(100);
    DigitalPinSet(PINS_FLL_SET_B[oscillatorIdx], LOW);
  }
} //@\label{line:fllMcu_OscillatorLowDutyDecrease_End}@

// function that enables duty cycle control of a given oscillator
FASTRUN __attribute__((noinline)) void OscillatorDutyControlEnable(const uint8_t oscillatorIdx) //@\label{line:fllMcu_OscillatorDutyControlEnable_Start}@
{
  DigitalPinSet(PINS_FLL_ENABLE[oscillatorIdx], HIGH);
} //@\label{line:fllMcu_OscillatorDutyControlEnable_End}@

// function that disables duty cycle control of a given oscillator
FASTRUN __attribute__((noinline)) void OscillatorDutyControlDisable(const uint8_t oscillatorIdx) //@\label{line:fllMcu_OscillatorDutyControlDisable_Start}@
{
  DigitalPinSet(PINS_FLL_ENABLE[oscillatorIdx], LOW);
} //@\label{line:fllMcu_OscillatorDutyControlDisable_End}@

//// SD CARD FUNCTIONS ////

// function that creates a new log file on the SD card with the provided file path
inline void SDLogFileNew(const String filePath) //@\label{line:fllMcu_SDLogFileNew_Start}@
{
  LogFile = SD.sdfs.open(filePath.c_str(), O_WRITE | O_CREAT | O_TRUNC);
  SDLogFileWriteLn("---- START ----\n");
} //@\label{line:fllMcu_SDLogFileNew_End}@

// function that writes a single line to the currently-opened log file on the SD card
inline void SDLogFileWriteLn(const String data) //@\label{line:fllMcu_SDLogFileWriteLn_Start}@
{
  LogFile.println(data);
} //@\label{line:fllMcu_SDLogFileWriteLn_End}@

// function that closes & saves the currently-opened log file on the SD card
inline void SDLogFileClose() //@\label{line:fllMcu_SDLogFileClose_Start}@
{
  LogFile.flush();
  LogFile.close();
} //@\label{line:fllMcu_SDLogFileClose_End}@

// function that initializes a connected SD card
inline void SDCardInit() //@\label{line:fllMcu_SDCardInit_Start}@
{
  while (!SD.sdfs.begin(SDCardConfig))
  {
    Serial.println("unable to find SD card!");
    delay(500);
  }
} //@\label{line:fllMcu_SDCardInit_End}@

// function that closes a connected SD card
inline void SDCardClose() //@\label{line:fllMcu_SDCardClose_Start}@
{
  SD.sdfs.end();
} //@\label{line:fllMcu_SDCardClose_End}@

//// CYCLE COUNTER FUNCTIONS ////

// function that provides the current state of the MCU's internal CPU cycle counter register
inline volatile uint32_t CPUCyclesGet() //@\label{line:fllMcu_CPUCyclesGet_Start}@
{
  return ARM_DWT_CYCCNT;
} //@\label{line:fllMcu_CPUCyclesGet_End}@

// function that initializes the MCU's internal CPU cycle counter register
inline void CPUCyclesInit() //@\label{line:fllMcu_CPUCyclesInit_Start}@
{
  ARM_DEMCR |= ARM_DEMCR_TRCENA;
  ARM_DWT_CTRL |= ARM_DWT_CTRL_CYCCNTENA;
  ARM_DWT_CYCCNT = 0;
} //@\label{line:fllMcu_CPUCyclesInit_End}@

//// SUPPORT FUNCTIONS ////

// function that sets a single digital IO pin to the provided digital value
inline void DigitalPinSet(const uint8_t pin, const bool value) //@\label{line:fllMcu_DigitalPinSet_Start}@
{
  digitalWrite(pin, value);
} //@\label{line:fllMcu_DigitalPinSet_End}@

// function that reads a single digital IO pin
inline bool DigitalPinGet(const uint8_t pin) //@\label{line:fllMcu_DigitalPinGet_Start}@
{
  return digitalReadFast(pin);
} //@\label{line:fllMcu_DigitalPinGet_End}@

// function that initializes a single digital IO pin
inline void DigitalPinInit(const uint8_t pin, const uint8_t mode) //@\label{line:fllMcu_DigitalPinInit_Start}@
{
  pinMode(pin, mode);
} //@\label{line:fllMcu_DigitalPinInit_End}@

// function that gets the absolute difference between two 32-bit unsigned integer numbers
inline uint32_t UnsignedGetDifference(const uint32_t valueA, const uint32_t valueB) //@\label{line:fllMcu_UnsignedGetDifference_Start}@
{
  return (valueB > valueA) ? (valueB - valueA) : (valueA - valueB);
} //@\label{line:fllMcu_UnsignedGetDifference_End}@

// function that subtracts two 32-bit unsigned integer numbers
// truncates result to 0 if an overflow is detected
inline uint32_t SubtractUnsigned(const uint32_t numA, const uint32_t numB) //@\label{line:fllMcu_SubtractUnsigned_Start}@
{
  return (numB > numA) ? 0 : (numA - numB);
} //@\label{line:fllMcu_SubtractUnsigned_End}@