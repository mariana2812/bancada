# Testes com hardware real

O codigo esta configurado com SIMULAR = False. Isso nao confirma a fiacao,
os limites mecanicos nem a calibracao. Nao execute a bancada completa antes
de confirmar os valores abaixo. Execute apenas um programa por vez.

## Dados para confirmar ou enviar

| Dado | Valor atual / informacao necessaria |
|---|---|
| Raspberry Pi | Modelo exato e versao do Raspberry Pi OS |
| Motor e driver | Modelo, corrente nominal do motor, tensao da fonte e foto da tabela/chaves do driver |
| Pulsos por volta | 2000 no teste e no config.py; confirmar esse ajuste no driver |
| Ligacao do driver | Informar onde PUL+, PUL-, DIR+, DIR-, ENA+, ENA- estao ligados e se existe conversor de nivel |
| ENA | USAR_ENA = False; confirmar se esta desconectado e se o driver fica habilitado assim |
| Sentido | DIRECAO_SUBIR_NIVEL = 1; informar se o comando subir realmente sobe |
| Velocidade | Teste separado: 200 pulsos/s; bancada: 1600 pulsos/s. Informar velocidade que funcionou sem perder passos |
| Fuso | FUSO_PASSO_MM = 8.0; informar avanco por volta e eventual reducao entre motor e fuso |
| Alturas | ALTURA_MINIMA_CM = 60 e ALTURA_MAXIMA_CM = 120 sao valores a confirmar por medicao; usar limites operacionais com margem dos batentes |
| Carga | CARGA_MAXIMA_KG = 20; informar limite seguro da estrutura e capacidade real da celula |
| Sensor de altura | Modelo, posicao, alvo e sentido; SENSOR_APONTA_PARA_BAIXO = True |
| Offset de altura | ALTURA_OFFSET_CM = 0 e provisório; enviar resultado da opcao 1 do calibrar.py |
| HX711 | Modelo, pinos DT/SCK, alimentacao e ligacao dos fios da celula |
| Calibracao de carga | HX711_FATOR = 1 e provisório; enviar resultado da opcao 2 e massa conhecida em kg |
| Tara | TARA_AO_INICIAR = True: iniciar com a mesa vazia; se False, preencher HX711_OFFSET da calibracao |
| Emergencia | PINO_EMERGENCIA = 16, EMERGENCIA_CONTATO_NF = True; confirmar contato NF/NA e corte eletrico do driver |

## Pinos atuais

Numeracao BCM no codigo; a coluna fisica refere-se ao conector de 40 pinos.

| Sinal | GPIO BCM | Pino fisico |
|---|---:|---:|
| PUL | 17 | 11 |
| DIR | 27 | 13 |
| ENA opcional | 22 | 15 |
| TRIG | 23 | 16 |
| ECHO | 24 | 18 |
| HX711 DT | 5 | 29 |
| HX711 SCK | 6 | 31 |
| Emergencia | 16 | 36 |

O testemotor.py tem pinos proprios para funcionar separado. Se mudar a fiacao
do motor, atualizar esse arquivo E config.py. Os demais testes usam config.py.
Nao aplique 5 V aos GPIOs. O ECHO do HC-SR04 precisa de adaptacao para 3,3 V.
Confirme no manual do driver a compatibilidade das entradas PUL/DIR com o
sinal do Pi; nao presuma que 3,3 V seja suficiente. Nao alimente o motor pelo Pi.

## Preparacao na Raspberry Pi

Na pasta do repositorio:

```bash
git pull
cat /proc/device-tree/model
cat /etc/os-release
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -c "import RPi.GPIO as GPIO; print(GPIO.VERSION)"
```

Se o import falhar, enviar o erro e o modelo do Pi. A biblioteca GPIO precisa
ser compativel com a placa. Para Pi 5, o RPi.GPIO tradicional precisa ser
substituido por uma implementacao compativel, como rpi-lgpio; nao instalar
as duas no mesmo ambiente. Referencia: https://rpi-lgpio.readthedocs.io/

## Ordem dos testes

1. Motor separado: `python testemotor.py`. Motor fixado, eixo livre, driver
   alimentado e ajustado para 2000 pulsos/volta. `s` e `d` enviam 2000 pulsos
   cada, em aproximadamente 10 segundos; `q` sai e Ctrl+C interrompe.
   Esse teste nao monitora sensores nem emergencia por software.
2. Emergencia: `python calibrar.py`, opcao 4. Conferir liberado/ACIONADO.
   Com NF, fio desconectado tambem deve aparecer como ACIONADO. Conferir
   separadamente o corte fisico de alimentacao; o teste so le o contato.
3. Altura: opcao 1, mesa parada. Medir com trena e copiar ALTURA_OFFSET_CM.
   Repetir em outra altura para conferir a orientacao e a montagem.
4. Carga: opcao 2. Mesa vazia para o zero, depois massa conhecida positiva.
   Copiar HX711_FATOR; copiar HX711_OFFSET se desativar tara automatica.
   Verificar com `python testecarga.py`. Sem calibracao, os valores em kg
   nao sao validos.
5. Sentido da bancada: so depois dos testes anteriores, opcao 3. Ela move
   diretamente por 2 segundos, sem monitorar limites ou emergencia por
   software; manter corte fisico ao alcance e verificar o sentido.
6. Bancada completa: com os valores reais preenchidos, `python app.py`.
   Abrir http://localhost:5000. Testar parar e emergencia com curso livre e
   pequenos movimentos antes de salvar alturas ou usar carga.

O programa para se ficar 3 segundos sem leitura nova da carga e bloqueia
movimento antes da primeira leitura. O HX711 pode ter intervalos sem dado
novo; nao e considerado defeito em uma unica leitura.

Os pulsos gerados por Python/Linux nao garantem temporizacao exata. A volta
comandada depende tambem do ajuste do driver, da ligacao e de nao perder
passos. A altura real de uma mesa pantografica nao deve ser calculada apenas
pelo avanco do fuso; o sistema usa o sensor de altura.
