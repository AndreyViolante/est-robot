"""Avisos antes de enviar: coisas que não impedem o programa de compilar, mas quase sempre são engano.

  - variável criada e nunca usada (do Python, ou do robô: guardar('x', ...) sem nenhum ler('x'))
  - laço sem fim (while True: / with para_sempre():) sem nenhuma espera e sem ler nenhum sensor
  - motor que fica ligado quando o programa termina

Cada aviso é um dicionário {linha, codigo, texto, arrumar}: a linha do arquivo do aluno (None se não se sabe),
o que está escrito nela, o problema e como arrumar. Os dois últimos usam os blocos do programa compilado, que
o enviar.carregar marca com a linha que criou cada um (atributo .linha).
"""
import ast

# blocos que fazem o laço esperar: Esperar, movimentos com quantidade (rotações, graus, segundos) e som
_ESPERAM = {('1002', m) for m in '345'} | {('1003', m) for m in '345'} | {('1004', m) for m in '345'}
# blocos que leem um sensor (ou botão, cronômetro, mensagem): o laço reage a alguma coisa
_LEEM = ({('3002', m) for m in '12345'} | {('3003', '1'), ('3003', '2'), ('3005', '1'), ('3005', '2'),
         ('3005', '3'), ('3007', '1'), ('3008', '1'), ('3009', '3'), ('3001', '1'), ('5001', '5')}
         | {('2004', m) for m in ('4', '5', '20', '21')} | {('2003', '2'), ('2003', '3')})
_LIGA = {('1002', '2'), ('1003', '2'), ('1004', '2')}               # Ligado: fica girando
_DESLIGA = {(t, m) for t in ('1002', '1003', '1004') for m in '1345'}   # Desligado, ou movimento que termina parado
_PARA_SEMPRE = ('2003', '33')


def do_programa(fonte, programa):
    """Os avisos do programa (texto do arquivo do aluno e a lista de blocos que ele gerou), na ordem das linhas."""
    linhas = fonte.replace('\r', '').split('\n')
    try:
        arvore = ast.parse(fonte)
    except SyntaxError:
        arvore = None
    avisos = []
    if arvore is not None:
        avisos += _variaveis_sem_uso(arvore) + _guardar_sem_ler(arvore)
    avisos += _lacos_sem_espera(programa, linhas) + _motores_ligados_no_fim(programa)
    for a in avisos:
        n = a['linha']
        a['codigo'] = linhas[n - 1].strip() if n and 0 < n <= len(linhas) else ''
    return sorted(avisos, key=lambda a: (a['linha'] or 0, a['texto']))


def como_texto(aviso, arquivo=''):
    """O aviso numa linha só (para o simulador e para listas): 'linha 5: ... Como arrumar: ...'."""
    onde = f'linha {aviso["linha"]}: ' if aviso['linha'] else ''
    return f'{onde}{aviso["texto"]} Como arrumar: {aviso["arrumar"]}'


def _aviso(linha, texto, arrumar):
    return {'linha': linha, 'texto': texto, 'arrumar': arrumar}


# ---------------------------------------------------------------- variáveis

def _alvos_de_laco(arvore):
    """Os nomes que são a variável de um for (for i in ...) ou de uma lista [x for x in ...]: não são avisados."""
    alvos = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.For, ast.AsyncFor, ast.comprehension)):
            alvos |= {id(n) for n in ast.walk(no.target)}
    return alvos


def _variaveis_sem_uso(arvore):
    usadas = {no.id for no in ast.walk(arvore) if isinstance(no, ast.Name) and isinstance(no.ctx, (ast.Load, ast.Del))}
    de_laco = _alvos_de_laco(arvore)
    criadas = {}
    for no in ast.walk(arvore):
        if (isinstance(no, ast.Name) and isinstance(no.ctx, ast.Store) and id(no) not in de_laco
                and not no.id.startswith('_') and no.id != 'PROGRAMA'):
            criadas[no.id] = min(criadas.get(no.id, no.lineno), no.lineno)
    return [_aviso(linha, f'a variável "{nome}" é criada mas nunca é usada no programa.',
                   f'use "{nome}" onde precisar desse valor, ou apague esta linha se ela sobrou.')
            for nome, linha in criadas.items() if nome not in usadas]


def _nomes_em(arvore, funcao):
    """{nome: primeira linha} das chamadas funcao('nome', ...) com o nome escrito entre aspas."""
    achados = {}
    for no in ast.walk(arvore):
        if (isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == funcao and no.args
                and isinstance(no.args[0], ast.Constant) and isinstance(no.args[0].value, str)):
            achados.setdefault(no.args[0].value, no.lineno)
    return achados


