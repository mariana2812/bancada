"""
Motor de passo, controlado pelo driver DR-SB050DC056D-CS.

O driver recebe 3 sinais:
    PUL = cada pulso faz o motor dar 1 passo
    DIR = define o sentido (subir ou descer)
    ENA = habilita o motor (opcional)
"""

import threading
import time

import RPi.GPIO as GPIO

import config


class Motor:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(config.PINO_PUL, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(config.PINO_DIR, GPIO.OUT, initial=GPIO.LOW)
        if config.USAR_ENA:
            GPIO.setup(config.PINO_ENA, GPIO.OUT, initial=1 - config.ENA_NIVEL_HABILITA)

        self._andando = threading.Event()   # ligado = gerando pulsos
        self._encerrar = False

        # Uma thread só para gerar os pulsos, para não travar o resto do sistema
        self._thread = threading.Thread(target=self._gerar_pulsos, daemon=True)
        self._thread.start()

    # ---------------------------------------------------------------
    # Comandos usados pelo restante do sistema
    # ---------------------------------------------------------------
    def iniciar(self, direcao):
        """direcao: 'subir' ou 'descer'."""
        nivel_subir = config.DIRECAO_SUBIR_NIVEL
        nivel = nivel_subir if direcao == "subir" else 1 - nivel_subir
        GPIO.output(config.PINO_DIR, nivel)
        time.sleep(0.001)  # o driver precisa do DIR estável antes dos pulsos

        if config.USAR_ENA:
            GPIO.output(config.PINO_ENA, config.ENA_NIVEL_HABILITA)

        self._andando.set()

    def parar(self):
        """Para os pulsos. O motor continua habilitado, segurando a posição."""
        self._andando.clear()

    def limpar(self):
        """Chamado ao encerrar o programa."""
        self._encerrar = True
        self._andando.set()  # acorda a thread para ela terminar
        self._andando.clear()
        GPIO.cleanup()

    # ---------------------------------------------------------------
    # Interno
    # ---------------------------------------------------------------
    def _gerar_pulsos(self):
        meio_periodo = 1 / (2 * config.VELOCIDADE_PASSOS_S)
        while not self._encerrar:
            self._andando.wait()
            while self._andando.is_set():
                GPIO.output(config.PINO_PUL, GPIO.HIGH)
                time.sleep(meio_periodo)
                GPIO.output(config.PINO_PUL, GPIO.LOW)
                time.sleep(meio_periodo)
