'use strict';
/* Imprimir uma arena da OBR do simulador em tamanho real, para montar a mesma pista no laboratório. Um
   ladrilho de 30 x 30 cm não cabe numa folha A4: cada um sai em 4 partes de 15 x 15 cm, com a linha de
   recorte e um mapa de onde a parte vai. A primeira folha mostra a arena inteira e como montar.
   Desenha com SVG em centímetros (viewBox) e tamanho em milímetros: impresso em 100%, 1 cm é 1 cm.
   paginas(pista) devolve o HTML (o ferramentas/teste_impressao.js confere sem navegador). */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

const PARTE = 15;                         // cm: um quarto do ladrilho por folha
const PRETO = '#000000', VERDE = '#00a651', VERMELHO = '#e2231a', CINZA = '#9aa0a6';
const QUARTOS = [[0, 0, 'em cima à esquerda'], [1, 0, 'em cima à direita'], [0, 1, 'embaixo à esquerda'],
                 [1, 1, 'embaixo à direita']];

const n = v => Math.round(v * 1000) / 1000;
const escapar = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

/* o chão da arena: linhas, verdes, faixa vermelha e o lugar do obstáculo, em cm */
function chao(pista) {
  const L = EST.LINHA || 2, partes = [];
  for (const t of pista.linhas) {
    if (t.seg) {
      const [x1, y1, x2, y2] = t.seg;
      partes.push(`<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}"/>`);
    } else if (t.arco) {
      const [cx, cy, r, a0, varre] = t.arco, rad = g => g * Math.PI / 180;
      const p0 = [cx + r * Math.cos(rad(a0)), cy + r * Math.sin(rad(a0))];
      const p1 = [cx + r * Math.cos(rad(a0 + varre)), cy + r * Math.sin(rad(a0 + varre))];
      partes.push(`<path d="M ${n(p0[0])} ${n(p0[1])} A ${n(r)} ${n(r)} 0 ${Math.abs(varre) > 180 ? 1 : 0} `
                  + `${varre > 0 ? 1 : 0} ${n(p1[0])} ${n(p1[1])}" fill="none"/>`);
    }
  }
  const retangulos = (lista, cor) => lista.map(q => `<rect x="${n(q.x)}" y="${n(q.y)}" width="${n(q.w)}" height="${n(q.h)}" fill="${cor}"/>`);
  return `<g stroke="${PRETO}" stroke-width="${L}" stroke-linecap="round">${partes.join('')}</g>`
    + retangulos(pista.verdes || [], VERDE).join('') + retangulos(pista.vermelhos || [], VERMELHO).join('')
    + (pista.caixas || []).map(c => `<rect x="${n(c.x)}" y="${n(c.y)}" width="${n(c.w)}" height="${n(c.h)}" fill="none" `
      + `stroke="${CINZA}" stroke-width="0.15" stroke-dasharray="0.6 0.4"/><text x="${n(c.x + c.w / 2)}" y="${n(c.y + c.h / 2)}" `
      + `font-size="1.2" text-anchor="middle" dominant-baseline="middle" fill="${CINZA}">obstáculo</text>`).join('');
}

/* os ladrilhos do percurso, sem repetir (o beco passa duas vezes no mesmo), numerados na ordem do caminho */
function ladrilhos(pista) {
  const vistos = new Map();
  for (const t of pista.obr.arena.percurso) {
    const k = `${t.c},${t.r}`;
    if (!vistos.has(k)) vistos.set(k, {c: t.c, r: t.r, numero: vistos.size + 1});
  }
  return [...vistos.values()];
}

/* mapa pequeno da arena: a grade, o número de cada ladrilho e, se marcar, o ladrilho e a parte desta folha */
function mapa(pista, lista, larguraMm, marcar) {
  const {LADO, BORDA} = pista.obr, a = pista.obr.arena;
  const w = a.colunas * LADO, h = a.linhas * LADO;
  let svg = `<svg class="mapa" width="${larguraMm}mm" height="${n(larguraMm * h / w)}mm" viewBox="${BORDA} ${BORDA} ${w} ${h}">`
    + `<rect x="${BORDA}" y="${BORDA}" width="${w}" height="${h}" fill="#fff"/>` + chao(pista);
  for (const t of lista) {
    const x = BORDA + t.c * LADO, y = BORDA + t.r * LADO, eu = marcar && marcar.t === t;
    svg += `<rect x="${x}" y="${y}" width="${LADO}" height="${LADO}" fill="${eu ? 'rgba(0,90,255,0.12)' : 'none'}" `
      + `stroke="${CINZA}" stroke-width="0.6"/>`;
    if (eu) {
      svg += `<rect x="${x + marcar.qx * PARTE}" y="${y + marcar.qy * PARTE}" width="${PARTE}" height="${PARTE}" `
        + `fill="rgba(0,90,255,0.28)" stroke="#0050e6" stroke-width="1"/>`;
    }
    svg += `<text x="${x + 2}" y="${y + 7}" font-size="6" font-weight="700" fill="#0050e6">${t.numero}</text>`;
  }
  return svg + '</svg>';
}