def _guardar_sem_ler(arvore):
    lidas = _nomes_em(arvore, 'ler')
    return [_aviso(linha, f'a variável do robô "{nome}" é guardada com guardar(...), mas nenhum ler("{nome}") usa o valor.',
                   f'leia com ler("{nome}") onde precisar do valor (ex.: mostrar(ler("{nome}"))), '
                   'ou apague o guardar se ele sobrou.')
            for nome, linha in _nomes_em(arvore, 'guardar').items() if nome not in lidas]


# ---------------------------------------------------------------- laços sem fim

def _ramos(b):
    return [b.b1, b.b2] + list(getattr(b, 'ramos', []))


def _dentro(blocos):
    """Todos os blocos de uma lista, com os de dentro de laços, decisões e tarefas."""
    for b in blocos:
        yield b
        for ramo in _ramos(b):
            yield from _dentro(ramo)


def _lacos_sem_espera(programa, linhas):
    avisos = []
    for b in _dentro(programa):
        if (b.t, b.mode) != _PARA_SEMPRE:
            continue
        corpo = list(_dentro(b.b1))
        tipos = {(x.t, x.mode) for x in corpo}
        if any(t == '2002' or t == '1006' or (t, m) in _ESPERAM or (t, m) in _LEEM for t, m in tipos):
            continue
        linha = getattr(b, 'linha', None)
        escrito = linhas[linha - 1].strip() if linha and 0 < linha <= len(linhas) else ''
        laco = 'o "while True:"' if escrito.startswith('while') else 'o "para_sempre()"'
        if not corpo:
            avisos.append(_aviso(linha, f'{laco} está vazio: o programa fica parado aqui para sempre, sem fazer nada.',
                                 'se é para o robô esperar um tempo, use esperar(segundos); se não, apague o laço.'))
        else:
            avisos.append(_aviso(linha, f'{laco} repete sem nenhuma espera e sem ler nenhum sensor: ele dá milhares de '
                                        'voltas por segundo, e o que está dentro (tela, som, contas) muda rápido demais '
                                        'para ver.',
                                 'ponha um esperar(0.1) dentro do laço (por exemplo, como última linha dele).'))
    return avisos


# ---------------------------------------------------------------- motor ligado no fim

def _portas(b):
    return [p for p in str(b.port).strip().upper().split('+') if p in ('A', 'B', 'C', 'D')]


def _mesclar(a, b):
    """União de dois estados {porta: {linhas que a ligaram}} (None = aquele caminho nunca termina)."""
    if a is None:
        return b
    if b is None:
        return a
    junto = {p: set(v) for p, v in a.items()}
    for p, v in b.items():
        junto.setdefault(p, set()).update(v)
    return junto


def _seguir(blocos, ligados):
    """Os motores que podem estar ligados depois desta sequência de blocos: {porta: {linhas}}, ou None se o
    programa nunca passa daqui (um para_sempre no caminho)."""
    for b in blocos:
        if ligados is None:
            return None
        chave = (b.t, b.mode)
        if chave in _LIGA:
            ligados = dict(ligados)
            for p in _portas(b):
                ligados[p] = {getattr(b, 'linha', None)}
        elif chave in _DESLIGA:
            ligados = {p: v for p, v in ligados.items() if p not in _portas(b)}
        elif chave == _PARA_SEMPRE:
            return None
        elif b.t == '2004':                                 # decisão: um ramo ou o outro
            ligados = _mesclar(_seguir(b.b1, ligados), _seguir(b.b2, ligados))
        elif b.t == '2003':                                 # laço: o corpo roda uma ou mais vezes
            volta = _seguir(b.b1, ligados)
            for _ in range(4):
                if volta is None:
                    break
                mais = _mesclar(volta, _seguir(b.b1, volta))
                if mais == volta:
                    break
                volta = mais
            ligados = volta
        elif getattr(b, 'ramos', None):                     # ao mesmo tempo: espera todas as tarefas acabarem
            fins = [_seguir(r, ligados) for r in b.ramos]
            if any(f is None for f in fins):
                return None
            for f in fins:
                ligados = _mesclar(ligados, f)
    return ligados


def _motores_ligados_no_fim(programa):
    fim = _seguir(programa, {})
    if not fim:
        return []
    por_linha = {}
    for porta, linhas in fim.items():
        for n in linhas:
            por_linha.setdefault(n, set()).add(porta)
    avisos = []
    for linha, portas in por_linha.items():
        if len(portas) > 1:
            texto = f'os motores {" e ".join(sorted(portas))} ficam ligados quando o programa termina: nada desliga eles depois.'
            arrumar = 'ponha parar() no fim do programa (ou depois do laço que usa os motores).'
        else:
            p = next(iter(portas))
            texto = f'o motor {p} fica ligado quando o programa termina: nada desliga ele depois.'
            arrumar = f"ponha desligar_motor('{p}') no fim do programa (ou parar(), se for um motor das rodas)."
        avisos.append(_aviso(linha, texto, arrumar))
    return avisos
