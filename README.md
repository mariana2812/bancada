# Bancada Pantográfica: automação da altura

Sistema para uma bancada de altura ajustável. O operador faz login, escolhe a máquina e a etapa de montagem, e a mesa sobe ou desce sozinha até a altura salva.

- **Interface** (display touch de 7"): HTML, CSS e JavaScript, em `static/`
- **Lógica e hardware**: Python (Flask), na Raspberry Pi
- **Segurança**: botão de emergência físico, limite de carga (célula de 20 kg), limites de altura e parada automática em caso de falha

> Este projeto assume uma **Raspberry Pi** como controlador. Se vocês usarem outra placa, só a pasta `hardware/` precisa mudar.

---

## 1. Testar no computador (sem hardware)

```bash
pip install -r requirements.txt
python3 app.py          # abra http://localhost:5000
python3 testes.py       # testes automáticos
```

Fora da Raspberry Pi o sistema entra sozinho em **modo simulado**. Aparece o botão "Simulação" no canto da tela, onde dá para colocar peso na mesa e acionar a emergência. Ótimo para ensaiar a apresentação.

## 2. Estrutura

```
bancada/
├── config.py            <- ÚNICO arquivo que você edita (pinos, limites, calibração)
├── app.py               <- servidor: é o que você executa
├── mesa.py              <- cérebro: movimento + regras de segurança
├── banco.py             <- usuários, máquinas e etapas (SQLite)
├── calibrar.py          <- assistente de calibração (altura, carga, motor)
├── testes.py            <- testes automáticos
├── hardware/
│   ├── motor.py         <- motor de passo + driver (PUL/DIR/ENA)
│   ├── sensor_altura.py <- ultrassônico HC-SR04
│   ├── celula_carga.py  <- célula de 20 kg + HX711
│   ├── emergencia.py    <- botão de emergência
│   └── simulacao.py     <- versão fake de tudo (para testar no PC)
└── static/              <- interface (index.html, css/, js/)
```

## 3. O que você precisa preencher (`config.py`)

Procure por `PREENCHER` no arquivo:

| Item | O que é |
|---|---|
| `ALTURA_MINIMA_CM` / `ALTURA_MAXIMA_CM` | Curso real da mesa. **Meça com trena.** |
| `PASSOS_POR_VOLTA` | Deve ser igual ao configurado nas chaves **SW5 a SW8** do driver (tabela "Pulse/rev" impressa nele) |
| `FUSO_PASSO_MM` | Avanço do fuso por volta (mm) |
| `PINO_*` | Em quais GPIOs você ligou cada fio (tabela abaixo) |
| `ALTURA_OFFSET_CM` | Descubra com `calibrar.py` (opção 1) |
| `HX711_FATOR` | Descubra com `calibrar.py` (opção 2) |
| `SENSOR_APONTA_PARA_BAIXO` | `True` se o sensor está no tampo olhando o chão |

## 4. Ligações (numeração BCM, pode mudar no `config.py`)

| Peça | Pino da peça | GPIO padrão |
|---|---|---|
| Driver | PUL+ | 17 |
| Driver | DIR+ | 27 |
| Driver | ENA+ (opcional) | 22 |
| Driver | PUL−, DIR−, ENA− | GND |
| HC-SR04 | TRIG | 23 |
| HC-SR04 | ECHO | 24 (**com divisor de tensão**) |
| HX711 | DT / SCK | 5 / 6 |
| Emergência | um fio / outro fio | 16 / GND |

**Atenção:**
- O **ECHO do HC-SR04 sai com 5 V** e o GPIO do Raspberry aguenta só 3,3 V. Use um divisor com dois resistores (por exemplo 1 kΩ em série e 2 kΩ para o GND).
- Os sinais PUL/DIR/ENA do driver são opto-acoplados. Se o motor não responder com 3,3 V, confira no manual do driver a tensão e o resistor em série indicados para o sinal.
- Alimentação do driver: **24 a 50 V DC**, com GND comum entre fonte e Raspberry.
- Ajuste a corrente do driver (chaves **SW1 a SW4**) conforme a corrente do **seu** motor.
- Botão de emergência: use contato **NF** (normalmente fechado). Se o fio soltar, o sistema trata como emergência.
- O botão de emergência por software **não substitui** o corte elétrico. Para um sistema real, o botão também deve cortar a alimentação do driver.

## 5. Calibração (uma vez)

```bash
python3 calibrar.py
```

1. **Motor**: confirma se "Subir" realmente sobe (se não, o programa diz qual valor trocar).
2. **Altura**: você mede com uma trena e ele calcula o `ALTURA_OFFSET_CM`.
3. **Carga**: com a célula vazia e depois com um peso conhecido, ele calcula o `HX711_FATOR`.
4. **Emergência**: confirma que o botão é lido corretamente.

Copie as linhas que ele mostrar para o `config.py`.

## 6. Rodar na bancada

```bash
python3 app.py
chromium-browser --kiosk http://localhost:5000
```

Para iniciar tudo junto com a Raspberry Pi, crie um serviço (systemd) ou coloque os dois comandos no autostart da sessão gráfica.

## 7. Como o operador usa

1. **Login**: entra com usuário e senha, ou toca em **Criar conta**.
2. **Escolha a máquina**: toca na máquina ou em **Nova máquina** (a primeira vez).
3. **Nova etapa**: digita o nome, usa **Subir / Descer**, toca em **Parar** na altura certa e em **Salvar etapa**.
4. **Nas próximas vezes**: escolhe a máquina e toca na etapa. A mesa ajusta sozinha, com barra de progresso e botão **Parar**.

A coluna da esquerda mostra sempre a altura, a posição na régua (com as etapas marcadas), a carga e o estado.

## 8. Regras de segurança (`mesa.py`)

| Situação | O que acontece |
|---|---|
| Botão de emergência | Para tudo e trava. Só volta depois de destravar o botão e tocar em **Reiniciar** |
| Carga acima de 20 kg | Para de subir e bloqueia a subida (descer continua liberado) |
| Altura mínima ou máxima | Para ao chegar |
| Sensor de altura sem leitura | Para e avisa |
| Movimento por mais de 2 minutos | Para sozinho |
| Operador sai (logout) | A mesa para |
| 10 minutos sem tocar na tela | Sai do login (`TEMPO_INATIVIDADE_MIN`) |

## 9. Problemas comuns

| Sintoma | Provável causa |
|---|---|
| Mesa sobe quando toca em Descer | Troque `DIRECAO_SUBIR_NIVEL` (0 ou 1) |
| Motor treme e não gira | Velocidade alta demais (`VELOCIDADE_PASSOS_S`) ou corrente baixa no driver |
| Altura "--" na tela | Sensor ultrassônico sem leitura (TRIG/ECHO, divisor de tensão) |
| Carga sempre 0 ou muito errada | Falta calibrar (`HX711_FATOR`) ou DT/SCK trocados |
| Sobrecarga logo ao ligar | A tara é feita ao iniciar: ligue com a mesa **vazia** |

## 10. Dados

Tudo fica em `dados/bancada.db` (SQLite). Para zerar usuários, máquinas e etapas, pare o programa e apague esse arquivo.
