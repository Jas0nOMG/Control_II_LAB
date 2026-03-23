import serial
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from scipy.signal import savgol_filter
import numpy as np

# ────────────────────────────────────────────────
#  CONFIGURACIÓN
# ────────────────────────────────────────────────
PUERTO                = 'COM5'
BAUD                  = 921600
VENTANA_PUNTOS        = 1000
SAVGOL_WIN            = 11         # impar
SAVGOL_POLY           = 5
TASA_ACTUALIZACION_MS = 40         # ~25 Hz refresco

MAX_DT_S              = 0.5
MAX_VEL_RAD_S         = 140.0

# ────────────────────────────────────────────────
#  GUI
# ────────────────────────────────────────────────
app = QtWidgets.QApplication([])

win = pg.GraphicsLayoutWidget(show=True, title="UAQ Control II - Identificación Sistema")
win.resize(1100, 650)

p1 = win.addPlot(title="Posición (rad)", row=0, col=0)
p1.showGrid(x=True, y=True, alpha=0.4)
curve_pos = p1.plot(pen='y', name='Posición')
p1.setLabel('left', "rad")
p1.setLabel('bottom', "Tiempo (s)")

p2 = win.addPlot(title="Velocidad Angular", row=1, col=0)
p2.showGrid(x=True, y=True, alpha=0.4)
curve_vel  = p2.plot(pen='c', name='Filtrada')
curve_vel2 = p2.plot(pen=pg.mkPen('w', width=1, style=QtCore.Qt.DotLine), name='Cruda')
p2.setLabel('left', "rad/s")
p2.setLabel('bottom', "Tiempo (s)")
p2.addLegend()

status_label = pg.LabelItem(justify='left')
win.addItem(status_label, row=2, col=0)

# ────────────────────────────────────────────────
#  BUFFERS
# ────────────────────────────────────────────────
times_list   = []
pos_list     = []
vel_raw_list = []

pos_offset = None   # FIX: referencia para posición relativa
n_errores  = 0
pico       = None

# ────────────────────────────────────────────────
#  ACTUALIZACIÓN
# ────────────────────────────────────────────────
def update():
    global times_list, pos_list, vel_raw_list, n_errores, pos_offset

    if pico is None or not pico.is_open:
        status_label.setText("<span style='color:red'>Puerto serial cerrado</span>")
        return

    while pico.in_waiting > 0:
        try:
            linea = pico.readline().decode('utf-8', errors='ignore').strip()
            if not linea or ',' not in linea:
                continue

            parts = linea.split(',', 1)
            t_ms  = float(parts[0])
            p_raw = float(parts[1])
            t     = t_ms / 1000.0

            # FIX: guardar offset en la primera muestra → posición siempre empieza en 0
            if pos_offset is None:
                pos_offset = p_raw
            p = p_raw - pos_offset

            times_list.append(t)
            pos_list.append(p)

            # Derivada centrada
            if len(pos_list) >= 3:
                dp = pos_list[-1] - pos_list[-3]
                dt = times_list[-1] - times_list[-3]

                if dt > 0 and dt < MAX_DT_S:
                    v_inst = dp / dt
                    if abs(v_inst) < MAX_VEL_RAD_S:
                        vel_raw_list.append(v_inst)
                    else:
                        prev_v = vel_raw_list[-1] if vel_raw_list else 0
                        vel_raw_list.append(prev_v)
                        n_errores += 1
                else:
                    vel_raw_list.append(0)
                    n_errores += 1

        except (ValueError, IndexError):
            n_errores += 1
            continue

    # Ventana deslizante
    if len(times_list) > VENTANA_PUNTOS:
        times_list   = times_list[-VENTANA_PUNTOS:]
        pos_list     = pos_list[-VENTANA_PUNTOS:]
        vel_raw_list = vel_raw_list[-(VENTANA_PUNTOS - 2):]

    # Graficación
    if len(times_list) > 0:
        t_arr = np.array(times_list)
        p_arr = np.array(pos_list)
        curve_pos.setData(t_arr, p_arr)

        if len(vel_raw_list) > 0:
            v_raw_arr = np.array(vel_raw_list)
            t_vel     = t_arr[1:len(v_raw_arr) + 1]
            curve_vel2.setData(t_vel, v_raw_arr)

            if len(v_raw_arr) >= SAVGOL_WIN:
                v_filt = savgol_filter(v_raw_arr, SAVGOL_WIN, SAVGOL_POLY, mode='interp')
                curve_vel.setData(t_vel, v_filt)

    # Barra de estado
    if len(pos_list) > 0:
        status_label.setText(
            "<span style='color:lime'>Online</span> | "
            "Pos: <b>{:.3f} rad</b> | "
            "T: {:.1f}s | "
            "Errores: {}".format(pos_list[-1], times_list[-1], n_errores)
        )

# ────────────────────────────────────────────────
#  INICIO
# ────────────────────────────────────────────────
try:
    pico = serial.Serial(port=PUERTO, baudrate=BAUD, timeout=0.005)
    pico.reset_input_buffer()

    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(TASA_ACTUALIZACION_MS)
    print("Graficando datos de {}...".format(PUERTO))
    app.exec_()

except Exception as e:
    print("Error: {}".format(e))

finally:
    if pico and pico.is_open:
        pico.close()