"""
SERVIDOR DA BANCADA - é este arquivo que você executa:

    python3 app.py

Ele faz 3 coisas:
    1. Entrega a interface (pasta static/) para o navegador do display.
    2. Responde aos pedidos da interface (login, máquinas, etapas...).
    3. Manda os comandos para a mesa (subir, descer, parar, ir para altura).
"""

import atexit
import os
import secrets
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory, session

import banco
import config
from hardware import simulacao
from mesa import Mesa

PASTA = os.path.dirname(os.path.abspath(__file__))


def _carregar_chave_secreta():
    """A chave protege o login. É criada na 1ª vez e reaproveitada depois."""
    caminho = os.path.join(banco.PASTA_DADOS, "chave_secreta.txt")
    os.makedirs(banco.PASTA_DADOS, exist_ok=True)
    if not os.path.exists(caminho):
        with open(caminho, "w") as arquivo:
            arquivo.write(secrets.token_hex(32))
    with open(caminho) as arquivo:
        return arquivo.read().strip()


banco.criar_tabelas()
app = Flask(__name__, static_folder=os.path.join(PASTA, "static"), static_url_path="/static")
app.secret_key = _carregar_chave_secreta()

mesa = Mesa()
atexit.register(mesa.encerrar)


def responder(ok, mensagem="", codigo=None, **dados):
    """Todas as respostas seguem o mesmo formato: {ok, mensagem, ...}."""
    if codigo is None:
        codigo = 200 if ok else 400
    return jsonify({"ok": ok, "mensagem": mensagem, **dados}), codigo


def login_obrigatorio(funcao):
    @wraps(funcao)
    def verificar(*args, **kwargs):
        if "usuario_id" not in session:
            return responder(False, "Faça login para continuar.", 401)
        return funcao(*args, **kwargs)
    return verificar


def corpo():
    """Dados JSON enviados pela interface (nunca None)."""
    return request.get_json(silent=True) or {}


@app.get("/")
def pagina_inicial():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/config")
def obter_config():
    return jsonify({
        "nome_sistema": config.NOME_SISTEMA,
        "altura_minima_cm": config.ALTURA_MINIMA_CM,
        "altura_maxima_cm": config.ALTURA_MAXIMA_CM,
        "carga_maxima_kg": config.CARGA_MAXIMA_KG,
        "inatividade_min": config.TEMPO_INATIVIDADE_MIN,
        "simulado": mesa.simulado,
    })


# =====================================================================
# LOGIN
# =====================================================================
@app.get("/api/sessao")
def sessao():
    if "usuario_id" in session:
        return jsonify({"logado": True, "nome": session["usuario_nome"]})
    return jsonify({"logado": False})


@app.post("/api/cadastro")
def cadastro():
    dados = corpo()
    try:
        usuario = banco.criar_usuario(
            dados.get("nome", ""), dados.get("usuario", ""), dados.get("senha", "")
        )
    except ValueError as erro:
        return responder(False, str(erro))

    session["usuario_id"] = usuario["id"]
    session["usuario_nome"] = usuario["nome"]
    return responder(True, "Conta criada!", nome=usuario["nome"])


@app.post("/api/login")
def login():
    dados = corpo()
    usuario = banco.autenticar(dados.get("usuario", ""), dados.get("senha", ""))
    if not usuario:
        return responder(False, "Usuário ou senha incorretos.", 401)

    session["usuario_id"] = usuario["id"]
    session["usuario_nome"] = usuario["nome"]
    return responder(True, "Bem-vindo!", nome=usuario["nome"])


@app.post("/api/logout")
def logout():
    mesa.parar()  # por segurança, a mesa para quando o operador sai
    session.clear()
    return responder(True)


# =====================================================================
# MÁQUINAS
# =====================================================================
@app.get("/api/maquinas")
@login_obrigatorio
def listar_maquinas():
    return jsonify(banco.listar_maquinas())


@app.post("/api/maquinas")
@login_obrigatorio
def criar_maquina():
    try:
        maquina = banco.criar_maquina(corpo().get("nome", ""), session["usuario_id"])
    except ValueError as erro:
        return responder(False, str(erro))
    return responder(True, "Máquina cadastrada!", maquina=maquina)


@app.delete("/api/maquinas/<int:maquina_id>")
@login_obrigatorio
def excluir_maquina(maquina_id):
    banco.excluir_maquina(maquina_id)
    return responder(True, "Máquina excluída.")


