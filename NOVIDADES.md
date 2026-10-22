# Novidades

Cada versão publicada fica em [Releases](https://github.com/AndreyViolante/est-robot/releases).
O "Atualizar o projeto" mostra daqui o que mudou desde a versão que você tem.

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
