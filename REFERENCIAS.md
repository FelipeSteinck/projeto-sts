# Referências técnicas

1. Guarnizo, D. et al. *Pose Estimation for Fitness Exercise Analysis*.
   Repositório consultado como referência de fluxo: extração de landmarks,
   classificação de fases e contagem de repetições.
   <https://github.com/DanielGuarnizo/Pose-Estimation-for-Fitness-Exercise-Analysis>

2. Google AI Edge. *Pose landmark detection guide for Python*. Documentação da
   API MediaPipe Pose Landmarker utilizada na aplicação.
   <https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python>

3. Bazarevsky, V. et al. *BlazePose: On-device Real-time Body Pose Tracking*.
   arXiv:2006.10204, 2020. <https://arxiv.org/abs/2006.10204>

## Observação metodológica

Os modelos Random Forest fornecidos no repositório de Guarnizo et al. não são
utilizados nesta versão. Eles foram treinados com dados próprios de três outros
exercícios. Reaproveitá-los para sentar e levantar produziria classes sem
significado para o nosso problema.

O protótipo atual utiliza ângulos calibrados, média móvel exponencial, filtro de
estabilidade e máquina de estados temporal. Uma comparação futura com modelos
supervisionados exigirá coleta e rotulagem específica de dados de sentar e
levantar.
