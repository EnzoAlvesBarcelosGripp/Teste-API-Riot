import os 
import json
import logging
import pandas as pd

class Dim_infoMatchError(Exception):
    """Classe base para erros da transformação da Dim_info_match."""
    pass

def transform_dim_info_match(info_folder_path: str) -> pd.DataFrame:
    """Lê os arquivos JSON de InfoMatch e gera a tabela dimensional Dim_info_match."""
    try:
        list_dir = os.listdir(info_folder_path)
    except Exception as e:
        logging.error(f"Erro ao listar o diretório {info_folder_path}: {e}")
        raise Dim_infoMatchError(f"Erro ao acessar o diretório {info_folder_path}: {e}")

    try:
        info_list = []  
        i = 1  

        # loop para cada arquivo dentro do diretório
        for json_file in list_dir:
            if json_file.endswith(".json"):
                file_path = os.path.join(info_folder_path, json_file)

                with open(file_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)

                info_dict = {
                    "sk_match": i, 
                    "match_id": json_data.get("metadata", {}).get("matchId"),
                    "game_creation": json_data.get("info", {}).get("gameCreation"),
                    "game_duration": json_data.get("info", {}).get("gameDuration"),
                    "game_version": json_data.get("info", {}).get("gameVersion"), 
                    "game_mode": json_data.get("info", {}).get("gameMode"),  
                }

                info_list.append(info_dict)
                i += 1

        logging.info(f"Extração das informações de {len(info_list)} partidas concluída com sucesso.")

        df_info = pd.DataFrame(info_list)

        final_path = "03_Transform/dim_info_match.csv"
        df_info.to_csv(final_path, index=False)

        return df_info

    except Exception as e:
        logging.error(f"Erro ao transformar dados das partidas: {e}")
        raise Dim_infoMatchError(f"Erro ao transformar dados das partidas: {e}")