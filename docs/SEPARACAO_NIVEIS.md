# Dois projetos independentes: Nível I e Nível II

Atualização: 22/10/2026, após a reunião relatada pelo usuário.

## Decisão vigente

O professor orientou dois projetos e duas propostas diferentes. O projeto STS existente passa a ser tratado como trabalho do **Nível II / EEL7825**. O Nível I / EEL7815 terá outro problema, proposta e entregas, a definir depois da conclusão do Nível II. Acrescentar um módulo ao STS não será apresentado como um segundo projeto.

Esta atualização substitui a estratégia anterior de usar o mesmo STS para contemplar os dois níveis. É o registro da orientação comunicada pelo usuário; não é uma nova aprovação formal do escopo técnico pelo professor.

## O que consta nos documentos

- `docs/fontes/EEL7815.pdf`: Projeto Nível I em Controle e Processamento de Sinais, plano 2026.2, 72 horas.
- `docs/fontes/EEL7825.pdf`: Projeto Nível 2 em Controle e Processamento de Sinais, plano 2026.2, 72 horas.
- Ambos têm 36 horas de introdução/laboratório de processamento de imagens e 36 horas de projeto. Listam aquisição/amostragem, Fourier, filtragem, equalização, morfologia, segmentação, limiarização, bordas, descritores e reconhecimento, inclusive métodos estatísticos e treinamento supervisionado.
- Os temas de projeto incluem reconhecimento de padrões, inspeção de peças, monitoramento de áreas e outros temas acordados com o professor. Os planos não atribuem técnicas específicas exclusivamente a um dos níveis nem exigem aplicar todas as técnicas listadas em cada projeto.
- Ambos indicam relatórios com peso de 20%, apresentações com 80% e frequência mínima de 75%. Não há, nos arquivos recuperados, uma rubrica que permita presumir maior ou menor complexidade obrigatória apenas pelo número do nível.
- `ProopostaProjetos.pdf` é uma orientação identificada como EEL7825. Pede título/equipe e responsabilidades, introdução, objetivos/metas, métodos, materiais/ferramentas (incluindo origem/rotulagem dos dados) e cronograma. Recomenda discutir a proposta antes da submissão no Moodle por todos os integrantes. Não se presume que esse documento seja também uma instrução específica para EEL7815.

## Delimitação atual

| Aspecto | Nível II: STS | Nível I: projeto independente |
|---|---|---|
| Problema | Reconhecer fases e contar ciclos completos sentado → em pé → sentado | Ainda não escolhido |
| Base | OpenCV, MediaPipe, ângulos 2D, calibração, EMA, estabilidade e máquina de estados | Será definida após concluir o Nível II |
| Programa | Monitor desktop histórico e adaptação web já existentes | Não iniciado |
| Proposta | Elaborar uma revisão própria para EEL7825 a partir do escopo efetivamente acordado | Nova proposta, com objetivos e experimento próprios |
| Evidências | Testes de software; faltam ensaios reais documentados | Nenhuma, pois o projeto não foi iniciado |
| Reuso | Bibliotecas e conhecimento podem ser reaproveitados com transparência | Não reapresentar o STS ou um de seus módulos como trabalho independente |
| Prioridade | Concluir primeiro | Trabalhar depois |

O STS já permite demonstrar o método geométrico. Isso não significa que sua avaliação experimental esteja concluída.

## Confirmação de escopo do Nível II

A proposta antiga corrigida inclui comparação entre regras, Regressão Logística e Floresta Aleatória, mas está identificada como Nível I e pertence à estratégia anterior. A reunião muda a organização dos projetos, porém não informa, por si só, se o professor manteve essa comparação como requisito do Nível II.

Após esclarecimento nesta conversa, o usuário confirmou **STS com classificadores treinados** para o Nível II. Portanto, a implementação de Regressão Logística e Floresta Aleatória, sua comparação com regras e a avaliação por sessão pertencem ao Nível II. Não constituem um projeto de Nível I separado. A implementação foi retomada com essa identificação; a conclusão experimental continua dependendo de dados próprios rotulados.

## Estado da implementação interrompida

Antes da nova orientação, foram criados quatro arquivos preliminares: `src/atributos.py`, `src/modelos.py`, `src/motor.py` e `sts_ml/__init__.py`. Não foram integrados ao `webapp.py`, à interface ou ao ambiente remoto; não houve treinamento nem validação desses módulos.

Eles foram preservados, com hashes conferidos, em `experimentos_suspensos/classificacao_supervisionada_2026-10-22/`. Após a confirmação do usuário, cópias voltaram ao desenvolvimento ativo como parte do Nível II. A cópia arquivada é apenas o estado preliminar, sem testes, e não representa a implementação concluída.

## Ordem de fechamento do Nível II

1. Produzir a proposta revisada identificada como EEL7825/Nível II, incluindo comparação supervisionada, mantendo a anterior como histórico.
2. Conferir a execução da versão ativa e os testes já existentes; preservar os originais recuperados.
3. Fazer um piloto com câmera lateral fixa, corpo inteiro e cadeira visíveis, calibração e ciclos completos. Registrar também tentativa incompleta e perda de rastreamento.
4. Medir contagem real versus estimada, falsas contagens, tentativas incompletas, perdas de pose, desempenho e atraso. A quantidade final de sessões e os critérios de anotação devem constar da proposta revisada.
5. Corrigir problemas demonstrados pelo piloto e repetir os casos afetados.
6. Atualizar o relatório IEEE, figuras, vídeo e apresentação com a identificação de Nível II e evidências realmente obtidas.
7. Conferir proposta, código, CSVs, resultados, instruções de reprodução e entrega. Somente então iniciar a escolha do Nível I.

Não se registram como confirmados novos prazos de entrega, aprovação de proposta revisada, experimentos com pessoas ou métricas de desempenho.

## Documentação anterior

Os 16 originais e o contexto recuperado permanecem preservados. A proposta antiga e a cópia histórica do relatório refletem a estratégia anterior. Foram produzidos uma nova proposta para EEL7825/Nível II e um relatório IEEE revisado, com o pipeline supervisionado implementado, 16 testes locais aprovados e demonstração sintética explicitamente identificada. Os documentos compilaram no Prism; a proposta continua sendo rascunho para discussão e a validação com pessoas permanece pendente.

O arquivo `PLANO_DE_CONTINUIDADE.md` registra a sequência de trabalho vigente. O documento de verificação da migração continua válido como evidência de software, sem equivaler à validação experimental.
