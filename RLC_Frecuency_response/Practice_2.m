%FFT CALCULATIONS

% 1.Estimate sample frecuency(fs)
fs = 1 / mean(diff(time_1)); 

% clean
v = v0_1; 
v(isnan(v)) = 0; 

% 3. computing the FFT and convert-> to dB
N = length(v);
f = (0:N-1) * (fs / N);           %Frecuency vector
y_mag = abs(fft(v));              %Normal module
y_db = 20*log10(y_mag + eps);     % dB module 


mitad = floor(N/2);
plot(f(1:mitad), y_db(1:mitad), 'LineWidth', 1.5)
grid on
xlabel('Frecuencia (Hz)')
ylabel('Ganancia (dB)')
title('Espectro de frecuencias ')

% 5. Encontrar la frecuencia 
% Buscamos el pico mas alto a partir del indice 2
[val, idx] = max(y_db(2:mitad)); 
fprintf('Frecuencia detectada : %.2f Hz\n', f(idx+1));



%% 1. PARÁMETROS DEL SISTEMA RLC
% Datos proporcionados
R = 99.4;           % Ohms
L = 100.9e-3;       % Henrios (100.9 mH)
C = 94.7e-9;        % Faradios (94.7 nF)

% Cálculo de parámetros teóricos
f_resonanacia = 1 / (2 * pi * sqrt(L*C));
fprintf('Frecuencia de resonancia teórica: %.2f Hz\n', f_resonanacia);

%% 2. PRE-ASIGNACIÓN DE VARIABLES (Corregida a 12 filas, 1 columna)
num_archivos = 12; % Índices del 0 al 11
f_Hz = zeros(num_archivos, 1);
omega_rad = zeros(num_archivos, 1);
Vi_V = zeros(num_archivos, 1);
Vo_V = zeros(num_archivos, 1);
Ganancia_K = zeros(num_archivos, 1);
Ganancia_dB = zeros(num_archivos, 1);
Fase_deg = zeros(num_archivos, 1);


%% 3. BUCLE DE PROCESAMIENTO (MEJORADO)
for i = 0:11
    try
        % Carga dinámica
        t  = eval(sprintf('time_%d', i));
        vi = eval(sprintf('vi_%d', i));
        vo = eval(sprintf('v0_%d', i));
    catch
        warning('Datos %d no encontrados.', i); continue;
    end
    
    % --- 1. Limpieza y DC ---
    vi(isnan(vi)) = 0; vo(isnan(vo)) = 0;
    vi_ac = vi - mean(vi);
    vo_ac = vo - mean(vo);
    
    % --- 2. Ventaneo Dinámico ---
    N = length(t);
    win = hann(N);
    % MEJORA 1: Cálculo exacto del factor de corrección de amplitud
    % Para Hann suele ser 2, pero esto lo hace exacto para cualquier ventana.
    win_corr = 1 / mean(win); 
    
    % --- 3. Zero-Padding ---
    N_pad = 2^nextpow2(N * 8); 
    
    dt = mean(diff(t));
    fs = 1/dt;
    f_axis = (0:N_pad-1) * (fs / N_pad);
    
    % FFT
    fft_vi = fft(vi_ac .* win, N_pad);
    fft_vo = fft(vo_ac .* win, N_pad);
    
    % --- 4. Buscar el Pico ---
    mitad = floor(N_pad/2);
    offset = 10; 
    [~, idx_rel] = max(abs(fft_vi(offset:mitad)));
    idx = idx_rel + (offset - 1);
    
    f_Hz(i+1) = f_axis(idx);
    omega_rad(i+1) = 2*pi*f_Hz(i+1);
    
    % --- 5. Magnitud y Fase ---
    % Nota: Dividimos por N (longitud original de señal), no por N_pad
    Vi_V(i+1) = abs(fft_vi(idx)) * (2/N) * win_corr; 
    Vo_V(i+1) = abs(fft_vo(idx)) * (2/N) * win_corr;
    
    Ganancia_K(i+1) = Vo_V(i+1) / Vi_V(i+1);
    Ganancia_dB(i+1) = 20*log10(Ganancia_K(i+1));
    
    % Fase "Cruda" (Raw Phase)
    % No intentamos corregirla aquí. Dejamos que angle() nos de +/- 180.
    H_complejo = fft_vo(idx) / fft_vi(idx);
    Fase_deg(i+1) = angle(H_complejo); % Guardamos en RADIANES temporalmente para unwrap
