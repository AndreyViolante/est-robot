'use strict';
/* Arquivo cifrado com um código: o simulador pode ter extras que só abrem com o código de quem os fez. O arquivo
   (extras.dat) fica público, mas sem o código ninguém lê nem roda o que está dentro.
   Chave: PBKDF2-SHA256 do código (com sal e muitas voltas); cifra: AES-256-GCM, que também confere se o arquivo
   não foi mexido. Funciona no navegador e no Node (crypto.subtle). O ferramentas/cifrar_extras.py faz o arquivo. */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

const FORMATO = 'est-extras';
const VOLTAS = 250000;
const sutil = () => globalThis.crypto && globalThis.crypto.subtle;
function paraB64(bytes) {
  const b = new Uint8Array(bytes);
  let s = '';
  for (let i = 0; i < b.length; i += 8192) s += String.fromCharCode(...b.subarray(i, i + 8192));
  return btoa(s);
}
const deB64 = texto => Uint8Array.from(atob(texto), c => c.charCodeAt(0));

async function chave(codigo, sal, voltas) {
  const base = await sutil().importKey('raw', new TextEncoder().encode(String(codigo)), 'PBKDF2', false, ['deriveKey']);
  return sutil().deriveKey({name: 'PBKDF2', hash: 'SHA-256', salt: sal, iterations: voltas}, base,
                           {name: 'AES-GCM', length: 256}, false, ['encrypt', 'decrypt']);
}

/* texto -> pacote {formato, versao, voltas, sal, iv, dados} (base64), para gravar como JSON */
async function fechar(texto, codigo, voltas = VOLTAS) {
  if (!sutil()) throw new Error('este navegador não tem a criptografia que o arquivo usa');
  const sal = globalThis.crypto.getRandomValues(new Uint8Array(16));
  const iv = globalThis.crypto.getRandomValues(new Uint8Array(12));
  const dados = await sutil().encrypt({name: 'AES-GCM', iv}, await chave(codigo, sal, voltas), new TextEncoder().encode(texto));
  return {formato: FORMATO, versao: 1, voltas, sal: paraB64(sal), iv: paraB64(iv), dados: paraB64(dados)};
}

/* pacote + código -> texto. Código errado (ou arquivo mexido): erro "código errado". */
async function abrir(pacote, codigo) {
  if (!pacote || pacote.formato !== FORMATO || pacote.versao !== 1) throw new Error('arquivo de extras desconhecido');
  if (!sutil()) throw new Error('este navegador não tem a criptografia que o arquivo usa (abra pelo endereço https)');
  try {
    const k = await chave(codigo, deB64(pacote.sal), pacote.voltas);
    const texto = await sutil().decrypt({name: 'AES-GCM', iv: deB64(pacote.iv)}, k, deB64(pacote.dados));
    return new TextDecoder().decode(texto);
  } catch (e) {
    throw new Error('código errado');
  }
}

EST.Cifra = {FORMATO, fechar, abrir};
})();
