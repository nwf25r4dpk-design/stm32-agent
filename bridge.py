import subprocess

# The same command you typed by hand, written as a list of pieces
QEMU_CMD = ["qemu-system-arm", "-M", "netduinoplus2",
            "-kernel", "fw.elf", "-nographic"]

# Each bit of the CFSR number means a specific kind of error.
# (bit number: name and plain-English meaning)
CFSR_BITS = {
    0:  "IACCVIOL: tried to run code from a forbidden memory area",
    1:  "DACCVIOL: tried to read/write a forbidden memory area",
    8:  "IBUSERR: bus error while fetching an instruction",
    9:  "PRECISERR: bus error on a data access (BFAR shows the address)",
    10: "IMPRECISERR: bus error on a data access (address unknown)",
    16: "UNDEFINSTR: CPU hit an instruction it doesn't understand",
    17: "INVSTATE: CPU tried to run code in an invalid state (e.g. jump to a bad address)",
    18: "INVPC: invalid program counter value on exception return",
    19: "NOCP: used a coprocessor that isn't there",
    24: "UNALIGNED: unaligned memory access",
    25: "DIVBYZERO: divided by zero",
}


def decode_cfsr(value):
    """Return the list of error names whose bits are set in value."""
    found = []
    for bit, text in CFSR_BITS.items():
        if value & (1 << bit):
            found.append(text)
    return found


def parse_fault(lines):
    """Turn lines like 'PC=0x00000000' into a dictionary {'PC': 0}."""
    regs = {}
    for line in lines:
        if "=" in line:
            name, val = line.split("=", 1)
            regs[name.strip()] = int(val.strip(), 16)
    return regs


def report(regs, telemetry):
    print("\n=========== FAULT DETECTED ===========")
    for name, val in regs.items():
        print(f"  {name:5} = 0x{val:08X}")

    print("\nDecoded by rules:")
    for text in decode_cfsr(regs.get("CFSR", 0)):
        print("  -", text)
    if regs.get("HFSR", 0) & (1 << 30):
        print("  - HFSR FORCED: a smaller fault escalated into a HardFault")
    if regs.get("PC", 1) == 0:
        print("  - PC is 0: the CPU jumped to address 0 (likely a NULL function pointer)")

    print("\nLast telemetry before the crash:")
    for line in telemetry[-5:]:
        print("  ", line)
    print("======================================\n")


def main():
    qemu = subprocess.Popen(
        QEMU_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
    )

    telemetry = []     # normal lines (BOOT OK, ADC=...)
    fault_lines = []   # lines inside the crash report
    in_fault = False

    try:
        for raw in qemu.stdout:          # read the chip's output, line by line
            line = raw.strip()
            if not line:
                continue
            print("[chip]", line)

            if "!!FAULT_BEGIN" in line:
                in_fault = True
                fault_lines = []
            elif "!!FAULT_END" in line:
                in_fault = False
                report(parse_fault(fault_lines), telemetry)
                break                    # we got what we wanted, stop watching
            elif in_fault:
                fault_lines.append(line)
            else:
                telemetry.append(line)
    finally:
        qemu.terminate()                 # always shut the pretend chip down


main()