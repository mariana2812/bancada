"""Teste isolado do motor de passo no terminal.

Execute na Raspberry Pi com o motor preso e o eixo livre, sem acoplamento
ao fuso na primeira verificacao. O movimento nao usa sensor nem emergencia
do sistema; mantenha o corte fisico da alimentacao ao alcance.
"""

import time
import RPi.GPIO as GPIO
import config
from hardware.motor import Motor


DURACAO_TESTE_S = 1.0
VELOCIDADE_TESTE_PASSOS_S = 200


def main():
    motor = None
    try:
        # Reduz a velocidade apenas neste processo de teste.
        config.VELOCIDADE_PASSOS_S = VELOCIDADE_TESTE_PASSOS_S
        motor = Motor()
        print("Teste isolado do motor. Cada comando dura 1 segundo.")
        print("Digite s para testar subir, d para descer ou q para sair.")

        while True:
            comando = input("Comando [s/d/q]: ").strip().lower()
            if comando == "q":
                break
            if comando not in ("s", "d"):
                print("Comando invalido. Digite s, d ou q.")
                continue

            direcao = "subir" if comando == "s" else "descer"
            print(f"Girando no sentido {direcao} por {DURACAO_TESTE_S:.0f} segundo...")
            motor.iniciar(direcao)
            time.sleep(DURACAO_TESTE_S)
            motor.parar()
            time.sleep(0.02)
            print("Motor parado.")
    except KeyboardInterrupt:
        print("\nTeste interrompido.")
    finally:
        if motor is not None:
            motor.parar()
            time.sleep(0.02)
            motor.limpar()
        else:
            GPIO.cleanup()


if __name__ == "__main__":
    main()