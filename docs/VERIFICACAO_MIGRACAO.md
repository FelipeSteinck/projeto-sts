# Verificação da migração web — 22/10/2026

## Atualização supervisionada do Nível II

Após nova orientação, o usuário confirmou dois projetos distintos e STS com classificadores treinados como escopo do Nível II/EEL7825. O Nível I terá outro projeto, a definir depois.

A implementação nova acrescenta atributos causais compartilhados entre web e offline, treinamento de Regressão Logística/Floresta Aleatória, CV por grupos, busca de α/estabilidade, avaliação reservada, modelos JSON numéricos e ferramenta de anotação manual. Os quatro arquivos inicialmente suspensos foram retomados nesse escopo.

Verificação local atual: **16 testes aprovados**, incluindo os cinco anteriores, equivalência JSON/Scikit-learn, orientação/continuidade, isolamento de partições e teste que altera rótulos de teste sem modificar pesos/configuração aprendidos. JavaScript dos dois fluxos conferido com `node --check`; `pip check` sem dependências quebradas. Há avisos de depreciação nas dependências, sem falha dos testes.

O treino demonstrativo utiliza oito sessões artificiais (seis de treino, duas de teste). Nenhum resultado desse conjunto será relatado como experimento humano. O usuário informou que ainda não gravou vídeos próprios.

As seções abaixo descrevem a migração anterior; seus cinco testes e commit são históricos, não a contagem atual de testes.

## Verificado localmente

- Cinco testes pytest aprovados: ângulo orientado e espelho; configuração e isolamento de sessões; ciclo completo, exportação e rejeição de timestamp decrescente; cancelamento por perda de pose; página inicial e saúde da API.
- Os testes do ciclo usam landmarks sintéticos, não participantes ou vídeos reais.
- Modelo oficial Pose Landmarker Lite baixado (5.777.746 bytes) e SHA-256 conferido: 59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a.
- Uma requisição HTTP com quadro preto sintético percorreu OpenCV e MediaPipe reais, retornando SEM POSTURA e zero repetições. Verifica carregamento/inferência, não precisão de detecção humana.
- pip check sem requisitos quebrados no ambiente local de verificação (Python 3.12/Windows). Codespaces configurado para Python 3.11/Linux; a execução naquele ambiente deve ser conferida separadamente.
- JavaScript conferido com node --check.

## Limites

Não foram usados webcam, participantes nem dados STS rotulados nesta verificação. A calibração real, taxa sustentada, latência de rede e contagem em vídeo humano precisam de ensaio. Não há resultado experimental de classificação supervisionada.

O núcleo desktop src foi copiado sem alterações da versão recuperada no ZIP pt-BR. Os novos arquivos web acrescentam adaptação e exportação sem substituir os originais locais.

## Codespaces

Verificado em Python 3.11.13/Linux: instalação concluída, modelo baixado com SHA-256 conferido e cinco testes aprovados. A preparação foi ajustada para evitar o repositório Yarn opcional da imagem, mantendo a verificação de assinaturas dos repositórios usados. O GitHub Actions também aprovou a execução no commit 8733ecb32b9d5cae85f20565833ec22c91db1d2a.

Repositório privado: https://github.com/FelipeSteinck/projeto-sts

Editor: https://legendary-space-carnival-j7x5v9w67px3jq56.github.dev/

Aplicação (porta privada): https://legendary-space-carnival-j7x5v9w67px3jq56-8000.app.github.dev/

A aplicação abriu e confirmou o ambiente pronto. O teste com webcam e movimentos reais ainda depende da participação do usuário; não foi realizado nesta migração.
