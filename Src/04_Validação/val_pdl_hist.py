import os
import logging
import pandas as pd

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOAD_FINAL_DIR = os.path.join(SRC_DIR, "05_Load_final")


class FctPdlValidationError(Exception):
    """Exceção personalizada para erros de validação na Fato PDL Histórico."""
    pass


class FctPdlValidator:
    def __init__(self, load_dir: str = LOAD_FINAL_DIR):
        self.load_dir = load_dir

    def _read_csv(self, filename: str) -> pd.DataFrame:
        """Lê o arquivo CSV da pasta 05_Load_final e trata erros de leitura."""
        path = os.path.join(self.load_dir, filename)
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Arquivo '{filename}' não encontrado em '{self.load_dir}'.")
            return pd.read_csv(path)
        except Exception as e:
            logging.error(f"Erro ao carregar o arquivo {filename}: {e}")
            raise FctPdlValidationError(f"Falha ao carregar {filename}: {e}")

    def validate_fct_pdl_hist(self) -> None:
        """Executa a suíte de testes de integridade, isolamento e valores da fct_pdl_hist.csv."""
        try:
            df_pdl = self._read_csv("fct_pdl_hist.csv")
            df_player = self._read_csv("dim_player.csv")
            df_time = self._read_csv("dim_time.csv")

            # 1. Validação de Presença de Dados (Tabela Não Vazia)
            if df_pdl.empty:
                raise FctPdlValidationError("A tabela 'fct_pdl_hist.csv' está completamente vazia.")

            # 2. Verifica se todos os registros pertencem à conta principal (is_main_account == True)
            main_player_row = df_player[df_player["is_main_account"].astype(str).str.upper() == "TRUE"]
            if main_player_row.empty:
                raise FctPdlValidationError("Nenhuma conta principal (is_main_account=True) encontrada na dim_player.")

            main_sk = main_player_row["sk_player"].values[0]
            invalid_players = df_pdl[df_pdl["sk_player"] != main_sk]

            if not invalid_players.empty:
                bad_sk = invalid_players["sk_player"].iloc[0]
                raise FctPdlValidationError(
                    f"A fct_pdl_hist contém registros do sk_player={bad_sk}, que não pertence à conta principal."
                )

            # 3. Integridade Referencial Estrita (Chaves Estrangeiras)
            if not df_pdl["sk_player"].isin(df_player["sk_player"]).all():
                raise FctPdlValidationError("A fct_pdl_hist possui 'sk_player' sem correspondência na dim_player.")

            orphan_time_mask = ~df_pdl["sk_time"].isin(df_time["sk_time"])
            if orphan_time_mask.any():
                sample_orphan = df_pdl.loc[orphan_time_mask, "sk_time"].iloc[0]
                total_orphans = df_pdl.loc[orphan_time_mask, "sk_time"].nunique()
                raise FctPdlValidationError(
                    f"A fct_pdl_hist possui {total_orphans} chave(s) 'sk_time' sem correspondência na dim_time "
                    f"(Exemplo de chave órfã: {sample_orphan})."
                )

            # 4. Auditoria de Nulos (Zero Nulos Permitidos)
            mandatory_cols = ["sk_player", "sk_time", "tier", "rank", "leaguePoints"]
            if df_pdl[mandatory_cols].isnull().any().any():
                raise FctPdlValidationError("A fct_pdl_hist possui valores nulos em colunas obrigatórias.")

            # 5. Domínio e Limites de Dados
            valid_tiers = {
                "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
                "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"
            }
            valid_ranks = {"I", "II", "III", "IV"}

            # Valida Tiers
            invalid_tiers = df_pdl[~df_pdl["tier"].astype(str).str.upper().isin(valid_tiers)]
            if not invalid_tiers.empty:
                bad_tier = invalid_tiers["tier"].iloc[0]
                raise FctPdlValidationError(f"Valor de Tier inválido encontrado na fct_pdl_hist: '{bad_tier}'")

            # Valida Ranks
            invalid_ranks = df_pdl[~df_pdl["rank"].astype(str).str.upper().isin(valid_ranks)]
            if not invalid_ranks.empty:
                bad_rank = invalid_ranks["rank"].iloc[0]
                raise FctPdlValidationError(f"Valor de Rank inválido encontrado na fct_pdl_hist: '{bad_rank}'")

            # Valida League Points (PDL >= 0)
            invalid_pdl = df_pdl[df_pdl["leaguePoints"] < 0]
            if not invalid_pdl.empty:
                bad_pdl = invalid_pdl["leaguePoints"].iloc[0]
                raise FctPdlValidationError(f"Valor negativo de PDL encontrado na fct_pdl_hist: {bad_pdl}")

            logging.info(f"✔ fct_pdl_hist: Validada com sucesso ({len(df_pdl)} registros em conformidade).")

        except FctPdlValidationError:
            raise
        except Exception as e:
            logging.error(f"Erro inesperado durante a validação da fct_pdl_hist: {e}")
            raise FctPdlValidationError(f"Falha na validação da fct_pdl_hist: {e}")

    def run_validations(self) -> None:
        """Executa o fluxo de testes da Fato PDL Histórico."""
        logging.info("[HOMOLOGAÇÃO] Validando Fct_Pdl_Hist")
        self.validate_fct_pdl_hist()
        logging.info("[HOMOLOGAÇÃO] Fct_Pdl_Hist Aprovada!FctPdlValidationError")