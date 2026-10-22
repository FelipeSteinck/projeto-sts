from __future__ import annotations

import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description='Experimentos STS - EEL7825 / Nível II')
    sub=parser.add_subparsers(dest='command',required=True)
    extract=sub.add_parser('extrair',help='Extrair todos os quadros de um vídeo de taxa constante.')
    extract.add_argument('--video',required=True); extract.add_argument('--saida',required=True)
    extract.add_argument('--sessao',required=True); extract.add_argument('--participante',required=True)
    extract.add_argument('--modelo',default=str(ROOT/'models/pose_landmarker_lite.task'))
    extract.add_argument('--espelhar',action='store_true')
    extract.add_argument('--tipo-dados',choices=('real','sintetico'),default='real')
    training=sub.add_parser('treinar',help='Treino e seleção usando somente grupos de treino.')
    training.add_argument('--manifesto',required=True); training.add_argument('--saida',default=str(ROOT/'models/sts'))
    training.add_argument('--alfas',default='0.25,1'); training.add_argument('--estabilidade',default='1,3')
    training.add_argument('--folds',type=int,default=3)
    evaluation=sub.add_parser('avaliar',help='Avaliar modelos congelados no teste reservado.')
    evaluation.add_argument('--manifesto',required=True); evaluation.add_argument('--modelos',default=str(ROOT/'models/sts'))
    evaluation.add_argument('--saida',default=str(ROOT/'outputs/avaliacao'))
    evaluation.add_argument('--tolerancia-evento',type=float,default=1.)
    demo=sub.add_parser('demo',help='Treinar e avaliar apenas em dados sintéticos identificados.')
    demo.add_argument('--dados',default=str(ROOT/'outputs/demo/dados'))
    demo.add_argument('--modelos',default=str(ROOT/'models/demo'))
    demo.add_argument('--resultados',default=str(ROOT/'outputs/demo/resultados'))
    args=parser.parse_args()
    try:
        if args.command=='extrair':
            from .extracao import extract_video
            result=extract_video(args.video,args.saida,args.sessao,args.participante,args.modelo,args.espelhar,args.tipo_dados)
            print(f'Extração concluída: {result["frames"]} quadros. Rótulos manuais ainda necessários.')
        elif args.command=='treinar':
            from .experimento import train
            result=train(args.manifesto,args.saida,tuple(map(float,args.alfas.split(','))),
                         tuple(map(int,args.estabilidade.split(','))),args.folds)
            print(f'Treino concluído ({result["tipo_dados"]}). Teste reservado não avaliado.')
        elif args.command=='avaliar':
            from .experimento import evaluate
            result=evaluate(args.manifesto,args.modelos,args.saida,args.tolerancia_evento)
            print(f'Avaliação concluída ({result["tipo_dados"]}). Consulte avaliacao.json e as figuras.')
        else:
            from .demo import run_demo
            run_demo(args.dados,args.modelos,args.resultados)
            print('DEMONSTRAÇÃO SINTÉTICA concluída. Não representa desempenho em pessoas.')
    except (ValueError,KeyError,FileNotFoundError) as exc:
        parser.exit(2,f'Erro: {exc}\n')


if __name__=='__main__':
    main()
