import os
import json
import gzip
import logging
import pandas as pd

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(SRC_DIR, "05_Load_final")


class FctPdlHistError(Exception):
    """Classe base para erros da Fct_pdl_hist."""
    pass


class FctPdlHistTransformer:
    """Classe responsável por transformar o histórico de PDLs na Fct_pdl_hist."""

    # Mapeamento hierárquico das ligas e divisões para cálculo do delta
    TIER_ORDER = {
        "IRON": 0, "BRONZE": 1, "SILVER": 2, "GOLD": 3,
        "PLATINUM": 4, "EMERALD": 5, "DIAMOND": 6,
        "MASTER": 7, "GRANDMASTER": 8, "CHALLENGER": 9
    }
    RANK_ORDER = {"IV": 0, "III": 1, "II": 2, "I": 3}

    def __init__(self, transform_dir: str = OUTPUT_DIR):
        self.transform_dir = transform_dir
        self.main_player_map = self._load_main_player_map()

    def _load_main_player_map(self) -> dict:
        """Carrega a Dim_player e cria o dicionário puuid -> sk_player APENAS para contas principais."""
        try:
            player_path = os.path.join(self.transform_dir, "dim_player.csv")
            df_player = pd.read_csv(player_path)

            df_main = df_player[df_player["is_main_account"].astype(str).str.upper() == "TRUE"]
            return dict(zip(df_main["puuid"], df_main["sk_player"]))
        except Exception as e:
            logging.error(f"Erro ao carregar dim_player em {self.transform_dir}: {e}")
            raise FctPdlHistError(f"Falha ao inicializar mapa de jogadores principais: {e}")

    def _get_latest_sk_time(self) -> int:
        """Busca o sk_time mais recente presente na dim_time.csv."""
        time_path = os.path.join(self.transform_dir, "dim_time.csv")
        try:
            df_time = pd.read_csv(time_path)
            return int(df_time["sk_time"].max())
        except Exception as e:
            logging.error(f"Erro ao carregar dim_time em {self.transform_dir}: {e}")
            raise FctPdlHistError(f"Não foi possível obter o sk_time da dim_time: {e}")

    def _to_absolute_pdl(self, tier: str, rank: str, lp: int) -> int:
        """Converte Tier, Rank e LP em uma pontuação absoluta contínua."""
        tier_val = self.TIER_ORDER.get(str(tier).upper(), 0)
        
        # Mestre+ não possui divisões (I, II, III, IV)
        if tier_val >= 7: 
            return (tier_val * 400) + lp
            
        rank_val = self.RANK_ORDER.get(str(rank).upper(), 0)
        return (tier_val * 400) + (rank_val * 100) + lp

    def _calculate_delta_pdl(self, df_pdl: pd.DataFrame) -> pd.DataFrame:
        """Calcula a variação de PDL (delta_pdl) entre sessões cronológicas consecutivas."""
        if df_pdl.empty or len(df_pdl) < 2:
            df_pdl["delta_pdl"] = 0
            return df_pdl

        # Ordenação cronológica estrita
        df_pdl = df_pdl.sort_values(by=["sk_player", "sk_time"], ascending=True).reset_index(drop=True)

        deltas = [0]  # O primeiro registro histórico começa com delta 0

        for i in range(1, len(df_pdl)):
            prev_row = df_pdl.iloc[i - 1]
            curr_row = df_pdl.iloc[i]

            prev_abs = self._to_absolute_pdl(prev_row["tier"], prev_row["rank"], prev_row["leaguePoints"])
            curr_abs = self._to_absolute_pdl(curr_row["tier"], curr_row["rank"], curr_row["leaguePoints"])

            delta = curr_abs - prev_abs
            deltas.append(delta)

        df_pdl["delta_pdl"] = deltas
        return df_pdl

    def transform_pdl_file(self, json_data: dict | list, file_timestamp: str, puuid: str) -> list[dict]:
        """Associa o registro ao sk_time mais recente presente na dim_time."""
        sk_player = self.main_player_map.get(puuid)
        if not sk_player:
            return []

        entries = json_data if isinstance(json_data, list) else [json_data]
        records = []
        latest_sk_time = self._get_latest_sk_time()

        for entry in entries:
            row = {
                "sk_player": sk_player,
                "sk_time": latest_sk_time,  # Chave 100% garantida na dim_time
                "tier": entry.get("tier"),
                "rank": entry.get("rank"),
                "leaguePoints": entry.get("leaguePoints", 0),
                "wins": entry.get("wins", 0),
                "losses": entry.get("losses", 0)
            }
            records.append(row)

        return records


def transform_fct_pdl_hist(pdl_folder_path: str) -> pd.DataFrame:
    """Lê a pasta de históricos de PDL, calcula delta_pdl e gera a Fct_pdl_hist.csv."""
    transformer = FctPdlHistTransformer()
    all_records = []

    try:
        list_dir = os.listdir(pdl_folder_path)
    except Exception as e:
        logging.error(f"Erro ao acessar diretório {pdl_folder_path}: {e}")
        raise FctPdlHistError(f"Erro ao acessar diretório {pdl_folder_path}: {e}")

    for json_file in list_dir:
        if not json_file.endswith(".json.gz"):
            continue    

        file_path = os.path.join(pdl_folder_path, json_file)
        try:
            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                entries = json.load(f)

            filename_clean = json_file.replace(".json.gz", "")
            parts = filename_clean.rsplit("_", 2)

            if len(parts) == 3:
                puuid = parts[0]
                timestamp = f"{parts[1]}_{parts[2]}"
            else:
                continue

            records = transformer.transform_pdl_file(entries, timestamp, puuid)
            all_records.extend(records)

        except Exception as e:
            logging.error(f"Erro ao ler arquivo {json_file}: {e}")

    df_pdl = pd.DataFrame(all_records)

    if not df_pdl.empty:
        # Mantém apenas o último snapshot por sk_time para evitar registros duplicados
        df_pdl = df_pdl.drop_duplicates(subset=["sk_player", "sk_time"], keep="last")
        df_pdl = transformer._calculate_delta_pdl(df_pdl)

    final_path = os.path.join(OUTPUT_DIR, "fct_pdl_hist.csv")
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    df_pdl.to_csv(final_path, index=False)

    logging.info(f"Fct_pdl_hist gerada com sucesso ({len(df_pdl)} registros salvos).")
    return df_pdl