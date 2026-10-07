/* =====================================================================
   API - conversa com o servidor Python (app.py)

   Uso:   const resposta = await Api.post("/api/login", { usuario, senha });
          if (resposta.ok) { ... } else { mostrar(resposta.mensagem); }
   ===================================================================== */

const Api = {
  // Função chamada quando o servidor diz "você não está logado" (código 401)
  aoPerderSessao: null,

  async chamar(metodo, url, dados) {
    const opcoes = { method: metodo, headers: { "Content-Type": "application/json" } };
    if (dados !== undefined) opcoes.body = JSON.stringify(dados);

    try {
      const resposta = await fetch(url, opcoes);
      const json = await resposta.json().catch(() => ({}));

      if (resposta.status === 401 && url !== "/api/login" && Api.aoPerderSessao) {
        Api.aoPerderSessao();
      }
      return json;
    } catch (erro) {
      return { ok: false, mensagem: "Sem conexão com o servidor." };
    }
  },

  get(url) { return Api.chamar("GET", url); },
  post(url, dados) { return Api.chamar("POST", url, dados || {}); },
  put(url, dados) { return Api.chamar("PUT", url, dados || {}); },
  excluir(url) { return Api.chamar("DELETE", url); },
};
