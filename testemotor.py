"""Teste independente do motor + driver, com o eixo livre da bancada.

Execute na Raspberry Pi: python3 testemotor.py
Nao usa config.py, sensores, interface ou controles da mesa.
"""

import time

import RPi.GPIO as GPIO

# Numeracao BCM: GPIO 17 = pino fisico 11; GPIO 27 = pino fisico 13.
# Ajuste estes valores conforme os fios do teste separado.
PINO_PUL = 17
PINO_DIR = 27
PINO_ENA = 22
USAR_ENA = False
ENA_NIVEL_HABILITA = 0

# Deve coincidir com o ajuste Pulse/rev nas chaves do driver.
PULSOS_POR_ROTACAO = 2000
ROTACOES_POR_COMANDO = 1
DURACAO_TESTE_S = 10.0  # tempo nominal; o sistema pode acrescentar atrasos
PULSOS_POR_COMANDO = PULSOS_POR_ROTACAO * ROTACOES_POR_COMANDO
VELOCIDADE_PASSOS_S = PULSOS_POR_COMANDO / DURACAO_TESTE_S


def girar(nivel_direcao):
    GPIO.output(PINO_DIR, nivel_direcao)
    if USAR_ENA:
        GPIO.output(PINO_ENA, ENA_NIVEL_HABILITA)
    time.sleep(0.01)

    meio_periodo = 1 / (2 * VELOCIDADE_PASSOS_S)
    try:
        # Conte os pulsos para completar a volta, mesmo com atrasos do Linux.
        for _ in range(PULSOS_POR_COMANDO):
            GPIO.output(PINO_PUL, GPIO.HIGH)
            time.sleep(meio_periodo)
            GPIO.output(PINO_PUL, GPIO.LOW)
            time.sleep(meio_periodo)
    finally:
        GPIO.output(PINO_PUL, GPIO.LOW)
        if USAR_ENA:
            GPIO.output(PINO_ENA, 1 - ENA_NIVEL_HABILITA)


def main():
    pinos = [PINO_PUL, PINO_DIR] + ([PINO_ENA] if USAR_ENA else [])
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PINO_PUL, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(PINO_DIR, GPIO.OUT, initial=GPIO.LOW)

        if USAR_ENA:
            GPIO.setup(
                PINO_ENA,
                GPIO.OUT,
                initial=1 - ENA_NIVEL_HABILITA,
            )

        print("Teste direto do driver. Prenda o motor e deixe o eixo livre.")
        print(f"Pinos BCM: PUL={PINO_PUL}, DIR={PINO_DIR}; ENA usado: {USAR_ENA}.")
        print(f"Configure o driver para {PULSOS_POR_ROTACAO} pulsos por rotacao.")
        print(
            f"Cada comando envia {PULSOS_POR_COMANDO} pulsos "
            f"({ROTACOES_POR_COMANDO} volta), em aproximadamente {DURACAO_TESTE_S}s."
        )
        print("Digite s para um sentido, d para o outro ou q para sair.")

        while True:
            comando = input("Comando [s/d/q]: ").strip().lower()
            if comando == "q":
                break
            if comando not in ("s", "d"):
                print("Comando invalido. Digite s, d ou q.")
                continue

            girar(1 if comando == "s" else 0)
            print("Comando concluido; motor sem pulsos.")
    except (KeyboardInterrupt, EOFError):
        print("\nTeste interrompido.")
    finally:
        GPIO.cleanup(pinos)


if __name__ == "__main__":
    main()
