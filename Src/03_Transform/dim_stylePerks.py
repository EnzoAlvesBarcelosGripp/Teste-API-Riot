import os 
import json
import logging
import pandas as pd

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(SRC_DIR, "04_Load_final")

class Dim_stylePerks_Error(Exception):
    """Classe base para erros da transformação da Dim_stylePerks."""
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


def transform_dim_stylePerks(datadragon_dir: str) -> pd.DataFrame:
    """Lê o runesReforged.json da versão mais recente e gera a dim_stylePerks.csv."""
    json_path = None
    try:
        latest_folder = _get_latest_version_folder(datadragon_dir)
        json_path = os.path.join(latest_folder, "runesReforged.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Arquivo de runas não encontrado em: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        logging.info(f"Dim_stylePerks lendo dados da versão mais recente: {latest_folder}")

        # Json flatten - Style -> Slots -> Runes 
        df_stylePerks = pd.json_normalize(
            json_data, 
            record_path=["slots", "runes"], 
            meta=["id", "icon"], 
            meta_prefix="style_"
        )
        
        df_stylePerks = df_stylePerks.rename(columns={"id": "perk_id", "icon": "perk_icon"})

        cols_order = ["style_id", "perk_id", "style_icon", "perk_icon"]
        df_stylePerks = df_stylePerks[cols_order]

        df_stylePerks.insert(0, "sk_perks", range(1, len(df_stylePerks) + 1))

        final_path = os.path.join(OUTPUT_DIR, "dim_stylePerks.csv")
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        df_stylePerks.to_csv(final_path, index=False)
        
        logging.info(f'Extração das informações do arquivo {json_path} concluída com sucesso.')

        return df_stylePerks
    
    except Exception as e:
        msg_path = json_path if json_path else datadragon_dir
        logging.error(f'Erro ao transformar dados do stylePerks em {msg_path}: {e}')
        raise Dim_stylePerks_Error(f"Erro ao transformar dados do stylePerks em {msg_path}: {e}")