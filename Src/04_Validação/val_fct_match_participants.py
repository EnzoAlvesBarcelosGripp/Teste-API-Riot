import os
import logging
import pandas as pd

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOAD_FINAL_DIR = os.path.join(SRC_DIR, "05_Load_final")

mandatory_cols = [
                # Chaves e Estrutura
                "sk_info_match", "sk_player", "sk_champion", "sk_summoner1", "sk_summoner2",
                "sk_primary_style", "sk_sub_style", "sk_sub_style_2", "sk_time", "teamId",
                # Resultado e Metadados Básicos
                "win", "summonerLevel",
                # Combate, Objetivos e Visão
                "kills", "deaths", "assists", "goldEarned", "totalDamageDealtToChampions",
                "magicDamageDealtToChampions", "physicalDamageDealtToChampions", "trueDamageDealtToChampions",
                "totalDamageTaken", "magicDamageTaken", "physicalDamageTaken", "trueDamageTaken",
                "damageDealtToTurrets", "detectorWardsPlaced", "totalDamageShieldedOnTeammates",
                "totalHealsOnTeammates", "totalTimeSpentDead",
                # Múltiplos Kills e Eventos
                "doubleKills", "tripleKills", "quadraKills", "pentaKills",
                "firstBloodKill", "firstBloodAssist", "firstTowerKill",
                # Challenges
                "controlWardTimeCoverageInRiverOrEnemyHalf", "controlWardsPlaced", "wardTakedowns",
                "soloKills", "junglerKillsEarlyJungle", "killsOnLanersEarlyJungleAsJungler", "epicMonsterSteals",
                # Métricas Derivadas
                "kda", "damagePerMinute", "goldPerMinute", "killParticipation", "teamDamagePercentage"
            ]



class FctMatchParticipantValidationError(Exception):
    """Exceção personalizada para erros de validação da Fato Match Participant."""
    pass


