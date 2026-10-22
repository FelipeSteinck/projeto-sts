# CONTEXTO PARA CONTINUIDADE NO CODEX — Projeto STS
Atualizado em 22/10/2026. Leia este documento antes de alterar o projeto.

## Como usar
Abra a pasta Projeto_STS_Transicao_Codex_2026-10-22 no Codex, mantendo as sete subpastas e este Markdown. Forneça o comando ao fim deste documento. Este é um pacote de contexto e fontes, não treinamento de modelo. Um novo chat não recebe automaticamente a conversa anterior.

## Objetivo e equipe
Projeto acadêmico de Processamento Digital de Imagens e Visão Computacional, UFSC/CTC, Engenharia Elétrica, EEL7825, professor Joceli Mayer.
Autores: Luiz Felipe Steinck (19100418) e Luis Felipe Candido Sola (22250296).
Reconhecer SENTADO, TRANSIÇÃO e EM PÉ e contar ciclos completos sentado → em pé → sentado, com webcam, OpenCV e MediaPipe, registrando resultados em tempo real. Motivação: acompanhamento de exercício de sentar/levantar em contexto de fisioterapia de idosos. Tratar como protótipo acadêmico; validação clínica não foi demonstrada.

## Origem e confiabilidade deste contexto
Este resumo combina mensagens anteriores fornecidas nesta conversa, recuperação de decisões da conversa PROJETO 26.2 e inventário atual de arquivos. Não é uma transcrição integral.
A análise anterior informou leitura dos sete PDFs e das 995 linhas do script avulso. Esta sessão confirmou a presença dos 16 arquivos, mas a transferência dos originais ao computador falhou. Não foi possível comparar o script avulso com o código dos ZIPs. Nenhum código foi executado ou modificado nesta etapa.
A presença de um arquivo no inventário não significa que todo seu conteúdo tenha sido inspecionado.

## Organização e inventário
Os 16 arquivos originais estão reunidos nas sete subpastas da pasta principal. Preserve nomes e versões; não substitua fontes históricas por documentos novos.

| Caminho relativo | Tamanho em bytes | Papel |
| --- | ---: | --- |
| 03_Proposta_e_Instrucoes/Proposta_Projeto_STS_Steinck_Sola_CORRIGIDA.pdf | 316171 | Proposta e instruções; priorizar versão CORRIGIDA |
| 03_Proposta_e_Instrucoes/Proposta_Projeto_STS_Overleaf_CORRIGIDA.zip | 71172 | Proposta e instruções; priorizar versão CORRIGIDA |
| 07_Historico/Proposta_Projeto_STS_Overleaf(1).zip | 70449 | Histórico; preservar para comparação |
| 07_Historico/Proposta_Projeto_STS_Overleaf.zip | 70449 | Histórico; preservar para comparação |
| 07_Historico/Proposta_Projeto_STS_Steinck_Sola.pdf | 310966 | Histórico; preservar para comparação |
| 05_Identidade_Visual/CTC_logo.png | 57559 | Identidade visual; preservar originais |
| 05_Identidade_Visual/logo.jpg | 3906 | Identidade visual; preservar originais |
| 03_Proposta_e_Instrucoes/ProopostaProjetos (1).pdf | 27171 | Proposta e instruções; priorizar versão CORRIGIDA |
| 01_Codigo/monitor_sentar_levantar_ptbr.zip | 69367 | Implementação própria; comparar versões |
| 06_Referencia_Externa/Pose-Estimation-for-Fitness-Exercise-Analysis-main.zip | 232507076 | Referência externa; não confundir com implementação própria |
| 03_Proposta_e_Instrucoes/ProopostaProjetos.pdf | 27171 | Proposta e instruções; priorizar versão CORRIGIDA |
| 04_Relatorio_Anterior/relatorio_monitoramento_sentar_levantar.pdf | 890555 | Relatório anterior e fontes LaTeX |
| 04_Relatorio_Anterior/relatorio_overleaf_monitor_sts.zip | 468348 | Relatório anterior e fontes LaTeX |
| 01_Codigo/monitorar_sentar_levantar.py | 32292 | Implementação própria; comparar versões |
| 02_Planos_de_Ensino/EEL7815.pdf | 99461 | Plano de ensino; fonte dos requisitos |
| 02_Planos_de_Ensino/EEL7825.pdf | 99452 | Plano de ensino; fonte dos requisitos |

## Arquitetura e estado registrado
1. Captura de imagens pelo OpenCV e conversão BGR → RGB.
2. MediaPipe Pose Landmarker, com 33 marcos corporais.
3. Extração de atributos: ângulos articulares, altura normalizada do quadril e variações temporais, conforme proposta.
4. Calibração individual e classificação por regras geométricas.
5. Suavização temporal e máquina de estados para estabilizar classificação e contar ciclos.
6. Interface em português e exportação CSV.

A análise anterior atribuiu ao script avulso: cálculo angular, calibração, filtragem, contagem, interface e CSV. Confirmar a implementação real antes de descrevê-la em relatório ou alterá-la.
Comparação com modelos supervisionados (Regressão Logística / Floresta Aleatória) é trabalho pendente no contexto recuperado; não afirmar que já houve treinamento ou avaliação.

## Decisões técnicas que devem ser preservadas
### Ângulo orientado
Para vetores u e v no plano, utilizar atan2(ux*vy - uy*vx, ux*vx + uy*vy), no intervalo (-π, π], com convenção explícita de orientação e unidade.
A proposta corrigida prevê preservar sinal/orientação, usar magnitude nos atributos quando apropriado e desenrolar a série quando necessário.
Divergência relatada: o script avulso usa atan2 seguido de abs(), descartando o sinal. Usar magnitude como atributo pode ser legítimo; o problema é perder a série orientada quando ela é necessária. Não remover abs() indiscriminadamente: manter uma saída orientada separada e verificar as regras existentes.
Marcos de imagem têm eixo vertical geralmente crescente para baixo. Definir sinal, lado do corpo e efeito do espelhamento. Ângulos são projeções 2D e não medidas articulares 3D validadas.

