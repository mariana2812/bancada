/* =====================================================================
   TECLADO VIRTUAL - a bancada não tem teclado físico, então a tela
   mostra este teclado sempre que o operador toca em um campo de texto.

   Funciona em qualquer <input inputmode="none">.
   Atributo opcional data-cap no campo:
       data-cap="palavras" -> primeira letra de cada palavra maiúscula (nomes)
       data-cap="frase"    -> só a primeira letra maiúscula
   ===================================================================== */

const Teclado = (() => {
  const elemento = document.getElementById("teclado");

  const NUMEROS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"];
  const LETRAS = [
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l", "ç"],
    ["z", "x", "c", "v", "b", "n", "m", ".", "-"],
  ];
  const ACENTOS = [
    ["á", "à", "â", "ã", "é", "ê", "í"],
    ["ó", "ô", "õ", "ú", "ü", "ñ", "ç"],
    ["_", "@", "#", "&", "+", "/", ","],
  ];

  let campo = null;          // campo de texto que está sendo preenchido
  let maiuscula = false;
  let camada = "letras";     // "letras" ou "acentos"

  // ---------------------------------------------------------------
  // Desenho do teclado
  // ---------------------------------------------------------------
  function criarTecla(texto, classe, acao) {
    const tecla = document.createElement("button");
    tecla.type = "button";
    tecla.className = "tecla " + (classe || "");
    tecla.textContent = texto;
    tecla.addEventListener("pointerdown", (evento) => {
      evento.preventDefault();   // mantém o foco no campo
      acao();
    });
    return tecla;
  }

  function criarLinha(teclas) {
    const linha = document.createElement("div");
    linha.className = "tecla-linha";
    teclas.forEach((tecla) => linha.appendChild(tecla));
    return linha;
  }

  function letra(caractere) {
    const texto = maiuscula ? caractere.toUpperCase() : caractere;
    return criarTecla(texto, "", () => digitar(texto));
  }

  function desenhar() {
    elemento.replaceChildren();

    // Linha dos números + apagar
    const numeros = NUMEROS.map(letra);
    numeros.push(criarTecla("⌫", "tecla-larga", apagar));
    elemento.appendChild(criarLinha(numeros));

    const linhas = camada === "letras" ? LETRAS : ACENTOS;
    linhas.forEach((caracteres, indice) => {
      const teclas = caracteres.map(letra);
      // Tecla de maiúscula no começo da última linha de letras
      if (camada === "letras" && indice === 2) {
        teclas.unshift(criarTecla("⇧", "tecla-larga" + (maiuscula ? " tecla-ativa" : ""), alternarMaiuscula));
      }
      elemento.appendChild(criarLinha(teclas));
    });

    // Linha de baixo: trocar camada, espaço, OK
    elemento.appendChild(criarLinha([
      criarTecla(camada === "letras" ? "áé@" : "ABC", "tecla-larga", alternarCamada),
      criarTecla("espaço", "tecla-espaco", () => digitar(" ")),
      criarTecla("OK", "tecla-larga tecla-ok", confirmar),
    ]));
  }

  // ---------------------------------------------------------------
  // Ações das teclas
  // ---------------------------------------------------------------
  function digitar(texto) {
    if (!campo) return;
    const limite = campo.maxLength > 0 ? campo.maxLength : Infinity;
    if (campo.value.length >= limite) return;
    campo.value += texto;
    depoisDeEditar(true);
  }

  function apagar() {
    if (!campo) return;
    campo.value = campo.value.slice(0, -1);
    depoisDeEditar(false);
  }

  function alternarMaiuscula() {
    maiuscula = !maiuscula;
    desenhar();
  }

  function alternarCamada() {
    camada = camada === "letras" ? "acentos" : "letras";
    desenhar();
  }

  function confirmar() {
    // Vai para o próximo campo da mesma janela/formulário; se não tiver, fecha
    const area = campo.closest("form, .modal, .coluna-form") || document;
    const campos = [...area.querySelectorAll('input[inputmode="none"]')].filter((c) => c.offsetParent !== null);
    const proximo = campos[campos.indexOf(campo) + 1];
    if (proximo) proximo.focus();
    else fechar();
  }

  function depoisDeEditar(digitou) {
    campo.dispatchEvent(new Event("input", { bubbles: true }));
    if (digitou) maiuscula = false;
    aplicarMaiusculaAutomatica();
    desenhar();
  }

  function aplicarMaiusculaAutomatica() {
    const modo = campo && campo.dataset.cap;
    if (modo === "palavras" && (campo.value === "" || campo.value.endsWith(" "))) maiuscula = true;
    if (modo === "frase" && campo.value === "") maiuscula = true;
  }

  // ---------------------------------------------------------------
  // Abrir e fechar
  // ---------------------------------------------------------------
  function abrir(novoCampo) {
    campo = novoCampo;
    maiuscula = false;
    camada = "letras";
    aplicarMaiusculaAutomatica();
    desenhar();

    elemento.hidden = false;
    document.body.classList.add("teclado-aberto");
    document.documentElement.style.setProperty("--altura-teclado", elemento.offsetHeight + "px");
    setTimeout(() => campo && campo.scrollIntoView({ block: "center" }), 60);
  }

  function fechar() {
    if (elemento.hidden) return;
    elemento.hidden = true;
    document.body.classList.remove("teclado-aberto");
    document.documentElement.style.setProperty("--altura-teclado", "0px");
    if (campo) campo.blur();
    campo = null;
  }

  function iniciar() {
    // Tocou em um campo -> abre o teclado
    document.addEventListener("focusin", (evento) => {
      if (evento.target.matches('input[inputmode="none"]')) abrir(evento.target);
    });

    // Tocou numa área vazia -> fecha. Botões e campos não fecham, senão a tela
    // se mexeria antes do toque terminar e o botão não funcionaria.
    document.addEventListener("pointerdown", (evento) => {
      if (elemento.hidden) return;
      if (evento.target.closest("#teclado, button, input, label, a")) return;
      fechar();
    });
  }

  return { iniciar, fechar };
})();
