"""
Célula de carga de 20 kg lida pelo amplificador HX711.

O HX711 entrega um número de 24 bits (leitura "bruta").
    peso (kg) = (leitura bruta - offset) / fator
O offset é o "zero" (tara) e o fator é descoberto com o calibrar.py.
"""

import time
import RPi.GPIO as GPIO
import config


class CelulaCarga:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(config.PINO_HX711_SCK, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(config.PINO_HX711_DT, GPIO.IN)

        self.offset = config.HX711_OFFSET
        self._ultimos = []  # últimas leituras, para suavizar

        if config.TARA_AO_INICIAR:
            self.tara()

    # ---------------------------------------------------------------
    # Usado pelo sistema
    # ---------------------------------------------------------------
    def ler_peso_kg(self):
        """Devolve o peso em kg, ou None se o HX711 ainda não tem leitura nova."""
        bruto = self._ler_bruto()
        if bruto is None:
            return None

        peso = (bruto - self.offset) / config.HX711_FATOR

        # Média das últimas 5 leituras (tira o "tremido" do número)
        self._ultimos.append(peso)
        self._ultimos = self._ultimos[-5:]
        return sum(self._ultimos) / len(self._ultimos)

    def tara(self):
        """Zera a balança (mesa vazia = 0 kg)."""
        media = self.ler_bruto_medio(amostras=10)
        if media is None:
            print("[celula] AVISO: HX711 não respondeu, tara não feita. Confira a fiação.")
            return False
        self.offset = media
        self._ultimos = []
        return True

    def ler_bruto_medio(self, amostras=10):
        """Média de várias leituras brutas. Usado na tara e no calibrar.py."""
        leituras = []
        limite = time.time() + 3
        while len(leituras) < amostras and time.time() < limite:
            bruto = self._ler_bruto()
            if bruto is not None:
                leituras.append(bruto)
            else:
                time.sleep(0.01)
        if not leituras:
            return None
        return sum(leituras) / len(leituras)

    # ---------------------------------------------------------------
    # Interno: leitura bit a bit do HX711
    # ---------------------------------------------------------------
    def _ler_bruto(self):
        # O HX711 avisa que tem dado novo colocando DT em nível baixo
        if GPIO.input(config.PINO_HX711_DT) == 1:
            return None

        valor = 0
        for _ in range(24):
            GPIO.output(config.PINO_HX711_SCK, GPIO.HIGH)
            GPIO.output(config.PINO_HX711_SCK, GPIO.LOW)
            valor = (valor << 1) | GPIO.input(config.PINO_HX711_DT)

        # 25º pulso: escolhe canal A com ganho 128 para a próxima leitura
        GPIO.output(config.PINO_HX711_SCK, GPIO.HIGH)
        GPIO.output(config.PINO_HX711_SCK, GPIO.LOW)

        # O número vem em complemento de 2 (pode ser negativo)
        if valor & 0x800000:
            valor -= 1 << 24
        return valor
