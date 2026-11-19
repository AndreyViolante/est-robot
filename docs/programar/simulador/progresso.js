'use strict';
/* Salvar e carregar o progresso num arquivo: o que o EST-LAB guarda neste navegador (desafios cumpridos, Minha
   pista, Minha arena OBR, medidas do robô, o programa, os blocos e as versões) vai para um .json que o aluno leva
   para outro computador ou guarda antes de limpar o navegador. Usado pelo simulador e pela página de programar;
   o ferramentas/teste_progresso.js testa no Node. */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

const FORMATO = 'est-lab-progresso';
const VERSAO = 1;
// o que cada página guarda no navegador (as que não existem neste navegador ficam de fora do arquivo)
const CHAVES = ['est-simulador-v1', 'est-programar-v1', 'est-programar-blocos-v1', 'est-programar-versoes-v1'];
const LIMITE = 5000000;                 // caracteres: o navegador guarda uns 5 MB por página

const objeto = v => v !== null && typeof v === 'object' && !Array.isArray(v);

/* O progresso guardado neste navegador, pronto para virar arquivo. armazenamento: o localStorage (ou um objeto com
   getItem/setItem, nos testes) */
function juntar(armazenamento = globalThis.localStorage, agora = new Date()) {
  const dados = {};
  for (const chave of CHAVES) {
    let texto = null;
    try { texto = armazenamento.getItem(chave); } catch (e) { /* sem armazenamento */ }
    if (texto == null) continue;
    try { dados[chave] = JSON.parse(texto); } catch (e) { /* guardado estragado: fica de fora */ }
  }
  return {formato: FORMATO, versao: VERSAO, salvoEm: agora.toISOString(), dados};
}

const texto = progresso => JSON.stringify(progresso, null, 1);

/* O progresso de um arquivo, conferido; um arquivo que não é progresso do EST-LAB dá um erro em português. */
function ler(conteudo) {
  if (typeof conteudo !== 'string' || conteudo.length > LIMITE) throw new Error('esse arquivo é grande demais para ser um progresso do EST-LAB');
  let p;
  try { p = JSON.parse(conteudo.replace(/^﻿/, '')); } catch (e) { p = null; }
  if (!objeto(p) || p.formato !== FORMATO || !objeto(p.dados)) {
    throw new Error('esse arquivo não é um progresso do EST-LAB (é o .json do "Salvar progresso")');
  }
  if (!Number.isInteger(p.versao) || p.versao > VERSAO) {
    throw new Error('esse progresso foi salvo por uma versão mais nova do EST-LAB: atualize a página e tente de novo');
  }
  const dados = {};
  for (const chave of CHAVES) if (chave in p.dados && p.dados[chave] !== null) dados[chave] = p.dados[chave];
  return {formato: FORMATO, versao: p.versao, salvoEm: typeof p.salvoEm === 'string' ? p.salvoEm : '', dados};
}

/* Grava o progresso no navegador, por cima do que estava. Devolve as chaves gravadas. Se o navegador não deixar
   (sem espaço, modo anônimo), desfaz o que já tinha gravado e dá um erro. */
function aplicar(progresso, armazenamento = globalThis.localStorage) {
  const antes = {}, gravadas = [];
  try {
    for (const [chave, valor] of Object.entries(progresso.dados)) {
      antes[chave] = armazenamento.getItem(chave);
      armazenamento.setItem(chave, JSON.stringify(valor));
      gravadas.push(chave);
    }
  } catch (e) {
    for (const chave of gravadas) {
      try {
        if (antes[chave] == null) armazenamento.removeItem(chave); else armazenamento.setItem(chave, antes[chave]);
      } catch (e2) { /* nada a fazer */ }
    }
    throw new Error('o navegador não deixou guardar o progresso (sem espaço, ou numa janela anônima)');
  }
  return gravadas;
}

