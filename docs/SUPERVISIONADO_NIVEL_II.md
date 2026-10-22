# Classificação supervisionada STS - EEL7825 / Nível II

Esta implementação pertence ao projeto STS de Nível II. O Nível I será outro projeto, definido depois. Ainda não existem vídeos próprios gravados, conforme informado pelo usuário. Modelos de demonstração são treinados com coordenadas sintéticas e não representam validação com pessoas.

## Fluxo executável

1. Extrair todos os quadros de vídeos próprios com taxa constante.
2. Anotar manualmente intervalos de sentado, transição e em pé; reservar os trechos de calibração.
3. Definir sessões de treino e de teste no manifesto antes de selecionar parâmetros.
4. Treinar Regressão Logística e Floresta Aleatória com validação por grupos no treino.
5. Avaliar os modelos congelados e o método geométrico nas sessões de teste.
6. Usar os modelos na interface web, com parâmetros de filtragem registrados e CSV exportável.

## Demonstração sem vídeos humanos

No terminal, na raiz do repositório:

```bash
python -m pip install -r requirements.txt
python -m sts_ml demo
python -m uvicorn webapp:app --host 0.0.0.0 --port 8000
```

O comando `demo` gera oito sessões artificiais, sendo seis de treino e duas de teste. Ajusta os dois classificadores, avalia regras e modelos e gera arquivos em `outputs/demo/` e `models/demo/`. O gerador usa coordenadas de uma cadeia articulada e rótulos do roteiro artificial, sem imagens humanas, MediaPipe ou modelos externos.

A aplicação oferece opções identificadas como **DEMO SINTÉTICA**. Usá-las com webcam demonstra integração, sem tornar o modelo validado em movimentos reais. A opção padrão continua sendo regras geométricas. Modelos reais só aparecem se existirem em `models/sts/` com metadados compatíveis.

## Coleta, calibração e anotação reais

Use códigos de participante e sessão (P01, P01_S01 etc.), sem nomes. Cada gravação deve ter identificador único. Controle câmera, luz, cadeira, orientação lateral e espelho. O plano da imagem fica aproximadamente paralelo ao sagital; o eixo óptico, aproximadamente perpendicular. Registre a configuração.

A aplicação permite baixar o CSV e a calibração JSON depois de registrar sentado e em pé. Use as posições individuais para obter a calibração do método geométrico, independentemente dos rótulos do trecho avaliado. Para comparar métodos com o mesmo vídeo, mantenha lado/espelhamento e configuração geométrica equivalentes.

Abra `/rotular` pelo botão **Anotar vídeo**. O vídeo fica no navegador nessa página. Marque os intervalos observando o movimento, sem copiar os rótulos previstos pelo algoritmo. O CSV exportado tem formato:

```text
inicio_s;fim_s;rotulo;uso
0;2;SENTADO;calibracao
2;4;EM PÉ;calibracao
4;6;SENTADO;avaliacao
6;7;TRANSIÇÃO;avaliacao
7;9;EM PÉ;avaliacao
9;10;TRANSIÇÃO;avaliacao
10;12;SENTADO;avaliacao
```

Exemplo de estrutura, não dado de experimento. Intervalos são [início, fim), não podem se sobrepor e devem cobrir a sequência avaliada. `calibracao` precede a avaliação e não entra no treinamento ou nas métricas. `INVALIDO` é reservado à referência humana indeterminável; pose ausente com postura humana observável deve manter seu rótulo verdadeiro, para que a falha conte na avaliação.

A contagem de referência é derivada dos extremos dos intervalos manuais, mesmo se a amostragem não observar algum extremo. Lacunas/INVALIDO na referência suspendem a métrica de contagem daquela sequência, com aviso. A avaliação por quadro continua nos intervalos conhecidos. Não se interpola uma verdade inexistente.

## Extração offline

```bash
python -m sts_ml extrair --video data/videos/P01_S01.mp4 --saida outputs/dados/P01_S01.csv --sessao P01_S01 --participante P01
```

Use `--espelhar` somente quando fizer parte do protocolo. O extrator percorre todos os quadros decodificados, sem depender da velocidade de reprodução/rede. Usa tempo `índice/fps_nominal` e gera `.meta.json` com hashes do vídeo/modelo, taxa, quantidade de quadros e convenção temporal. **A versão atual pressupõe taxa constante.** Vídeos VFR precisam de conversão previamente documentada. A prévia web pode saltar quadros e não substitui esse processamento para avaliação final.

O CSV contém a cadeia de pontos em pixels e medidas brutas, além de schema/tipo/identificadores. CSVs antigos sem essas informações são rejeitados; reextraia os vídeos ou grave com a versão nova. Não se usam CSVs, vídeos ou modelos da referência externa como dados próprios.

## Manifesto e divisão

Exemplo de um item de sessão (o manifesto real deve conter várias sessões):

```json
{
  "tipo_dados": "real",
  "agrupar_por": "sessao",
  "sessoes": [
    {
      "id": "P01_S01",
      "participante": "P01",
      "particao": "treino",
      "quadros": "P01_S01.csv",
      "rotulos": "P01_S01_rotulos.csv",
      "calibracao": "calibracao_P01_S01.json"
    }
  ]
}
```

