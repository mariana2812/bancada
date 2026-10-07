"""
Sensor ultrassônico HC-SR04: mede a altura da mesa.

Como funciona: o sensor manda um "grito" (TRIG) e mede quanto tempo
o eco (ECHO) demora a voltar. Tempo x velocidade do som = distância.
"""

import time

import RPi.GPIO as GPIO

import config

VELOCIDADE_SOM_CM_S = 34300


class SensorAltura:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(config.PINO_TRIG, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(config.PINO_ECHO, GPIO.IN)

    def ler_altura_cm(self):
        """Devolve a altura da mesa em cm, ou None se a leitura falhou."""
        distancia = self.ler_distancia_cm()
        if distancia is None:
            return None

        if config.SENSOR_APONTA_PARA_BAIXO:
            return distancia + config.ALTURA_OFFSET_CM
        return config.ALTURA_OFFSET_CM - distancia

    def ler_distancia_cm(self):
        # 1) Dispara o pulso de 10 microssegundos
        GPIO.output(config.PINO_TRIG, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(config.PINO_TRIG, GPIO.LOW)

        # 2) Espera o eco começar (com limite de tempo, para nunca travar)
        limite = time.perf_counter() + 0.03
        while GPIO.input(config.PINO_ECHO) == 0:
            if time.perf_counter() > limite:
                return None
        inicio = time.perf_counter()

        # 3) Espera o eco terminar
        limite = inicio + 0.03
        while GPIO.input(config.PINO_ECHO) == 1:
            if time.perf_counter() > limite:
                return None
        fim = time.perf_counter()

        # 4) Tempo de ida e volta -> distância (divide por 2)
        distancia = (fim - inicio) * VELOCIDADE_SOM_CM_S / 2

        # O HC-SR04 só é confiável entre 2 cm e 400 cm
        if distancia < 2 or distancia > 400:
            return None
        return distancia
