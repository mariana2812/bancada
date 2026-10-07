"""
TESTES AUTOMÁTICOS (rodam no computador, em modo simulado):

    python3 testes.py

Conferem login, máquinas, etapas e as regras de segurança da mesa.
Usam um banco temporário, então não mexem nos seus dados reais.
"""

import os
import tempfile
import time

import banco
import config

# Força o modo simulado e um banco temporário ANTES de importar o app
config.SIMULAR = True
banco.PASTA_DADOS = tempfile.mkdtemp()
banco.CAMINHO_BANCO = os.path.join(banco.PASTA_DADOS, "teste.db")

import app as servidor            # noqa: E402
from hardware import simulacao    # noqa: E402

cliente = servidor.app.test_client()
mesa = servidor.mesa


def conferir(descricao, condicao):
    print(("  OK    " if condicao else "  FALHOU  ") + descricao)
    if not condicao:
        raise SystemExit(1)


def esperar(condicao, tempo=15):
    limite = time.time() + tempo
    while time.time() < limite:
        if condicao():
            return True
        time.sleep(0.05)
    return False


time.sleep(0.4)

print("Login")
conferir("rotas protegidas exigem login", cliente.get("/api/maquinas").status_code == 401)
conferir("cria conta", cliente.post("/api/cadastro", json={"nome": "Maria", "usuario": "maria", "senha": "1234"}).json["ok"])
cliente.post("/api/logout")
conferir("senha errada é recusada", cliente.post("/api/login", json={"usuario": "maria", "senha": "x"}).status_code == 401)
conferir("senha certa entra", cliente.post("/api/login", json={"usuario": "maria", "senha": "1234"}).json["ok"])

print("Máquinas e etapas")
maquina = cliente.post("/api/maquinas", json={"nome": "Prensa 01"}).json["maquina"]
conferir("não repete nome de máquina", not cliente.post("/api/maquinas", json={"nome": "prensa 01"}).json["ok"])
conferir("rejeita altura fora dos limites",
         not cliente.post(f"/api/maquinas/{maquina['id']}/etapas", json={"nome": "X1", "altura_cm": 500}).json["ok"])
etapa = cliente.post(f"/api/maquinas/{maquina['id']}/etapas", json={"nome": "Fixar base", "usar_altura_atual": True}).json["etapa"]
conferir("salva etapa com a altura atual da mesa", abs(etapa["altura_cm"] - mesa.altura_cm) < 0.5)

print("Movimento")
cliente.post("/api/mesa/subir")
esperar(lambda: mesa.altura_cm > etapa["altura_cm"] + 3)
cliente.post("/api/mesa/parar")
conferir("parar interrompe o movimento", mesa.estado == "parada")
resposta = cliente.post("/api/mesa/ir_para_etapa", json={"etapa_id": etapa["id"]}).json
conferir("ir para etapa começa a mover", resposta["ok"] and resposta["movendo"])
conferir("chega na altura da etapa", esperar(lambda: mesa.estado == "parada"))
conferir("erro de altura dentro da tolerância", abs(mesa.altura_cm - etapa["altura_cm"]) <= 0.5)

print("Segurança")
simulacao.definir_carga(config.CARGA_MAXIMA_KG + 3)
time.sleep(0.3)
conferir("sobrecarga bloqueia subir", not cliente.post("/api/mesa/subir").json["ok"] and mesa.estado == "sobrecarga")
simulacao.definir_carga(0)
time.sleep(0.3)
conferir("sobrecarga some ao tirar o peso", mesa.estado == "parada")

cliente.post("/api/mesa/descer")
time.sleep(0.3)
simulacao.definir_emergencia(True)
time.sleep(0.3)
conferir("emergência para e trava", mesa.estado == "emergencia" and not cliente.post("/api/mesa/descer").json["ok"])
conferir("não reinicia com botão acionado", not cliente.post("/api/mesa/reiniciar").json["ok"])
simulacao.definir_emergencia(False)
time.sleep(0.3)
conferir("reinicia depois de soltar o botão", cliente.post("/api/mesa/reiniciar").json["ok"] and mesa.estado == "parada")

mesa.encerrar()
print("\nTudo certo.")
