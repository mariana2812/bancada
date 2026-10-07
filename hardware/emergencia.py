"""
Botão de emergência (o único botão físico da bancada).

Ligação: um fio no GPIO e o outro no GND (o Raspberry usa um resistor interno).
Com contato NF (normalmente fechado) o botão fica "ligado" o tempo todo,
e qualquer corte (apertar o botão OU fio solto) é tratado como emergência.
"""

import RPi.GPIO as GPIO

import config


class Emergencia:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(config.PINO_EMERGENCIA, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def pressionada(self):
        nivel = GPIO.input(config.PINO_EMERGENCIA)
        if config.EMERGENCIA_CONTATO_NF:
            return nivel == 1   # NF aberto = pino sobe para 1
        return nivel == 0       # NA fechado = pino cai para 0
