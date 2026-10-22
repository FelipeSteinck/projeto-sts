# Proposta de Projeto Nível II - EEL7825

Minuta atualizada em 22/10/2026 após orientação relatada pelo usuário. Deve ser revisada pela equipe e discutida com o professor antes da submissão. Não é comprovante de aprovação.

## 1. Título e equipe

**Reconhecimento e contagem de ciclos de sentar e levantar: comparação entre regras geométricas e classificação supervisionada a partir de pose corporal.**

Luiz Felipe Steinck e Luis Felipe Candido Sola, Universidade Federal de Santa Catarina, Centro Tecnológico, Departamento de Engenharia Elétrica e Eletrônica. Professor: Joceli Mayer. Disciplina: EEL7825, Projeto Nível 2 em Controle e Processamento de Sinais.

Divisão proposta, sujeita à revisão da equipe: Steinck concentra integração OpenCV/MediaPipe, aplicação web, contagem e exportação; Sola concentra protocolo de aquisição, rotulagem e análise dos experimentos. Ambos revisam treinamento, resultados, relatório e apresentação. A infraestrutura e parte do protótipo são trabalho anterior explicitamente identificado, não uma nova contribuição duplicada entre disciplinas.

## 2. Introdução

Reconhecer movimentos com uma câmera comum envolve aquisição, extração de características, classificação e interpretação temporal. O STS permite estudar essas etapas com marcos de tronco e membros inferiores. A motivação é acompanhamento de exercícios, mas o escopo é um protótipo acadêmico sem diagnóstico, prescrição ou validação clínica.

O trabalho parte do monitor geométrico próprio já existente. A contribuição do Nível II é integrar e comparar classificadores treinados com dados próprios, preservando um método interpretável de referência e medindo erros e atrasos. O Nível I terá outro problema e outra proposta, definidos posteriormente.

## 3. Objetivos, metas e resultados esperados

Desenvolver e avaliar reconhecimento das classes SENTADO, TRANSIÇÃO e EM PÉ e contagem apenas do ciclo completo sentado → em pé → sentado. Comparar regras geométricas, Regressão Logística e Floresta Aleatória nas mesmas sessões reservadas.

Extrair magnitudes articulares, inclinação do tronco, altura relativa do quadril e variações temporais. Preservar canais angulares orientados com convenção documentada. Avaliar F1 macro, suporte/matriz de confusão, cobertura, contagem, falsas contagens, perdas de rastreamento e latência. As metas históricas de F1 ≥ 0,85, ≥ 15 FPS e erro de até uma repetição por dez movimentos permanecem como metas propostas para discussão, sem alegação de atingimento.

Entregar proposta específica, código reproduzível, dados/rótulos próprios autorizados, modelos, resultados, figuras, relatório e demonstração. Um ensaio sintético verifica software, mas não substitui os resultados humanos.

## 4. Métodos

Aquisição lateral fixa com corpo inteiro e cadeira visíveis, pessoa centralizada, plano da imagem aproximadamente paralelo ao sagital e eixo óptico aproximadamente perpendicular. Documentar distância, altura, iluminação, resolução, lateralidade e espelho.

MediaPipe Pose Landmarker Lite estima os marcos; OpenCV lê/decodifica e converte cores. Usar cadeia de ombro, quadril, joelho e tornozelo do lado de maior qualidade, ângulos em pixels com atan2 e magnitudes para postura. O método de regras usa calibração individual independente do trecho avaliado, EMA, estabilidade e máquina de estados. Ângulos são projeções 2D.

O treinamento usa atributos causais compartilhados entre offline e web. Regressão Logística com escalonamento ajustado dentro de cada fold e Floresta Aleatória são comparadas por validação agrupada. Ajustar modelo, α e estabilidade apenas no treino/validação; reservar o teste antes das escolhas. Registrar versões, hashes, partições, parâmetros e convenções temporais.

A coleta inicial proposta mantém 12 sessões, seis por integrante, com 8 a 12 repetições por sessão, a confirmar após um piloto. Incluir tentativas incompletas e perdas de pose documentadas. Rotular intervalos por observação independente; revisar uma parte por outro integrante. Separar a calibração das amostras de avaliação.

Dividir por sessão, sem misturar frames vizinhos entre treino e teste. Com dois participantes, as conclusões se restringem a sessões controladas dessas pessoas. Generalização para novos participantes exigirá outro desenho e mais participantes. A referência de ciclos virá dos intervalos anotados, independentemente da saída do programa.

Os três métodos usarão as mesmas sessões de teste. Apresentar resultados por quadro e por sessão, cobertura e eventos pareados um a um com tolerância fixada previamente. Medir custo de processamento e resposta da aplicação separadamente da latência do evento. Não interpretar uma observação pontual de FPS como benchmark sustentado.

## 5. Materiais, dados e ferramentas

Python 3.11/Linux no Codespaces, OpenCV, MediaPipe, NumPy, Scikit-learn, Matplotlib e interface FastAPI/HTML/JavaScript. Webcam e computador da equipe. Ferramenta local de anotação no navegador e extração offline para vídeos com taxa constante. O acesso à aplicação permanece privado.

Situação: monitor geométrico e ambiente web disponíveis; fluxo supervisionado em implementação/verificação; vídeos próprios ainda não gravados; rótulos, modelos reais e avaliação humana pendentes. Modelos sintéticos serão claramente marcados como demonstração. O material externo é apenas referência atribuída, sem transferência de métricas ou autoria.

As gravações exigem autorização dos envolvidos. Usar códigos de participante e guardar vídeos separadamente do repositório. Não coletar condições médicas ou usar a aplicação como instrumento clínico.

## 6. Cronograma por marcos

1. Consolidar esta proposta e conferir com o professor os critérios e prazos de entrega.
2. Concluir implementação e verificações do fluxo de treino, inferência e avaliação.
3. Executar piloto e revisar aquisição, guia de anotação e grade de parâmetros.
4. Gravar, anotar e congelar partições e protocolo antes dos ajustes.
5. Selecionar configurações em treino/validação e avaliar uma vez no teste reservado.
6. Analisar falhas e limitações, redigir resultados e preparar demonstração/apresentação.

As datas serão inseridas após conferir o cronograma vigente informado pelo professor/Moodle. Não reutilizar automaticamente os prazos históricos sem a fonte original. O Nível I será iniciado somente após o fechamento deste projeto.
