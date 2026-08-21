import os 
import json
import pandas as pd
import logging

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(SRC_DIR, "04_Load_final")

class dim_playerError(Exception):
    """Classe base para erros da transformação."""
    pass

def transform_dim_player(info_folder_path: str) -> pd.DataFrame:
    """Lê os arquivos JSON de InfoMatch e gera a tabela dimensional Dim_player."""

    main_game_name = os.getenv("GAME_NAME")
    main_tag_line = os.getenv("TAG_LINE")

    try:
        list_dir = os.listdir(info_folder_path)

    except Exception as e:
        logging.error(f"Erro ao listar o diretório {info_folder_path}: {e}")
        raise dim_playerError(f"Erro ao acessar o diretório {info_folder_path}: {e}")

    try:
        player_list = []

        for json_file in list_dir:
            if not json_file.endswith(".json"):
                continue

            with open(os.path.join(info_folder_path, json_file), "r", encoding="utf-8") as f:
                json_data = json.load(f)

            info_data = json_data.get('info', {})
            region = info_data.get('platformId', '')
            game_creation = info_data.get('gameCreation', 0)

            # loop interno para extrair as informações de cada participante
            for participant in info_data.get('participants', []):
                g_name = participant.get('riotIdGameName')
                t_line = participant.get('riotIdTagline')

                # Lógica para confirmar qual conta é a principal    
                is_main = False
                if main_game_name and main_tag_line:
                    if str(g_name).lower() == str(main_game_name).lower() and str(t_line).lower() == str(main_tag_line).lower():
                        is_main = True

                player_dict = {
                    "puuid": participant.get('puuid'),
                    "game_name": g_name,
                    "tag_line": t_line,
                    "region": region,
                    "profile_iconId": participant.get('profileIcon'),
                    "gameCreation": game_creation,
                    "is_main_account": is_main
                }
                player_list.append(player_dict)

        logging.info(f"Extração das informações de {len(player_list)} registros concluída com sucesso.")

        df_player = pd.DataFrame(player_list)

        # Ordena por gameCreation para garantir que a última ocorrência seja a mais recente
        df_player = df_player.sort_values("gameCreation")
        df_player = df_player.drop_duplicates(subset=['puuid'], keep='last')

        # Remove a coluna auxiliar de ordenação
        df_player = df_player.drop(columns=['gameCreation'])

        df_player['sk_player'] = range(1, len(df_player) + 1)

        final_path = os.path.join(OUTPUT_DIR, "dim_player.csv")
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        df_player.to_csv(final_path, index=False)

        return df_player

    except Exception as e:
        logging.error(f'Erro ao transformar dados das partidas: {e}')
        raise dim_playerError(f"Erro ao transformar dados das partidas: {e}")