/* O que tem no progresso, em português, para o aluno conferir antes de carregar. */
function resumo(progresso) {
  const d = progresso.dados, partes = [];
  const sim = objeto(d['est-simulador-v1']) ? d['est-simulador-v1'] : null;
  if (sim) {
    const feitos = objeto(sim.desafios) ? Object.values(sim.desafios).filter(v => v && v.feito).length : 0;
    partes.push(feitos === 1 ? '1 desafio cumprido' : `${feitos} desafios cumpridos`);
    const arena = objeto(sim.arenaOBR) && Array.isArray(sim.arenaOBR.percurso) ? sim.arenaOBR.percurso.length : 0;
    if (arena) partes.push(`Minha arena OBR com ${arena} ladrilho${arena === 1 ? '' : 's'}`);
    if (objeto(sim.minha) && Array.isArray(sim.minha.linhas) && sim.minha.linhas.length) partes.push('Minha pista');
  }
  const prog = d['est-programar-v1'];
  if (objeto(prog) && typeof prog.fonte === 'string') {
    partes.push(`o programa ${typeof prog.nome === 'string' && prog.nome ? prog.nome + '.py' : 'da página de programar'}`);
  }
  if (d['est-programar-blocos-v1']) partes.push('os blocos');
  const versoes = Array.isArray(d['est-programar-versoes-v1']) ? d['est-programar-versoes-v1'].length : 0;
  if (versoes) partes.push(versoes === 1 ? '1 versão guardada' : `${versoes} versões guardadas`);
  return partes;
}

function nomeDoArquivo(agora = new Date()) {
  const dois = n => String(n).padStart(2, '0');
  return `progresso-est-lab-${agora.getFullYear()}-${dois(agora.getMonth() + 1)}-${dois(agora.getDate())}.json`;
}

const juntarComVirgulas = partes => (partes.length < 2 ? partes.join('')
  : `${partes.slice(0, -1).join(', ')} e ${partes[partes.length - 1]}`);

// ---------------------------------------------------------------- na página (botões)

function baixar(progresso = juntar()) {
  const url = URL.createObjectURL(new Blob([texto(progresso)], {type: 'application/json'}));
  const a = document.createElement('a');
  a.href = url;
  a.download = nomeDoArquivo();
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
  return resumo(progresso);
}

// dentro da página de programar o simulador é um quadro: recarrega a página toda, que também guarda o programa
function recarregar() {
  try {
    if (window.top !== window && window.top.location.origin === window.location.origin) { window.top.location.reload(); return; }
  } catch (e) { /* outra origem: só este quadro */ }
  window.location.reload();
}

/* Abre a janela de escolher arquivo, confere, pergunta e grava. Depois de gravar, recarrega a página (cada parte
   lê de novo o que está guardado). avisar(texto): mostra por que não carregou. */
const frase = t => t.charAt(0).toUpperCase() + t.slice(1) + (/[.!?]$/.test(t) ? '' : '.');
function escolherECarregar(avisar = t => window.alert(`Não carreguei o progresso. ${t}`)) {
  const entrada = document.createElement('input');
  entrada.type = 'file';
  entrada.accept = '.json,application/json';
  entrada.addEventListener('change', async () => {
    const arquivo = entrada.files && entrada.files[0];
    if (!arquivo) return;
    let progresso;
    try {
      progresso = ler(await arquivo.text());
    } catch (e) {
      avisar(frase(e.message));
      return;
    }
    const partes = resumo(progresso);
    const quando = progresso.salvoEm ? new Date(progresso.salvoEm) : null;
    const data = quando && !isNaN(quando) ? ` (salvo em ${quando.toLocaleDateString('pt-BR')})` : '';
    if (!Object.keys(progresso.dados).length) { avisar('Esse arquivo de progresso está vazio.'); return; }
    if (!window.confirm(`Carregar o progresso${data}: ${juntarComVirgulas(partes) || 'as configurações'}?\n\n`
                        + 'O que está guardado neste navegador é trocado pelo do arquivo.')) return;
    try {
      aplicar(progresso);
    } catch (e) {
      avisar(frase(e.message));
      return;
    }
    recarregar();
  });
  entrada.click();
}

EST.Progresso = {FORMATO, VERSAO, CHAVES, juntar, texto, ler, aplicar, resumo, nomeDoArquivo, juntarComVirgulas, baixar,
                 escolherECarregar};
})();
