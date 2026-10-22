# Recuperação e análise do projeto STS — 22/10/2026

Esta análise é documental e estática. Nenhum código do projeto foi alterado ou executado; não foram instaladas suas dependências, aberto acesso à webcam ou repetidos os autotestes. Os scripts auxiliares desta auditoria apenas copiaram, verificaram, extraíram e leram os arquivos.

## Recuperação e preservação

A pasta foi localizada na Biblioteca do ChatGPT, em `https://chatgpt.com/library/d/6ada22159fec819180dad63ff5099e9c?tab=all`. O conector Google Drive não retornou a pasta nem os nomes específicos procurados. Os downloads foram feitos pelos controles de download da Biblioteca, não por reconstrução do texto das conversas.

Os 16 originais foram copiados para `../Projeto_STS_Transicao_Codex_2026-10-22`, conservando as sete subpastas e os nomes do inventário. Total: 235.121.565 bytes, sem contar o Markdown. Todos os tamanhos coincidem com CONTEXTO_CODEX.md. O manifesto `manifesto_recuperacao.json` registra origem local do download, tamanho, SHA-256, conteúdo dos ZIPs e diretório de extração. Nova verificação ao fim da leitura confirmou os 16 hashes.

CONTEXTO_CODEX.md foi lido integralmente antes dos documentos/códigos. A cópia baixada da Biblioteca é idêntica à que já existia localmente: SHA-256 `098e4eea00388b5fd506350f4d32074b9881b1fcba817a992f8bf1f5fe4d7537`.

**Originais inacessíveis: nenhum dos 16.** Foram recuperados todos os bytes. Isso não significa que os vídeos foram assistidos integralmente ou que os modelos binários foram executados; o escopo preciso aparece abaixo.

| Subpasta | Arquivo | Leitura/análise nesta sessão |
|---|---|---|
| 01_Codigo | monitorar_sentar_levantar.py | 995 linhas lidas integralmente; geometria, filtros, calibração, estados, CSV, captura, interface e autoteste inspecionados |
| 01_Codigo | monitor_sentar_levantar_ptbr.zip | CRC verificado; extração separada; todos os códigos, guias, scripts PowerShell e requirements lidos; imagem da interface inspecionada |
| 02_Planos_de_Ensino | EEL7815.pdf | Texto integral das 3 páginas lido; páginas renderizadas |
| 02_Planos_de_Ensino | EEL7825.pdf | Texto integral das 3 páginas lido; páginas renderizadas |
| 03_Proposta_e_Instrucoes | ProopostaProjetos.pdf | Página integral lida |
| 03_Proposta_e_Instrucoes | ProopostaProjetos (1).pdf | Idêntico ao anterior por SHA-256; página também renderizada |
| 03_Proposta_e_Instrucoes | Proposta_Projeto_STS_Steinck_Sola_CORRIGIDA.pdf | Texto integral das 7 páginas lido; equações e protocolo conferidos nas páginas renderizadas |
| 03_Proposta_e_Instrucoes | Proposta_Projeto_STS_Overleaf_CORRIGIDA.zip | CRC verificado; main.tex, referencias.bib e README integralmente lidos; imagens preservadas |
| 04_Relatorio_Anterior | relatorio_monitoramento_sentar_levantar.pdf | Texto integral das 19 páginas lido; figuras, placeholders e captura preliminar inspecionados |
| 04_Relatorio_Anterior | relatorio_overleaf_monitor_sts.zip | CRC verificado; main.tex, referências e README integralmente lidos; script comparado por hash; imagens inspecionadas |
| 05_Identidade_Visual | CTC_logo.png | Inspeção visual; PNG RGBA 300×248 |
| 05_Identidade_Visual | logo.jpg | Inspeção visual; JPEG RGB 200×200, símbolo ψ |
| 06_Referencia_Externa | Pose-Estimation-for-Fitness-Exercise-Analysis-main.zip | CRC verificado; README, dois scripts Python, 48 células do notebook e PDF de 5 páginas lidos; três CSVs percorridos integralmente para conferir estrutura/classes; vídeos e modelos binários inventariados |
| 07_Historico | Proposta_Projeto_STS_Overleaf.zip | CRC verificado; main.tex, README e bibliografia lidos e comparados à corrigida |
| 07_Historico | Proposta_Projeto_STS_Overleaf(1).zip | CRC verificado; bytes idênticos ao outro ZIP histórico |
| 07_Historico | Proposta_Projeto_STS_Steinck_Sola.pdf | Texto integral das 6 páginas lido; comparado ao PDF corrigido |

Os textos extraídos estão em `textos_pdf`, `textos_pdf_extraidos` e `GuideLine_leitura_integral.txt`. As renderizações estão em `visuais`. Textos extraídos não substituem os PDFs originais para avaliação da diagramação.

