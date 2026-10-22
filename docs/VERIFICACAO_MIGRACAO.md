# Verificação da migração web — 22/10/2026

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
Verificado em Python 3.11.13/Linux: instalação concluída, modelo baixado com SHA-256 conferido e cinco testes aprovados. A preparação foi ajustada para evitar o repositório Yarn opcional da imagem, mantendo a verificação de assinaturas dos repositórios usados.
