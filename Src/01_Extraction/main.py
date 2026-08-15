import logging
import os
import json
from Endpoints import RiotAPIClient, RiotAPIError
from datetime import datetime
from Static import DataDragon

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOAD_DIR = os.path.join(SRC_DIR, "02_Load")

def save_json(data: dict | list, folder_path: str, filename: str) -> None:
    """
    Salva os dados retirados do endpoint da Riot Games em um arquivo JSON.
    """
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)    

    logging.info(f"Arquivo JSON salvo em: {file_path}")

def main():
    client = RiotAPIClient()
    
    try:
        puuid = client.get_puuid_by_gamename_tagline()
    except RiotAPIError as e:
        logging.critical(f"Falha ao obter PUUID, encerrando pipeline: {e}")
        return
    try:
        # Extração de dados do endpoint League-V4 usando o PUUID
        league_data = client.get_league_entries_by_puuid(puuid)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        league_folder = os.path.join(LOAD_DIR, "League-V4")
        save_json(league_data, league_folder, f"{puuid}_{timestamp}.json")
    except RiotAPIError as e:
        logging.error(f'falha ao extrair liga, pulando etapa: {e}')
    match_ids = []
    try:
        # Extração de dados do endpoint Match-V5 usando o PUUID
        match_ids = client.get_match_ids_by_puuid(puuid, count=20)
        list_folder = os.path.join(LOAD_DIR, "Match-V5", "listMatchId")
        save_json(match_ids, list_folder, f"{puuid}_matches.json")
    except RiotAPIError as e:
        logging.error(f'falha ao extrair dados da partida, pulando etapa: {e}')


        # loop partidas
    
    for i, match_id in enumerate(match_ids, start=1):
        # Extração de informações detalhadas da partida e do timeline
        try:
            path_info = os.path.join(LOAD_DIR, "Match-V5", "InfoMatch")
            path_timeline = os.path.join(LOAD_DIR, "Match-V5", "TimelineMatch")

            # Verifica se os arquivos já existem antes de salvar
            if os.path.exists(os.path.join(path_info,f"{match_id}_info.json")):
                    logging.info(f"Informações da partida {match_id} já existem. Pulando a extração.")
            else:
                # Extração de informações detalhadas da partida e do timeline 
                info = client.get_match_info_by_matchid(match_id)
                save_json(info, path_info,f"{match_id}_info.json")

            if os.path.exists(os.path.join(path_timeline,f"{match_id}_timeline.json")):
                logging.info(f"Timeline da partida {match_id} já existe. Pulando a extração.")
            else:
               # Extração do timeline completa da partida para depois filtrar até o minuto 15)
                timeline = client.extract_early_game_timeline(match_id, max_minute=15)
                save_json(timeline, path_timeline,f"{match_id}_timeline.json")

        except RiotAPIError as e:
            logging.error(f"Erro ao obter informações da partida {match_id}: {e} | Tentativa: {i} de {len(match_ids)}")
            continue

    # Dados Estáticos
    dragon = DataDragon()
    versions = dragon.get_list_versions()
    if versions: 
        list_folder = os.path.join(LOAD_DIR, "DataDragon")
        save_json(versions, list_folder, "versions.json")
    
    return
if __name__ == "__main__":
    main()