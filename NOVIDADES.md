# Novidades

Cada versão publicada fica em [Releases](https://github.com/AndreyViolante/est-robot/releases).
O "Atualizar o projeto" mostra daqui o que mudou desde a versão que você tem.

## 0.1.4 (27/10/2026)

- Registro no Zenodo: cada versão publicada ganha um DOI permanente, para citar o EST-ROBOT em
  trabalhos acadêmicos, artigos e relatos de aula.

## 0.1.3 (27/10/2026)

- Atalhos no VS Code: digite `para_sempre`, `seguidor_2_sensores`, `desviar`, `mostrar_sensor`... e
  aperte Tab. O modelo aparece pronto para trocar os números (a lista está na cola de comandos).
- Enquanto você escreve, o VS Code mostra as opções de cada comando: as portas, as comparações
  (`'<'`, `'>'`...) e as cores da luz.
- Mais erros explicados em português: `=` no lugar de `==`, `else` sem `if`, texto + número, vírgula no
  número, `from robot import *`... Porta de sensor fora de 1 a 4 ou de motor fora de A a D agora avisa.
- Cola de comandos em PDF, frente e verso, para imprimir: `docs/cola-do-aluno.pdf`.
- Tarefa "Teste geral no robô": confere um por um os comandos ainda não vistos funcionando no robô e
  grava o resultado em `resultado_teste_geral.txt`.
- Tarefa "Diagnóstico (para pedir ajuda)": copia um resumo do computador e do robô para colar no
  WhatsApp, sem dados pessoais.
- No pacote com o Python dentro, o VS Code já usa esse Python (sem pedir *Select Interpreter*).
- A página de cada versão mostra o código SHA-256 do pacote, para conferir o download.

## 0.1.2 (23/10/2026)

- O pacote traz só os dois programas de exemplo: o `meu_programa.py` (luz, som e "Funcionou!") e o
  seguidor de linha básico com dois sensores.
- O `formato.md` documenta a consulta de bateria e os comandos de listar e apagar arquivos do robô.

## 0.1.1 (22/10/2026)

- "Atualizar o projeto" pega a última versão publicada, que já passou pelos testes, e mostra as novidades.
- O `calibracao.py` só ganha os campos novos de cada versão; as suas medidas ficam como estão.
- Tarefa "Voltar para a versão anterior", para desfazer uma atualização.
- O envio avisa quando sai uma versão nova (no máximo uma vez por dia).
- Correção: a tarefa "Testar conexão com o robô" voltou a funcionar.

## 0.1.0 (22/10/2026)

- Primeira versão beta: programar a controladora EST em Python pelo VS Code, sem a IDE do fabricante.
- `if`, `elif`, `else`, `while`, `and`, `or`, `not` e `for` do Python funcionam com os sensores.
- `calibracao.py` com as medidas do robô; `limite(porta)` dá o meio entre o preto e o branco.
- Notas pelo nome (`tocar('la')`, `melodia(...)`) e `painel(...)` na tela do robô.
- Antes de enviar: aviso de IDE EST aberta e de porta sem nada ligado.
- Simulador com pistas de prova, passo a passo e trilha de 8 desafios.
- Programar no navegador, em Python ou com blocos, sem instalar nada.
- Pacote para Windows com o Python dentro e tarefa "Atualizar o projeto".
- Ainda não testados no robô: `ao_mesmo_tempo`, botões da controladora, `ajustando`, envio pelo
  navegador e as tarefas "Programas no robô" e "Bateria do robô".
