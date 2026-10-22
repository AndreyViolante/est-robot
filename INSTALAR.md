# Instalação (uma vez por computador)

Leva uns 10 minutos por computador. Funciona no **Windows**.

## 1. Python

1. Baixe em [python.org/downloads](https://www.python.org/downloads/) (versão 3.10 ou mais nova).
2. Na primeira tela da instalação, **marque "Add python.exe to PATH"**. Sem isso o resto não funciona.
3. Clique em *Install Now*.

## 2. VS Code

1. Baixe em [code.visualstudio.com](https://code.visualstudio.com/) e instale.
2. Abra o VS Code, vá em *Extensions* (ícone de quadradinhos na barra da esquerda), procure
   **Python** (da Microsoft) e instale.

## 3. Este projeto

1. Na página do projeto no GitHub, clique em **Code → Download ZIP**.
2. Extraia o ZIP numa pasta fácil de achar, por exemplo `Documentos\robotica`.
3. Dentro da pasta extraída, dê **dois cliques em `instalar.bat`**. Ele confere o Python e instala o
   que falta. No final, pode responder **S** para testar o robô (com o cabo ligado).

## 4. Abrir no VS Code

1. No VS Code: **Arquivo → Abrir Pasta…** e escolha a pasta do projeto.
2. Se aparecer *"Do you trust the authors?"*, clique em **Yes, I trust**.
3. Se o VS Code sugerir instalar a extensão Python, aceite.

## 5. Testar

1. Ligue o robô e conecte o cabo USB.
2. No VS Code: **Terminal → Executar Tarefa… → Testar conexão com o robô**. O robô deve apitar,
   acender a luz e escrever "Funcionou!".
3. Abra o `meu_programa.py` e aperte **`Ctrl+Shift+B`**. O robô acende a luz, apita e escreve
   "Funcionou!": pronto para programar.

## Problemas comuns

| O que aparece | O que fazer |
|---|---|
| `python não é reconhecido` | Reinstale o Python marcando **"Add python.exe to PATH"**, feche e abra o VS Code |
| `Robo nao encontrado no USB` | Confira se o robô está ligado e o cabo bem encaixado; teste outra porta USB; feche a IDE EST se estiver aberta |
| `Falta o pywinusb` | Rode o `instalar.bat` de novo (precisa de internet) |
| O `Ctrl+Shift+B` pergunta qual tarefa usar | Escolha **Enviar para o Robô** |
| `ERRO na linha …` | É um erro no programa: a mensagem explica o que corrigir |
| O robô anda de ré quando deveria ir para frente | No `calibracao.py`, mude para `INVERTIDO = True` |
| O robô vira mais ou menos que 90° | No `calibracao.py`, ajuste `ENTRE_RODAS_CM`: diminua se virar a mais, aumente se virar a menos. Se a `PAUSA` estiver em 0, volte para 0.5 |
| O envio avisa que a IDE EST está aberta | Feche a IDE: ela conversa com o robô ao mesmo tempo e pode impedir o programa de começar |

Em computadores da escola, a instalação do Python e do `pywinusb` pode precisar de permissão do
responsável pela rede.
