"""Teste isolado da celula de carga no terminal.

Execute na Raspberry Pi com a bancada parada e a celula sem peso no inicio.
Pressione Ctrl+C para encerrar.
"""

import time
import RPi.GPIO as GPIO
from hardware.celula_carga import CelulaCarga


def main():
	try:
		celula = CelulaCarga()
		print("Teste da celula de carga. Pressione Ctrl+C para sair.")
		print("Deixe a celula vazia durante a tara inicial.")

		while True:
			peso = celula.ler_peso_kg()
			if peso is None:
				texto = "Aguardando leitura do HX711..."
			else:
				texto = f"Peso: {peso:.2f} kg"

			print(texto, end="\r", flush=True)
			time.sleep(0.1)
	except KeyboardInterrupt:
		print("\nTeste encerrado.")
	finally:
		GPIO.cleanup()


if __name__ == "__main__":
	main()
