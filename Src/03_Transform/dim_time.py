import os
import json
import logging
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(SRC_DIR, "04_Load_final")

load_dotenv() # estava causando conflito .env.example

class dim_timeError(Exception):
    """Classe base para erros da transformação."""
    pass

def transform_dim_time(info_folder_path: str) -> pd.DataFrame:
    """Lê os arquivos JSON de InfoMatch e gera a tabela dimensional Dim_time."""

    tz_env = os.getenv("TIMEZONE")
    try:
        if tz_env:
            pass
    except ZoneInfoNotFoundError as e:
            raise dim_timeError(f"A variável de ambiente TIMEZONE não está definida no .env: {e}")
    try:
        target_tz = ZoneInfo(tz_env)
    except ZoneInfoNotFoundError as e:
        raise dim_timeError(f"Fuso horário inválido configurado na variável TIMEZONE: '{tz_env}'. Informe uma string IANA válida (ex: 'America/Sao_Paulo'): {e}")

    try:
        list_dir = os.listdir(info_folder_path)
    except Exception as e:
        logging.error(f"Erro ao listar o diretório {info_folder_path}: {e}")
        raise dim_timeError(f"Erro ao acessar o diretório {info_folder_path}: {e}")

    try:
        time_list = []

        for json_file in list_dir:
            if not json_file.endswith(".json"):
                continue

            with open(os.path.join(info_folder_path, json_file), "r", encoding="utf-8") as f:
                json_data = json.load(f)

            game_creation = json_data.get("info", {}).get("gameCreation")

            if game_creation:
                # Converte epoch em milissegundos para datetime UTC e aplica o fuso correto
                dt_utc = datetime.fromtimestamp(game_creation / 1000, tz=timezone.utc)
                dt_local = dt_utc.astimezone(target_tz)

                time_dict = {
                    "sk_time": game_creation, # mantem epoch em milissegundos 
                    "year": dt_local.year,
                    "month": dt_local.month,
                    "day": dt_local.day,
                    "hour": dt_local.hour,
                    "minute": dt_local.minute,
                    "seconds": dt_local.second,
                }

                time_list.append(time_dict)

        df_time = pd.DataFrame(time_list)

        path_final = os.path.join(OUTPUT_DIR, "dim_time.csv")
        os.makedirs(os.path.dirname(path_final), exist_ok=True)
        df_time.to_csv(path_final, index=False)

        return df_time
    
    except Exception as e:
        logging.error(f'Erro ao transformar dados das partidas: {e}')
        raise dim_timeError(f'Erro ao transformar dados das partidas: {e}')