## Extrações canônicas

Todos os seis ZIPs passaram pela verificação CRC de todos os membros. Diretórios independentes em `extraidos`:

| Diretório | ZIP | Entradas no ZIP |
|---|---|---:|
| 01_monitor_ptbr | monitor_sentar_levantar_ptbr.zip | 23 (16 arquivos e 7 diretórios) |
| 03_proposta_corrigida | Proposta_Projeto_STS_Overleaf_CORRIGIDA.zip | 5 arquivos |
| 04_relatorio | relatorio_overleaf_monitor_sts.zip | 6 arquivos |
| 06_ref_externa | Pose-Estimation-for-Fitness-Exercise-Analysis-main.zip | 26 (21 arquivos e 5 diretórios) |
| 07_proposta_historica_1 | Proposta_Projeto_STS_Overleaf(1).zip | 5 arquivos |
| 07_proposta_historica_2 | Proposta_Projeto_STS_Overleaf.zip | 5 arquivos |

Uma primeira extração falhou por limite de comprimento de caminho do Windows. A nova extração usou nomes mais curtos e foi concluída. Restaram diretórios de extração preliminar chamados `01_Codigo`, `03_Proposta_e_Instrucoes`, `06_Referencia_Externa` e `07_Historico` dentro de `extraidos`; são duplicatas/parciais, não são as extrações canônicas acima. A revisão automática bloqueou sua remoção; não se tentou contornar o bloqueio. Nenhum original foi afetado.

## Comparação das versões próprias

O ZIP próprio não contém outro arquivo chamado monitorar_sentar_levantar.py: contém uma versão modular. A comparação foi feita entre as responsabilidades do avulso e `main.py`, `src/nucleo.py`, `src/aplicacao.py`, `src/interface.py`. O arquivo `script_avulso_vs_pacote.diff` conserva um diff textual do avulso contra a concatenação dos módulos, útil como registro, mas a reorganização e a tradução impedem tratá-lo como simples atualização linha a linha.

| Aspecto | Script avulso | ZIP pt-BR |
|---|---|---|
| Organização | Um arquivo, 995 linhas | main.py (5), __init__.py (2), nucleo.py (491), aplicacao.py (509), interface.py (545) |
| Interface | Texto e painel sobre o quadro via OpenCV | Composição Pillow com acentos, vídeo e painel lateral, progresso e cartões; padrão 1280×720, mínimo 1050×700 |
| Teclas | 1, 2, Q/Esc | Acrescenta P pausa, R reinício, M espelho, L esqueleto |
| Espelho | Sem inversão explícita no laço | Ativado por padrão; flip antes da inferência; opção --sem-espelho |
| Geometria | abs(degrees(atan2(cross,dot))) | Mesmo cálculo de magnitude, com nomes em português |
| Calibração | 95°/170° ilustrativos; amplitude mínima 20°; limites 45%/75% | Mesma lógica; propriedade esta_calibrada |
| JSON | seated_knee, standing_hip etc. | joelho_sentado, quadril_em_pe etc.; formato incompatível com o antigo sem conversão |
| Filtros | EMA α=0,25 e 3 quadros estáveis | Mesmos parâmetros e equações |
| Contagem | Máquina de estados; incompletas e cancelamento após 15 quadros ausentes | Mesma lógica central, com reiniciar() e progresso visual |
| CSV | Cabeçalhos ingleses, vírgula entre campos, ponto decimal, UTF-8 | Cabeçalhos portugueses, ponto e vírgula, vírgula decimal, UTF-8 com BOM |
| Calibração concluída | Reinicia filtro de posturas e recria rastreador; não limpa EMA nesse trecho | Reinicia rastreador, filtro de postura e suavizador |
| Autoteste existente | Ângulos 90°/180°, classes e um ciclo sintético | Acrescenta teste de estabilidade e geração de prévia da interface |
| Dependências declaradas | Não há requirements avulso nos originais | mediapipe >=0.10.14,<0.11; opencv-contrib-python >=4.10,<6; numpy >=1.26,<3; Pillow >=10,<13 |

O script do ZIP do relatório é **idêntico byte a byte ao avulso**, SHA-256 `98fda55efbab5a2117dc5018cd2698632d2b436801d20035fdaaa37ed06ebfc7`.

Nenhuma versão própria contém classificador supervisionado, rotina de treinamento, cálculo de F1, matriz de confusão, altura normalizada do quadril ou derivadas angulares. A inclinação do tronco é calculada e registrada, mas a classificação atual usa apenas ângulos de joelho e quadril. A direção subir/descer é inferida pela sequência dos estados, não pelo sinal ou derivada angular.

## Proposta corrigida versus implementação

