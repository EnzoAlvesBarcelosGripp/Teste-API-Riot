import os
import pandas as pd
import json
import logging


class Dim_championError(Exception):
    """Classe base para erros da transformação."""
    pass


def transform_dim_champion(json_path) -> pd.DataFrame:
    Error = Dim_championError()

    try:
        with open(json_path,"r",encoding="utf-8") as f:
            data_json = json.load(f)

    except Exception as e:
        logging.error(f'Erro ao abrir ou ler o arquivo JSON em {json_path}:')
        raise Dim_championError(f"Erro ao abrir ou ler o arquivo JSON em {json_path}: {e}")

    try: 
        champion_list = []
        i = 1

        for nome_campeao, detail in data_json.get("data", {}).items():
        # Extrai os dados de 1 campeão
            campeao_dict = {
                "sk_champion": i,  
                "champion_key": int(detail.get("key", 0)),  
                "championName": detail.get("name", ""),  
                "image_full": detail.get("image", {}).get("full", ""),  
                "champion_tags": ", ".join(detail.get("tags", [])),  
            }

            # Adiciona o dicionário na lista
            champion_list.append(campeao_dict)

            i+=1
        logging.info(f'Extração das informações do arquivo {json_path} concluída com sucesso')

        # Cria o DataFrame com a lista completa
        df_champions = pd.DataFrame(champion_list)

        final_path = r"03_Transform/dim_champion.csv"
        df_champions.to_csv(final_path,index=False)

        return df_champions
        
    except Exception as e:
        logging.error(f'Erro ao extrair informação do arquivo {data_json}: ')
        raise Dim_championError(f'Erro ao extrair informação do arquivo {data_json}: {e}')