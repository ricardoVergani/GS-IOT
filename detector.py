import cv2
import mediapipe as mp
import serial
from datetime import datetime
import time


# Salva o LOG do sinal com data e hora

def salvar_log(mensagem):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('logs.txt', 'a') as f:
        f.write(f'{timestamp} - {mensagem}\n')


# Calcula a distancia entre os pontos do MediaPipe
def calcular_distancia(a, b):
    return ((a.x - b.x)**2 + (a.y - b.y)**2) ** 0.5

# Try Except para o codigo funcionar com ou sem o arduino
try:
    arduino = serial.Serial('COM3', 9600, timeout=1)
    arduino_conectado = True
    print("Arduino conectado")
except:
    arduino = None
    arduino_conectado = False
    print(" Arduino nao conectado.")


# Acessa o Hands do MediaPipe, cria um rastreador, e desenha as maos
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

# Abre a Webcam conectada
cap = cv2.VideoCapture(0)


# Variaveis passageiras para escrituras na tela, logs e variavel com delay entre logs. 
ultimo_estado = ''
tempo_ultimo_log = 0
delay_log = 3 


# Comeco do programa

while True:
    success, img = cap.read()
    img = cv2.resize(img, (960, 720))
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    resultados = hands.process(img_rgb)

    estado_atual = 'Sem gesto'
    punho_detectado = 0
    indicador_detectado = 0
    mao_aberta_detectada = 0

    if resultados.multi_hand_landmarks:
        for hand_landmarks in resultados.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            palm_point = hand_landmarks.landmark[9]

            # Detecta punho fechado
            closed = True
            for ponta_id in [8, 12, 16, 20]:
                ponta_dedo = hand_landmarks.landmark[ponta_id]
                if calcular_distancia(palm_point, ponta_dedo) > 0.1:
                    closed = False

            if closed:
                punho_detectado += 1
            else:
                # Detecta dedo indicador levantado
                ponta_indicador = hand_landmarks.landmark[8]
                base_indicador = hand_landmarks.landmark[7]
                meio_ponta = hand_landmarks.landmark[12]
                anelar_ponta = hand_landmarks.landmark[16]
                dedinho_ponta = hand_landmarks.landmark[20]

                indicador_esticado = ponta_indicador.y < base_indicador.y
                outros_dobrados = True
                for ponta_id in [12, 16, 20]:
                    ponta_dedo = hand_landmarks.landmark[ponta_id]
                    if calcular_distancia(palm_point, ponta_dedo) > 0.1:
                        outros_dobrados = False
                        break

                if indicador_esticado and outros_dobrados:
                    indicador_detectado+= 1
                else:
                    # Detecta mão aberta
                    dedos_abertos = 0
                    for ponta_id in [8, 12, 16, 20]:
                        ponta_dedo = hand_landmarks.landmark[ponta_id]
                        if calcular_distancia(palm_point, ponta_dedo) > 0.15:
                            dedos_abertos += 1
                    if dedos_abertos >= 4:
                        mao_aberta_detectada += 1

    if punho_detectado >= 1:
        estado_atual = 'Punhos fechados detectados! SOCORRO'
        if arduino_conectado:
            arduino.write(b'2')
    elif mao_aberta_detectada >= 1:
        estado_atual = 'Mao aberta detectada! Acendendo luzes de emergencia'
        if arduino_conectado:
            arduino.write(b'1')
    elif indicador_detectado >= 1:
        estado_atual = 'Dedo indicador levantado detectado! Acionando modo seguro'
        if arduino_conectado:
            arduino.write(b'3')
    else:
        if arduino_conectado:
            arduino.write(b'0')


    # Indica o estado atual
    cv2.putText(img, estado_atual, (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    # Cria o log corretamente
    hora_atual = time.time()
    if estado_atual != ultimo_estado and (hora_atual - tempo_ultimo_log) > delay_log:
        salvar_log(estado_atual)
        print(f'[LOG] {estado_atual}')
        ultimo_estado = estado_atual
        tempo_ultimo_log = hora_atual

    cv2.imshow('Detector de Gestos', img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
if arduino_conectado:
    arduino.close()
