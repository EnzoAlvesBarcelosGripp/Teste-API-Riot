import os 
import json
import pandas as pd
import logging

class dim_playerError(Exception):
    """Classe base para erros da transformação."""
    pass

def transform_dim_player(info_folder_path:str) -> pd.DataFrame:
    """Lê os arquivos JSON de InfoMatch e gera a tabela dimensional Dim_player."""

    try:
        list_dir = os.listdir(info_folder_path)

    except Exception as e:
            logging.error(f"Erro ao listar o diretório {info_folder_path}: {e}")
            raise dim_playerError(f"Erro ao acessar o diretório {info_folder_path}: {e}")

    try:
        player_list = []

        for json_file in list_dir:
            with open(os.path.join(info_folder_path,json_file)) as f:
                json_data = json.load(f)

            region = json_data.get('info',{}).get('platformId','')

            # loop interno para extrair as informações de cada participante
            for participant in json_data.get('info',{}).get('participants',[]):
                 player_dict = {
                      "puuid": participant.get('puuid'),
                      "game_name": participant.get('riotIdGameName'),
                      "tag_line": participant.get('riotIdTagline'),
                      "region": region,
                      "profile_iconId": participant.get('profileIcon')
                 }
                 player_list.append(player_dict)
        logging.info(f"Extração das informações de {len(player_list)} partidas concluída com sucesso.")

        df_player = pd.DataFrame(player_list)

        # como jogadores podem aparecer em mais de uma partida 
        # será mantido apenas as informações (nome,tag e icone) mais recente
        df_player = df_player.drop_duplicates(subset=['puuid'])

        df_player['sk_player'] = range(1,len(df_player) + 1)

        final_path = "03_Transform/dim_player.csv"
        df_player.to_csv(final_path, index=False)

        return df_player

    except Exception as e:
        logging.error(f'Erro ao transformar dados das partidas: {e}')
        raise dim_playerError(f"Erro ao transformar dados das partidas: {e}")