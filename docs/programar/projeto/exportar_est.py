"""Salva um programa do EST-LAB no formato da IDE EST (.est): o caminho inverso do importar_est.py.

O programa em Python vira os mesmos blocos que vão para o robô (enviar.carregar), e cada bloco vira um bloco da
IDE no .est, com a ordem, os containers (Repetir e Decisão), os fios de dados e as variáveis. O formato e o desenho
dos blocos na tela são os dos projetos que a IDE já abriu (gabaritos/*.est). Os fios de um bloco ficam todos num
<line_info> só, como a IDE grava: ao abrir, ela guarda os fios num mapa pelo bloco de origem e um <line_info>
repetido apaga o anterior. No fim, confere: o .est lido de volta (importar_est) compila para os mesmos bytes.

Uso:  python exportar_est.py programa.py                 grava para_ide/programa.est
      python exportar_est.py programa.py --saida pasta   em outra pasta
"""
import base64, json, os, re, sys

LARGURA = {'2001': 117, '4001': 144, '1007': 144, '5005': 144, '1005': 246, '1006': 212}
LARGURA_MOTOR = {'1': 144, '2': 144, '3': 246, '4': 246, '5': 246}      # Desligado, Ligado, segundos/graus/rotações
CONTAINERS = ('2003', '2004')
PARALELO = '9001'
X0, Y0 = -600, 300                          # o bloco de início, onde a IDE põe


class NaoCabeNaIde(ValueError):
    """O programa tem algo que a IDE não sabe representar (a mensagem diz o quê e o que fazer)."""


def _esc(s):
    return str(s).replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')


def _largura(b):
    if b.t == '1004' and b.mode == '2':
        return 178                                       # Mover Tanque Ligado (medido em arquivo da IDE)
    if b.t in ('1002', '1003', '1004'):
        return LARGURA_MOTOR.get(b.mode, 246)
    if b.t.startswith('6'):
        return 111
    return LARGURA.get(b.t, 212)


def _ramos(b):
    if b.t == '2004':
        return [b.b1, b.b2]
    if b.t == '2003':
        return [b.b1]
    return []


# ---------------------------------------------------------------- desenho na tela (medido em arquivos da IDE)

class _No:
    """Um bloco no .est: o bloco do EST-LAB, a posição, o pai e o anterior na sequência."""
    def __init__(self, b):
        self.b, self.id, self.anterior, self.pai = b, None, None, None
        self.x = self.y = 0
        self.z = 1
        self.extra = {}                                     # str1..str5 dos containers
        self.tamanho = None


def _tamanho(no, nos):
    """(largura, altura) do bloco; containers pelo que têm dentro."""
    if no.tamanho:
        return no.tamanho
    b = no.b
    if b.t == '2004':
        h1, h2 = (_altura_ramo(r, nos) for r in (b.b1, b.b2))
        logico = b.mode in ('37', '35', '36', '38', '33')
        ix = 129 if logico else 163
        dentro = min(max(_largura_cadeia(b.b1, nos), _largura_cadeia(b.b2, nos), 111) + 180, 3000 - ix - 14)
        no.geo = dict(h1=h1, h2=h2, ix=ix, dentro=dentro, W=dentro + ix + 14, H=h1 + h2)
        no.tamanho = (no.geo['W'], no.geo['H'])
    elif b.t == '2003':
        alturas = [_tamanho(nos[id(x)], nos)[1] for x in b.b1 if x.t in CONTAINERS]
        H = max(alturas) + 100 if alturas else 316
        no.geo = dict(W=_largura_cadeia(b.b1, nos) + 260, H=H)
        no.tamanho = (no.geo['W'], H)
    else:
        no.tamanho = (_largura(b), 110)
    return no.tamanho


def _largura_cadeia(cadeia, nos):
    return sum(_tamanho(nos[id(b)], nos)[0] for b in cadeia)


def _altura_ramo(cadeia, nos):
    alturas = [_tamanho(nos[id(b)], nos)[1] for b in cadeia if b.t in CONTAINERS]
    return max(alturas) + 60 if alturas else 219


def _altura_cadeia(cadeia, nos):
    return max([_tamanho(nos[id(b)], nos)[1] for b in cadeia] or [110])


