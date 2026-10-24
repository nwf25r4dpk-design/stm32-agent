#include <stdint.h>

// ---- UART (STM32F4 USART1) ----
#define USART1_SR (*(volatile uint32_t*)0x40011000)
#define USART1_DR (*(volatile uint32_t*)0x40011004)
static void uart_putc(char c) { while (!(USART1_SR & (1u << 7))) {} USART1_DR = c; }
static void uart_puts(const char* s) { while (*s) uart_putc(*s++); }
static void uart_hex(uint32_t v) {
    uart_puts("0x");
    for (int i = 28; i >= 0; i -= 4) uart_putc("0123456789ABCDEF"[(v >> i) & 0xF]);
}
static void kv(const char* k, uint32_t v) { uart_puts(k); uart_putc('='); uart_hex(v); uart_putc('\n'); }

// ---- Fault handling: dump the CPU state so the LLM can analyze it ----
#define SCB_CFSR (*(volatile uint32_t*)0xE000ED28)
#define SCB_HFSR (*(volatile uint32_t*)0xE000ED2C)
#define SCB_BFAR (*(volatile uint32_t*)0xE000ED38)

extern "C" void HardFault_C(uint32_t* s) {
    uart_puts("\n!!FAULT_BEGIN\n");
    kv("R0", s[0]); kv("R1", s[1]); kv("R2", s[2]); kv("R3", s[3]);
    kv("R12", s[4]); kv("LR", s[5]); kv("PC", s[6]); kv("xPSR", s[7]);
    kv("CFSR", SCB_CFSR); kv("HFSR", SCB_HFSR); kv("BFAR", SCB_BFAR);
    uart_puts("!!FAULT_END\n");
    while (1) {}
}
extern "C" __attribute__((naked)) void HardFault_Handler() {
    asm volatile("tst lr, #4 \n ite eq \n mrseq r0, msp \n mrsne r0, psp \n b HardFault_C");
}
extern "C" void Default_Handler() { while (1) {} }

// ---- Application ----
static uint32_t fake_adc(uint32_t t) { return 2000 + (t * 37) % 500; } // simulated sensor

int main() {
    uart_puts("BOOT OK\n");
    for (uint32_t t = 0; t < 10; t++) {
        uart_puts("ADC="); uart_hex(fake_adc(t)); uart_putc('\n');
    }
    uart_puts("Triggering bug...\n");
    void (*bad)() = (void (*)())0x0;   // call a null function pointer
    bad();
    while (1) {}
}

// ---- Startup ----
extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
extern "C" void Reset_Handler() {
    for (uint32_t *s = &_sidata, *d = &_sdata; d < &_edata;) *d++ = *s++;
    for (uint32_t* b = &_sbss; b < &_ebss;) *b++ = 0;
    main();
    while (1) {}
}
extern "C" void HardFault_Handler();
__attribute__((section(".isr_vector"), used))
void (*const vectors[])() = {
    (void (*)())&_estack, Reset_Handler,
    Default_Handler, HardFault_Handler,   // NMI, HardFault
    Default_Handler, Default_Handler, Default_Handler  // MemManage, BusFault, UsageFault
};