# =====================================================================
# ETAPAS
# =====================================================================
def _altura_pedida(dados):
    """A altura vem do pedido, ou é lida da mesa quando 'usar_altura_atual' = true."""
    if not dados.get("usar_altura_atual"):
        return dados.get("altura_cm")

    status = mesa.status()
    if status["estado"] in ("subindo", "descendo"):
        raise ValueError("Pare a mesa antes de salvar a altura.")
    if status["altura_cm"] is None:
        raise ValueError("Sensor de altura sem leitura.")
    return status["altura_cm"]


@app.get("/api/maquinas/<int:maquina_id>/etapas")
@login_obrigatorio
def listar_etapas(maquina_id):
    return jsonify(banco.listar_etapas(maquina_id))


@app.post("/api/maquinas/<int:maquina_id>/etapas")
@login_obrigatorio
def criar_etapa(maquina_id):
    dados = corpo()
    try:
        etapa = banco.criar_etapa(maquina_id, dados.get("nome", ""), _altura_pedida(dados))
    except ValueError as erro:
        return responder(False, str(erro))
    return responder(True, "Etapa salva!", etapa=etapa)


@app.put("/api/etapas/<int:etapa_id>")
@login_obrigatorio
def atualizar_etapa(etapa_id):
    dados = corpo()
    try:
        altura = _altura_pedida(dados) if ("altura_cm" in dados or dados.get("usar_altura_atual")) else None
        etapa = banco.atualizar_etapa(etapa_id, dados.get("nome"), altura)
    except ValueError as erro:
        return responder(False, str(erro))
    return responder(True, "Etapa atualizada!", etapa=etapa)


@app.delete("/api/etapas/<int:etapa_id>")
@login_obrigatorio
def excluir_etapa(etapa_id):
    banco.excluir_etapa(etapa_id)
    return responder(True, "Etapa excluída.")


# =====================================================================
# MESA
# =====================================================================
@app.get("/api/mesa/status")
def status_da_mesa():
    # Sem exigir login: a tela de emergência precisa aparecer sempre
    return jsonify(mesa.status())


@app.post("/api/mesa/subir")
@login_obrigatorio
def mesa_subir():
    ok, mensagem = mesa.subir()
    return responder(ok, mensagem)


@app.post("/api/mesa/descer")
@login_obrigatorio
def mesa_descer():
    ok, mensagem = mesa.descer()
    return responder(ok, mensagem)


@app.post("/api/mesa/parar")
def mesa_parar():
    # Sem exigir login de propósito: parar tem que funcionar sempre
    ok, mensagem = mesa.parar()
    return responder(ok, mensagem)


@app.post("/api/mesa/ir_para_etapa")
@login_obrigatorio
def mesa_ir_para_etapa():
    etapa = banco.obter_etapa(corpo().get("etapa_id"))
    if not etapa:
        return responder(False, "Etapa não encontrada.")
    ok, mensagem = mesa.ir_para(etapa["altura_cm"])
    movendo = mesa.status()["estado"] in ("subindo", "descendo")
    return responder(ok, mensagem, movendo=movendo)


@app.post("/api/mesa/zerar_balanca")
@login_obrigatorio
def mesa_zerar_balanca():
    ok, mensagem = mesa.zerar_balanca()
    return responder(ok, mensagem)


@app.post("/api/mesa/reiniciar")
def mesa_reiniciar():
    # Sem exigir login: a tela de emergência aparece mesmo na tela de login
    ok, mensagem = mesa.reiniciar_emergencia()
    return responder(ok, mensagem)


# =====================================================================
# SIMULAÇÃO (só existe quando o hardware é simulado)
# =====================================================================
if mesa.simulado:
    @app.post("/api/simulacao/carga")
    def simular_carga():
        simulacao.definir_carga(corpo().get("kg", 0))
        return responder(True)

    @app.post("/api/simulacao/emergencia")
    def simular_emergencia():
        simulacao.definir_emergencia(corpo().get("ativa", False))
        return responder(True)


# =====================================================================
if __name__ == "__main__":
    modo = "SIMULADO" if mesa.simulado else "HARDWARE REAL"
    print(f"\n  {config.NOME_SISTEMA} - modo {modo}")
    print(f"  Abra no navegador: http://localhost:{config.PORTA}\n")
    app.run(host=config.HOST, port=config.PORTA, threaded=True, debug=False)
