import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os

# Experimental frequencies in Hz and input
freq_hz = [0.1, 0.2, 0.3, 0.5, 0.9, 1.1, 3, 5, 10, 11.1, 15, 20, 50, 60, 70, 80, 90, 100, 200, 500]
V_in = 5.2 * 0.1  # Input amplitude [V]

w_exp, mag_db, B_vals, f_vals = [], [], [], []

# Signal Processing
for f in freq_hz:
    name = f"motor_muestreo_{float(f)}Hz.csv"
    if os.path.exists(name):
        df = pd.read_csv(name)
        t, pos = df.iloc[:, 0].values, df.iloc[:, 1].values

        vel = np.gradient(pos, t)
        v_clean = vel - np.mean(vel)

        N = len(v_clean)
        y_fft = np.abs(np.fft.fft(v_clean)) * (2 / N)
        B = np.max(y_fft[1:N//2])

        w_exp.append(2 * np.pi * f)
        mag_db.append(20 * np.log10(B / V_in))
        B_vals.append(B)
        f_vals.append(f)

w_exp, mag_db = np.array(w_exp), np.array(mag_db)

# Curve fit: G(s) = Y / (s + c)
def bode_model(w, Y, c):
    return 20 * np.log10(Y) - 20 * np.log10(np.sqrt(w**2 + c**2))

popt, _ = curve_fit(bode_model, w_exp, mag_db, p0=[400, 18], bounds=(0.01, np.inf))
Y_id, c_id = popt
constant_contribution = 20 * np.log10(Y_id / c_id)

# Plotting
w_fine = np.logspace(-2, 4, 1000)
plt.figure(figsize=(12, 7))
plt.semilogx(w_exp, mag_db, 'ro', label='Measured')
plt.semilogx(w_fine, bode_model(w_fine, *popt), 'b', lw=2, label='Model')

plt.semilogx(w_fine[w_fine < c_id*2], [constant_contribution]*sum(w_fine < c_id*2), 'g--', label='0 dB/dec')
plt.semilogx(w_fine[w_fine > c_id/2], 20*np.log10(Y_id) - 20*np.log10(w_fine[w_fine > c_id/2]), 'm--', label='-20 dB/dec')

plt.grid(True, which="both", alpha=0.3)
plt.title(f'Bode Plot: G(s) = {Y_id:.2f} / (s + {c_id:.2f})')
plt.xlabel('Frequency [rad/s]')
plt.ylabel('Magnitude [dB]')
plt.legend()
plt.show()

# ── TABLA DE RESULTADOS ──────────────────────────────────────────────────
print("\n" + "="*60)
print(f"{'ω̄ [rad/s]':>14} {'f [Hz]':>10} {'A [V]':>10} {'B [rad/s]':>12} {'|G| [dB]':>10}")
print("-"*60)
for f, w, B, db in zip(f_vals, w_exp, B_vals, mag_db):
    print(f"{w:>14.4f} {f:>10.2f} {V_in:>10.4f} {B:>12.4f} {db:>10.4f}")
print("="*60)

print(f"\nIdentification Results:")
print(f"  Y  = {Y_id:.4f}  [rad/(s·V)]")
print(f"  c  = {c_id:.4f}  [rad/s]")
print(f"  G(s) = {Y_id:.2f} / (s + {c_id:.2f})")
print(f"  Ganancia estatica (DC) = {Y_id/c_id:.4f}  [rad/(s·V)]  =  {constant_contribution:.2f} dB")