def _posicionar(cadeia, x, y, pai, z, nos, ordem, anterior=None):
    """Põe cada bloco da sequência na tela, na ordem em que a IDE numera (em profundidade)."""
    for b in cadeia:
        if b.t == PARALELO:                                  # vira a sequência dividida da IDE
            yy = y
            for ramo in b.ramos:
                _posicionar(ramo, x, yy, pai, z, nos, ordem, anterior)
                yy += _altura_cadeia(ramo, nos) + 60
            return
        no = nos[id(b)]
        w, h = _tamanho(no, nos)
        no.pai, no.z, no.anterior, no.x = pai, z, anterior, x
        if b.t == '2004':
            g = no.geo
            no.y = y - (g['h1'] - 54)
            ordem.append(no)
            s1, s2 = (g['h1'] - 119) // 2, (g['h2'] - 119) // 2
            no.extra = {
                'str1': (f"{no.x},{no.y},{g['W']},{g['H']}|{g['ix']},0,{g['dentro']},{g['H']}|"
                         f"{g['ix'] - 13},0,13,{g['H']}|{g['W'] - 14},0,14,{g['H']}|0,0,{g['ix'] - 13},{g['H']}|"),
                'str2': f"{g['ix']},0,{g['dentro']},{g['h1']}|{g['ix']},{g['h1']},{g['dentro']},{g['h2']}|",
                'str3': f'{s1}|{s2}|', 'str4': f'0|0|0|{b.mode}|0|', 'str5': '1|0|'}
            dx = g['ix'] + 24
            _posicionar(b.b1, no.x + dx, no.y + s1 + 5, (no, 1), z + 1, nos, ordem)
            _posicionar(b.b2, no.x + dx, no.y + g['h1'] + s2 + 5, (no, 2), z + 1, nos, ordem)
        elif b.t == '2003':
            g = no.geo
            no.y = y - (g['H'] - 109) // 2
            ordem.append(no)
            no.extra = {'str1': '', 'str2': f"0,0,{g['W']},{g['H']}|", 'str3': f"{(g['H'] - 132) // 2}|",
                        'str4': '0|' if b.mode == '35' else '1|', 'str5': f"{b.label or '01'}|"}
            _posicionar(b.b1, no.x + 99, y, (no, 1), z + 1, nos, ordem)
        else:
            no.y = y
            ordem.append(no)
        anterior = no
        x += w


# ---------------------------------------------------------------- conferências antes de gravar

def _conferir(cadeia, dentro_de=None):
    """Recusa o que a IDE não tem como abrir: blocos que só existem no EST-LAB."""
    import estc
    for i, b in enumerate(cadeia):
        if b.t == PARALELO:
            onde = f'na linha {b.linha} ' if getattr(b, 'linha', None) else ''
            oque = (f'{onde}o programa faz partes ao mesmo tempo (ao_mesmo_tempo, ajustes, ajustando ou medir_laco)')
            if dentro_de is not None:
                raise NaoCabeNaIde(f'{oque} dentro de um laço ou de um if: na IDE as partes ao mesmo tempo só podem '
                                   'sair da sequência principal do programa')
            if i == len(cadeia) - 1 and len(b.ramos) >= 2:
                for ramo in b.ramos:
                    if not ramo:
                        raise NaoCabeNaIde(f'{oque} e uma das partes está vazia')
                    _conferir(ramo, None)
                continue
            raise NaoCabeNaIde(f'{oque} e depois continua: na IDE as partes ao mesmo tempo não se juntam de novo. '
                               'Para salvar para a IDE, elas precisam ser a última coisa do programa '
                               '(o medir_laco sempre continua depois, então não vai para a IDE)')
        if b.t != '2001' and b.t not in ('4001',) and (b.t, b.mode) not in estc.MODELOS:
            raise NaoCabeNaIde(f'o bloco {b.t} (modo {b.mode}) não tem modelo no compilador')
        for ramo in _ramos(b):
            _conferir(ramo, b)


def _variaveis(nos):
    vistos = []
    for no in nos:
        if no.b.t == '4001' and no.b.port not in vistos:
            vistos.append(no.b.port)
    return vistos


# ---------------------------------------------------------------- o XML

