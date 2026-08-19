import os 
import json
import logging
import pandas as pd

class Dim_summonerSpell_Error(Exception):
    """Classe base para erros da transformação"""

def transform_dim_summoner(json_path) -> pd.DataFrame:
    Error = Dim_summonerSpell_Error()

    try:
        with open(json_path,"r",encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as e:
        logging.error(f'Erro ao abrir ou ler o arquivo JSON em {json_path}:')
        raise Dim_summonerSpell_Error(f"Erro ao abrir ou ler o arquivo JSON em {json_path}: {e}")
        
    try: 
        sumooner_list = []

        i = 1

        for itens in json_data.get('data',{}).items():
            summoner_dict={
                "sk_sumonner": i,
                "id": int(itens.get('key')),
                "full": itens.get('image',{}).get('full')
            }

            # adiciona o dicionario na lista
            sumooner_list.append(summoner_dict)

            i+=1
        logging.info(f'Extração das informações do arquivo {json_path} concluída com sucesso')

        # Cria o DataFrame das summoners
        df_summoner = pd.DataFrame(sumooner_list)

        final_path = r"03_Transform/dim_summoner.csv"
        df_summoner.to_csv(final_path,index=False)

        return df_summoner
    except Exception as e:
        logging.error(f'Erro ao transformar dados do summoner spell')
        raise Dim_summonerSpell_Error(f"Erro ao transformar dados do summoner spell: {e}")