Os caminhos são relativos ao manifesto. `calibracao` pode ser o JSON exportado pela aplicação ou um objeto com os quatro extremos articulares e `origem`. O programa exige calibração válida, treino e teste distintos e três classes nos dados usados para ajustar cada fold. Com CV de três folds, são necessários ao menos três grupos de treino e um grupo de teste; o desenho de coleta deve fornecer suporte suficiente em cada classe.

`agrupar_por: sessao` mantém cada gravação inteira em uma divisão. Participantes podem aparecer em sessões de treino e teste, medindo generalização para novas sessões dessas mesmas pessoas. Para generalização a pessoas novas, use `participante`; os grupos precisam ser distintos, em número suficiente. Dois participantes não permitem três folds de treino mais teste por participante.

Os IDs devem representar as gravações reais, sem duplicar uma gravação sob outro ID. Os hashes detectam alterações de arquivos, não garantem a veracidade dos identificadores.

## Treinamento e seleção

```bash
python -m sts_ml treinar --manifesto outputs/dados/manifesto.json --saida models/sts --alfas 0.1,0.25,0.5,1 --estabilidade 1,3 --folds 3
```

O programa utiliza apenas grupos de **treino** para aprender parâmetros e escolher configuração. A Regressão Logística usa `StandardScaler` dentro do pipeline e busca C em 0,1, 1 e 10. A Floresta Aleatória usa 80 árvores, mínimo de duas amostras por folha e profundidade 5 ou sem limite. Ambas usam pesos balanceados e semente 42.

A busca também compara α e quadros estáveis informados. O critério é maior F1 macro médio por sessão na CV; desempates usam MAE de contagem e latência absoluta de eventos. O método geométrico escolhe α/N na mesma CV. A grade precisa ser fixada antes da avaliação final. A comparação científica deve explicitar esse procedimento e o tamanho amostral.

O comando de treino valida estrutura e hashes do manifesto completo, mas não calcula métricas do teste para selecionar parâmetros. `treinamento.json` registra folds, grupos, candidatos, seleção e `test_evaluated: false`. Não use os resultados de teste para repetir ajustes e continuar chamando o mesmo conjunto de teste independente.

## Atributos compartilhados e convenções

Schema `sts-atributos-v1`, sete atributos: ângulos EMA de joelho/quadril, inclinação EMA do tronco, altura relativa EMA do quadril e velocidades desses dois ângulos e da altura. A altura é `(y_tornozelo - y_quadril)/(comprimento_coxa + comprimento_perna)` no próprio quadro. É uma razão de projeções 2D, sem interpretação clínica. Derivadas usam Δt da fonte; a primeira amostra de cada segmento recebe velocidade zero.

A EMA é causal, inicializada pela primeira medida válida. Menor α aumenta suavização e tende a aumentar atraso. A extração temporal reinicia após troca de lado, intervalo entre poses válidas maior que 1 s ou 15 quadros sem pose. Uma descontinuidade de lado/tempo cancela ciclo ativo, preservando as contagens já concluídas. Esse comportamento é novo no adaptador; o núcleo desktop histórico foi preservado.

O cálculo orientado usa atan2(det,dot), com y da imagem crescente para baixo. Os canais orientados brutos, normalizados e contínuos são exportados. A convenção de normalização por cadeia usa como âncora a primeira flexão com `10 < |ângulo| < 170`, tornada positiva; até essa âncora, os canais normalizados ficam vazios. A continuidade usa o menor incremento angular entre observações, pressupondo deslocamento menor que 180° por amostra. Troca de lado reinicia a convenção.

Isso fornece invariância à reflexão para a cadeia ancorada, **não** uma convenção anatômica de rotação. O sinal isolado não indica subida/descida. Os canais orientados não entram no vetor v1; as magnitudes e suas variações são usadas no modelo. Medidas continuam sendo projeções 2D.

## Avaliação e integração

```bash
python -m sts_ml avaliar --manifesto outputs/dados/manifesto.json --modelos models/sts --saida outputs/avaliacao --tolerancia-evento 1
```

A avaliação rejeita arquivos diferentes do manifesto congelado no treino e interseção indevida de grupos. Produz JSON, CSVs de predições e matrizes de confusão PNG para os três métodos. Reporta F1 macro, média de revocação por classe, suporte, coluna DESCONHECIDA para ausência de pose, cobertura, erro de contagem por sessão e por dez movimentos e pareamento um a um dos eventos, com tolerância declarada, falsas contagens, perdas e latência assinada/absoluta.

Os arquivos de modelo são JSON numérico próprio (coeficientes/escalonamento ou árvores), sem desserialização de pickle/joblib. Testes comparam rótulos e pontuações à inferência original do Scikit-learn. A aplicação aceita apenas os modelos em caminhos previstos e schema compatível. α e estabilidade ficam bloqueados para reproduzir a seleção do modelo. Pontuação de classe não é garantia de acerto nem probabilidade clinicamente calibrada.

Na interface, as regras são executadas em paralelo usando a mesma α/N do método selecionado para facilitar observação. No relatório offline, cada método usa sua própria configuração escolhida na CV; a diferença é registrada nos resultados. Nenhum modelo é escolhido automaticamente como vencedor consultando o teste.

## Limite atual

O fluxo pode ser treinado e avaliado de ponta a ponta com dados sintéticos. Ainda faltam gravações próprias, rótulos independentes, treino real, avaliação reservada e demonstração com movimentos humanos. Métricas sintéticas não serão apresentadas como resultados do Nível II. O Nível I permanece sem tema e sem implementação própria.
