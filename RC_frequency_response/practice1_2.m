


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
%%
% --- PARÁMETROS DEL CIRCUITO ---
R = 1000;      % Ohmios
C = 2.2e-6;    % Faradios
tau = R * C;

% Pre-asignación (Mismas columnas exactas que pediste)
f_Hz = zeros(13, 1);
omega_rad = zeros(13, 1);
Vi_V = zeros(13, 1);
Vo_V = zeros(13, 1);
Ganancia_K = zeros(13, 1);
Ganancia_dB = zeros(13, 1);
Fase_deg = zeros(13, 1);

%% 2. Bucle de Procesamiento
for i = 1:13
    try
        % Carga dinámica de variables
        t = eval(sprintf('time_%d', i));
        vi = eval(sprintf('vi_%d', i));
        vo = eval(sprintf('v0_%d', i));
    catch
        warning('Datos para el índice %d no encontrados.', i);
        break;
    end
    
    % Parámetros de Muestreo
    dt = mean(diff(t));
    fs = 1 / dt;
    N = length(t);
    f_axis = (0:N-1) * (fs / N);
    
    % --- ACONDICIONAMIENTO DE SEÑAL ---
    % Quitar offset DC
    vi_ac = vi - mean(vi);
    vo_ac = vo - mean(vo);
    
    % Ventana Hann para reducir fugas espectrales (Spectral Leakage)
    win = hann(N);
    win_corr = 2; % Factor de corrección de amplitud para Hann
    
    % FFT con Ventaneo
    fft_vi = fft(vi_ac .* win);
    fft_vo = fft(vo_ac .* win);
    
    % --- CORRECCIÓN CRÍTICA: Buscar frecuencia SOLO en Vin ---
    mitad = floor(N/2);
    % Buscamos el pico máx en Vin omitiendo el índice 1 (DC)
    % Usamos un rango seguro (ej. 2 a mitad)
    [~, relative_idx] = max(abs(fft_vi(2:mitad)));
    idx = relative_idx + 1; 
    
    % --- LLENADO DE TABLA (VARIABLES EXACTAS) ---
    
    % 1. Frecuencia detectada
    f_Hz(i) = f_axis(idx);
    omega_rad(i) = 2 * pi * f_Hz(i);
    
    % 2. Voltajes (Vi_V, Vo_V) usando magnitud FFT precisa
    mag_vi_spec = abs(fft_vi(idx));
    mag_vo_spec = abs(fft_vo(idx));
    
    Vi_V(i) = mag_vi_spec * (2/N) * win_corr;
    Vo_V(i) = mag_vo_spec * (2/N) * win_corr;
    
    % 3. Ganancia
    Ganancia_K(i) = Vo_V(i) / Vi_V(i);
    Ganancia_dB(i) = 20 * log10(Ganancia_K(i));
    
    % 4. Fase
    % Usamos división compleja: Ángulo(Vo/Vi). 
    % Esto resta los ángulos automáticamente y es más robusto al ruido.
    phi_rad = angle(fft_vo(idx) / fft_vi(idx));
    Fase_deg(i) = rad2deg(phi_rad);
end

% Ajuste de fase a rango [-180, 180]
Fase_deg = mod(Fase_deg + 180, 360) - 180;

%% 3. Generar Tabla (Columnas Intactas)
Resultados = table(f_Hz, omega_rad, Vi_V, Vo_V, Ganancia_K, Ganancia_dB, Fase_deg, ...
    'VariableNames', {'Frecuencia_f_Hz', 'Frecuencia_w_rad_s', 'Vi_V', 'Vo_V', 'Ganancia_K', 'Ganancia_dB', 'Fase_grados'});

disp('--- TABLA DE DATOS EXPERIMENTALES ---');
disp(Resultados);


%% 4. Modelo Teórico (FILTRO PASA ALTAS)
% Generamos vector suave logarítmico
if min(f_Hz(f_Hz>0)) > 0
    f_teorica = logspace(log10(min(f_Hz(f_Hz>0))*0.8), log10(max(f_Hz)*1.2), 500);
else
    f_teorica = logspace(0, 6, 500); 
end

w_t = 2 * pi * f_teorica;

% --- CAMBIO PRINCIPAL: Función de Transferencia Pasa Altas ---
% H(jw) = (jwRC) / (1 + jwRC)
num = 1j * w_t * tau;
den = 1 + 1j * w_t * tau;
G_s = num ./ den;

mag_teorica_db = 20 * log10(abs(G_s)); 
fase_teorica_deg = rad2deg(angle(G_s));

%% 5. Plot Inteligente: Teoría vs Experimental

umbral_ruido_db = -40; 
mask_valid = Ganancia_dB > umbral_ruido_db; 

figure('Color', 'w', 'Name', 'Bode Pasa Altas: Teoria vs Experimental');

% --- Magnitud ---
subplot(2,1,1)
semilogx(f_teorica, mag_teorica_db, 'k--', 'LineWidth', 2); hold on;
semilogx(f_Hz, Ganancia_dB, 'ro', 'MarkerFaceColor', 'r', 'MarkerSize', 6);
grid on; 
ylabel('Magnitud (dB)');
title('Magnitud');
legend('Teoria', 'Experimental', 'Location', 'southeast'); % Leyenda movida para no tapar la curva
xlim([min(f_teorica) max(f_teorica)]);

% --- Fase ---
subplot(2,1,2)
semilogx(f_teorica, fase_teorica_deg, 'k--', 'LineWidth', 2); hold on;

% Graficamos puntos válidos
semilogx(f_Hz(mask_valid), Fase_deg(mask_valid), 'bo', 'MarkerFaceColor', 'b', 'MarkerSize', 6);

% Puntos descartados por ruido (opcional)
semilogx(f_Hz(~mask_valid), Fase_deg(~mask_valid), 'o', 'Color', [0.7 0.7 0.7], 'MarkerSize', 4);

grid on;
ylabel('Fase (grados)');
xlabel('Frecuencia (Hz)');
title('Fase');
legend('Teoria', 'Experimental', 'Ruido', 'Location', 'northeast'); % Leyenda movida
xlim([min(f_teorica) max(f_teorica)]);

% --- CAMBIO VISUAL: Ajuste del Eje Y para Fase Positiva ---
ylim([-10 100]); % Rango típico Pasa Altas: 0 a 90 grados