'use strict';
/* Versões do programa guardadas neste navegador (página de programar): a cada simulação ou envio, no Ctrl+S, antes
   de abrir outro programa e, enquanto o aluno escreve, de tempos em tempos. Dá para voltar a qualquer uma. Sem
   página: o programar.js mostra a lista, e o ferramentas/teste_versoes.js testa no Node. */
(function () {
const CHAVE = 'est-programar-versoes-v1';
const MAXIMO = 30;                    // versões guardadas, no máximo (a mais velha sai)
const LIMITE = 1500000;               // caracteres de todas juntas (o navegador guarda uns 5 MB por página)

const valida = v => v && typeof v === 'object' && typeof v.fonte === 'string' && Number.isFinite(v.quando);
const tamanho = v => v.fonte.length + (v.blocos ? JSON.stringify(v.blocos).length : 0);

/* armazenamento: o localStorage (ou um objeto com getItem/setItem, nos testes); agora: o relógio, em ms */
function criar(armazenamento = globalThis.localStorage, agora = () => Date.now()) {
  let contador = 0;

  function lista() {
    try {
      const l = JSON.parse(armazenamento.getItem(CHAVE));
      return Array.isArray(l) ? l.filter(valida) : [];
    } catch (e) {
      return [];                                        // sem armazenamento, ou guardado estragado
    }
  }

  // grava; se não couber, tira as mais velhas até caber (fica pelo menos a mais nova)
  function gravar(l) {
    for (;;) {
      try {
        armazenamento.setItem(CHAVE, JSON.stringify(l));
        return true;
      } catch (e) {
        if (l.length <= 1) return false;
        l.pop();
      }
    }
  }

  /* guarda uma versão {fonte, nome, modo, blocos, motivo}; não guarda se for igual à mais nova.
     Devolve a versão guardada ou null. */
  function guardar({fonte, nome = '', modo = 'python', blocos = null, motivo = ''}) {
    if (typeof fonte !== 'string' || !fonte.trim()) return null;
    const l = lista(), nova = l[0];
    const blocosJson = blocos ? JSON.stringify(blocos) : null;
    if (nova && nova.fonte === fonte && nova.modo === modo &&
        (nova.blocos ? JSON.stringify(nova.blocos) : null) === blocosJson) return null;
    const v = {id: `${agora().toString(36)}-${(contador++).toString(36)}`, quando: agora(), fonte, nome, modo, motivo};
    if (blocos) v.blocos = blocos;
    l.unshift(v);
    l.length = Math.min(l.length, MAXIMO);
    let total = 0;
    const cabem = l.filter(x => (total += tamanho(x)) <= LIMITE || x === v);
    return gravar(cabem) ? v : null;
  }

  function achar(id) { return lista().find(v => v.id === id) || null; }

  function apagar(id) {
    const l = lista(), resto = l.filter(v => v.id !== id);
    return resto.length !== l.length && gravar(resto);
  }

  /* há quanto tempo a versão mais nova foi guardada (ms; Infinity sem nenhuma) */
  function idadeDaMaisNova() {
    const nova = lista()[0];
    return nova ? agora() - nova.quando : Infinity;
  }

  return {lista, guardar, achar, apagar, idadeDaMaisNova};
}

const dois = n => String(n).padStart(2, '0');

/* "agora há pouco", "há 5 min", "hoje às 10:42", "ontem às 16:03", "12/11 às 09:15", "12/11/2025 às 09:15" */
function quando(ms, agora = Date.now()) {
  const d = new Date(ms), hoje = new Date(agora);
  const diferenca = agora - ms;
  if (diferenca >= 0 && diferenca < 60000) return 'agora há pouco';
  if (diferenca >= 0 && diferenca < 3600000) return `há ${Math.floor(diferenca / 60000)} min`;
  const hora = `${dois(d.getHours())}:${dois(d.getMinutes())}`;
  const mesmoDia = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  if (mesmoDia(d, hoje)) return `hoje às ${hora}`;
  const ontem = new Date(hoje);
  ontem.setDate(hoje.getDate() - 1);
  if (mesmoDia(d, ontem)) return `ontem às ${hora}`;
  const dia = `${dois(d.getDate())}/${dois(d.getMonth() + 1)}`;
  return d.getFullYear() === hoje.getFullYear() ? `${dia} às ${hora}` : `${dia}/${d.getFullYear()} às ${hora}`;
}

/* quantas linhas a versão tem a mais e a menos que o programa de agora: {mais, menos} (pelas linhas iguais em
   comum, a maior sequência; programas muito grandes contam só as linhas que não aparecem no outro) */
function diferenca(antiga, atual) {
  const a = antiga.replace(/\r\n?/g, '\n').replace(/\n+$/, '').split('\n');
  const b = atual.replace(/\r\n?/g, '\n').replace(/\n+$/, '').split('\n');
  if (a.length * b.length > 4e6) {
    const conta = l => l.reduce((m, x) => m.set(x, (m.get(x) || 0) + 1), new Map());
    const ca = conta(a), cb = conta(b);
    let comum = 0;
    for (const [x, n] of ca) comum += Math.min(n, cb.get(x) || 0);
    return {mais: a.length - comum, menos: b.length - comum};
  }
  let anterior = new Array(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    const linha = new Array(b.length + 1).fill(0);
    for (let j = 1; j <= b.length; j++) {
      linha[j] = a[i - 1] === b[j - 1] ? anterior[j - 1] + 1 : Math.max(anterior[j], linha[j - 1]);
    }
    anterior = linha;
  }
  const comum = anterior[b.length];
  return {mais: a.length - comum, menos: b.length - comum};
}

globalThis.ESTVersoes = {criar, quando, diferenca, MAXIMO, CHAVE};
})();
