"""
CONFIGURAÇÃO DA BANCADA
=======================
Este é o ÚNICO arquivo que você precisa editar para ajustar a bancada.
Procure por "PREENCHER" para ver o que ainda precisa ser medido ou conferido.

Tudo que é altura está em CENTÍMETROS e tudo que é carga está em QUILOS.
Os números dos pinos são "BCM" (o número GPIO, não o número do pino físico).
"""

# =====================================================================
# 1) GERAL
# =====================================================================
NOME_SISTEMA = "Bancada Pantográfica"

HOST = "127.0.0.1"   # 127.0.0.1 = só o próprio display acessa a interface
PORTA = 5000

# True  = simula motor e sensores (para testar no computador)
# False = usa o hardware real (Raspberry Pi)
# None  = automático: simula sozinho se não estiver numa Raspberry Pi
SIMULAR = True


# =====================================================================
# 2) LIMITES DE SEGURANÇA
# =====================================================================
ALTURA_MINIMA_CM = 60.0     # PREENCHER: menor altura que a mesa pode chegar
ALTURA_MAXIMA_CM = 120.0    # PREENCHER: maior altura que a mesa pode chegar
CARGA_MAXIMA_KG = 20.0      # A célula de carga suporta 20 kg (pode usar menos, p/ ter margem)


# =====================================================================
# 3) MOTOR DE PASSO + DRIVER  (DR-SB050DC056D-CS)
# =====================================================================
PINO_PUL = 17               # PREENCHER: GPIO ligado em PUL+ do driver
PINO_DIR = 27               # PREENCHER: GPIO ligado em DIR+ do driver
PINO_ENA = 22               # PREENCHER: GPIO ligado em ENA+ (só se USAR_ENA = True)

USAR_ENA = False            # False = deixa ENA desligado (driver sempre habilitado)
ENA_NIVEL_HABILITA = 0      # nível do pino que HABILITA o motor (confira no manual do driver)

DIRECAO_SUBIR_NIVEL = 1     # se a mesa DESCER ao tocar em "Subir", troque para 0

PASSOS_POR_VOLTA = 1600     # PREENCHER: tem que ser igual ao configurado nas chaves SW5-SW8 do driver
FUSO_PASSO_MM = 8.0         # PREENCHER: quanto o fuso avança (mm) a cada volta do motor
VELOCIDADE_PASSOS_S = 1600  # velocidade do motor em passos por segundo (1600 = 1 volta/s)


# =====================================================================
# 4) SENSOR ULTRASSÔNICO (HC-SR04) - mede a altura da mesa
# =====================================================================
PINO_TRIG = 23              # PREENCHER
PINO_ECHO = 24              # PREENCHER (ATENÇÃO: o ECHO é 5V, use divisor de tensão para o Pi)

SENSOR_APONTA_PARA_BAIXO = True   # True = sensor no tampo olhando para o chão
                                  # False = sensor fixo olhando para o tampo/teto
ALTURA_OFFSET_CM = 0.0      # PREENCHER: use o calibrar.py para descobrir este valor


# =====================================================================
# 5) CÉLULA DE CARGA 20 kg + HX711
# =====================================================================
PINO_HX711_DT = 5           # PREENCHER
PINO_HX711_SCK = 6          # PREENCHER

HX711_FATOR = 1.0           # PREENCHER: use o calibrar.py para descobrir este valor
HX711_OFFSET = 0            # valor "zero" da balança (é refeito pela tara)
TARA_AO_INICIAR = True      # True = zera a balança ao ligar (a mesa deve estar vazia!)


# =====================================================================
# 6) BOTÃO DE EMERGÊNCIA (único botão físico)
# =====================================================================
PINO_EMERGENCIA = 16        # PREENCHER: o outro fio do botão vai no GND
EMERGENCIA_CONTATO_NF = True  # True = botão com contato NF (recomendado: se o fio soltar, para)


# =====================================================================
# 7) AJUSTES FINOS (normalmente não precisa mexer)
# =====================================================================
PERIODO_MONITOR_S = 0.03    # de quanto em quanto tempo a segurança confere tudo
TOLERANCIA_ALTURA_CM = 0.3  # erro aceito ao ir para uma altura salva
TIMEOUT_MOVIMENTO_S = 120   # se andar por mais tempo que isso, para sozinho
FALHAS_SENSOR_MAX = 10      # leituras ruins seguidas até parar a mesa
TEMPO_INATIVIDADE_MIN = 10  # minutos sem tocar na tela até sair do login (0 = nunca)


# =====================================================================
# CÁLCULO AUTOMÁTICO (não editar)
# =====================================================================
VELOCIDADE_CM_S = VELOCIDADE_PASSOS_S / PASSOS_POR_VOLTA * FUSO_PASSO_MM / 10