**Ângulo orientado:** a proposta corrigida usa atan2(det,dot) em (-π,π], preserva magnitude para postura e prevê normalização entre lados e desenrolamento temporal quando necessário. Os dois códigos próprios descartam imediatamente o sinal com abs(). Não há série orientada paralela, unwrap nem normalização da orientação entre os lados. Isso é uma pendência confirmada por leitura; não implica que o abs() deva ser removido de todos os atributos. Os limiares existentes foram definidos sobre magnitudes. A orientação futura deve explicitar ordem dos vetores, eixo y da imagem crescente para baixo, lateralidade e espelhamento; o pacote espelha antes de estimar a pose.

**Suavização e atraso:** as duas implementações usam y=0,25*x+0,75*y_anterior e exigem 3 rótulos iguais para confirmar postura. A proposta corrigida prevê selecionar α e janela de estabilidade em treino/validação, medindo qualidade, falsas transições, erro de contagem e latência. Não há rotina nem resultados dessa seleção nos arquivos. A aplicação fornece timestamps monotônicos crescentes ao MediaPipe e mede durações com relógio monotônico; isso não torna a EMA ou as janelas de 3/15 quadros independentes do FPS. Os CSVs guardam ângulos já suavizados: “raw_posture”/“postura_bruta” é a classe antes do filtro de estabilidade, mas depois da EMA. Não há exportação paralela dos ângulos brutos que permita medir diretamente o atraso entre as duas séries.

**Câmera:** a proposta corrigida exige câmera fixa aproximadamente à altura do quadril, pessoa de perfil e centralizada, corpo inteiro, plano do sensor paralelo ao sagital e eixo óptico aproximadamente perpendicular, com marcas no piso. O programa e o guia solicitam câmera lateral/enquadramento, mas não verificam ortogonalidade, altura ou distância. A captura real disponível é frontal e parcial e não valida esse protocolo lateral.

**Contagem:** a máquina precisa ser armada em SENTADO, atingir EM PÉ e retornar a SENTADO para incrementar. Não exige necessariamente observar uma classe TRANSIÇÃO entre todos os extremos: há atalhos explícitos PRONTO→EM PÉ e EM PÉ→SENTADO. Essa é a implementação efetiva; o diagrama nominal do relatório mostra as transições intermediárias. Há tratamento de tentativas interrompidas e perdas prolongadas, mas seus ensaios reais não estão documentados no pacote.

Observações estáticas adicionais a investigar futuramente, sem correção nesta etapa: no pacote, uma pausa no meio do ciclo não desconta o intervalo do relógio usado para duração; alternar espelho limpa filtros, mas não reinicia a máquina de estados; a troca automática do lado corporal pode misturar medidas de lados distintos na EMA. São implicações da leitura, não falhas reproduzidas experimentalmente nesta sessão.

## O que está proposto, implementado e validado

| Item | Evidência e estado |
|---|---|
| Captura, landmarks, ângulos, calibração, regras, filtros, contagem e CSV | Implementação confirmada por leitura; funcionamento histórico descrito no relatório; não executado nesta auditoria |
| Interface revisada | Código presente no ZIP, imagem de demonstração presente; já vai além da indicação “em desenvolvimento” da proposta, mas não prova teste integrado com webcam |
| Autotestes do avulso | Código presente e saída histórica “AUTOTESTE OK” registrada no relatório; não repetidos agora |
| Autoteste do pacote pt-BR | Código e resultado esperado presentes nos guias; não há log independente de execução recuperado |
| 15,2 FPS | Valor observado na captura preliminar real, não média nem benchmark da aplicação final |
| 28,7 FPS e 3 repetições na prévia | Valores fixados por gerar_demonstracao_interface(); são dados ilustrativos, não medições |
| Regressão Logística e Floresta Aleatória para STS | Propostos na versão corrigida; nenhum modelo ou treinamento STS encontrado |
| 12 sessões, 6 por integrante, 8–12 repetições | Protocolo planejado; gravações e rótulos STS não estão no pacote |
| F1 macro ≥0,85, ≥15 FPS e erro ≤1 por 10 movimentos | Metas de engenharia da proposta; não resultados atingidos comprovados |
| Validação de ciclos completos, generalização e validação clínica | Não demonstradas nos arquivos recuperados |

O relatório anterior registra Python 3.11.9, importações/pip check, modelo Lite de 5.777.746 bytes carregado e webcam 640×480. Esses são relatos históricos, não verificação do ambiente atual. Há espaços reservados para fotos e evidências de calibração, repetição, eventos e CSV; os placeholders não constituem resultados.

## Dependências e dados realmente incluídos

