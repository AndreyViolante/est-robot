'use strict';
/* Web Worker que compila os programas com o Python do navegador (Pyodide), fora da página: um laço sem
   fim no programa do aluno não trava a tela, e a página pode parar este worker e criar outro.
   Mensagens: {id, fonte, nome} -> {id, resultado} (o dicionário de ponte.compilar) ou {id, falha};
   {id, ligadas} -> {id, resultado} (os avisos de portas do último programa compilado). */
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.29.5/full/';
const PASTA = '/home/pyodide/est';

importScripts(PYODIDE + 'pyodide.js');

async function baixar(caminho) {
  const r = await fetch(caminho, {cache: 'no-cache'});
  if (!r.ok) throw new Error(`não consegui baixar ${caminho} (${r.status})`);
  return r.text();
}

const pronto = (async () => {
  const [py, lista] = await Promise.all([
    loadPyodide({indexURL: PYODIDE}),
    baixar('projeto/arquivos.json').then(JSON.parse),
  ]);
  py.FS.mkdirTree(PASTA);
  const arquivos = [...lista.arquivos.map(a => ['projeto/' + a, a]), ['ponte.py', 'ponte.py']];
  const textos = await Promise.all(arquivos.map(([url]) => baixar(url)));
  arquivos.forEach(([, nome], i) => py.FS.writeFile(`${PASTA}/${nome}`, textos[i]));
  py.runPython(`import sys\nsys.path.insert(0, ${JSON.stringify(PASTA)})\nimport ponte`);
  return py.pyimport('ponte');
})();

pronto.then(() => postMessage({pronto: true}), e => postMessage({falhaCarga: String(e && e.message || e)}));

onmessage = async ({data}) => {
  let ponte;
  try {
    ponte = await pronto;
  } catch (e) {
    postMessage({id: data.id, falha: String(e && e.message || e)});
    return;
  }
  try {
    const json = data.ligadas ? ponte.avisos_de_portas_json(JSON.stringify(data.ligadas))
                              : ponte.compilar_json(data.fonte, data.nome);
    postMessage({id: data.id, resultado: JSON.parse(json)});
  } catch (e) {
    // erro que não é do programa do aluno (ou um exit() dentro dele): mostra a última linha do Python
    const linhas = String(e && e.message || e).trim().split('\n');
    postMessage({id: data.id, falha: linhas[linhas.length - 1]});
  }
};
