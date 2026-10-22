# Monitor STS · sentar e levantar

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

Os arquivos na raiz são a versão ativa do projeto. projeto-sts-bootstrap.zip é um snapshot da transferência inicial, incluindo documentos originais próprios; não é necessário extraí-lo para executar a aplicação.

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

A interface envia quadros JPEG ao Python. A inferência gera landmarks, e o núcleo existente calcula magnitudes angulares, aplica EMA e estabilidade e conta ciclos. A adaptação também exporta ângulos orientados e medidas antes/depois da EMA, além dos timestamps da fonte e do processamento do servidor.

Os ângulos orientados usam eixo y crescente para baixo e ordem quadril–joelho–tornozelo / ombro–quadril–joelho. Sinal muda com lado e espelhamento. Ainda não há normalização entre lados ou unwrap, nem classificador treinado. A classificação por regras continua usando magnitudes, preservando o significado dos limiares anteriores.

## Evidência e pendências

- Os testes automáticos usam coordenadas sintéticas; sua aprovação não demonstra precisão real do MediaPipe ou qualidade clínica.
- Não há métricas experimentais novas, vídeos STS rotulados ou modelos supervisionados treinados neste repositório.
- A proposta prevê comparar Regressão Logística e Floresta Aleatória por sessão; isso continua no roteiro em `docs/PLANO_DE_CONTINUIDADE.md`.
- A webcam e os vídeos no navegador são processados por amostragem, limitada pela rede e pela inferência. Não confundir a resposta da API com latência total nem usar essa prévia como benchmark offline final.
- Janelas de 3 quadros estáveis e 15 quadros ausentes dependem da taxa de processamento; α deve ser selecionado em validação.
- Em vídeos, não retroceda enquanto uma sessão estiver ativa. Inicie outra sessão para voltar ao início.
- A calibração usa uma amostra em cada postura e fica apenas na memória da sessão web. Não importa automaticamente o JSON do desktop.

## Dados e preservação

Os quadros passam pela memória do servidor e não são gravados pela aplicação. Os resultados numéricos ficam temporariamente em memória; baixe o CSV antes de reiniciar o servidor ou excluir o Codespace. Não envie dados sensíveis sem autorização dos participantes.

Os 16 originais foram preservados na pasta local de transição. Este repositório contém uma seleção das fontes próprias e documentos. O ZIP externo de 232 MB e seus vídeos/modelos não são versionados aqui. A referência é atribuída em `REFERENCIAS.md`, não constitui autoria nem dados STS da equipe. Nenhuma licença ampla é atribuída automaticamente aos documentos ou ao material externo.

Protótipo acadêmico sem validação clínica. A aplicação não fornece diagnóstico nem prescrição.