O ZIP pt-BR traz README, GUIA_WINDOWS, REFERENCIAS, requirements, três scripts PowerShell, cinco arquivos Python contando o __init__, prévia PNG e arquivos .gitkeep/LEIA-ME. **Não contém pose_landmarker_lite.task, .venv, calibração JSON salva, vídeos STS nem CSVs de sessão.** O README desenha alguns desses caminhos como estrutura esperada; a presença real foi conferida no ZIP, não presumida a partir da árvore ilustrativa.

O ZIP do relatório contém seu texto LaTeX, bibliografia, README, duas imagens e o script avulso. Não traz detectar_pose.py, requirements-lock.txt, modelo ou ambiente citados na árvore documental.

## Referência externa e autoria

A referência externa é o projeto de Veronica Di Gennaro e Daniel Yezid Guarnizo Orjuela, Sapienza Università di Roma, orientado por Daniele Pannone. Não é código nem experimento dos alunos da UFSC.

O pacote externo contém README, createCSV.py, Model_Predictions.py, GuideLine.ipynb, PDF ComputerVisionProject, 3 CSVs, 3 modelos Random Forest .pkl, 9 vídeos MP4 e .DS_Store. Usa mp.solutions.pose, vetores de 33×4 coordenadas/visibilidade e classes de agachamento, levantamento terra e supino. Sua contagem incrementa na passagem down→up, diferente do ciclo STS sentado→em pé→sentado.

O notebook foi lido em suas 48 células, incluindo saídas persistidas. Treina pipelines com StandardScaler e LogisticRegression, RidgeClassifier, RandomForestClassifier e GradientBoostingClassifier. Faz train_test_split(test_size=0.3) sobre linhas, sem agrupamento por sessão/participante; não transferir esse protocolo nem suas métricas altas para o STS. A proposta própria corrigida prevê separação por sessão e validação em grupos.

Os CSVs externos foram percorridos integralmente: todos têm 133 colunas e valores numéricos nos atributos, sem linhas de largura inesperada. coords_BP_C: 1.841 exemplos/5 classes; coords_DL_C: 2.478 exemplos/6 classes; coords_SQ_C: 1.303 exemplos/4 classes. Esses dados não são sessões próprias de sentar/levantar.

Os .pkl foram preservados e inventariados, mas não desserializados/executados. Os nove MP4 foram preservados e inventariados, não assistidos integralmente. Não há LICENSE ou declaração explícita de licença no conteúdo do ZIP; não se presume autorização de reutilização a partir do simples acesso ao repositório. Atribuição consta na documentação própria. Nenhum modelo externo é importado pelo programa STS recuperado.

## Diferenças documentais e identidade

Os dois ZIPs históricos da proposta são idênticos. A versão corrigida difere em main.tex, substituindo arccos por ângulo orientado, detalhando atraso/seleção da EMA e protocolo de câmera; README, bibliografia e imagens são iguais. O diff completo está em `proposta_historica_vs_corrigida.diff`. O PDF histórico tem 6 páginas e o corrigido tem 7.

Os dois PDFs ProopostaProjetos são idênticos. Pedem título/equipe, introdução, objetivos, métodos, materiais/ferramentas e cronograma, com consulta ao professor e submissão no Moodle por todos os integrantes. Não confirmam os prazos específicos recuperados indiretamente no contexto.

EEL7815 identifica Projeto Nível I em Controle e Processamento de Sinais; EEL7825 identifica Projeto Nível 2. Ambos os planos são de 2026.2, 72 h, professor Joceli Mayer, com relatórios 20%, apresentações 80% e frequência mínima 75%. A proposta usa “Projeto Nível I” na capa enquanto as instruções citam EEL7825; não foi inferida a matrícula correta dos integrantes nem alterada a identificação.

CTC_logo.png mostra a identidade do CTC/UFSC. logo.jpg contém um símbolo ψ; foi preservado, sem reinterpretá-lo como brasão oficial da UFSC. O relatório possui uma imagem institucional diferente, ufsc_ctc.png. A identidade visual deve ser revisada em uma etapa posterior se necessário.

## Limites da recuperação da conversa e continuidade

Foram consultados apenas registros recentes acessíveis de “PROJETO 26.2” e “Analisar contexto do projeto”, além do contexto consolidado. Não foi recuperada nem alegada a conversa completa. Os registros corroboram a cronologia e as decisões, mas não substituem os bytes dos originais ou evidências de experimentos.

Prazos mencionados no contexto (vídeo em 30/11, apresentação em 03/12 e relatório em 04/12) continuam sem aviso original/Moodle conferido nesta auditoria.

O estado atual permite escolher conscientemente qual versão própria usar numa próxima etapa. Nenhuma escolha definitiva, correção, instalação, treinamento ou validação nova foi feita. Aguardam-se os próximos comandos do usuário.
