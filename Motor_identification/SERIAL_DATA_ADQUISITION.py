import serial
import time
import csv

# CONFIGURACIÓN
PUERTO          = 'COM5'
BAUD            = 921600
LIMITE_PUNTOS   = 10000 
freq_actual     = 60.0
NOMBRE_ARCHIVO  = f"motor_muestreo_{freq_actual}Hz.csv"

# VARIABLES DE CONTROL
count = 0
pico  = None
ultimo_t_ms = -1.0 # <-- Fundamental para evitar tiempos duplicados o en reversa

try:
    # Aumentamos el timeout a 0.1s. Al usar readline(), esto no hace la lectura más lenta,
    # solo le da un margen de seguridad extra para no cortar líneas a la mitad.
    pico = serial.Serial(port=PUERTO, baudrate=BAUD, timeout=0.1)
    time.sleep(0.5)

    pico.write(b'w\n')
    print("-> Comando 'w' enviado al Pico")
    time.sleep(0.1) # Damos un instante para que el micro procese el comando
    
    # Limpiamos el buffer EXACTAMENTE antes de empezar a leer para botar basura vieja
    pico.reset_input_buffer()

    with open(NOMBRE_ARCHIVO, mode='w', newline='') as f:
        escritor_csv = csv.writer(f)
        escritor_csv.writerow(["TIEMPO_S", "POS_RAD"])

        print(f"--- Capturando {LIMITE_PUNTOS} puntos a {freq_actual} Hz ---")
        print(f"--- Guardando en: {NOMBRE_ARCHIVO} ---")
        print("{:<15} | {:<15}".format("TIEMPO (s)", "POSICION (rad)"))
        print("-" * 35)

        while count < LIMITE_PUNTOS:
            if pico.in_waiting > 0:
                linea = pico.readline().decode('utf-8', errors='ignore').strip()

                if not linea or ',' not in linea:
                    continue

                try:
                    # Separación estricta para evitar listas incompletas
                    parts = linea.split(',')
                    if len(parts) != 2:
                        continue
                        
                    t_ms  = float(parts[0])
                    rad   = float(parts[1])
                    
                    # FILTRO CRÍTICO: Bloqueamos tiempos en reversa o duplicados
                    if t_ms <= ultimo_t_ms:
                        continue 
                        
                    ultimo_t_ms = t_ms # Actualizamos la validación del tiempo
                    t_s   = t_ms / 1000.0

                    escritor_csv.writerow([t_s, rad])
                    count += 1

                    # Imprimimos menos en consola (cada 100). 
                    # Print es una función muy lenta y causa cuellos de botella en Python.
                    if count % 100 == 0: 
                        print(f"{t_s:<15.3f} | {rad:<15.4f} (Punto {count}/{LIMITE_PUNTOS})")
                        f.flush()

                except ValueError:
                    # Si llega basura inconvertible a float (ej. "12.3,a.bc"), se ignora silenciosamente
                    continue

    print(f"\n[ÉXITO] Captura completada: {count} puntos guardados de forma limpia.")

except KeyboardInterrupt:
    print("\nCaptura interrumpida manualmente.")

finally:
    if pico is not None and pico.is_open:
        pico.write(b'x\n') # Comando para detener el motor
        time.sleep(0.1)
        pico.close()
    print("Puerto cerrado.")