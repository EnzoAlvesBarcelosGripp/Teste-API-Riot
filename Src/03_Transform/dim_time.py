import os
import pandas as pd
import json
import logging
import datetime

class dim_timeError (Exception):
    """Classe base para erros da transformação."""

def transform_dim_time(info_folder_path:str) -> pd.DataFrame:
    """Lê os arquivos JSON de InfoMatch e gera a tabela dimensional Dim_time."""

    try:
        list_dir = os.listdir(info_folder_path)
    
    except Exception as e:
        logging.error(f"Erro ao listar o diretório {info_folder_path}: {e}")
        raise dim_timeError(f"Erro ao acessar o diretório {info_folder_path}: {e}")

    try:
        time_list = []

        for json_file in list_dir:
            with open(os.path.join(info_folder_path,json_file),"r",encoding="utf-8") as f:
                json_data = json.load(f)

            game_creation = json_data.get("info",{}).get("gameCreation")

            if game_creation:
                # Converte para o objeto datetime (dividindo ms por 1000)
                dt = datetime.datetime.fromtimestamp(game_creation/1000)

                time_dict = {
                    "sk_time": game_creation, 
                    "year": dt.year,
                    "month": dt.month,
                    "week": dt.isocalendar().week,
                    "day": dt.day,
                    "hour": dt.hour,
                    "minute": dt.minute,
                    "seconds": dt.second,
                }

                time_list.append(time_dict)

        df_time = pd.DataFrame(time_list)

        path_final = "03_Transform/dim_time.csv"
        df_time.to_csv(path_final,index=False)

        return df_time
    
    except Exception as e:
        logging.error(f'Erro ao transformar dados das partidas: {e}')
        raise dim_timeError(f'Erro ao transformar dados das partidas: {e}')