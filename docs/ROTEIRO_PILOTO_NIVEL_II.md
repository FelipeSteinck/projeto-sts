# Piloto do monitor STS - Nível II / EEL7825

Roteiro de engenharia proposto em 22/10/2026. Não é resultado executado nem requisito quantitativo já aprovado pelo professor. Serve para verificar a versão geométrica existente antes dos experimentos finais.

## Preparação

1. Abrir o Codespace e a aplicação na porta privada 8000. Conferir a mensagem de ambiente pronto.
2. Manter câmera fixa, pessoa de perfil e centralizada, corpo inteiro e cadeira visíveis. Registrar altura/distância e lado. O plano da imagem deve ser aproximadamente paralelo ao plano sagital, e o eixo óptico aproximadamente perpendicular a ele.
3. Anotar commit, resolução, iluminação, navegador, fonte, espelhamento, α e quadros estáveis. Começar pelos padrões α=0,25 e N=3 como configuração inicial, sem alegar que sejam ótimos.
4. Registrar sentado e em pé com a pessoa imóvel. Conferir calibração concluída. Iniciar o ensaio sentado.
5. Usar observação independente para a referência de contagem. Se houver vídeo para análise posterior, registrar a autorização de uso. O servidor atual não grava imagens ou vídeos automaticamente.

## Casos

| Caso | Execução proposta | O que conferir |
|---|---|---|
| Inicialização | Antes de armar em sentado, observar a pessoa em pé | Não contar uma repetição apenas por iniciar em pé |
| Ciclos completos | Após calibrar, executar uma sequência de dez ciclos sentado → em pé → sentado | Contagem manual e estimada, eventos, fase final e CSV |
| Tentativa incompleta | Iniciar subida e retornar sem chegar à posição em pé de referência | Se o algoritmo registra incompleta, se produz falsa repetição e quais ângulos foram observados |
| Permanência | Permanecer sentado e depois em pé | Se oscilações produzem eventos ou contagens indevidas |
| Perda de pose | Durante um ciclo, interromper a visibilidade por pelo menos 15 observações processadas; depois reaparecer sentado | Cancelamento, ausência de falsa repetição e recuperação. Não converter 15 quadros em segundos fixos |
| Exportação | Encerrar sessão e baixar o CSV | Número de linhas, tempos crescentes, campos, eventos e coerência da última contagem |

Se a calibração ou algum caso falhar, registrar o observado e as condições antes de alterar parâmetros. Não redefinir o resultado esperado para coincidir com a saída do programa.

## Registro a preencher

- Identificador da sessão:
- Data e operador:
- Commit / ambiente:
- Fonte e resolução:
- Geometria, luz e oclusões:
- Espelhamento / lado:
- α / N:
- Calibração concluída:
- Contagem de referência / estimada:
- Falsas contagens / repetições perdidas:
- Tentativas incompletas / cancelamentos observados:
- Caminho do CSV exportado:
- Referência independente disponível e autorização de imagem:
- Falhas e passos para reproduzir:

O CSV registra tempo da fonte e processamento no servidor. Esses campos permitem análise parcial, mas não medem sozinhos todo o atraso entre movimento real e resposta da interface. A latência exige instantes de referência anotados. FPS sustentado também exige intervalo e método de medição declarados.

## Critério de encerramento desta etapa

Registrar resultados dos casos, corrigir falhas reproduzíveis e repetir os afetados. Um piloto aprovado permite preparar uma demonstração controlada; não prova generalização ou validação clínica. O protocolo experimental final, incluindo tamanho da amostra, depende da proposta revisada do Nível II.
