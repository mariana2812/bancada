"""Gera pulsos diretamente para testar o motor e o driver."""

import time

import RPi.GPIO as GPIO

import config


VELOCIDADE_PASSOS_S = 2000
DURACAO_TESTE_S = 10.0


def main():
    pwm = None
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(config.PINO_PUL, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(config.PINO_DIR, GPIO.OUT, initial=GPIO.LOW)

        if config.USAR_ENA:
            GPIO.setup(
                config.PINO_ENA,
                GPIO.OUT,
                initial=1 - config.ENA_NIVEL_HABILITA,
            )

        print("Teste direto do driver. Prenda o motor e deixe o eixo livre.")
        print(f"Cada comando envia {VELOCIDADE_PASSOS_S} passos/s por {DURACAO_TESTE_S}s.")
        print("Digite s para um sentido, d para o outro ou q para sair.")

        while True:
            comando = input("Comando [s/d/q]: ").strip().lower()
            if comando == "q":
                break
            if comando not in ("s", "d"):
                print("Comando invalido. Digite s, d ou q.")
                continue

            nivel_subir = config.DIRECAO_SUBIR_NIVEL
            nivel_direcao = nivel_subir if comando == "s" else 1 - nivel_subir
            GPIO.output(config.PINO_DIR, nivel_direcao)
            time.sleep(0.01)

            if config.USAR_ENA:
                GPIO.output(config.PINO_ENA, config.ENA_NIVEL_HABILITA)

            pwm = GPIO.PWM(config.PINO_PUL, VELOCIDADE_PASSOS_S)
            pwm.start(50)
            time.sleep(DURACAO_TESTE_S)
            pwm.stop()
            pwm = None
            GPIO.output(config.PINO_PUL, GPIO.LOW)
            print("Comando concluido; motor sem pulsos.")
    except KeyboardInterrupt:
        print("\nTeste interrompido.")
    finally:
        if pwm is not None:
            pwm.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()