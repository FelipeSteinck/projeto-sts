# Continuidade: concluir o Nível II primeiro

## Orientação vigente em 22/10/2026

Após reunião com o professor, o usuário informou que são necessários dois projetos e duas propostas distintos. O STS atual será tratado no Nível II/EEL7825. O Nível I/EEL7815 terá outro projeto, definido somente depois. O detalhamento e as fontes estão em [SEPARACAO_NIVEIS.md](SEPARACAO_NIVEIS.md).

A ampliação foi interrompida brevemente para esclarecer o escopo. O usuário confirmou STS com classificadores treinados para o Nível II; o desenvolvimento supervisionado foi retomado como parte de EEL7825. A cópia preliminar arquivada não é uma versão validada.

## Entrega de migração

- Repositório privado e ambiente Codespaces em Python 3.11.
- Interface de webcam e vídeo acessível no navegador, mantendo OpenCV e MediaPipe no Python.
- Núcleo desktop recuperado preservado; adaptação web em arquivos novos.
- Exportação de magnitudes brutas/EMA e ângulos orientados para futura análise temporal.
- Testes de integração sintéticos e instruções de execução.

## Próximas etapas do Nível II

1. Coletar e rotular vídeos próprios para o pipeline supervisionado já implementado, com separação por sessão ou participante. A demonstração sintética e os 16 testes locais verificam software, sem medir desempenho humano.
2. Revisar com a equipe e discutir com o professor a proposta de EEL7825 já redigida, com problema, metas, métodos, dados, ferramentas e cronograma próprios.
3. Conferir a execução e os testes da versão ativa e realizar um piloto real com aquisição lateral controlada.
4. Documentar contagem, tentativas incompletas, perda de pose, FPS e atraso com referências verificáveis; corrigir falhas observadas.
5. Acrescentar resultados reais ao relatório IEEE do Nível II já revisado e compilado; atualmente ele distingue implementação, demonstração sintética e avaliação experimental pendente.
6. Fechar as entregas do Nível II; só depois definir outro tema e outra proposta para o Nível I.

## Roteiro anterior, preservado como histórico

Os itens abaixo pertencem à proposta antiga, que combinava as duas disciplinas. Não são uma atribuição automática de requisitos à nova proposta do Nível II nem o plano de um segundo projeto.

1. Confirmar com a equipe a identificação EEL7815/Nível I versus EEL7825/Nível II nos documentos.
2. Definir protocolo lateral fixo: plano do sensor paralelo ao sagital, eixo óptico aproximadamente perpendicular, distância/altura/resolução/luz/cadeira/lado registrados.
3. Criar processamento offline determinístico dos vídeos e rotulagem por intervalos, com identificadores de sessão e participante.
4. Coletar as 12 sessões propostas, se o protocolo for mantido, sem presumir que já existem.
5. Normalizar a orientação entre lados, tratar espelhamento e continuidade angular, calcular derivadas e altura normalizada do quadril.
6. Comparar regras, Regressão Logística e Floresta Aleatória. Ajustar pré-processamento, α e estabilidade apenas no treino/validação por grupos.
7. Medir F1 macro, matriz de confusão, erro de contagem, falsas transições e latência com referências rotuladas. Medir FPS separadamente do trânsito de rede.
8. Atualizar relatório e apresentação com resultados realmente medidos e limitações.

As metas F1≥0,85, ≥15 FPS e erro≤1 por dez repetições são metas da proposta, não resultados. A prévia antiga com 28,7 FPS e três repetições é ilustrativa.

## Convenção da versão web

Timestamps são milissegundos da fonte: tempo decorrido desde início da captura da webcam ou currentTime do vídeo. O servidor rejeita valores repetidos ou decrescentes. A rede muda a taxa de amostragem da webcam; vídeos reproduzidos no navegador podem ter quadros ignorados quando a inferência é lenta. Um pipeline offline deve preceder a avaliação quantitativa final.

Cada sessão tem filtros, calibração, contagem e CSV próprios. O parâmetro α é configurável, mas a aplicação não escolhe automaticamente um valor ótimo. Os ângulos orientados são adicionais e não substituem os atributos de magnitude usados pelas regras existentes.
