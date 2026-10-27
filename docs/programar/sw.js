'use strict';
/* Service worker da página de programar: depois da primeira visita, a página funciona sem internet neste
   navegador (laboratório com internet ruim). Guarda a página, o simulador, o Python do navegador (Pyodide),
   o editor (CodeMirror) e os blocos (Blockly).
   - Arquivos da página: primeiro a internet (assim as atualizações chegam) e, sem internet, a cópia guardada.
   - Bibliotecas da CDN: têm a versão no endereço e nunca mudam, então vale a cópia guardada.
   Trocou a versão de uma biblioteca no compilador.js, no modo_blocos.js ou no index.html? Troque aqui também
   (o verificar_gabaritos.py confere). A lista de arquivos da página vem do projeto/arquivos.json, que o
   ferramentas/publicar_programar.py escreve. */
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.29.5/full/';
const BLOCKLY = 'https://cdn.jsdelivr.net/npm/blockly@12.3.1/';
const CODEMIRROR = 'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.18/';
const BIBLIOTECAS = [PYODIDE, BLOCKLY, CODEMIRROR];
const DAS_BIBLIOTECAS = [
  PYODIDE + 'pyodide.js', PYODIDE + 'pyodide.asm.js', PYODIDE + 'pyodide.asm.wasm',
  PYODIDE + 'python_stdlib.zip', PYODIDE + 'pyodide-lock.json',
  BLOCKLY + 'blockly_compressed.js', BLOCKLY + 'blocks_compressed.js', BLOCKLY + 'msg/pt-br.js',
  CODEMIRROR + 'codemirror.min.css', CODEMIRROR + 'codemirror.min.js', CODEMIRROR + 'mode/python/python.min.js',
  CODEMIRROR + 'addon/edit/matchbrackets.min.js',
];
const CACHE_PAGINA = 'est-programar-pagina';
const CACHE_BIBLIOTECAS = 'est-programar-bibliotecas ' + BIBLIOTECAS.join(' ');   // versão nova = cópia nova
const PASTA = new URL('./', self.location).pathname;

// a cópia guardada não depende do ?número que a página põe no simulador para recarregar
const semBusca = url => { const u = new URL(url); return u.origin + u.pathname; };
// nas bibliotecas, sempre com CORS: a resposta serve para <script integrity> e para o importScripts do worker
const baixarBiblioteca = url => fetch(url, {mode: 'cors', credentials: 'omit'});

self.addEventListener('install', evento => {
  evento.waitUntil((async () => {
    const lista = await (await fetch('projeto/arquivos.json', {cache: 'no-cache'})).json();
    await (await caches.open(CACHE_PAGINA)).addAll(['./', ...(lista.offline || [])]);
    const bib = await caches.open(CACHE_BIBLIOTECAS);
    await Promise.all(DAS_BIBLIOTECAS.map(async url => {
      if (await bib.match(url)) return;
      try {
        const r = await baixarBiblioteca(url);
        if (r.ok) await bib.put(url, r);
      } catch (e) { /* fica para a próxima visita */ }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', evento => {
  evento.waitUntil((async () => {
    for (const nome of await caches.keys()) {
      if (nome.startsWith('est-programar-') && nome !== CACHE_PAGINA && nome !== CACHE_BIBLIOTECAS) await caches.delete(nome);
    }
    await self.clients.claim();
  })());
});

async function daBiblioteca(pedido) {
  const bib = await caches.open(CACHE_BIBLIOTECAS);
  const guardada = await bib.match(pedido.url);
  if (guardada) return guardada;
  const r = await baixarBiblioteca(pedido.url);
  if (r.ok) await bib.put(pedido.url, r.clone());
  return r;
}

async function daPagina(pedido) {
  const pagina = await caches.open(CACHE_PAGINA);
  try {
    const r = await fetch(pedido);
    if (r.ok) await pagina.put(semBusca(pedido.url), r.clone());
    return r;
  } catch (erro) {                                  // sem internet
    const guardada = await pagina.match(semBusca(pedido.url)) ||
                     (pedido.mode === 'navigate' ? await pagina.match('./') : undefined);
    if (guardada) return guardada;
    throw erro;
  }
}

self.addEventListener('fetch', evento => {
  const pedido = evento.request;
  if (pedido.method !== 'GET') return;
  if (BIBLIOTECAS.some(b => pedido.url.startsWith(b))) {
    evento.respondWith(daBiblioteca(pedido));
    return;
  }
  const url = new URL(pedido.url);
  if (url.origin === self.location.origin && url.pathname.startsWith(PASTA)) evento.respondWith(daPagina(pedido));
  // o resto (a contagem de visitas no GitHub, por exemplo) segue direto, sem guardar nada
});