function paginas(pista, titulo = pista.nome || 'Arena da OBR') {
  if (!pista || !pista.obr) throw new Error('só dá para imprimir uma arena da OBR');
  const {LADO, BORDA} = pista.obr, lista = ladrilhos(pista), a = pista.obr.arena;
  const folhas = [`<section class="folha capa">
  <h1>${escapar(titulo)}</h1>
  <p>${lista.length} ladrilhos de 30 × 30 cm, em ${lista.length * 4} folhas A4 (4 por ladrilho), mais esta.
     Arena de ${a.colunas} × ${a.linhas} ladrilhos; o número de cada um é a ordem do caminho (1 = partida).</p>
  ${mapa(pista, lista, 180)}
  <ol>
    <li>Imprima em <b>tamanho real</b>: na janela de imprimir, escala 100% (desligue "ajustar à página").</li>
    <li>Confira com uma régua: o quadrado de cada folha tem 15 cm de lado.</li>
    <li>Recorte na linha cinza e cole as 4 partes de cada ladrilho num papelão de 30 × 30 cm, na posição do
        mapa da folha (o lado de cima da folha é o lado de cima da arena).</li>
    <li>A linha tem 2 cm (fita isolante de 1,9 cm serve) e o verde, 2,5 cm. No lugar marcado "obstáculo", ponha
        uma caixa de 10 cm.</li>
  </ol>
</section>`];
  for (const t of lista) {
    for (const [qx, qy, onde] of QUARTOS) {
      const x0 = BORDA + t.c * LADO + qx * PARTE, y0 = BORDA + t.r * LADO + qy * PARTE;
      folhas.push(`<section class="folha">
  <div class="topo"><span><b>Ladrilho ${t.numero}</b> · parte ${onde} · coluna ${t.c + 1}, linha ${t.r + 1}</span>${mapa(pista, lista, 38, {t, qx, qy})}</div>
  <svg class="parte" width="150mm" height="150mm" viewBox="${x0} ${y0} ${PARTE} ${PARTE}">
    <rect x="${x0}" y="${y0}" width="${PARTE}" height="${PARTE}" fill="#fff"/>${chao(pista)}
    <rect x="${x0}" y="${y0}" width="${PARTE}" height="${PARTE}" fill="none" stroke="${CINZA}" stroke-width="0.05"/>
  </svg>
  <p class="pe">Recorte na linha cinza. Lado de cima da folha = lado de cima da arena. ${escapar(titulo)}</p>
</section>`);
    }
  }
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${escapar(titulo)}: ladrilhos para imprimir</title>
<style>
  @page { size: A4 portrait; margin: 12mm; }
  body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; color: #1d2230; background: #fff; }
  .folha { page-break-after: always; break-after: page; display: flex; flex-direction: column; align-items: center; }
  .folha:last-child { page-break-after: auto; break-after: auto; }
  .capa { align-items: stretch; }
  .capa h1 { font-size: 20pt; margin: 0 0 4mm; }
  .capa p, .capa li { font-size: 11pt; line-height: 1.45; }
  .capa .mapa { margin: 4mm auto; display: block; }
  .topo { width: 150mm; display: flex; justify-content: space-between; align-items: center; font-size: 11pt; margin-bottom: 6mm; }
  .parte { display: block; }
  .pe { width: 150mm; font-size: 9pt; color: #5b6170; margin-top: 4mm; }
  .barra { position: sticky; top: 0; background: #eef1f6; padding: 8px 12px; display: flex; gap: 12px; align-items: center;
           font-size: 14px; border-bottom: 1px solid #d0d5de; }
  .barra button { font: inherit; padding: 6px 14px; border-radius: 6px; border: 1px solid #8a93a6; background: #fff; cursor: pointer; }
  @media print { .barra { display: none; } }
</style></head><body>
<div class="barra"><button type="button" onclick="window.print()">Imprimir</button>
<span>Imprima em tamanho real (escala 100%). Para guardar, escolha "Salvar como PDF" na janela de imprimir.</span></div>
${folhas.join('\n')}
</body></html>`;
}

/* abre as folhas numa aba nova (a janela tem que ser aberta no clique, senão o navegador bloqueia) */
function abrir(pista, titulo) {
  const janela = window.open('', '_blank');
  if (!janela) {
    window.alert('O navegador bloqueou a janela nova: permita janelas deste site e tente de novo.');
    return false;
  }
  janela.document.open();
  janela.document.write(paginas(pista, titulo));
  janela.document.close();
  return true;
}

EST.ImprimirArena = {paginas, abrir, ladrilhos, PARTE};
})();
