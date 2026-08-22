import os 
import json
import gzip
import logging
import pandas as pd

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(SRC_DIR, "05_Load_final")

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
            if json_file.endswith(".json.gz"):
                file_path = os.path.join(info_folder_path, json_file)

                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    json_data = json.load(f)

                info_data = json_data.get("info", {})

                info_dict = {
                    "sk_info_match": i, 
                    "match_id": json_data.get("metadata", {}).get("matchId"),
                    "game_duration": info_data.get("gameDuration"),
                    "game_version": info_data.get("gameVersion"), 
                    "platform_id": info_data.get("platformId"),
                    "game_ended_in_surrender": info_data.get("gameEndedInSurrender"),
                    "game_ended_in_early_surrender": info_data.get("gameEndedInEarlySurrender")
                }

                info_list.append(info_dict)
                i += 1

        logging.info(f"Extração das informações de {len(info_list)} partidas concluída com sucesso.")

        df_info = pd.DataFrame(info_list)

        final_path = os.path.join(OUTPUT_DIR, "dim_info_match.csv")
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        df_info.to_csv(final_path, index=False)

        return df_info

    except Exception as e:
        logging.error(f"Erro ao transformar dados das partidas: {e}")
        raise Dim_infoMatchError(f"Erro ao transformar dados das partidas: {e}")