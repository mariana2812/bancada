"""
Hardware SIMULADO, para testar a interface e a lógica no computador.

Cada classe aqui tem os mesmos métodos da versão real, então o resto do
sistema não percebe a diferença. Quando o programa roda na Raspberry Pi,
este arquivo nem é usado.
"""

import random
import threading
import time

import config

# A bancada real é lenta; na simulação andamos mais rápido para a demonstração
MULTIPLICADOR_VELOCIDADE = 3


class _Mundo:
    """O 'estado físico' da bancada fake, compartilhado entre as peças."""

    def __init__(self):
        self.altura_cm = (config.ALTURA_MINIMA_CM + config.ALTURA_MAXIMA_CM) / 2
        self.carga_kg = 0.0
        self.emergencia = False
        self.direcao = 0  # +1 subindo, -1 descendo, 0 parada


mundo = _Mundo()


def definir_carga(kg):
    """Simula colocar peso na mesa (usado pela interface em modo simulação)."""
    mundo.carga_kg = max(0.0, float(kg))


def definir_emergencia(ativa):
    """Simula apertar/soltar o botão de emergência."""
    mundo.emergencia = bool(ativa)


class MotorSimulado:
    def __init__(self):
        threading.Thread(target=self._mover, daemon=True).start()

    def iniciar(self, direcao):
        mundo.direcao = 1 if direcao == "subir" else -1

    def parar(self):
        mundo.direcao = 0

    def limpar(self):
        mundo.direcao = 0

    def _mover(self):
        passo_s = 0.01
        while True:
            time.sleep(passo_s)
            deslocamento = config.VELOCIDADE_CM_S * MULTIPLICADOR_VELOCIDADE * passo_s
            mundo.altura_cm += mundo.direcao * deslocamento


class SensorAlturaSimulado:
    def ler_altura_cm(self):
        time.sleep(0.02)  # uma medição de verdade também leva um tempinho
        return mundo.altura_cm + random.uniform(-0.05, 0.05)


class CelulaCargaSimulada:
    def ler_peso_kg(self):
        return max(0.0, mundo.carga_kg + random.uniform(-0.01, 0.01))

    def tara(self):
        return True


class EmergenciaSimulada:
    def pressionada(self):
        return mundo.emergencia