### Filtro temporal
EMA é causal e introduz atraso. Para y[k]=α*x[k]+(1-α)*y[k-1], α menor aumenta a suavização e tende a aumentar atraso. Confirmar a convenção de α usada no código.
Selecionar o parâmetro com dados rotulados e avaliar F1 macro, erro de contagem, falsas transições e latência. Não apresentar filtragem como melhoria sem custo.
Verificar a influência de FPS variável e timestamps antes de comparar tempos entre execuções.

### Câmera
Câmera fixa, pessoa de perfil, corpo inteiro visível, aproximadamente centralizado e marcas no piso para repetibilidade. O eixo óptico deve ser aproximadamente perpendicular ao plano sagital; o plano da imagem fica aproximadamente paralelo a esse plano corporal. Evitar a frase ambígua “câmera paralela ao plano sagital” sem indicar qual eixo/plano está sendo descrito.
Documentar distância, altura, resolução, luz, oclusões, posição da cadeira e lateralidade.

### Contagem e avaliação
Contar apenas o ciclo completo sentado → em pé → sentado, evitando dupla contagem por oscilações ou ciclos incompletos.
Para avaliação supervisionada, separar conjuntos por sessão e, quando possível, por participante; não misturar frames vizinhos da mesma gravação entre treino e teste. Isto é recomendação de validação, não procedimento já executado.

## Resultados existentes e limites
O relatório anterior registra Python 3.11.9, importações de MediaPipe/OpenCV/NumPy, carregamento de pose_landmarker_lite.task, webcam em 640×480 e autotestes de ângulos, fases e contagem.
15,2 FPS é uma observação pontual registrada, não média de benchmark nem garantia de desempenho.
Há demonstração preliminar de detecção. Não foi apresentada, na análise disponível, avaliação quantitativa dos ciclos completos nem comparação supervisionada.
Não inventar métricas, participantes, acurácia, F1, erros ou resultados clínicos.
Não presumir que o modelo .task, vídeos, CSVs, dependências ou ambiente Python estejam incluídos: verificar o interior dos ZIPs.

## Cronologia recuperada
- Agosto/2026: protótipo, script avulso, relatório e pacotes de implementação/referência.
- Setembro/2026: proposta e revisão de orientação angular, atraso da EMA e geometria da câmera; versão CORRIGIDA deve orientar a leitura metodológica.
- 22/10/2026: organização para continuidade no Codex; inventário de 16 arquivos confirmado.
O histórico recuperado menciona vídeo YouTube de 5 minutos até 30/11/2026, apresentação em 03/12/2026 e relatório PDF/Notebook até 04/12/2026. Esses prazos vieram de recuperação indireta de comunicações; conferir o aviso original/Moodle antes de depender deles.

## Ordem de leitura para o próximo agente
1. Este contexto e instruções do professor em 03_Proposta_e_Instrucoes.
2. Proposta_Projeto_STS_Steinck_Sola_CORRIGIDA.pdf e fontes do ZIP corrigido.
3. Planos EEL7825 e EEL7815; verificar a aplicação de cada plano, sem trocar a identificação da disciplina.
4. Script avulso e monitor_sentar_levantar_ptbr.zip; extrair em diretórios separados e comparar hashes/diferenças antes de escolher uma versão.
5. Relatório anterior e fontes LaTeX, distinguindo demonstração de avaliação.
6. Histórico, referência externa e identidade visual.

## Próximas ações recomendadas
- Recuperar os bytes de todos os originais e verificar a integridade dos seis ZIPs.
- Listar o conteúdo dos ZIPs e identificar código, requirements, modelo, imagens, dados e instruções.
- Comparar versões sem decidir “mais recente” apenas pelo nome ou data de upload.
- Reconstruir ambiente a partir das dependências efetivamente encontradas.
- Executar autotestes existentes e registrar comando, versão e resultado. Webcam exige verificação no computador com acesso à câmera.
- Conferir divergências entre proposta e implementação: série orientada, EMA/latência e captura lateral.
- Definir protocolo de vídeos rotulados e métricas antes de alegar desempenho.
- Atualizar este contexto a cada marco, indicando evidências e pendências.

## Instruções para o agente Codex
Responda em português, com precisão técnica. Continue o trabalho existente antes de propor reescrita.
Preserve os originais e trabalhe em cópia separada. Não execute scripts desconhecidos antes de ler seu conteúdo.
Não trate código de referência externa como autoria dos alunos; verificar licença e registrar atribuição.
Distinguir sempre: requisito, implementação confirmada, resultado demonstrado, decisão histórica e recomendação nova.
Quando faltar evidência, explicitar a limitação e procurar a fonte; não preencher lacunas com resultados plausíveis.
Não iniciar correções apenas por ler este pacote: a primeira tarefa é entender e confirmar o contexto; aguardar o próximo comando de implementação.

## Comando inicial para colar no novo chat
> Leia integralmente CONTEXTO_CODEX.md e os arquivos das sete subpastas deste projeto. Inspecione os ZIPs em diretórios separados e compare o script avulso com a versão empacotada. Consulte a proposta corrigida, as instruções do professor e o relatório anterior. Não altere os originais. Confirme o que foi realmente lido, qual versão de código existe, as divergências entre proposta e implementação e as evidências de resultados. Não invente métricas nem afirme acesso à conversa completa PROJETO 26.2. Depois aguarde meus próximos comandos.

