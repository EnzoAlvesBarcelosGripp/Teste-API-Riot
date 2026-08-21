import os 
import json
import logging
import pandas as pd

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(SRC_DIR, "05_Load_final")

class Dim_summonerSpell_Error(Exception):
    """Classe base para erros da transformação da Dim_summonerSpell."""
    pass

def _get_latest_version_folder(datadragon_dir: str) -> str:
    """Encontra a subpasta referente à versão/patch mais recente dentro do DataDragon."""
    subdirs = [
        d for d in os.listdir(datadragon_dir) 
        if os.path.isdir(os.path.join(datadragon_dir, d))
    ]

    if not subdirs:
        raise FileNotFoundError(f"Nenhuma pasta de versão encontrada dentro de {datadragon_dir}")

    def parse_version(version_str: str):
        try:
            return tuple(map(int, version_str.split('.')))
        except ValueError:
            return (0, 0, 0)

    latest_version = max(subdirs, key=parse_version)
    return os.path.join(datadragon_dir, latest_version)


def transform_dim_summonerSpell(datadragon_dir: str) -> pd.DataFrame:
    """Lê o summoner.json da versão mais recente e gera a dim_summoner.csv."""
    json_path = None
    try:
        latest_folder = _get_latest_version_folder(datadragon_dir)
        json_path = os.path.join(latest_folder, "summoner.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Arquivo de feitiços não encontrado em: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        logging.info(f"Dim_summoner lendo dados da versão mais recente: {latest_folder}")

        summoner_list = []
        i = 1

        for name_spell, itens in json_data.get('data', {}).items():
            summoner_dict = {
                "sk_summonerspell": i,
                "id": int(itens.get('key', 0)),
                "full": itens.get('image', {}).get('full', '')
            }

            summoner_list.append(summoner_dict)
            i += 1

        logging.info(f'Extração das informações do arquivo {json_path} concluída com sucesso.')

        df_summoner = pd.DataFrame(summoner_list)

        final_path = os.path.join(OUTPUT_DIR, "dim_summoner.csv")
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        df_summoner.to_csv(final_path, index=False)

        return df_summoner

    except Exception as e:
        msg_path = json_path if json_path else datadragon_dir
        logging.error(f'Erro ao transformar dados do summoner spell em {msg_path}: {e}')
        raise Dim_summonerSpell_Error(f"Erro ao transformar dados do summoner spell em {msg_path}: {e}")