def _programa(nome, cadeia, recuo):
    """O <top> de um programa principal (tipo 1)."""
    nos = {}

    def criar(lista):
        for b in lista:
            nos[id(b)] = _No(b)
            for ramo in _ramos(b) + list(getattr(b, 'ramos', [])):
                criar(ramo)
    criar(cadeia)
    ordem = []
    _posicionar(cadeia, X0, Y0, None, 1, nos, ordem)
    for i, no in enumerate(ordem, 1):
        no.id = i
    if not ordem or ordem[0].b.t != '2001':
        raise NaoCabeNaIde('o programa precisa começar pelo bloco de início')

    modulos = {}
    for no in ordem:
        b = no.b
        pai = '0' if no.pai is None else str(no.pai[0].id * 32768 + no.pai[1])
        d = {'ifportbeconnect': '1' if any(e == 0 for e, _, _ in b.wires) else '0', 'moduleifchoose': '0',
             'moduleifvisible': '1', 'moduleposx': str(no.x), 'moduleposy': str(no.y), 'modulestate': str(b.mode),
             'moduletype': str(b.t), 'paramvalues': str(b.params), 'parentid': pai, 'portvalue': str(b.port)}
        d.update(no.extra)
        d['zvalue'] = str(no.z)
        modulos[str(no.id)] = d
    info = {'0': len(ordem), 'blockline': '', 'rd': ''}
    info.update(modulos)
    info = {k: info[k] for k in sorted(info)}               # o QJsonObject da IDE grava as chaves em ordem de texto

    seguintes = {no.id: [] for no in ordem}
    for no in ordem:
        if no.anterior is not None:
            seguintes[no.anterior.id].append(no.id)
    fios = {}                                               # id do bloco de origem -> [(saída, destino, entrada)]
    for no in ordem:
        for entrada, origem, saida in no.b.wires:
            if id(origem) not in nos or nos[id(origem)].id is None:
                raise NaoCabeNaIde('um fio vem de um bloco que não está no programa')
            fios.setdefault(nos[id(origem)].id, []).append((saida, no.id, entrada))

    I = ' ' * recuo
    L = [f'{I}<top show="1" name="{_esc(nome)}" type="1">',
         f'{I}    <modulesInfos info="{_esc(json.dumps(info, separators=(",", ":"), ensure_ascii=False))}"/>',
         f'{I}    <head_info>']
    L += [f'{I}        <head_relation pre="{-1 if no.anterior is None else no.anterior.id}" post="{no.id}"/>'
          for no in ordem]
    L += [f'{I}    </head_info>', f'{I}    <tear_info>']
    L += [f'{I}        <tear_relation pre="{no.id}" post="{"".join(f"{s}/" for s in seguintes[no.id])}"/>'
          for no in ordem]
    L += [f'{I}    </tear_info>', f'{I}    <dataline_info>']
    for origem in sorted(fios):                             # um <line_info> por bloco de origem, com todos os fios
        L.append(f'{I}        <line_info out_module_id="{origem}">')
        L += [f'{I}            <line_info_other out_para_id="{s}" in_module_id="{d}" in_para_id="{e}"/>'
              for s, d, e in fios[origem]]
        L.append(f'{I}        </line_info>')
    L += [f'{I}    </dataline_info>', f'{I}    <noteInfos note_info="0"/>']
    especial = ''
    for no in ordem:
        if no.b.t not in CONTAINERS:
            continue
        especial += f'{no.id}*'
        for ramo in _ramos(no.b):
            ids = [nos[id(x)].id for x in ramo]
            if not ids:
                especial += '////|'
                continue
            elos = ''.join(f'{m}+{p}+' for m, p in zip(ids, [-1] + ids[:-1]))
            tipos = ''.join(f'{nos[id(x)].id}-{x.t}-' for x in ramo)
            especial += f'{ids[0]}-//{elos}/{tipos}/' + '-'.join(str(m) for m in reversed(ids)) + '|'
        especial += '}'
    L += [f'{I}    <special_info special="{_esc(especial)}"/>', f'{I}</top>']
    return '\r\n'.join(L), _variaveis(ordem)


