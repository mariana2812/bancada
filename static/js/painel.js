/* =====================================================================
   PAINEL - tudo que mostra o estado da mesa em tempo real:
       - coluna da régua (altura, ponteiro, carga, estado)
       - avisos de sobrecarga/erro
       - tela de emergência
       - mensagens rápidas (toast)
       - painel de teste do modo simulado

   O painel pergunta o status ao servidor a cada 300 ms e avisa o resto
   do sistema (app.js) através de Painel.aoAtualizar(funcao).
   ===================================================================== */

const Painel = (() => {
  const INTERVALO_MS = 300;

  const NOMES_ESTADO = {
    parada: "Parada",
    subindo: "Subindo",
    descendo: "Descendo",
    emergencia: "Emergência",
    sobrecarga: "Sobrecarga",
    erro: "Erro",
  };

  let config = { altura_minima_cm: 60, altura_maxima_cm: 120, carga_maxima_kg: 20 };
  let ultimoStatus = null;
  const ouvintes = [];
  let temporizadorToast = null;

  const el = (id) => document.getElementById(id);

  // ---------------------------------------------------------------
  // Utilidades
  // ---------------------------------------------------------------
  function formatar(numero, casas = 1) {
    if (numero === null || numero === undefined) return "--";
    return Number(numero).toFixed(casas).replace(".", ",");
  }

  function porcentagemDaAltura(altura) {
    const faixa = config.altura_maxima_cm - config.altura_minima_cm;
    const pct = ((altura - config.altura_minima_cm) / faixa) * 100;
    return Math.min(100, Math.max(0, pct));
  }

  function toast(mensagem, tipo = "info") {
    const caixa = el("toast");
    caixa.textContent = mensagem;
    caixa.dataset.tipo = tipo;
    caixa.hidden = false;
    clearTimeout(temporizadorToast);
    temporizadorToast = setTimeout(() => { caixa.hidden = true; }, 2800);
  }

  // ---------------------------------------------------------------
  // Régua
  // ---------------------------------------------------------------
  function desenharRegua() {
    const marcas = el("regua-marcas");
    marcas.replaceChildren();

    const primeira = Math.ceil(config.altura_minima_cm / 5) * 5;
    for (let altura = primeira; altura <= config.altura_maxima_cm; altura += 5) {
      const marca = document.createElement("div");
      const maior = altura % 10 === 0;
      marca.className = "regua-marca" + (maior ? " maior" : "");
      marca.style.bottom = porcentagemDaAltura(altura) + "%";
      if (maior) {
        const rotulo = document.createElement("span");
        rotulo.textContent = altura;
        marca.appendChild(rotulo);
      }
      marcas.appendChild(marca);
    }
  }

  /** Mostra na régua onde estão as etapas da máquina aberta (ou nada, se lista vazia). */
  function definirEtapas(etapas) {
    const area = el("regua-etapas");
    area.replaceChildren();
    etapas.forEach((etapa) => {
      const bolinha = document.createElement("div");
      bolinha.className = "regua-etapa";
      bolinha.textContent = etapa.ordem;
      bolinha.style.bottom = porcentagemDaAltura(etapa.altura_cm) + "%";
      area.appendChild(bolinha);
    });
  }

  // ---------------------------------------------------------------
  // Atualização a cada status recebido
  // ---------------------------------------------------------------
  function atualizar(status) {
    ultimoStatus = status;

    // Altura e ponteiro
    el("altura-valor").textContent = formatar(status.altura_cm);
    if (status.altura_cm !== null) {
      el("regua-ponteiro").style.bottom = porcentagemDaAltura(status.altura_cm) + "%";
    }

    // Carga
    const proporcao = status.carga_kg / config.carga_maxima_kg;
    el("carga-valor").textContent = formatar(status.carga_kg);
    const barra = el("carga-preenchida");
    barra.style.width = Math.min(100, proporcao * 100) + "%";
    barra.dataset.nivel = proporcao > 1 ? "excedida" : proporcao >= 0.8 ? "atencao" : "normal";

    // Estado
    const chip = el("estado-chip");
    chip.dataset.estado = status.estado;
    chip.textContent = NOMES_ESTADO[status.estado] || status.estado;

    // Aviso fixo no topo da área de trabalho
    const aviso = el("aviso");
    const mostrarAviso = status.estado === "sobrecarga" || status.estado === "erro";
    aviso.hidden = !mostrarAviso;
    if (mostrarAviso) {
      aviso.textContent = status.mensagem;
      aviso.dataset.tipo = status.estado === "erro" ? "erro" : "sobrecarga";
    }

    // Tela de emergência
    el("tela-emergencia").hidden = !status.emergencia;
    const reiniciar = el("btn-reiniciar");
    reiniciar.disabled = status.botao_pressionado;
    reiniciar.textContent = status.botao_pressionado ? "Botão ainda acionado" : "Reiniciar";

    ouvintes.forEach((funcao) => funcao(status));
  }

  function semConexao() {
    const aviso = el("aviso");
    aviso.hidden = false;
    aviso.dataset.tipo = "erro";
    aviso.textContent = "Sem conexão com o servidor da bancada.";
  }

  async function ciclo() {
    try {
      const resposta = await fetch("/api/mesa/status");
      atualizar(await resposta.json());
    } catch (erro) {
      semConexao();
    }
    setTimeout(ciclo, INTERVALO_MS);
  }

  // ---------------------------------------------------------------
  // Emergência e simulação
  // ---------------------------------------------------------------
  async function reiniciarAposEmergencia() {
    const resposta = await Api.post("/api/mesa/reiniciar");
    if (!resposta.ok) toast(resposta.mensagem, "erro");
  }

  function iniciarSimulacao() {
    el("painel-simulacao").hidden = false;

    el("btn-simulacao").addEventListener("click", () => {
      const corpo = el("simulacao-corpo");
      corpo.hidden = !corpo.hidden;
    });

    el("simulacao-carga").addEventListener("input", (evento) => {
      const kg = Number(evento.target.value);
      el("simulacao-carga-valor").textContent = formatar(kg);
      Api.post("/api/simulacao/carga", { kg });
    });

    const botaoEmergencia = el("simulacao-emergencia");
    let acionada = false;
    botaoEmergencia.addEventListener("click", () => {
      acionada = !acionada;
      botaoEmergencia.textContent = acionada ? "Soltar emergência" : "Acionar emergência";
      Api.post("/api/simulacao/emergencia", { ativa: acionada });
    });
  }

  // ---------------------------------------------------------------
  // Início
  // ---------------------------------------------------------------
  function iniciar(configuracao) {
    config = configuracao;
    el("carga-max").textContent = formatar(config.carga_maxima_kg, 0);
    desenharRegua();
    el("btn-reiniciar").addEventListener("click", reiniciarAposEmergencia);
    if (config.simulado) iniciarSimulacao();
    ciclo();
  }

  return {
    iniciar,
    definirEtapas,
    formatar,
    toast,
    aoAtualizar: (funcao) => ouvintes.push(funcao),
    status: () => ultimoStatus,
  };
})();
