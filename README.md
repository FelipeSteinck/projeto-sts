# Monitor STS · sentar e levantar

**Organização acadêmica atualizada em 22/10/2026:** este STS, incluindo a comparação com classificadores treinados, é o projeto do **Nível II / EEL7825**, conforme confirmação do usuário após reunião com o professor. O Nível I terá outro projeto e outra proposta, a definir depois. Veja [a separação de escopos](docs/SEPARACAO_NIVEIS.md).

Projeto acadêmico de Luiz Felipe Steinck e Luis Felipe Candido Sola, com orientação do professor Joceli Mayer (UFSC). Reconhece SENTADO, TRANSIÇÃO e EM PÉ e conta o ciclo sentado → em pé → sentado.

## Começar no navegador

1. Abra **Code → Codespaces → Create codespace on main** neste repositório.
2. Aguarde a instalação automática das dependências, o download do modelo oficial e os testes.
3. Na aba **Ports**, abra a porta **8000 / Monitor STS** em uma nova aba do navegador. Mantenha a visibilidade da porta **Private**.
4. Escolha webcam ou um vídeo do computador. A permissão da câmera só é solicitada ao clicar em **Iniciar sessão**; não há captura de áudio.
5. Com o corpo inteiro de perfil, registre sentado e em pé. Depois execute os movimentos e baixe o CSV.

Se a aplicação não abrir automaticamente, execute no terminal:

```bash
python -m uvicorn webapp:app --host 0.0.0.0 --port 8000
```

Os arquivos na raiz são a versão ativa do projeto. `projeto-sts-bootstrap.zip` é um snapshot da transferência inicial, incluindo documentos originais próprios; não é necessário extraí-lo para executar a aplicação.

## Executar no computador

Python 3.11 recomendado. Instale as dependências em um ambiente virtual e execute:

```bash
python -m pip install -r requirements.txt
python scripts/download_model.py
python -m pytest -q
python -m uvicorn webapp:app --host 127.0.0.1 --port 8000
```

Abra http://localhost:8000. A interface desktop histórica continua disponível via `python main.py` em um computador com câmera e sistema gráfico. O Codespace usa a interface web.

## Organização

- `src/`: versão modular própria recuperada, preservada como base desktop.
- `webapp.py` e `web/`: adaptação web com FastAPI; usa OpenCV e MediaPipe no Python do servidor.
- `.devcontainer/`: Python 3.11, dependências de sistema e porta 8000.
- `tests/`: integração sintética da API, ciclo completo, perda de rastreamento, CSV e timestamps.
- `docs/`: contexto, auditoria, protocolo e documentos acadêmicos.
- `historico/`: fontes próprias anteriores, com hashes de origem.
- `scripts/download_model.py`: download do Pose Landmarker Lite oficial; o binário não é versionado.

## O que esta versão faz

A interface envia quadros JPEG ao Python. O motor compartilhado extrai magnitudes, altura relativa e variações temporais, aplica EMA e estabilidade e conta ciclos. Permite selecionar regras, Regressão Logística ou Floresta Aleatória quando o respectivo modelo estiver disponível. Exporta coordenadas/medidas brutas, séries orientadas e contínuas, atributos, predições e eventos.

Os ângulos orientados usam eixo y crescente para baixo e ordem quadril–joelho–tornozelo / ombro–quadril–joelho. Uma convenção por cadeia ancorada em flexão normaliza sinal e acompanha continuidade; até obter âncora, os campos ficam vazios. Não é uma convenção anatômica. Os sete atributos v1 usam magnitudes/velocidades, sem interpretar o sinal como direção do movimento. Veja [o fluxo supervisionado e as convenções](docs/SUPERVISIONADO_NIVEL_II.md).

## Treinar e demonstrar os classificadores

Para exercitar o fluxo sem gravações humanas:

```bash
python -m sts_ml demo
```

Reabra a aplicação para selecionar os modelos **DEMO SINTÉTICA**. Esse comando gera dados artificiais, treina os dois modelos por validação agrupada e avalia regras e modelos em sessões sintéticas reservadas. Os resultados não representam desempenho com pessoas.

Para dados próprios, use **Anotar vídeo**, extração offline, manifesto com sessões e calibração, `python -m sts_ml treinar` e `python -m sts_ml avaliar`, conforme [o guia](docs/SUPERVISIONADO_NIVEL_II.md). A proposta revisada do Nível II está em [minuta para discussão](docs/PROPOSTA_NIVEL_II_RASCUNHO.md).

## Evidência e pendências

- Os testes automáticos usam coordenadas sintéticas; sua aprovação não demonstra precisão real do MediaPipe ou qualidade clínica.
- Ainda não há vídeos próprios gravados, modelos treinados em pessoas ou métricas experimentais humanas. Há treinamento/inferência/avaliação verificáveis com dados sintéticos explicitamente identificados.
- A comparação entre regras, Regressão Logística e Floresta Aleatória foi confirmada como parte do Nível II. A existência do código de treinamento não equivale à validação com vídeos humanos.
- A webcam e os vídeos no navegador são processados por amostragem, limitada pela rede e pela inferência. Não confundir a resposta da API com latência total nem usar essa prévia como benchmark offline final.
- A busca seleciona α e estabilidade somente na validação agrupada do treino. O cancelamento após 15 quadros ausentes continua dependente da taxa; troca de lado ou intervalo maior que 1 s entre poses válidas também cancela ciclo ativo no novo motor web.
- Em vídeos, não retroceda enquanto uma sessão estiver ativa. Inicie outra sessão para voltar ao início.
- A calibração usa uma amostra em cada postura e fica apenas na memória da sessão web. Não importa automaticamente o JSON do desktop.

## Dados e preservação

Os quadros passam pela memória do servidor e não são gravados pela aplicação. Os resultados numéricos ficam temporariamente em memória; baixe o CSV antes de reiniciar o servidor ou excluir o Codespace. Não envie dados sensíveis sem autorização dos participantes.

Os 16 originais foram preservados na pasta local de transição. Este repositório contém uma seleção das fontes próprias e documentos. O ZIP externo de 232 MB e seus vídeos/modelos não são versionados aqui. A referência é atribuída em `REFERENCIAS.md`, não constitui autoria nem dados STS da equipe. Nenhuma licença ampla é atribuída automaticamente aos documentos ou ao material externo.

Protótipo acadêmico sem validação clínica. A aplicação não fornece diagnóstico nem prescrição.
