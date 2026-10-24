# STM32 Fault Analyzer

An emulated ARM Cortex-M4 firmware test environment. Bare-metal C++ firmware runs on a simulated STM32 (QEMU), crashes on purpose, and a Python tool catches and decodes the HardFault automatically.

## How it works

```
main.cpp --arm-none-eabi-g++--> fw.elf --QEMU--> virtual UART
                                                     |
                                      bridge.py reads the live output
                                                     |
                                   detects fault -> decodes CFSR/HFSR
```

1. **Firmware (C++):** simulated ADC sensor readings are sent over UART. A HardFault handler dumps the CPU registers when the chip crashes.
2. **Emulator:** QEMU runs the firmware on a Netduino Plus 2 (STM32F405, Cortex-M4).
3. **Python bridge:** launches QEMU, reads the serial stream, detects the crash report, and decodes the fault status registers into plain English.

## Example output

```
Decoded by rules:
  - INVSTATE: CPU tried to run code in an invalid state
  - HFSR FORCED: a smaller fault escalated into a HardFault
  - PC is 0: the CPU jumped to address 0 (likely a NULL function pointer)
```

## Run it

```bash
brew install qemu arm-none-eabi-gcc

arm-none-eabi-g++ -mcpu=cortex-m4 -mthumb -O0 -g -ffreestanding \
  -fno-exceptions -fno-rtti -nostdlib -T linker.ld main.cpp -o fw.elf

python3 bridge.py
```

## Tech

C++, Python, ARM Cortex-M4, QEMU, UART, GCC cross-compiler

## Roadmap

- [ ] More fault scenarios (divide by zero, unaligned access, stack overflow)
- [ ] Claude API integration for automatic diagnosis and fix suggestions