class FctMatchParticipantValidator:
    def __init__(self, load_dir: str = LOAD_FINAL_DIR):
        self.load_dir = load_dir

    def _read_csv(self, filename: str) -> pd.DataFrame:
        """Lê o arquivo CSV da pasta 05_Load_final e trata erros de leitura."""
        path = os.path.join(self.load_dir, filename)
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Arquivo '{filename}' não encontrado em '{self.load_dir}'.")
            return pd.read_csv(path)
        except FctMatchParticipantValidationError as e:
            logging.error(f"Erro ao carregar o arquivo {filename}: {e}")
            raise FctMatchParticipantValidationError(f"Falha ao carregar {filename}: {e}")

    def validate_null_values(self) -> None:
        """Valida a presença de nulos proibidos e a consistência dos nulos esperados nas vantagens de rota."""
        try:
            df_fct = self._read_csv("fct_match_participant.csv")
            df_player = self._read_csv("dim_player.csv")
            df_info = self._read_csv("dim_info_match.csv")

            null_mandatory = df_fct[mandatory_cols].isnull().sum()

            if not null_mandatory[null_mandatory > 0].empty:
                bad_col = null_mandatory[null_mandatory > 0].index[0]
                bad_count = null_mandatory[null_mandatory > 0].iloc[0]
                raise FctMatchParticipantValidationError(f"Coluna mandatória '{bad_col}' possui {bad_count} valores nulos não permitidos.")

            # 2. Validação de Nulos Controlados (Vantagens de Rota aos 15'), em caso da partida não chegar aos 15
            lane_cols = ["laningPhaseGoldAdvantage", "laningPhaseExpAdvantage", "laningPhaseCsAdvantage"]

            # Identifica a sk_player da conta principal e pega sua chave sk
            main_player_row = df_player[df_player["is_main_account"].astype(str).str.upper() == "TRUE"]
            main_sk = main_player_row["sk_player"].values[0]

            # Regra 2A: Contas secundárias NUNCA devem ter vantagens de rota preenchidas
            non_main_df = df_fct[df_fct["sk_player"] != main_sk]
            non_main_nulls = non_main_df[lane_cols].notnull().sum()
            invalid_non_main = non_main_nulls[non_main_nulls > 0]

            if not invalid_non_main.empty:
                bad_col = invalid_non_main.index[0]
                bad_count = invalid_non_main.iloc[0]
                raise FctMatchParticipantValidationError(f"A coluna '{bad_col}' possui {bad_count} registros preenchidos para jogadores que não são a conta principal.")

            # Regra 2B: Conta principal DEVE ter vantagens preenchidas em partidas longas (com tolerância para faltas pontuais da API)
            fct_with_duration = df_fct.merge(df_info[["sk_info_match", "game_duration"]], on="sk_info_match", how="left")
            
            main_long_matches = fct_with_duration[
                (fct_with_duration["sk_player"] == main_sk) & 
                (fct_with_duration["game_duration"] >= 900)
            ]
            
            main_nulls = main_long_matches[lane_cols].isnull().sum()
            
            # Tolerância: Se mais de 5% das partidas de 15m+ estiverem nulas, aponta erro estrutural no pipeline.
            # Se for apenas 1 ou 2 jogos isolados, considera desvio esperado do League/Riot API.
            total_long_matches = len(main_long_matches)
            max_allowed_nulls = max(1, int(total_long_matches * 0.05)) # Tolerância de até 5% das partidas

            for col in lane_cols:
                null_count = main_nulls[col]
                if null_count > max_allowed_nulls:
                    raise FctMatchParticipantValidationError(
                        f"A conta principal possui {null_count} registros nulos na coluna '{col}' "
                        f"em partidas com >= 15 min (Limite tolerado de desvio da API: {max_allowed_nulls})."
                    )

            logging.info("Auditoria de Nulos: Validada com sucesso (Nulos Mandatórios e Vantagens de Rota ok).")

        except FctMatchParticipantValidationError as e:
            logging.error(f"Erro inesperado durante a auditoria de nulos: {e}")
            raise FctMatchParticipantValidationError(f"Falha na auditoria de nulos: {e}")


    def validate_volumetry_and_granularity(self) -> None:
        """
        Valida a proporção de linhas por partida e a distribuição por equipes, nos seguintes pontos:
        1. Se foram lidas 20 partidas e 10 jogadores por partida temos que ter 200 registros.
        2. Para cada partida deve se ter 10 registros com a mesma sk_info_match, simbolizando 10 jogadores.
        3. Verifica se para cada jogador em uma mesma partida e time tem o mesmo N° de integrantes.
        4. Verifica se todos do time estão com o mesmo valor de win.
        5. Verifica se os 2 times de uma mesma partida tem o mesmo valor.
        """
        try:
            df_fct = self._read_csv("fct_match_participant.csv")
            df_info = self._read_csv("dim_info_match.csv")

            total_matches = len(df_info)
            expected_total_rows = total_matches * 10
            actual_total_rows = len(df_fct)

            # 1. Validação do Volume Total (10 participantes por partida)
            if actual_total_rows != expected_total_rows:
                raise FctMatchParticipantValidationError(
                    f"Volume total inconsistente: Esperado {expected_total_rows} linhas "
                    f"({total_matches} partidas x 10), mas foi encontrado {actual_total_rows}."
                )

            # 2. Validação da Contagem Granular por sk_info_match
            match_counts = df_fct["sk_info_match"].value_counts()
            invalid_matches = match_counts[match_counts != 10]

            if not invalid_matches.empty:
                bad_match_id = invalid_matches.index[0]
                bad_count = invalid_matches.iloc[0]
                raise FctMatchParticipantValidationError(f"Partida 'sk_info_match={bad_match_id}' possui {bad_count} participantes (esperado: 10).")

            # 3. Validação do Equilíbrio de Equipes (5 vs 5 por partida)
            teams_group = df_fct.groupby(["sk_info_match", "teamId"])

            teams_per_match = teams_group.size().unstack(fill_value=0)
            
            # Verifica se os times 100 e 200 estão presentes
            if 100 not in teams_per_match.columns or 200 not in teams_per_match.columns:
                raise FctMatchParticipantValidationError("A Fato possui partidas onde teamId 100 ou 200 está ausente.")

            imbalanced_teams = teams_per_match[(teams_per_match[100] != 5) | (teams_per_match[200] != 5)]
            if not imbalanced_teams.empty:
                bad_match_id = imbalanced_teams.index[0]
                raise FctMatchParticipantValidationError(
                    f"Partida 'sk_info_match={bad_match_id}' está desbalanceada. "
                    f"Time 100: {imbalanced_teams.loc[bad_match_id, 100]} jgs, "
                    f"Time 200: {imbalanced_teams.loc[bad_match_id, 200]} jgs."
                )

            logging.info(f"Volumetria & Granularidade: Validada com sucesso ({actual_total_rows} linhas / {total_matches} partidas).")

            # 4. Validação de Consistência da Flag 'win' dentro da Equipe (Deve haver o mesmo valor para todos do mesmo time na mesma partida)
            win_consistency = df_fct.groupby(["sk_info_match", "teamId"])["win"].nunique()
            inconsistent_wins = win_consistency[win_consistency > 1]

            if not inconsistent_wins.empty:
                bad_match_id, bad_team = inconsistent_wins.index[0]
                raise FctMatchParticipantValidationError(f"Partida 'sk_info_match={bad_match_id}', Time {bad_team} possui integrantes com valores divergentes na coluna 'win'.")

            # 5. Validação de Consistência da Flag 'win' dentro entre Equipe (Deve haver exatamente 1 time vencedor e 1 perdedor por partida)
            match_wins = df_fct.groupby(["sk_info_match", "teamId"])["win"].first().unstack()
            
            match_wins[100] = match_wins[100].astype(str).str.upper() == "TRUE"
            match_wins[200] = match_wins[200].astype(str).str.upper() == "TRUE"

            invalid_match_results = match_wins[match_wins[100] == match_wins[200]]
            if not invalid_match_results.empty:
                bad_match_id = invalid_match_results.index[0]
                raise FctMatchParticipantValidationError(f"Partida 'sk_info_match={bad_match_id}' possui resultado inválido: ambos os times possuem win={match_wins.loc[bad_match_id, 100]}.")

            logging.info(f"Volumetria, Equipes & Resultado (win): Validados com sucesso ({actual_total_rows} linhas / {total_matches} partidas).")
            
        except FctMatchParticipantValidationError as e:
            logging.error(f"Erro inesperado ao validar volumetria e granularidade: {e}")
            raise FctMatchParticipantValidationError(f"Falha na validação de volumetria: {e}")

    def validate_referential_integrity(self) -> None:
        """Valida se todas as Foreign Keys (SKs) na Fato possuem correspondência nas tabelas dimensionais."""
        try:
            df_fct = self._read_csv("fct_match_participant.csv")

            fk_mappings = {
                "sk_info_match": ("dim_info_match.csv", "sk_info_match"),
                "sk_player": ("dim_player.csv", "sk_player"),
                "sk_champion": ("dim_champion.csv", "sk_champion"),
                "sk_summoner1": ("dim_summoner.csv", "sk_summonerspell"),
                "sk_summoner2": ("dim_summoner.csv", "sk_summonerspell"),
                "sk_primary_style": ("dim_stylePerks.csv", "sk_perks"),
                "sk_sub_style": ("dim_stylePerks.csv", "sk_perks"),
                "sk_sub_style_2": ("dim_stylePerks.csv", "sk_perks"),
                "sk_time": ("dim_time.csv", "sk_time"),
            }

            for fk_col, (dim_file, sk_col) in fk_mappings.items():
                df_dim = self._read_csv(dim_file)

                # Busca todas as chaves da Fato que não existem na Dimensão
                orphan_mask = ~df_fct[fk_col].isin(df_dim[sk_col])
                
                if orphan_mask.any():
                    sample_orphan = df_fct.loc[orphan_mask, fk_col].iloc[0]
                    total_orphans = df_fct.loc[orphan_mask, fk_col].nunique()
                    
                    raise FctMatchParticipantValidationError(
                        f"Integridade Referencial violada na coluna '{fk_col}': "
                        f"Encontrado {total_orphans} chave(s) órfã(s) sem correspondência em '{dim_file}' "
                        f"(Exemplo de chave órfã: {sample_orphan})."
                    )

            logging.info(f"Integridade Referencial: Validada com sucesso (100% das SKs mapeadas nas Dimensões).")

        except FctMatchParticipantValidationError as e:
            logging.error(f"Erro inesperado ao validar integridade referencial: {e}")
            raise FctMatchParticipantValidationError(f"Falha na validação de integridade referencial: {e}")

    def validate_metrics_sanity(self) -> None:
        """Audita a consistência matemática, fórmulas derivadas e limites aceitáveis das métricas."""
        try:
            df_fct = self._read_csv("fct_match_participant.csv")

            # 1. Validação de Porcentagens (0.0 <= x <= 1.0)
            pct_cols = ["killParticipation", "teamDamagePercentage"]
            for col in pct_cols:
                invalid_pct = df_fct[(df_fct[col] < 0.0) | (df_fct[col] > 1.0)]
                if not invalid_pct.empty:
                    bad_val = invalid_pct[col].iloc[0]
                    raise FctMatchParticipantValidationError(f"Coluna de porcentagem '{col}' possui valor fora do limite [0.0, 1.0]: {bad_val}")

            # 2. Validação de Taxas por Minuto (DPM e GPM devem ser estritamente positivos)
            rate_cols = ["damagePerMinute", "goldPerMinute"]
            for col in rate_cols:
                invalid_rates = df_fct[df_fct[col] < 0]
                if not invalid_rates.empty:
                    bad_val = invalid_rates[col].iloc[0]
                    raise FctMatchParticipantValidationError(
                        f"Coluna de taxa '{col}' possui valor menor ou igual a zero: {bad_val}"
                    )

            # 3. Validação Matemática da Fórmula do KDA: (Kills + Assists) / max(1, Deaths)
            expected_kda = (
                (df_fct["kills"] + df_fct["assists"]) / df_fct["deaths"].clip(lower=1)
            ).round(2)
            
            # Compara com tolerância de arredondamento de 0.01
            kda_diff = (df_fct["kda"] - expected_kda).abs()
            invalid_kda = df_fct[kda_diff > 0.01]

            if not invalid_kda.empty:
                bad_row = invalid_kda.iloc[0]
                raise FctMatchParticipantValidationError(
                    f"Divergência no cálculo do KDA para sk_info_match={bad_row['sk_info_match']}, "
                    f"sk_player={bad_row['sk_player']}: Armazenado={bad_row['kda']}, Esperado={expected_kda.loc[bad_row.name]}"
                )

            # 4. Auditoria de Valores Negativos Inesperados (Métricas de combate e visão devem ser >= 0)
            non_negative_cols = [
                "kills", "deaths", "assists", "goldEarned", "totalDamageDealtToChampions",
                "totalDamageTaken", "detectorWardsPlaced", "controlWardsPlaced", "wardTakedowns"
            ]
            for col in non_negative_cols:
                invalid_negatives = df_fct[df_fct[col] < 0]
                if not invalid_negatives.empty:
                    bad_val = invalid_negatives[col].iloc[0]
                    raise FctMatchParticipantValidationError(
                        f"Coluna '{col}' possui valor negativo não permitido: {bad_val}"
                    )

            logging.info("Sanidade de Métricas: Validada com sucesso (KDA, DPM, GPM, % KP e % Dano em conformidade).")

        except FctMatchParticipantValidationError as e:
            logging.error(f"Erro inesperado durante a validação de sanidade de métricas: {e}")
            raise FctMatchParticipantValidationError(f"Falha na validação de métricas: {e}")    

    def run_validations(self) -> None:
        """Executa o fluxo completo de testes da Fato Match Participant."""
        logging.info("[HOMOLOGAÇÃO] Validando Fct_Match_Participant")
        self.validate_volumetry_and_granularity()
        self.validate_referential_integrity()
        self.validate_null_values()
        self.validate_metrics_sanity()
        logging.info("[HOMOLOGAÇÃO] Fct_Match_Participant Aprovada!")