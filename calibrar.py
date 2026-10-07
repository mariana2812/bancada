"""
CALIBRAÇÃO DA BANCADA (rode na Raspberry Pi, com o hardware ligado):

    python3 calibrar.py

Menu:
    1) Altura   -> descobre o ALTURA_OFFSET_CM
    2) Carga    -> descobre o HX711_FATOR (precisa de um peso conhecido)
    3) Motor    -> confere o sentido (Subir realmente sobe?)
    4) Emergência -> confere o botão

No final de cada passo o programa mostra a linha para colar no config.py.
"""

import statistics
import time

import config
from hardware import _deve_simular


def pedir_numero(texto):
    while True:
        try:
            return float(input(texto).replace(",", "."))
        except ValueError:
            print("  Digite um número, por exemplo 85,5")


# ---------------------------------------------------------------------
def calibrar_altura(sensor):
    print("\n== ALTURA ==")
    print("Deixe a mesa parada e meça a altura REAL com uma trena (em cm).")
    real = pedir_numero("Altura real medida com a trena: ")

    print("Lendo o sensor...")
    leituras = []
    for _ in range(15):
        distancia = sensor.ler_distancia_cm()
        if distancia is not None:
            leituras.append(distancia)
        time.sleep(0.06)

    if len(leituras) < 5:
        print("O sensor quase não respondeu. Confira TRIG, ECHO e a alimentação.")
        return

    distancia = statistics.median(leituras)
    if config.SENSOR_APONTA_PARA_BAIXO:
        offset = real - distancia
    else:
        offset = real + distancia

    print(f"Distância lida pelo sensor: {distancia:.1f} cm")
    print("\nCole no config.py:")
    print(f"ALTURA_OFFSET_CM = {offset:.1f}")


# ---------------------------------------------------------------------
def calibrar_carga(celula):
    print("\n== CARGA ==")
    input("1) Deixe a célula SEM peso e aperte Enter... ")
    zero = celula.ler_bruto_medio(20)
    if zero is None:
        print("O HX711 não respondeu. Confira DT, SCK e a alimentação.")
        return

    peso = pedir_numero("2) Coloque um peso conhecido e digite quantos kg ele tem: ")
    input("   Aperte Enter quando o peso estiver parado... ")
    com_peso = celula.ler_bruto_medio(20)
    if com_peso is None:
        print("O HX711 parou de responder.")
        return

    fator = (com_peso - zero) / peso
    print(f"\nLeitura sem peso: {zero:.0f}   com peso: {com_peso:.0f}")
    print("\nCole no config.py:")
    print(f"HX711_FATOR = {fator:.2f}")


# ---------------------------------------------------------------------
def testar_motor(motor):
    print("\n== MOTOR ==")
    print("ATENÇÃO: a mesa vai SUBIR por 2 segundos. Deixe o caminho livre e")
    print("fique com a mão perto do botão de emergência.")
    if input("Digite 's' para continuar: ").strip().lower() != "s":
        return

    motor.iniciar("subir")
    time.sleep(2)
    motor.parar()

    resposta = input("A mesa subiu? (s = subiu / n = desceu / x = não mexeu): ").strip().lower()
    if resposta == "n":
        novo = 1 - config.DIRECAO_SUBIR_NIVEL
        print("\nTroque no config.py:")
        print(f"DIRECAO_SUBIR_NIVEL = {novo}")
    elif resposta == "x":
        print("Confira: alimentação do driver (24-50 V), fios A+/A-/B+/B-, PUL/DIR e")
        print("as chaves de corrente (SW1-SW4) e de passos (SW5-SW8) do driver.")
    else:
        print("Perfeito, o sentido está certo.")


# ---------------------------------------------------------------------
def testar_emergencia(botao):
    print("\n== EMERGÊNCIA ==")
    print("Aperte e solte o botão algumas vezes. Ctrl+C para sair.")
    try:
        anterior = None
        while True:
            atual = botao.pressionada()
            if atual != anterior:
                print("  ACIONADO" if atual else "  liberado")
                anterior = atual
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()


# ---------------------------------------------------------------------
def main():
    if _deve_simular():
        print("Este computador não é uma Raspberry Pi (ou SIMULAR = True no config.py).")
        print("A calibração só funciona com o hardware real.")
        return

    from hardware.motor import Motor
    from hardware.sensor_altura import SensorAltura
    from hardware.celula_carga import CelulaCarga
    from hardware.emergencia import Emergencia

    motor, sensor, celula, botao = Motor(), SensorAltura(), CelulaCarga(), Emergencia()

    try:
        while True:
            print("\n1) Altura   2) Carga   3) Motor   4) Emergência   0) Sair")
            opcao = input("Escolha: ").strip()
            if opcao == "1":
                calibrar_altura(sensor)
            elif opcao == "2":
                calibrar_carga(celula)
            elif opcao == "3":
                testar_motor(motor)
            elif opcao == "4":
                testar_emergencia(botao)
            elif opcao == "0":
                break
    finally:
        motor.limpar()


if __name__ == "__main__":
    main()
