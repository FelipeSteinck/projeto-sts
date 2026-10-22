# Continuidade da proposta acadêmica

## Entrega de migração

- Repositório privado e ambiente Codespaces em Python 3.11.
- Interface de webcam e vídeo acessível no navegador, mantendo OpenCV e MediaPipe no Python.
- Núcleo desktop recuperado preservado; adaptação web em arquivos novos.
- Exportação de magnitudes brutas/EMA e ângulos orientados para futura análise temporal.
- Testes de integração sintéticos e instruções de execução.

## Próximas implementações acadêmicas

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
