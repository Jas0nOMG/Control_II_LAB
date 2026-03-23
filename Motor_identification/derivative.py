import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

# ────────────────────────────────────────────────
#  CONFIGURACIÓN
# ────────────────────────────────────────────────
base_dir = r'D:\Semesters Data\6to semestre\control II\Lab\3\Motor_identification'
output_dir = os.path.join(base_dir, 'Graficas_Guardadas')

# Crear la carpeta de salida si no existe
os.makedirs(output_dir, exist_ok=True)

freq_hz = [0.1, 0.2, 0.3, 0.5, 0.9, 1.1, 3.0, 5.0, 10.0, 11.1, 15.0, 17.7, 20.0, 30.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 200.0, 500.0]

# ────────────────────────────────────────────────
#  PROCESAMIENTO EN BUCLE
# ────────────────────────────────────────────────
for freq in freq_hz:
    # Construcción dinámica del nombre del archivo basado en tu imagen (.csv)
    file_name = f'motor_muestreo_{freq}Hz.csv'
    file_path = os.path.join(base_dir, file_name)
    
    if not os.path.exists(file_path):
        print(f" Archivo no encontrado, saltando: {file_name}")
        continue
        
    print(f"Procesando: {file_name}...")

    # CARGA DE DATOS
    try:
        data = np.genfromtxt(file_path, delimiter=',', skip_header=1)
    except Exception as e:
        print(f"Error al leer {file_name}: {e}")
        continue

    if data.ndim < 2 or data.shape[0] == 0:
        print(f"El archivo está vacío o mal formado: {file_name}")
        continue

    time_s   = data[:, 0]   # segundos
    position = data[:, 1]   # rad 

    # PRE-PROCESAMIENTO
    time_s   = time_s - time_s[0]          # empieza en t=0
    position = position - position[0]      # empieza en pos=0 rad
    
    # Prevenir divisiones por cero si el archivo tiene muy pocos datos
    if len(time_s) < 2:
        print(f"Datos insuficientes en {file_name}")
        continue
        
    dt = float(np.mean(np.diff(time_s)))

    # FILTRO SAVITZKY-GOLAY (Ajuste dinámico de ventana)
    polyorder = 5
    data_length = len(position)
    window_length = 71 
    
    # La ventana debe ser impar y menor o igual al número de datos
    if window_length >= data_length:
        window_length = data_length - 1 if data_length % 2 == 0 else data_length
        # El orden del polinomio debe ser menor que la ventana
        if polyorder >= window_length:
            polyorder = window_length - 1
            if polyorder < 1:
                print(f"No hay suficientes datos para filtrar {file_name}")
                continue

    position_filtered = savgol_filter(position, window_length, polyorder)
    velocity_sg       = savgol_filter(position, window_length, polyorder,
                                      deriv=1, delta=dt)

    # GRÁFICAS
    plt.figure(figsize=(12, 10))

    # Subplot Posición
    plt.subplot(2, 1, 1)
    plt.plot(time_s, position,          color='lightgray',  label='Posición cruda')
    plt.plot(time_s, position_filtered, color='royalblue',
             linewidth=2,                                   label='Posición filtrada')
    plt.title(f'Identificación Motor ({freq} Hz): Posición Angular', fontsize=14)
    plt.ylabel('Posición (rad)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    # Subplot Velocidad
    plt.subplot(2, 1, 2)
    plt.plot(time_s, velocity_sg, color='darkmagenta',
             linewidth=1.5,             label='Velocidad Angular')
    plt.title(f'Identificación Motor ({freq} Hz): Velocidad Angular', fontsize=14)
    plt.xlabel('Tiempo (s)', fontsize=12)
    plt.ylabel('Velocidad (rad/s)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    plt.tight_layout()
    
    # GUARDAR IMAGEN
    save_path = os.path.join(output_dir, f'Grafica_Motor_{freq}Hz.png')
    plt.savefig(save_path, dpi=300, bbox_inches='tight') # Alta resolución
    plt.close() # Cierra la figura para liberar memoria RAM

print(f"\n ¡Proceso terminado! Todas las gráficas se guardaron en: {output_dir}")