end

%% 4. POST-PROCESAMIENTO 


validos = f_Hz > 0;
f_Hz = f_Hz(validos); 
Vi_V = Vi_V(validos); Vo_V = Vo_V(validos); 
Ganancia_dB = Ganancia_dB(validos); 
Fase_rad_temp = Fase_deg(validos); % Recuperamos la fase en radianes


[f_Hz, sort_idx] = sort(f_Hz);
Vi_V = Vi_V(sort_idx);
Vo_V = Vo_V(sort_idx);
Ganancia_dB = Ganancia_dB(sort_idx);
Fase_rad_temp = Fase_rad_temp(sort_idx);



Fase_rad_unwrapped = unwrap(Fase_rad_temp);
Fase_deg = rad2deg(Fase_rad_unwrapped);


disp('Procesamiento completado con corrección de fase global.');

%% 4. GENERAR TABLA DE RESULTADOS
Resultados = table(f_Hz, omega_rad, Vi_V, Vo_V, Ganancia_K, Ganancia_dB, Fase_deg, ...
    'VariableNames', {'Frecuencia_Hz', 'Omega_rad_s', 'Vi_V', 'Vo_V', 'Ganancia_K', 'Ganancia_dB', 'Fase_deg'});
disp('--- TABLA DE DATOS EXPERIMENTALES (RLC) ---');
disp(Resultados);

%% 5. MODELO TEÓRICO
f_teorica = logspace(1, 5, 10000); 
w_t = 2 * pi * f_teorica;


% H(jw) = (j * RCw) / [ (1 - LCw^2) + j(RCw) ]

RCw = R * C * w_t;                 % Término común (Imag del den y magnitud del num)
Re_denom = 1 - (L * C * w_t.^2);   % Parte Real del denominador
Im_denom = RCw;                    % Parte Imaginaria del denominador

% --- 1. MAGNITUD  ---
% |Num| = RCw (La magnitud de j*RCw es simplemente RCw)
% |Den| = sqrt( Real^2 + Imag^2 )
mag_num = RCw;
mag_den = sqrt(Re_denom.^2 + Im_denom.^2);

mag_lineal = mag_num ./ mag_den;
mag_teorica_db = 20 * log10(mag_lineal);

% --- 2. FASE (Sin usar angle) ---
% Fase(H) = Fase(Numerador) - Fase(Denominador)


fase_num = pi/2; 

% Fase Denominador: atan2(Imag, Real)
fase_den = atan2(Im_denom, Re_denom);

% Fase Total
fase_rad = fase_num - fase_den;

% Conversión a Grados
fase_teorica_deg = rad2deg(fase_rad);



%% 6. PLOT: TEORÍA VS EXPERIMENTAL
figure('Color', 'w', 'Name', 'Bode RLC: Segundo Orden');

% --- Subplot Magnitud ---
subplot(2,1,1)
semilogx(f_teorica, mag_teorica_db, 'k--', 'LineWidth', 2); hold on;
semilogx(f_Hz, Ganancia_dB, 'ro', 'MarkerFaceColor', 'r', 'MarkerSize', 8);
grid on; 
ylabel('Magnitud (dB)');
title('Respuesta en Frecuencia: Magnitud (Resistencia)');
legend('Teoría', 'Experimental', 'Location', 'southwest');
xlim([10 10^6]);

% --- Subplot Fase ---
subplot(2,1,2)
semilogx(f_teorica, fase_teorica_deg, 'k--', 'LineWidth', 2); hold on;
semilogx(f_Hz, Fase_deg, 'bo', 'MarkerFaceColor', 'b', 'MarkerSize', 8);
grid on;
ylabel('Fase (grados)');
xlabel('Frecuencia (Hz)');
title('Respuesta en Frecuencia: Fase');
legend('Teoría', 'Experimental', 'Location', 'southwest');
xlim([10 10^5]);
ylim([-200 100]);


