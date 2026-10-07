/* =====================================================================
   APP - o fluxo das telas da bancada:

       Login  ->  Máquinas  ->  Etapas da máquina  ->  Cadastro de etapa
                                      |
                                      +-> toque na etapa: a mesa ajusta a altura sozinha

   Os arquivos que ajudam este:
       api.js      conversa com o servidor Python
       teclado.js  teclado virtual na tela
       painel.js   régua, carga, estado, emergência e avisos
   ===================================================================== */

(() => {
  const el = (id) => document.getElementById(id);
  const toast = Painel.toast;
  const formatar = Painel.formatar;

  // Ícones simples (desenhados em SVG, para não depender de fontes)
  const TRACO = 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"';
  const ICONES = {
    voltar: `<svg width="18" height="18" viewBox="0 0 24 24"><path d="M15 5 L8 12 L15 19" ${TRACO}/></svg>`,
    lapis: `<svg viewBox="0 0 24 24"><path d="M4 20 L5 15 L16 4 L20 8 L9 19 Z" ${TRACO}/></svg>`,
    lixeira: `<svg viewBox="0 0 24 24"><path d="M4 7 H20 M9 7 V4 H15 V7 M6 7 L7 20 H17 L18 7" ${TRACO}/></svg>`,
  };

  let config = { nome_sistema: "Bancada Pantográfica", altura_minima_cm: 60, altura_maxima_cm: 120,
                 carga_maxima_kg: 20, inatividade_min: 0, simulado: false };

  const estado = { maquina: null, etapas: [] };
  const formulario = { modo: "nova", etapa: null, mexeu: false };  // 'mexeu' = moveu a mesa ao editar
  let movimento = null;            // dados do ajuste automático em andamento
  let fechamentoMovimento = null;  // temporizador que fecha a janela "Mesa na altura certa"
  let modoLogin = "entrar";
  let temporizadorInatividade = null;

  function criar(tag, classe, texto) {
    const elemento = document.createElement(tag);
    if (classe) elemento.className = classe;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  // =================================================================
  // LOGIN
  // =================================================================
  function definirModoLogin(modo) {
    modoLogin = modo;
    const criando = modo === "criar";
    el("aba-entrar").setAttribute("aria-selected", String(!criando));
    el("aba-criar").setAttribute("aria-selected", String(criando));
    el("campo-nome").hidden = !criando;
    el("btn-login").textContent = criando ? "Criar conta" : "Entrar";
    el("login-erro").hidden = true;
  }

  async function enviarLogin(evento) {
    evento.preventDefault();
    const dados = { usuario: el("login-usuario").value, senha: el("login-senha").value };
    let url = "/api/login";
    if (modoLogin === "criar") {
      url = "/api/cadastro";
      dados.nome = el("login-nome").value;
    }

    el("btn-login").disabled = true;
    const resposta = await Api.post(url, dados);
    el("btn-login").disabled = false;

    if (!resposta.ok) {
      el("login-erro").textContent = resposta.mensagem;
      el("login-erro").hidden = false;
      return;
    }
    entrar(resposta.nome);
  }

  function entrar(nome) {
    Teclado.fechar();
    el("tela-login").hidden = true;
    el("app").hidden = false;
    el("usuario-nome").textContent = nome;
    reiniciarTemporizador();
    irParaMaquinas();
  }

  function voltarAoLogin() {
    Teclado.fechar();
    movimento = null;
    ["modal-maquina", "modal-confirmar", "modal-movendo"].forEach((id) => { el(id).hidden = true; });
    el("app").hidden = true;
    el("tela-login").hidden = false;
    ["login-nome", "login-usuario", "login-senha"].forEach((id) => { el(id).value = ""; });
    el("login-senha").type = "password";
    el("btn-ver-senha").textContent = "Ver";
    definirModoLogin("entrar");
  }

  async function sair(motivo) {
    await Api.post("/api/logout");   // o servidor também para a mesa
    voltarAoLogin();
    if (motivo) toast(motivo);
  }

  // Sair sozinho depois de um tempo sem ninguém tocar na tela
  function reiniciarTemporizador() {
    clearTimeout(temporizadorInatividade);
    if (!config.inatividade_min || el("app").hidden) return;
    temporizadorInatividade = setTimeout(
      () => sair("Sessão encerrada por inatividade."),
      config.inatividade_min * 60000
    );
  }

  // =================================================================
  // NAVEGAÇÃO
  // =================================================================
  function mostrarVista(nome) {
    Teclado.fechar();
    ["maquinas", "etapas", "form"].forEach((vista) => {
      el("vista-" + vista).hidden = vista !== nome;
    });
    if (nome === "maquinas") Painel.definirEtapas([]);
  }

  // =================================================================
  // MÁQUINAS
  // =================================================================
  async function irParaMaquinas() {
    estado.maquina = null;
    mostrarVista("maquinas");
    await carregarMaquinas();
  }

  async function carregarMaquinas() {
    const lista = await Api.get("/api/maquinas");
    if (!Array.isArray(lista)) return;

    const grade = el("lista-maquinas");
    grade.replaceChildren();

    if (lista.length === 0) {
      grade.appendChild(criar("p", "vazio", "Nenhuma máquina cadastrada ainda. Toque em Nova máquina para começar."));
      return;
    }

    lista.forEach((maquina) => {
      const botao = criar("button", "cartao-maquina");
      botao.appendChild(criar("strong", "", maquina.nome));
      const total = maquina.total_etapas;
      botao.appendChild(criar("span", "", total === 1 ? "1 etapa" : `${total} etapas`));
      botao.addEventListener("click", () => abrirMaquina(maquina));
      grade.appendChild(botao);
    });
  }

  function abrirModalMaquina() {
    el("maquina-nome").value = "";
    el("modal-maquina").hidden = false;
    el("maquina-nome").focus();
  }

  function fecharModalMaquina() {
    Teclado.fechar();
    el("modal-maquina").hidden = true;
  }

  async function salvarMaquina() {
    const resposta = await Api.post("/api/maquinas", { nome: el("maquina-nome").value });
    if (!resposta.ok) {
      toast(resposta.mensagem, "erro");
      return;
    }
    fecharModalMaquina();
    toast("Máquina cadastrada.", "ok");
    abrirMaquina(resposta.maquina);   // já abre para cadastrar as etapas
  }

  async function excluirMaquina() {
    const maquina = estado.maquina;
    const confirmou = await confirmar(
      "Excluir máquina?",
      `"${maquina.nome}" e todas as etapas dela serão removidas.`
    );
    if (!confirmou) return;

    const resposta = await Api.excluir(`/api/maquinas/${maquina.id}`);
    toast(resposta.ok ? "Máquina excluída." : resposta.mensagem, resposta.ok ? "ok" : "erro");
    if (resposta.ok) irParaMaquinas();
  }

  // =================================================================
  // ETAPAS
  // =================================================================
  function abrirMaquina(maquina) {
    estado.maquina = maquina;
    el("titulo-maquina").textContent = maquina.nome;
    mostrarVista("etapas");
    carregarEtapas();
  }

  async function carregarEtapas() {
    const lista = await Api.get(`/api/maquinas/${estado.maquina.id}/etapas`);
    if (!Array.isArray(lista)) return;

    lista.forEach((etapa, indice) => { etapa.ordem = indice + 1; });  // 1, 2, 3... sem buracos
    estado.etapas = lista;
    Painel.definirEtapas(lista);
    desenharEtapas();
  }

  function desenharEtapas() {
    const ol = el("lista-etapas");
    ol.replaceChildren();
    el("dica-etapas").hidden = estado.etapas.length === 0;

    if (estado.etapas.length === 0) {
      ol.appendChild(criar("li", "vazio", "Nenhuma etapa ainda. Toque em Nova etapa para guardar a primeira altura."));
      return;
    }

    estado.etapas.forEach((etapa) => {
      const item = criar("li", "etapa");

      const ir = criar("button", "etapa-ir");
      ir.appendChild(criar("span", "etapa-num", etapa.ordem));
      ir.appendChild(criar("span", "etapa-nome", etapa.nome));
      ir.appendChild(criar("span", "etapa-altura", formatar(etapa.altura_cm) + " cm"));
      ir.addEventListener("click", () => irParaEtapa(etapa));

      const editar = criar("button", "btn btn-claro btn-icone");
      editar.innerHTML = ICONES.lapis;
      editar.setAttribute("aria-label", "Editar etapa " + etapa.nome);
      editar.addEventListener("click", () => abrirFormulario("editar", etapa));

      const apagar = criar("button", "btn btn-claro btn-icone");
      apagar.innerHTML = ICONES.lixeira;
      apagar.setAttribute("aria-label", "Excluir etapa " + etapa.nome);
      apagar.addEventListener("click", () => excluirEtapa(etapa));

      item.append(ir, editar, apagar);
      ol.appendChild(item);
    });
  }

  async function excluirEtapa(etapa) {
    const confirmou = await confirmar("Excluir etapa?", `"${etapa.nome}" será removida de ${estado.maquina.nome}.`);
    if (!confirmou) return;

    const resposta = await Api.excluir(`/api/etapas/${etapa.id}`);
    toast(resposta.ok ? "Etapa excluída." : resposta.mensagem, resposta.ok ? "ok" : "erro");
    carregarEtapas();
  }

  // =================================================================
  // AJUSTE AUTOMÁTICO PARA UMA ETAPA
  // =================================================================
  async function irParaEtapa(etapa) {
    const status = Painel.status();
    const resposta = await Api.post("/api/mesa/ir_para_etapa", { etapa_id: etapa.id });

    if (!resposta.ok) {
      toast(resposta.mensagem, "erro");
      return;
    }
    if (!resposta.movendo) {            // a mesa já estava na altura
      toast(resposta.mensagem, "ok");
      return;
    }

    clearTimeout(fechamentoMovimento);
    movimento = {
      alvo: etapa.altura_cm,
      inicial: status && status.altura_cm !== null ? status.altura_cm : etapa.altura_cm,
      inicio: Date.now(),
    };

    document.querySelector(".modal-movendo").classList.remove("concluido");
    el("movendo-titulo").textContent = "Ajustando a mesa";
    el("movendo-etapa").textContent = `Etapa ${etapa.ordem}: ${etapa.nome}`;
    el("movendo-alvo-valor").textContent = formatar(etapa.altura_cm);
    el("movendo-progresso").style.width = "0%";
    el("btn-movendo-parar").hidden = false;
    el("modal-movendo").hidden = false;
  }

  /** Chamado a cada status novo: acompanha o ajuste e fecha a janela quando termina. */
  function acompanharMovimento(status) {
    if (!movimento) return;

    const andando = status.estado === "subindo" || status.estado === "descendo";
    if (andando) {
      const total = Math.abs(movimento.alvo - movimento.inicial) || 1;
      const falta = Math.abs(movimento.alvo - status.altura_cm);
      const progresso = Math.min(100, Math.max(0, (1 - falta / total) * 100));
      el("movendo-progresso").style.width = progresso + "%";
      return;
    }

    // Ignora um status "parado" antigo que chegue logo depois de começar
    if (Date.now() - movimento.inicio < 800) return;

    const chegou = status.mensagem === "Altura alcançada.";
    movimento = null;

    if (chegou) {
      document.querySelector(".modal-movendo").classList.add("concluido");
      el("movendo-titulo").textContent = "Mesa na altura certa";
      el("movendo-progresso").style.width = "100%";
      el("btn-movendo-parar").hidden = true;
      fechamentoMovimento = setTimeout(() => { el("modal-movendo").hidden = true; }, 1300);
    } else {
      el("modal-movendo").hidden = true;
      if (status.estado !== "emergencia") toast(status.mensagem || "Movimento interrompido.", "erro");
    }
  }

  async function pararAjuste() {
    movimento = null;
    el("modal-movendo").hidden = true;
    await Api.post("/api/mesa/parar");
    toast("Mesa parada.");
  }

  // =================================================================
  // CADASTRO / EDIÇÃO DE ETAPA (subir, descer e parar)
  // =================================================================
  function abrirFormulario(modo, etapa) {
    formulario.modo = modo;
    formulario.etapa = etapa || null;
    formulario.mexeu = false;
    el("titulo-form").textContent = modo === "nova" ? "Nova etapa" : "Editar etapa";
    el("etapa-nome").value = etapa ? etapa.nome : "";
    mostrarVista("form");
    atualizarFormulario(Painel.status());
  }

  /** Mantém a altura e os botões do formulário em sincronia com a mesa. */
  function atualizarFormulario(status) {
    if (el("vista-form").hidden || !status) return;

    el("form-altura").textContent = formatar(status.altura_cm);
    el("jog-subir").classList.toggle("ativo", status.estado === "subindo");
    el("jog-descer").classList.toggle("ativo", status.estado === "descendo");

    const dica = el("dica-form");
    if (formulario.modo === "editar") {
      const antes = formatar(formulario.etapa.altura_cm);
      dica.textContent = formulario.mexeu
        ? `Nova altura: ${formatar(status.altura_cm)} cm (antes: ${antes} cm).`
        : `Altura salva: ${antes} cm. Mova a mesa só se quiser mudar.`;
    } else {
      dica.textContent = "Suba ou desça a mesa, toque em Parar na altura certa e salve.";
    }
  }

  async function mover(caminho) {
    Teclado.fechar();   // libera a tela para ver os botões Parar e a altura
    const resposta = await Api.post(caminho);
    if (resposta.ok) formulario.mexeu = true;
    else toast(resposta.mensagem, "erro");
  }

  async function salvarEtapa() {
    const nome = el("etapa-nome").value.trim();
    if (nome.length < 2) {
      toast("Digite o nome da etapa.", "erro");
      el("etapa-nome").focus();
      return;
    }

    Teclado.fechar();

    // O servidor lê a altura direto do sensor, assim o valor salvo é o real
    let resposta;
    if (formulario.modo === "nova") {
      resposta = await Api.post(`/api/maquinas/${estado.maquina.id}/etapas`, { nome, usar_altura_atual: true });
    } else {
      resposta = await Api.put(`/api/etapas/${formulario.etapa.id}`, { nome, usar_altura_atual: formulario.mexeu });
    }

    if (!resposta.ok) {
      toast(resposta.mensagem, "erro");
      return;
    }
    toast("Etapa salva.", "ok");
    voltarParaEtapas();
  }

  async function cancelarFormulario() {
    await Api.post("/api/mesa/parar");   // se a mesa estiver andando, para
    voltarParaEtapas();
  }

  function voltarParaEtapas() {
    mostrarVista("etapas");
    carregarEtapas();
  }

  // =================================================================
  // JANELA DE CONFIRMAÇÃO
  // =================================================================
  function confirmar(titulo, texto, rotuloBotao = "Excluir") {
    return new Promise((resolver) => {
      el("confirmar-titulo").textContent = titulo;
      el("confirmar-texto").textContent = texto;
      el("btn-confirmar-sim").textContent = rotuloBotao;
      el("modal-confirmar").hidden = false;

      const responder = (valor) => {
        el("modal-confirmar").hidden = true;
        resolver(valor);
      };
      el("btn-confirmar-sim").onclick = () => responder(true);
      el("btn-confirmar-nao").onclick = () => responder(false);
    });
  }

  // =================================================================
  // INÍCIO
  // =================================================================
  function ligarEventos() {
    // Login
    el("form-login").addEventListener("submit", enviarLogin);
    el("aba-entrar").addEventListener("click", () => definirModoLogin("entrar"));
    el("aba-criar").addEventListener("click", () => definirModoLogin("criar"));
    el("btn-ver-senha").addEventListener("click", () => {
      const campo = el("login-senha");
      const escondida = campo.type === "password";
      campo.type = escondida ? "text" : "password";
      el("btn-ver-senha").textContent = escondida ? "Ocultar" : "Ver";
    });
    el("btn-sair").addEventListener("click", () => sair());

    // Máquinas
    el("btn-nova-maquina").addEventListener("click", abrirModalMaquina);
    el("btn-cancelar-maquina").addEventListener("click", fecharModalMaquina);
    el("btn-salvar-maquina").addEventListener("click", salvarMaquina);
    el("maquina-nome").addEventListener("keydown", (e) => { if (e.key === "Enter") salvarMaquina(); });

    // Etapas
    el("btn-voltar-maquinas").innerHTML = ICONES.voltar + "<span>Máquinas</span>";
    el("btn-excluir-maquina").innerHTML = ICONES.lixeira;
    el("btn-voltar-maquinas").addEventListener("click", irParaMaquinas);
    el("btn-excluir-maquina").addEventListener("click", excluirMaquina);
    el("btn-nova-etapa").addEventListener("click", () => abrirFormulario("nova"));

    // Cadastro de etapa
    el("jog-subir").addEventListener("click", () => mover("/api/mesa/subir"));
    el("jog-descer").addEventListener("click", () => mover("/api/mesa/descer"));
    el("jog-parar").addEventListener("click", () => {
      Teclado.fechar();
      Api.post("/api/mesa/parar");
    });
    el("btn-salvar-etapa").addEventListener("click", salvarEtapa);
    el("btn-cancelar-form").addEventListener("click", cancelarFormulario);

    // Ajuste automático
    el("btn-movendo-parar").addEventListener("click", pararAjuste);

    // Qualquer toque reinicia o relógio de inatividade
    ["pointerdown", "keydown"].forEach((tipo) => document.addEventListener(tipo, reiniciarTemporizador));
  }

  async function iniciar() {
    try {
      config = await (await fetch("/api/config")).json();
    } catch (erro) {
      console.warn("Não foi possível ler /api/config. Usando valores padrão.");
    }

    document.title = config.nome_sistema;
    el("login-titulo").textContent = config.nome_sistema;
    el("topo-nome").textContent = config.nome_sistema;

    Api.aoPerderSessao = voltarAoLogin;
    Teclado.iniciar();
    Painel.iniciar(config);
    Painel.aoAtualizar((status) => {
      acompanharMovimento(status);
      atualizarFormulario(status);
    });
    ligarEventos();

    // Se a página for recarregada com o usuário já logado, continua de onde parou
    const sessao = await Api.get("/api/sessao");
    if (sessao.logado) entrar(sessao.nome);
  }

  iniciar();
})();
