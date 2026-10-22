# Instalação (uma vez por computador)

Funciona no **Windows**. Há dois jeitos:

- **A. Pacote com o Python dentro** (o melhor para computador de escola): não instala o Python e não
  precisa de administrador. Leva uns 5 minutos.
- **B. Com o Python instalado no computador**: para quem já tem o Python ou pode instalá-lo. Leva uns
  10 minutos.

## 1. VS Code (nos dois jeitos)

1. Baixe em [code.visualstudio.com](https://code.visualstudio.com/) e instale. A versão normal
   (*User Installer*) instala só para o seu usuário e não pede administrador. Se nem isso for
   permitido, baixe a versão **.zip** do Windows, descompacte e abra o `Code.exe`.
2. Abra o VS Code, vá em *Extensions* (ícone de quadradinhos na barra da esquerda), procure
   **Python** (da Microsoft) e instale. Ela completa os comandos e sublinha erros enquanto você escreve.

## 2A. Este projeto, com o Python dentro (jeito A)

1. Baixe o **est-robot-windows.zip** na página
   [Releases do projeto](https://github.com/AndreyViolante/est-robot/releases/latest) no GitHub.
2. Clique com o botão direito no zip → **Extrair Tudo…** e escolha uma pasta fácil de achar, por
   exemplo `Documentos\robotica`. Extraia tudo antes de usar: não abra os arquivos de dentro do zip.
3. Pronto: o Python está na pasta `python` do projeto, já com o que precisa para falar com o robô.
   Não precisa rodar o `instalar.bat` (se rodar, ele só confere).

## 2B. Este projeto, com o Python do computador (jeito B)

1. Instale o Python: baixe em [python.org/downloads](https://www.python.org/downloads/) (versão 3.10 ou
   mais nova), **marque "Add python.exe to PATH"** na primeira tela e clique em *Install Now*.
2. Na página do projeto no GitHub, clique em **Code → Download ZIP** e extraia o ZIP numa pasta fácil
   de achar, por exemplo `Documentos\robotica`.
3. Dentro da pasta extraída, dê **dois cliques em `instalar.bat`**. Ele confere o Python e instala o
   que falta. No final, pode responder **S** para testar o robô (com o cabo ligado).

## 3. Abrir no VS Code

1. No VS Code: **Arquivo → Abrir Pasta…** e escolha a pasta do projeto (a que tem o `meu_programa.py`).
2. Se aparecer *"Do you trust the authors?"*, clique em **Yes, I trust**.
3. Se o VS Code sugerir instalar a extensão Python, aceite.

## 4. Testar

1. Ligue o robô e conecte o cabo USB.
2. No VS Code: **Terminal → Executar Tarefa… → Testar conexão com o robô**. O robô deve apitar,
   acender a luz e escrever "Funcionou!".
3. Abra o `meu_programa.py` e aperte **`Ctrl+Shift+B`**. O robô acende a luz, apita e escreve
   "Funcionou!": pronto para programar.

As tarefas usam sozinhas o Python da pasta `python` quando ele existe (jeito A) e o Python do
computador quando não existe (jeito B).

## Atualizar o projeto

Quando sair uma versão nova: **Terminal → Executar Tarefa… → Atualizar o projeto** (precisa de
internet). A tarefa baixa a versão mais nova do GitHub, troca os arquivos do projeto e mostra o que
mudou:

- **não mexe** no `calibracao.py`, no `meu_programa.py`, no `minha_pid.py` nem nos programas que você
  e os alunos criaram (qualquer `.py` que não seja do projeto);
- não apaga nada; a versão antiga de cada arquivo trocado fica guardada num zip na pasta
  `copias_de_seguranca`.

Computador sem internet: em outro computador, baixe o ZIP do projeto no GitHub (**Code → Download
ZIP**), traga num pendrive e, no terminal do VS Code (**Terminal → Novo Terminal**), rode:

    ferramentas\rodar.cmd ferramentas\atualizar.py D:\est-robot-master.zip

(troque `D:\est-robot-master.zip` pelo lugar onde o arquivo está).

A tarefa não troca o Python da pasta `python`. Para um Python mais novo, baixe o pacote de novo e
copie para a pasta nova o `calibracao.py` e os seus programas.

## Problemas comuns

| O que aparece | O que fazer |
|---|---|
| `python não é reconhecido` ou "O Python não foi encontrado" | Use o pacote com o Python dentro (jeito A). Ou reinstale o Python marcando **"Add python.exe to PATH"**, feche e abra o VS Code |
| `Robo nao encontrado no USB` | Confira se o robô está ligado e o cabo bem encaixado; teste outra porta USB; feche a IDE EST se estiver aberta |
| `Falta o pywinusb` | Jeito A: baixe e extraia o pacote de novo. Jeito B: rode o `instalar.bat` de novo (precisa de internet) |
| O Windows não deixa abrir o `python.exe` do pacote ("bloqueado pelo administrador") | Alguns computadores de escola só rodam programas instalados pelo administrador: peça ao responsável para liberar a pasta do projeto |
| O VS Code pede para escolher um Python (*Select Interpreter*) | No jeito A, escolha *Enter interpreter path…* e indique o `python\python.exe` da pasta do projeto. As tarefas funcionam mesmo sem isso |
| O `Ctrl+Shift+B` pergunta qual tarefa usar | Escolha **Enviar para o Robô** |
| `ERRO na linha …` | É um erro no programa: a mensagem explica o que corrigir |
| O robô anda de ré quando deveria ir para frente | No `calibracao.py`, mude para `INVERTIDO = True` |
| O robô vira mais ou menos que 90° | No `calibracao.py`, ajuste `ENTRE_RODAS_CM`: diminua se virar a mais, aumente se virar a menos. Se a `PAUSA` estiver em 0, volte para 0.5 |
| O envio avisa que a IDE EST está aberta | Feche a IDE: ela conversa com o robô ao mesmo tempo e pode impedir o programa de começar |
| "Atualizar o projeto" diz que está sem internet | Confira a conexão; se a rede da escola bloquear o GitHub, use o ZIP trazido de outro computador (veja acima) |

Em computadores da escola, instalar o Python e o `pywinusb` (jeito B) pode precisar de permissão do
responsável pela rede. O pacote com o Python dentro (jeito A) evita isso.
