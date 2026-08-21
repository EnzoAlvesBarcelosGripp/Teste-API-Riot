import os
import logging
import pandas as pd

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOAD_FINAL_DIR = os.path.join(SRC_DIR, "05_Load_final")


class DimValidationError(Exception):
    """Exceção personalizada para erros de validação em dimensões."""
    pass


class DimValidator:
    def __init__(self, load_dir: str = LOAD_FINAL_DIR):
        self.load_dir = load_dir

    def _read_csv(self, filename: str) -> pd.DataFrame:
        """Lê o arquivo CSV da pasta 05_Load_final e trata erro de ausência."""
        path = os.path.join(self.load_dir, filename)
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Arquivo '{filename}' não encontrado em '{self.load_dir}'.")
            return pd.read_csv(path)
        except Exception as e:
            logging.error(f"Erro ao carregar o arquivo {filename}: {e}")
            raise DimValidationError(f"Falha ao carregar {filename}: {e}")

    def validate_dim_champion(self) -> None:
        """Homologa a dim_champion.csv."""
        try:
            df = self._read_csv("dim_champion.csv")

            # 1. Unicidade das chaves
            if not df["sk_champion"].is_unique:
                raise DimValidationError("dim_champion: Coluna 'sk_champion' possui valores duplicados.")
            if not df["champion_key"].is_unique:
                raise DimValidationError("dim_champion: Coluna 'champion_key' possui valores duplicados.")

            # 2. Ausência de Nulos em qualquer coluna 
            if df[df.columns].isnull().any().any():
                raise DimValidationError("dim_champion: Colunas possuem valores nulos.")

            logging.info("dim_champion: Validada com sucesso.")
        
        except Exception as e:
            logging.error(f"Erro inesperado ao validar dim_champion: {e}")
            raise DimValidationError(f"Falha na validação da dim_champion: {e}")

    def validate_dim_summoner(self) -> None:
        """Homologa a dim_summoner.csv."""
        try:
            df = self._read_csv("dim_summoner.csv")

            # 1. Unicidade das chaves
            if not df["sk_summonerspell"].is_unique:
                raise DimValidationError("dim_summoner: Coluna 'sk_summonerspell' possui valores duplicados.")
            if not df["id"].is_unique:
                raise DimValidationError("dim_summoner: Coluna 'id' (spell key) possui valores duplicados.")

            # 2. Ausência de Nulos
            if df[df.columns].isnull().any().any():
                raise DimValidationError("dim_summoner: Colunas possuem valores nulos.")

            logging.info("dim_summoner: Validada com sucesso.")
        
        except Exception as e:
            logging.error(f"Erro inesperado ao validar dim_summoner: {e}")
            raise DimValidationError(f"Falha na validação da dim_summoner: {e}")

    def validate_dim_style_perks(self) -> None:
        """Homologa a dim_stylePerks.csv."""
        try:
            df = self._read_csv("dim_stylePerks.csv")

            # 1. Unicidade
            if not df["sk_perks"].is_unique:
                raise DimValidationError("dim_stylePerks: Coluna 'sk_perks' possui valores duplicados.")

            # 2. Ausência de Nulos
            if df[df.columns].isnull().any().any():
                raise DimValidationError("dim_stylePerks: Colunas possuem valores nulos.")

            logging.info("dim_stylePerks: Validada com sucesso.")
        
        except Exception as e:
            logging.error(f"Erro inesperado ao validar dim_stylePerks: {e}")
            raise DimValidationError(f"Falha na validação da dim_stylePerks: {e}")

    def validate_dim_player(self) -> None:
        """Homologa a dim_player.csv."""
        try:
            df = self._read_csv("dim_player.csv")

            # 1. Unicidade
            if not df["sk_player"].is_unique:
                raise DimValidationError("dim_player: Coluna 'sk_player' possui valores duplicados.")
            if not df["puuid"].is_unique:
                raise DimValidationError("dim_player: Coluna 'puuid' possui valores duplicados.")

            # 2. Exatamente 1 conta marcada como principal
            main_accounts = df[df["is_main_account"].astype(str).str.upper() == "TRUE"]
            if len(main_accounts) != 1:
                raise DimValidationError(
                    f"dim_player: Esperado exatamente 1 conta principal (is_main_account=True), "
                    f"encontrado: {len(main_accounts)}."
                )

            # 3. Ausência de Nulos em chaves mandatórias
            columns = ["puuid", "sk_player"]
            if df[columns].isnull().any().any():
                raise DimValidationError("dim_player: Colunas 'puuid' ou 'sk_player' possuem valores nulos.")


            logging.info("dim_player: Validada com sucesso (1 conta principal identificada).")
        
        except Exception as e:
            logging.error(f"Erro inesperado ao validar dim_player: {e}")
            raise DimValidationError(f"Falha na validação da dim_player: {e}")

    def validate_dim_time(self) -> None:
        """Homologa a dim_time.csv."""
        try:
            df = self._read_csv("dim_time.csv")

            # 1. Unicidade
            if not df["sk_time"].is_unique:
                raise DimValidationError("dim_time: Coluna 'sk_time' possui valores duplicados.")

            # 2. Ausência de Nulos
            if df[df.columns].isnull().any().any():
                raise DimValidationError("dim_time: Colunas possuem valores nulos.")

            logging.info("dim_time: Validada com sucesso.")
        
        except Exception as e:
            logging.error(f"Erro inesperado ao validar dim_time: {e}")
            raise DimValidationError(f"Falha na validação da dim_time: {e}")

    def validate_dim_info_match(self) -> None:
        """Homologa a dim_info_match.csv."""
        try:
            df = self._read_csv("dim_info_match.csv")

            # 1. Unicidade
            if not df["sk_info_match"].is_unique:
                raise DimValidationError("dim_info_match: Coluna 'sk_info_match' possui valores duplicados.")
            if not df["match_id"].is_unique:
                raise DimValidationError("dim_info_match: Coluna 'match_id' possui valores duplicados.")

            # 2. Ausência de Nulos nas colunas em snake_case
            mandatory_cols = ["sk_info_match", "match_id", "game_duration"]
            if df[mandatory_cols].isnull().any().any():
                raise DimValidationError("dim_info_match: Colunas obrigatórias possuem valores nulos.")

            logging.info("dim_info_match: Validada com sucesso.")

        except Exception as e:
            logging.error(f"Erro inesperado ao validar dim_info_match: {e}")
            raise DimValidationError(f"Falha na validação da dim_info_match: {e}")

    def run_all_dim_validations(self) -> None:
        """Executa a suíte de testes de todas as dimensões."""
        logging.info("[HOMOLOGAÇÃO] Validando Dimensões Base e de Negócio")
        self.validate_dim_champion()
        self.validate_dim_summoner()
        self.validate_dim_style_perks()
        self.validate_dim_player()
        self.validate_dim_time()
        self.validate_dim_info_match()
        logging.info("[HOMOLOGAÇÃO] Todas as Dimensões Aprovadas!")