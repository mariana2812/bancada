"""
Este arquivo junta o motor e os sensores e aplica as regras de segurança:
    - Botão de emergência: para tudo e trava até alguém reiniciar.
    - Carga acima do limite: a mesa para de subir.
    - Limites de altura (mínima e máxima).
    - Sensor de altura com defeito ou movimento longo demais: para.

Uma "thread de monitoramento" roda o tempo todo em segundo plano,
lendo os sensores e conferindo as regras (a cada PERIODO_MONITOR_S).
"""

import statistics
import threading
import time
import config
from hardware import criar_hardware

# Estados possíveis da mesa (a interface usa estes mesmos nomes)
PARADA = "parada"
SUBINDO = "subindo"
DESCENDO = "descendo"
EMERGENCIA = "emergencia"
SOBRECARGA = "sobrecarga"
ERRO = "erro"

HISTERESE_CARGA_KG = 0.5   # evita o alarme "piscar" quando a carga está no limite


class Mesa:
    def __init__(self):
        (self._motor, self._sensor, self._celula,
         self._botao, self.simulado) = criar_hardware()

        self._trava = threading.RLock()   # evita dois comandos ao mesmo tempo

        self.estado = PARADA
        self.mensagem = ""
        self.altura_cm = None
        self.carga_kg = 0.0
        self.alvo_cm = None               # altura que estamos indo buscar (ou None)

        self._historico_altura = []
        self._falhas_sensor = 0
        self._inicio_movimento = 0.0
        self._emergencia_travada = False  # fica ligada até alguém reiniciar
        self._botao_pressionado = False
        self._pedido_tara = False
        self._rodando = True

        threading.Thread(target=self._monitorar, daemon=True).start()

    # =================================================================
    # COMANDOS (chamados pela API)
    # Todos devolvem (deu_certo, mensagem)
    # =================================================================
    def subir(self):
        return self._mover("subir")

    def descer(self):
        return self._mover("descer")

    def parar(self):
        with self._trava:
            self._parar_motor()
            if self.estado in (SUBINDO, DESCENDO):
                self.estado = PARADA
            return True, "Mesa parada."

    def ir_para(self, altura_cm):
        """Move a mesa sozinha até uma altura salva."""
        if not config.ALTURA_MINIMA_CM <= altura_cm <= config.ALTURA_MAXIMA_CM:
            return False, "Essa altura está fora dos limites da mesa."

        with self._trava:
            if self.altura_cm is None:
                return False, "Sensor de altura sem leitura."
            if abs(altura_cm - self.altura_cm) <= config.TOLERANCIA_ALTURA_CM:
                return True, "A mesa já está nessa altura."

            direcao = "subir" if altura_cm > self.altura_cm else "descer"
            return self._mover(direcao, alvo_cm=altura_cm)

    def zerar_balanca(self):
        with self._trava:
            if self.estado in (SUBINDO, DESCENDO):
                return False, "Pare a mesa antes de zerar a balança."
            self._pedido_tara = True   # quem lê a célula é a thread de monitoramento
            return True, "Balança zerada."

    def reiniciar_emergencia(self):
        """Libera a mesa depois de uma emergência."""
        with self._trava:
            if self._botao_pressionado:
                return False, "Destrave o botão de emergência primeiro."
            self._emergencia_travada = False
            self.estado = PARADA
            self.mensagem = ""
            return True, "Sistema reiniciado."

    def status(self):
        """Tudo que a interface precisa para se desenhar."""
        with self._trava:
            return {
                "estado": self.estado,
                "mensagem": self.mensagem,
                "altura_cm": None if self.altura_cm is None else round(self.altura_cm, 1),
                "carga_kg": round(self.carga_kg, 2),
                "alvo_cm": self.alvo_cm,
                "emergencia": self._emergencia_travada,
                "botao_pressionado": self._botao_pressionado,
                "simulado": self.simulado,
            }

    def encerrar(self):
        self._rodando = False
        self._motor.limpar()

    # =================================================================
    # MOVIMENTO
    # =================================================================
    def _mover(self, direcao, alvo_cm=None):
        with self._trava:
            motivo = self._motivo_para_bloquear(direcao)
            if motivo:
                return False, motivo

            # Se já está andando, para um instante antes de inverter o sentido
            if self.estado in (SUBINDO, DESCENDO):
                self._motor.parar()
                time.sleep(0.15)

            self.alvo_cm = alvo_cm
            self._inicio_movimento = time.monotonic()
            self.estado = SUBINDO if direcao == "subir" else DESCENDO
            self.mensagem = ""
            self._motor.iniciar(direcao)
            return True, "Movendo."

    def _motivo_para_bloquear(self, direcao):
        """Devolve o motivo de NÃO poder mover, ou None se pode."""
        if self._emergencia_travada:
            return "Emergência ativa. Destrave o botão e reinicie."
        if self.altura_cm is None:
            return "Sensor de altura sem leitura."
        if direcao == "subir":
            if self.carga_kg > config.CARGA_MAXIMA_KG:
                return "Carga acima do limite. Retire peso da mesa."
            if self.altura_cm >= config.ALTURA_MAXIMA_CM:
                return "A mesa já está na altura máxima."
        else:
            if self.altura_cm <= config.ALTURA_MINIMA_CM:
                return "A mesa já está na altura mínima."
        return None

    def _parar_motor(self, novo_estado=None, mensagem=None):
        """Para o motor e, se pedido, muda o estado e a mensagem."""
        self._motor.parar()
        self.alvo_cm = None
        if novo_estado is not None:
            self.estado = novo_estado
        if mensagem is not None:
            self.mensagem = mensagem

    # =================================================================
    # MONITORAMENTO (roda sozinho em segundo plano)
    # =================================================================
    def _monitorar(self):
        while self._rodando:
            try:
                self._ler_sensores()
                self._verificar_seguranca()
                self._verificar_alvo()
            except Exception as erro:  # qualquer problema inesperado => para por segurança
                with self._trava:
                    self._parar_motor(ERRO, f"Erro interno: {erro}")
            time.sleep(config.PERIODO_MONITOR_S)

    def _ler_sensores(self):
        if self._pedido_tara:
            self._pedido_tara = False
            self._celula.tara()

        # As leituras ficam FORA da trava porque podem demorar alguns milissegundos
        altura = self._sensor.ler_altura_cm()
        peso = self._celula.ler_peso_kg()
        botao = self._botao.pressionada()

        with self._trava:
            self._botao_pressionado = botao

            if altura is None:
                self._falhas_sensor += 1
            else:
                self._falhas_sensor = 0
                # Mediana das últimas 3 leituras: ignora um "pico" isolado
                self._historico_altura = (self._historico_altura + [altura])[-3:]
                self.altura_cm = statistics.median(self._historico_altura)

            if peso is not None:
                self.carga_kg = peso

    def _verificar_seguranca(self):
        with self._trava:
            # 1) EMERGÊNCIA: prioridade máxima
            if self._botao_pressionado:
                self._emergencia_travada = True
            if self._emergencia_travada:
                self._parar_motor(EMERGENCIA, "EMERGÊNCIA! Mesa travada.")
                return

            # 2) CARGA: acima do limite a mesa não sobe
            acima_do_limite = self.carga_kg > config.CARGA_MAXIMA_KG
            if acima_do_limite and self.estado == SUBINDO:
                self._parar_motor(SOBRECARGA, "Carga acima do limite! Subida bloqueada.")
            elif acima_do_limite and self.estado == PARADA:
                self.estado = SOBRECARGA
                self.mensagem = "Carga acima do limite! Retire peso da mesa."
            elif self.estado == SOBRECARGA and self.carga_kg < config.CARGA_MAXIMA_KG - HISTERESE_CARGA_KG:
                self.estado = PARADA
                self.mensagem = ""

            # 3) SENSOR DE ALTURA: sem leitura, não dá para andar com segurança
            if self._falhas_sensor >= config.FALHAS_SENSOR_MAX:
                if self.estado in (SUBINDO, DESCENDO):
                    self._parar_motor(ERRO, "Sensor de altura sem leitura. Mesa parada.")
                elif self.estado == PARADA:
                    self.estado = ERRO
                    self.mensagem = "Sensor de altura sem leitura. Confira a fiação."
            elif self.estado == ERRO and self._falhas_sensor == 0:
                self.estado = PARADA
                self.mensagem = ""

            # 4) LIMITES de altura e de tempo
            if self.altura_cm is None:
                return
            if self.estado == SUBINDO and self.altura_cm >= config.ALTURA_MAXIMA_CM:
                self._parar_motor(PARADA, "Altura máxima atingida.")
            if self.estado == DESCENDO and self.altura_cm <= config.ALTURA_MINIMA_CM:
                self._parar_motor(PARADA, "Altura mínima atingida.")
            if self.estado in (SUBINDO, DESCENDO):
                if time.monotonic() - self._inicio_movimento > config.TIMEOUT_MOVIMENTO_S:
                    self._parar_motor(ERRO, "Tempo máximo de movimento excedido.")

    def _verificar_alvo(self):
        """Quando estamos indo para uma altura salva, para ao chegar nela."""
        with self._trava:
            if self.alvo_cm is None or self.altura_cm is None:
                return
            if self.estado not in (SUBINDO, DESCENDO):
                return

            chegou = abs(self.alvo_cm - self.altura_cm) <= config.TOLERANCIA_ALTURA_CM
            passou = (self.estado == SUBINDO and self.altura_cm >= self.alvo_cm) or \
                     (self.estado == DESCENDO and self.altura_cm <= self.alvo_cm)
            if chegou or passou:
                self._parar_motor(PARADA, "Altura alcançada.")
