"""
Ponto de entrada principal.
Uso: python run.py meu_programa.py
"""
import sys, os, importlib.util

def main():
    if len(sys.argv) < 2:
        print("Uso: python run.py <programa.py>")
        print("Exemplo: python run.py meu_programa.py")
        sys.exit(1)

    prog_file = sys.argv[1]
    if not os.path.exists(prog_file):
        print(f"ERRO: arquivo '{prog_file}' nao encontrado.")
        sys.exit(1)

    # Importa e executa o programa do usuario
    # Isso preenche est._program_instructions
    import est
    est._reset()

    # Adiciona o diretório do programa ao path
    prog_dir = os.path.dirname(os.path.abspath(prog_file))
    if prog_dir not in sys.path:
        sys.path.insert(0, prog_dir)

    # Injeta as funções do est no namespace global do programa
    import types
    spec = importlib.util.spec_from_file_location("user_program", prog_file)
    module = importlib.util.module_from_spec(spec)

    # Copia funções publicas do est para o modulo
    for name in dir(est):
        if not name.startswith('_'):
            setattr(module, name, getattr(est, name))

    print(f"[*] Carregando {prog_file}...")
    spec.loader.exec_module(module)

    instrucoes = est._program_instructions
    print(f"[*] {len(instrucoes)} instrucao(oes) encontrada(s):")
    for i, instr in enumerate(instrucoes):
        tipo = instr['tipo']
        params = {k: v for k, v in instr.items() if k != 'tipo'}
        print(f"    {i+1}. {tipo}({', '.join(f'{k}={v}' for k, v in params.items())})")

    print()

    # Compila
    from est_compiler import compile_program
    try:
        print("[*] Compilando...")
        program_data = compile_program(instrucoes)
        print(f"[OK] Compilado: {len(program_data)} bytes")
    except NotImplementedError as e:
        print(f"[ERRO] {e}")
        sys.exit(1)

    print()

    # Upload
    from est_protocol import upload
    upload(program_data)


if __name__ == '__main__':
    main()