def para_xml(cadeia, nome='programa'):
    """O XML do projeto da IDE com um programa principal (a lista de blocos, começando pelo início)."""
    _conferir(cadeia)
    nome = re.sub(r'[^A-Za-z0-9_]', '_', nome) or 'programa'
    top, variaveis = _programa(nome, cadeia, 4)
    atributos = {'prj_name': nome, 'prj_photo_content': '', 'prj_sec_photo_content': '', 'prj_description': '',
                 'programs': [{'0': nome}], 'my_graphs': [], 'my_sounds': [], 'my_module': [],
                 'my_varieties': [{'num': v} for v in variaveis]}
    L = [f'<project image="" video="" conEditQStr="0+-*/+-*/1+-*/0+-*/ /*-+" projectDesc="" '
         f'projAttri="{_esc(json.dumps(atributos, separators=(",", ":"), ensure_ascii=False))}" name="{_esc(nome)}" '
         f'info="" firstTimeOpen="1" projectTitle="" VideoImage="">',
         '    <myModule>', '    </myModule>', top, '</project>']
    return '\r\n'.join(L) + '\r\n'


def para_est(cadeia, nome='programa'):
    """O conteúdo do arquivo .est (bytes): o XML em base64, numa linha só, como a IDE grava."""
    return base64.b64encode(para_xml(cadeia, nome).encode('utf-8'))


def conferir_bytes(cadeia, est):
    """True se o .est, lido de volta como a IDE lê (importar_est), compila para os mesmos bytes que os blocos."""
    import estc, importar_est
    programas, _ = importar_est.ler(est)
    return estc.compilar(programas[0].blocos) == estc.compilar(cadeia)


def exportar(arquivo, pasta='para_ide'):
    """Compila o .py e grava pasta/<nome>.est. Devolve (caminho, bytes iguais?)."""
    import enviar
    cadeia = enviar.carregar(arquivo)
    nome = re.sub(r'[^A-Za-z0-9_]', '_', os.path.splitext(os.path.basename(arquivo))[0]) or 'programa'
    est = para_est(cadeia, nome)
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, f'{nome}.est')
    with open(destino, 'wb') as f:
        f.write(est)
    return destino, conferir_bytes(cadeia, est)


def para_est_json(arquivo, nome):
    """Para a página de programar (Pyodide): o .py do aluno -> {base64, iguais} ou {erro}."""
    import enviar
    try:
        cadeia = enviar.carregar(arquivo)
        est = para_est(cadeia, nome)
        return json.dumps({'est': est.decode('ascii'), 'iguais': conferir_bytes(cadeia, est)})
    except NaoCabeNaIde as e:
        return json.dumps({'erro': str(e)}, ensure_ascii=False)
    except Exception as e:                      # o programa do aluno pode ter qualquer erro
        linha, codigo, texto = enviar.explicar(e, arquivo)
        return json.dumps({'erro': texto, 'linha': linha, 'codigo': codigo}, ensure_ascii=False)


def main():
    args, pasta, resto = [], 'para_ide', sys.argv[1:]
    while resto:
        a = resto.pop(0)
        if a == '--saida' and resto:
            pasta = resto.pop(0)
        elif not a.startswith('--'):
            args.append(a)
    if not args or not args[0].endswith('.py'):
        sys.exit('Diga qual programa salvar: python exportar_est.py programa.py')
    import enviar
    arquivo = args[0]
    try:
        destino, iguais = exportar(arquivo, pasta)
    except NaoCabeNaIde as e:
        sys.exit(f'ERRO: não dá para salvar para a IDE: {e}.')
    except OSError as e:
        sys.exit(f'ERRO: {e}')
    except Exception as e:                      # o programa do aluno pode ter qualquer erro
        enviar._mostrar_erro(e, arquivo)
        sys.exit(1)
    print(f'[OK] {os.path.normpath(destino)}')
    if iguais:
        print('     lido de volta, o .est tem os mesmos blocos e dá os mesmos bytes que o EST-LAB manda para o robô.')
    else:
        print('     AVISO: lido de volta, o .est não deu os mesmos bytes. Confira o programa na IDE antes de enviar.')
    print('     Na IDE EST: Arquivo > Abrir e escolha o .est. Ao enviar, a IDE grava por cima do arquivo aberto.')


if __name__ == '__main__':
    main()
