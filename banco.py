"""
BANCO DE DADOS (SQLite) - guarda usuários, máquinas e etapas.

O arquivo do banco fica em dados/bancada.db e é criado sozinho.
Para "zerar tudo" basta apagar esse arquivo.

Estrutura:
    usuarios  -> quem trabalha na bancada (login e senha)
    maquinas  -> máquinas cadastradas (compartilhadas por todos os usuários)
    etapas    -> etapas de montagem de cada máquina, com a altura da mesa
"""

import os
import sqlite3
from contextlib import contextmanager

from werkzeug.security import check_password_hash, generate_password_hash

import config

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
CAMINHO_BANCO = os.path.join(PASTA_DADOS, "bancada.db")


@contextmanager
def _conexao():
    """Abre o banco, salva as alterações no final e fecha."""
    os.makedirs(PASTA_DADOS, exist_ok=True)
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


def criar_tabelas():
    with _conexao() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT NOT NULL,
                usuario    TEXT NOT NULL UNIQUE COLLATE NOCASE,
                senha_hash TEXT NOT NULL,
                criado_em  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS maquinas (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT NOT NULL UNIQUE COLLATE NOCASE,
                criado_por INTEGER REFERENCES usuarios(id),
                criado_em  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS etapas (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                maquina_id INTEGER NOT NULL REFERENCES maquinas(id) ON DELETE CASCADE,
                nome       TEXT NOT NULL,
                altura_cm  REAL NOT NULL,
                ordem      INTEGER NOT NULL,
                criado_em  TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)


def criar_usuario(nome, usuario, senha):
    nome, usuario = nome.strip(), usuario.strip()
    if len(nome) < 2:
        raise ValueError("Digite seu nome.")
    if len(usuario) < 3:
        raise ValueError("O usuário precisa ter pelo menos 3 letras.")
    if len(senha) < 4:
        raise ValueError("A senha precisa ter pelo menos 4 caracteres.")

    try:
        with _conexao() as con:
            cursor = con.execute(
                "INSERT INTO usuarios (nome, usuario, senha_hash) VALUES (?, ?, ?)",
                (nome, usuario, generate_password_hash(senha)),
            )
            return {"id": cursor.lastrowid, "nome": nome, "usuario": usuario}
    except sqlite3.IntegrityError:
        raise ValueError("Esse usuário já existe. Escolha outro.")


def autenticar(usuario, senha):
    """Devolve o usuário se login e senha estiverem certos; senão, None."""
    with _conexao() as con:
        linha = con.execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (usuario.strip(),)
        ).fetchone()
    if linha and check_password_hash(linha["senha_hash"], senha):
        return {"id": linha["id"], "nome": linha["nome"], "usuario": linha["usuario"]}
    return None


def listar_maquinas():
    with _conexao() as con:
        linhas = con.execute("""
            SELECT m.id, m.nome, COUNT(e.id) AS total_etapas
            FROM maquinas m
            LEFT JOIN etapas e ON e.maquina_id = m.id
            GROUP BY m.id
            ORDER BY m.nome
        """).fetchall()
    return [dict(linha) for linha in linhas]


def criar_maquina(nome, usuario_id):
    nome = nome.strip()
    if len(nome) < 2:
        raise ValueError("Digite o nome da máquina.")
    try:
        with _conexao() as con:
            cursor = con.execute(
                "INSERT INTO maquinas (nome, criado_por) VALUES (?, ?)", (nome, usuario_id)
            )
            return {"id": cursor.lastrowid, "nome": nome, "total_etapas": 0}
    except sqlite3.IntegrityError:
        raise ValueError("Já existe uma máquina com esse nome.")


def excluir_maquina(maquina_id):
    with _conexao() as con:
        con.execute("DELETE FROM maquinas WHERE id = ?", (maquina_id,))


def listar_etapas(maquina_id):
    with _conexao() as con:
        linhas = con.execute(
            "SELECT id, maquina_id, nome, altura_cm, ordem FROM etapas "
            "WHERE maquina_id = ? ORDER BY ordem, id",
            (maquina_id,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def obter_etapa(etapa_id):
    with _conexao() as con:
        linha = con.execute(
            "SELECT id, maquina_id, nome, altura_cm, ordem FROM etapas WHERE id = ?",
            (etapa_id,),
        ).fetchone()
    return dict(linha) if linha else None


def _validar_altura(altura_cm):
    try:
        altura_cm = round(float(altura_cm), 1)
    except (TypeError, ValueError):
        raise ValueError("Altura inválida.")
    if not config.ALTURA_MINIMA_CM <= altura_cm <= config.ALTURA_MAXIMA_CM:
        raise ValueError(
            f"A altura precisa estar entre {config.ALTURA_MINIMA_CM:g} e "
            f"{config.ALTURA_MAXIMA_CM:g} cm."
        )
    return altura_cm


def criar_etapa(maquina_id, nome, altura_cm):
    nome = nome.strip()
    if len(nome) < 2:
        raise ValueError("Digite o nome da etapa.")
    altura_cm = _validar_altura(altura_cm)

    with _conexao() as con:
        ultima = con.execute(
            "SELECT COALESCE(MAX(ordem), 0) FROM etapas WHERE maquina_id = ?", (maquina_id,)
        ).fetchone()[0]
        cursor = con.execute(
            "INSERT INTO etapas (maquina_id, nome, altura_cm, ordem) VALUES (?, ?, ?, ?)",
            (maquina_id, nome, altura_cm, ultima + 1),
        )
        return {"id": cursor.lastrowid, "maquina_id": maquina_id, "nome": nome,
                "altura_cm": altura_cm, "ordem": ultima + 1}


def atualizar_etapa(etapa_id, nome=None, altura_cm=None):
    etapa = obter_etapa(etapa_id)
    if not etapa:
        raise ValueError("Etapa não encontrada.")

    novo_nome = etapa["nome"] if nome is None else nome.strip()
    nova_altura = etapa["altura_cm"] if altura_cm is None else _validar_altura(altura_cm)
    if len(novo_nome) < 2:
        raise ValueError("Digite o nome da etapa.")

    with _conexao() as con:
        con.execute(
            "UPDATE etapas SET nome = ?, altura_cm = ? WHERE id = ?",
            (novo_nome, nova_altura, etapa_id),
        )
    return obter_etapa(etapa_id)


def excluir_etapa(etapa_id):
    with _conexao() as con:
        con.execute("DELETE FROM etapas WHERE id = ?", (etapa_id,))
