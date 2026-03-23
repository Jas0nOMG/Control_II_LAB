import math
from machine import Pin, PWM, Timer, UART
import utime
import sys
import uselect

# ────────────────────────────────────────────────
#  HARDWARE CONFIG
# ────────────────────────────────────────────────
IN1 = Pin(18, Pin.OUT)
IN2 = Pin(17, Pin.OUT)
ENA = PWM(Pin(16))
ENA.freq(500000)

pin_a = Pin(0, Pin.IN, Pin.PULL_UP)
pin_b = Pin(1, Pin.IN, Pin.PULL_UP)

uart = UART(1, baudrate=921600, tx=Pin(4), rx=Pin(5), timeout=0)

# ────────────────────────────────────────────────
#  PARÁMETROS
# ────────────────────────────────────────────────
PPR              = 955
rad_factor    = 2*math.pi / (PPR*4)   # x4 cuadratura completa

DIV              = 100
U0               = 0.85
A_AMP            = 0.1
SAMPLE_PERIOD_MS = 1                    #fs = 1000 Hz

# ────────────────────────────────────────────────
#  VARIABLES GLOBALES
# ────────────────────────────────────────────────
counter        = 0
motor_state    = 0
index          = 0
target_freq    = 60.0
sample_pending = False

t0_us         = utime.ticks_us()
last_degrees  = 0.0
last_time_ms  = 0

vsen = [int((U0 + A_AMP * math.sin(2 * math.pi * j / DIV)) * 65535) for j in range(DIV)]

# ────────────────────────────────────────────────
#  ENCODER — TABLA DE CUADRATURA
# ────────────────────────────────────────────────
_QEM = ( 0, -1,  1,  0,
         1,  0,  0, -1,
        -1,  0,  0,  1,
         0,  1, -1,  0)

_qstate = (pin_a.value() << 1) | pin_b.value()

def encoder_isr(pin):
    global counter, _qstate
    new_state = (pin_a.value() << 1) | pin_b.value()
    counter  += _QEM[(_qstate << 2) | new_state]
    _qstate   = new_state

pin_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=encoder_isr)
pin_b.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=encoder_isr)

# ────────────────────────────────────────────────
#  CALLBACKS DE TIMERS
# ────────────────────────────────────────────────
def pwm_callback(t):
    global index
    if motor_state == 0:
        return
    ENA.duty_u16(vsen[index])
    IN1(1); IN2(0)              # siempre adelante
    index = (index + 1) % DIV

def sample_callback(t):
    global last_degrees, last_time_ms, sample_pending
    if motor_state == 0:
        return
    last_degrees  = counter * rad_factor
    last_time_ms  = utime.ticks_ms()
    sample_pending = True

tim_pwm    = Timer() #type:ignore
tim_sample = Timer() # type: ignore #ignore

# ────────────────────────────────────────────────
#  CONTROL DE MOTORES
# ────────────────────────────────────────────────
def start_motors(freq=None):
    global target_freq, index, t0_us, counter   # FIX: counter incluido
    tim_pwm.deinit()
    tim_sample.deinit()

    if freq is not None:
        target_freq = freq

    counter = 0                     # FIX: resetea posición a 0° al arrancar
    index   = 0
    t0_us   = utime.ticks_us()

    pwm_freq_hz = int(target_freq * DIV)
    tim_pwm.init(freq=pwm_freq_hz, mode=Timer.PERIODIC, callback=pwm_callback)
    tim_sample.init(period=SAMPLE_PERIOD_MS, mode=Timer.PERIODIC, callback=sample_callback)

def stop_motors():
    global motor_state
    motor_state = 0
    tim_pwm.deinit()
    tim_sample.deinit()
    ENA.duty_u16(0)
    IN1(0); IN2(0)

# ────────────────────────────────────────────────
#  BUCLE PRINCIPAL
# ────────────────────────────────────────────────
spoll = uselect.poll()
spoll.register(sys.stdin, uselect.POLLIN)

print("Sistema Listo. Comandos: f [val], w, x, q")
print("DEGREE_FACTOR={:.5f}  (PPR={} x4)".format(rad_factor, PPR))

try:
    while True:
        # Tarea 1: Envío UART
        if sample_pending:
            msg = "{},{:.2f}\n".format(last_time_ms, last_degrees)
            uart.write(msg)
            sample_pending = False

        # Tarea 2: Teclado
        if spoll.poll(1):
            line = sys.stdin.readline().strip().lower()
            if line.startswith('f'):
                try:
                    val = float(line.replace('f', '').strip())
                    if val <= 0:
                        raise ValueError("debe ser > 0")
                    start_motors(val)
                    print("-> Frecuencia: {} Hz".format(val))
                except Exception as e:
                    print("Error:", e)
            elif line == 'w':
                motor_state = 1
                start_motors()
                print("-> Marcha Adelante")
            elif line == 'x':
                stop_motors()
                print("-> Paro")
            elif line == 'q':
                break

        utime.sleep_us(10)

except KeyboardInterrupt:
    pass
finally:
    stop_motors()
    print("Sistema cerrado.")