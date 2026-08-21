import os
import json
import logging
import pandas as pd

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(SRC_DIR, "04_Load_final")

class FctMatchParticipantError(Exception):
    """Classe base para erros da Fct_match_participant."""
    pass

class FctMatchParticipantTransformer:
    """Classe responsável por transformar os JSONs de partidas na Fct_match_participant."""

    def __init__(self, transform_dir: str = OUTPUT_DIR):
        self.transform_dir = transform_dir
        self.dim_maps = self._load_dimension_maps()
        self.dim_player_main_map = self._load_main_player_map()

    def _load_main_player_map(self) -> dict:
        """Mapeia a sk_player para a flag is_main_account."""
        try:
            df_player = pd.read_csv(os.path.join(self.transform_dir, "dim_player.csv"))
            return dict(zip(df_player["sk_player"], df_player["is_main_account"]))
        except Exception as e:
            logging.error(f"Erro ao carregar mapa de conta principal: {e}")
            return {}

    def _load_dimension_maps(self) -> dict:
        """Carrega os CSVs dimensionais e constrói os dicionários hash para busca O(1)."""
        try:
            df_info = pd.read_csv(os.path.join(self.transform_dir, "dim_info_match.csv"))
            df_player = pd.read_csv(os.path.join(self.transform_dir, "dim_player.csv"))
            df_champion = pd.read_csv(os.path.join(self.transform_dir, "dim_champion.csv"))
            df_summoner = pd.read_csv(os.path.join(self.transform_dir, "dim_summoner.csv"))
            df_perks = pd.read_csv(os.path.join(self.transform_dir, "dim_stylePerks.csv"))

            return {
                "match": dict(zip(df_info["match_id"], df_info["sk_info_match"])),
                "player": dict(zip(df_player["puuid"], df_player["sk_player"])),
                "champion": dict(zip(df_champion["champion_key"], df_champion["sk_champion"])),
                "summoner": dict(zip(df_summoner["id"], df_summoner["sk_summonerspell"])),
                "perks": {(sid, pid): sk for sid, pid, sk in zip(df_perks["style_id"], df_perks["perk_id"], df_perks["sk_perks"])},
            }
        except Exception as e:
            logging.error(f"Erro ao carregar mapas dimensionais de {self.transform_dir}: {e}")
            raise FctMatchParticipantError(f"Falha ao inicializar mapas de dimensões: {e}")

    def _calculate_kda(self, kills: int, assists: int, deaths: int) -> float:
        """Calcula a razão de KDA (Kills + Assists) / max(1, Deaths). ->  max(1, Deaths), evita a divisão por 0"""
        deaths_adjusted = max(1, deaths)
        return round((kills + assists) / deaths_adjusted, 2)

    def _calculate_per_minute(self, total_value: float, game_duration_seconds: int) -> float:
        """Função genérica para calcular taxas por minuto (DPM, GPM, etc.)."""
        if not game_duration_seconds or game_duration_seconds <= 0:
            return 0.0
        
        duration_in_minutes = game_duration_seconds / 60.0
        return round(total_value / duration_in_minutes, 2)

    def _calculate_dpm(self, total_damage: int, game_duration_seconds: int) -> float:
        """Calcula o Dano Por Minuto (DPM)."""
        return self._calculate_per_minute(total_damage, game_duration_seconds)

    def _calculate_gpm(self, total_gold: int, game_duration_seconds: int) -> float:
        """Calcula o Ouro Por Minuto (GPM)."""
        return self._calculate_per_minute(total_gold, game_duration_seconds)

    def _calculate_team_share(self, player_value: float, team_total_value: float) -> float:
        """Função genérica para calcular a participação do jogador no total da equipe."""
        if not team_total_value or team_total_value <= 0:
            return 0.0
        
        return round(player_value / team_total_value, 4)

    def _calculate_kill_participation(self, kills: int, assists: int, team_total_kills: int) -> float:
        """Calcula a Porcentagem de Participação em Abates (KP)."""
        player_kills_participation = kills + assists
        return self._calculate_team_share(player_kills_participation, team_total_kills)

    def _calculate_team_damage_percentage(self, player_damage: int, team_total_damage: int) -> float:
        """Calcula a Porcentagem do Dano Total da Equipe."""
        return self._calculate_team_share(player_damage, team_total_damage)

    def _extract_15min_stats(self, timeline_json: dict) -> dict:
        """Varre o JSON da timeline e extrai os stats aos 15 minutos."""
        if not timeline_json:
            return {}

        frames = timeline_json.get("info", {}).get("frames", [])
        if not frames:
            return {}

        # Alvo: 15 minutos (900.000 ms)
        target_ms = 15 * 60 * 1000
        closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - target_ms))

        participant_frames = closest_frame.get("participantFrames", {})
        stats_15m = {}

        for pid_str, p_data in participant_frames.items():
            pid = int(pid_str)
            minions = p_data.get("minionsKilled", 0)
            jungle_minions = p_data.get("jungleMinionsKilled", 0)
            
            stats_15m[pid] = {
                "gold": p_data.get("totalGold", 0),
                "xp": p_data.get("xp", 0),
                "cs": minions + jungle_minions
            }

        return stats_15m

    def _calculate_laning_advantages(self, participant_id: int, is_main_account: bool,participants_info: list, stats_15m: dict) -> dict:
        """Calcula as vantagens de fase de rotas apenas se for a conta principal (is_main_account == True)."""
        default_advantages = {
            "laningPhaseGoldAdvantage": None, # valor nulo
            "laningPhaseExpAdvantage": None,
            "laningPhaseCsAdvantage": None
        }

        # Trava: Executa os cálculos avançados apenas para a sua conta principal
        if not is_main_account or not stats_15m or participant_id not in stats_15m:
            return default_advantages

        # Localiza as informações do jogador principal
        current_p = next((p for p in participants_info if p.get("participantId") == participant_id), None)
        if not current_p:
            return default_advantages

        team_id = current_p.get("teamId")
        position = current_p.get("individualPosition")

        # Se a posição for inválida ou vazia (ex: remakes ou jogos atípicos), não há confronto de rota
        if not position or position in ["Invalid", ""]:
            return default_advantages

        # Procura o rival de rota (Time oposto + Mesma posição)
        opponent = next((
            p for p in participants_info 
            if p.get("teamId") != team_id and p.get("individualPosition") == position
        ), None)

        if not opponent or opponent.get("participantId") not in stats_15m:
            return default_advantages

        opponent_id = opponent.get("participantId")

        # Resgata os atributos aos 15' do jogador principal e do seu rival
        p_stats = stats_15m[participant_id]
        opp_stats = stats_15m[opponent_id]

        return {
            "laningPhaseGoldAdvantage": p_stats["gold"] - opp_stats["gold"],
            "laningPhaseExpAdvantage": p_stats["xp"] - opp_stats["xp"],
            "laningPhaseCsAdvantage": p_stats["cs"] - opp_stats["cs"]
        }

    def _get_style_selection(self, styles: list, description: str, selection_index: int = 0) -> tuple[int | None, int | None]:
        """
        Localiza a árvore de runas (primaryStyle ou subStyle) pela descrição
        e retorna (style_id, perk_id) da seleção no índice indicado dessa árvore.
        """
        style_entry = next((s for s in styles if s.get("description") == description), None)
        if not style_entry:
            return None, None

        style_id = style_entry.get("style")
        selections = style_entry.get("selections", [])
        perk_id = selections[selection_index].get("perk") if len(selections) > selection_index else None

        return style_id, perk_id

    def extract_derived_metrics(self, participant: dict, json_data: dict, is_main_account: bool,stats_15m: dict) -> dict:
        """Orquestra e calcula todas as métricas derivadas do participante na partida."""
        
        info_data = json_data.get("info", {})
        participants_info = info_data.get("participants", [])
        game_duration_seconds = info_data.get("gameDuration", 0)

        # 1. Atributos do jogador atual
        kills = participant.get("kills", 0)
        deaths = participant.get("deaths", 0)
        assists = participant.get("assists", 0)
        player_damage = participant.get("totalDamageDealtToChampions", 0)
        player_gold = participant.get("goldEarned", 0)
        team_id = participant.get("teamId")
        participant_id = participant.get("participantId")

        # 2. Totais da equipe do jogador para KP e % Dano
        team_participants = [p for p in participants_info if p.get("teamId") == team_id]
        team_total_kills = sum(p.get("kills", 0) for p in team_participants)
        team_total_damage = sum(p.get("totalDamageDealtToChampions", 0) for p in team_participants)

        # 3. Métricas Básicas e de Equipe
        kda = self._calculate_kda(kills, assists, deaths)
        dpm = self._calculate_dpm(player_damage, game_duration_seconds)
        gpm = self._calculate_gpm(player_gold, game_duration_seconds)
        kp = self._calculate_kill_participation(kills, assists, team_total_kills)
        team_dmg_pct = self._calculate_team_damage_percentage(player_damage, team_total_damage)

        # 4. Métricas de Rotas (Timeline aos 15') - Calculadas apenas se is_main_account == True
        laning_advantages = self._calculate_laning_advantages(
            participant_id=participant_id,
            is_main_account=is_main_account,
            participants_info=participants_info,
            stats_15m=stats_15m
        )

        return {
            "kda": kda,
            "damagePerMinute": dpm,
            "goldPerMinute": gpm,
            "killParticipation": kp,
            "teamDamagePercentage": team_dmg_pct,
        } | laning_advantages

    def extract_match_level_data(self, json_data: dict) -> dict:
        """Extrai metadados do nível da partida (raiz/info do JSON)."""
        match_id = json_data.get("metadata", {}).get("matchId")
        game_creation = json_data.get("info", {}).get("gameCreation")
    
        return {
            "sk_info_match": self.dim_maps["match"].get(match_id),
            "sk_time": game_creation,
            "gameCreation": game_creation
        }

    
    def extract_participant_level_data(self, participant: dict) -> dict:
        """Extrai atributos do jogador/participante (dentro da lista info.participants)."""
        
        # 1. Jogador (puuid -> sk_player)
        puuid = participant.get("puuid")
        sk_player = self.dim_maps["player"].get(puuid)

        # 2. Campeão (championID -> sk_champion)
        champion_id = participant.get("championId")
        sk_champion = self.dim_maps["champion"].get(champion_id)

        # 3. Feitiços de Invocador (Summoner Spells)
        # Como há 2 feitiços por jogador há 2 chaves
        # summoner (summonerId -> sk_summonerspell)
        summoner1_id = participant.get("summoner1Id")
        summoner2_id = participant.get("summoner2Id")
        sk_summoner1 = self.dim_maps["summoner"].get(summoner1_id)
        sk_summoner2 = self.dim_maps["summoner"].get(summoner2_id)

        # 4. Estilos de Runas (Primary e as 2 escolhas do Sub Style)
        styles = participant.get("perks", {}).get("styles", [])

        primary_style_id, primary_perk_id = self._get_style_selection(styles, "primaryStyle", 0)
        sub_style_id, sub_perk_id = self._get_style_selection(styles, "subStyle", 0)
        sub_style_id_2, sub_perk_id_2 = self._get_style_selection(styles, "subStyle", 1)

        sk_primary_style = self.dim_maps["perks"].get((primary_style_id, primary_perk_id))
        sk_sub_style = self.dim_maps["perks"].get((sub_style_id, sub_perk_id))
        sk_sub_style_2 = self.dim_maps["perks"].get((sub_style_id_2, sub_perk_id_2))

        return {
            # Chaves
            "sk_player": sk_player,
            "sk_champion": sk_champion,
            "sk_primary_style": sk_primary_style, 
            "sk_sub_style": sk_sub_style, 
            "sk_sub_style_2": sk_sub_style_2,
            "sk_summoner1": sk_summoner1,
            "sk_summoner2": sk_summoner2,

            # Combate 
            "assists": participant.get("assists", 0),
            "deaths": participant.get("deaths", 0),

            # Objetivos
            "damageDealtToTurrets": participant.get("damageDealtToTurrets", 0),

            # Visão
            "detectorWardsPlaced": participant.get("detectorWardsPlaced", 0),

            # Gold
            "goldEarned": participant.get("goldEarned", 0),

            # Múltiplos kills
            "doubleKills": participant.get("doubleKills", 0),
            "tripleKills": participant.get("tripleKills", 0),
            "quadraKills": participant.get("quadraKills", 0),
            "pentaKills": participant.get("pentaKills", 0),

            # Eventos booleanos
            "firstBloodAssist": participant.get("firstBloodAssist", False),
            "firstBloodKill": participant.get("firstBloodKill", False),
            "firstTowerKill": participant.get("firstTowerKill", False),
            "win": participant.get("win", False),

            # Tipos de Totais (Dano, Dano recebido, Escudo, cura, tempo morto)
            "magicDamageDealtToChampions": participant.get("magicDamageDealtToChampions", 0),
            "magicDamageTaken": participant.get("magicDamageTaken", 0),
            "physicalDamageDealtToChampions": participant.get("physicalDamageDealtToChampions", 0),
            "physicalDamageTaken": participant.get("physicalDamageTaken", 0),
            "trueDamageDealtToChampions": participant.get("trueDamageDealtToChampions", 0),
            "trueDamageTaken": participant.get("trueDamageTaken", 0),
            "totalDamageDealtToChampions": participant.get("totalDamageDealtToChampions", 0),
            "totalDamageTaken": participant.get("totalDamageTaken", 0),
            "totalDamageShieldedOnTeammates": participant.get("totalDamageShieldedOnTeammates", 0),
            "totalHealsOnTeammates": participant.get("totalHealsOnTeammates", 0),
            "totalTimeSpentDead": participant.get("totalTimeSpentDead", 0),

            # Informação da equipe
            "teamId": participant.get("teamId", 0),

            # Informação individual
            "summonerLevel": participant.get("summonerLevel", 0),


        }

    def _extract_challenges_data(self, participant: dict) -> dict:
        """Extrai com segurança as métricas contidas no sub-dicionário 'challenges'."""
        challenges = participant.get("challenges", {})
        
        # Garante tratamento seguro caso challenges seja None em partidas antigas
        if not isinstance(challenges, dict):
            challenges = {}

        return {
            # Visão
            "controlWardTimeCoverageInRiverOrEnemyHalf": challenges.get("controlWardTimeCoverageInRiverOrEnemyHalf", 0.0),
            "controlWardsPlaced": challenges.get("controlWardsPlaced", 0),
            "wardTakedowns": challenges.get("wardTakedowns", 0),

            # Kills
            "soloKills": challenges.get("soloKills", 0),
            "junglerKillsEarlyJungle": challenges.get("junglerKillsEarlyJungle", 0),
            "killsOnLanersEarlyJungleAsJungler": challenges.get("killsOnLanersEarlyJungleAsJungler", 0),

            # Objetivos
            "epicMonsterSteals": challenges.get("epicMonsterSteals", 0),
        }

    def transform_match(self, match_json: dict, timeline_json: dict | None = None) -> list[dict]:
        """Transforma um único JSON de partida e timeline em linhas da Fato."""
        match_meta = self.extract_match_level_data(match_json)
        info_data = match_json.get("info", {})
        participants = info_data.get("participants", [])

        stats_15m = self._extract_15min_stats(timeline_json) if timeline_json else {}
        rows = []

        for participant in participants:
            puuid = participant.get("puuid")
            sk_player = self.dim_maps["player"].get(puuid)
            is_main = self.dim_player_main_map.get(sk_player, False) if sk_player else False

            part_data = self.extract_participant_level_data(participant)
            challenges_data = self._extract_challenges_data(participant)
            derived_data = self.extract_derived_metrics(
                participant=participant,
                json_data=match_json,
                is_main_account=is_main,
                stats_15m=stats_15m
            )

            row = match_meta | part_data | challenges_data | derived_data
            rows.append(row)

        return rows

def transform_fct_match_participant(matches_folder: str, timelines_folder: str | None = None) -> pd.DataFrame:
    """Função orquestradora chamada pelo main.py para partidas."""
    # Instancia a classe CORRETA para partidas
    transformer = FctMatchParticipantTransformer()
    all_rows = []

    try:
        list_files = os.listdir(matches_folder)
    except Exception as e:
        logging.error(f"Erro ao acessar diretório de partidas em {matches_folder}: {e}")
        raise FctMatchParticipantError(f"Falha ao acessar diretório {matches_folder}: {e}")

    for json_file in list_files:
        if not json_file.endswith(".json"):
            continue

        match_path = os.path.join(matches_folder, json_file)
        try:
            with open(match_path, "r", encoding="utf-8") as f:
                match_json = json.load(f)

            timeline_json = None
            if timelines_folder:
                match_id = json_file.replace("_info.json", "")
                timeline_filename = f"{match_id}_timeline.json"
                timeline_path = os.path.join(timelines_folder, timeline_filename)

                if os.path.exists(timeline_path):
                    with open(timeline_path, "r", encoding="utf-8") as f:
                        timeline_json = json.load(f)

            # Chama o método que pertence à classe FctMatchParticipantTransformer
            match_rows = transformer.transform_match(match_json, timeline_json)
            all_rows.extend(match_rows)

        except Exception as e:
            logging.error(f"Erro ao processar arquivo de partida {json_file}: {e}")

    df_fct = pd.DataFrame(all_rows)

    final_path = os.path.join(OUTPUT_DIR, "fct_match_participant.csv")
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    df_fct.to_csv(final_path, index=False)

    logging.info(f"Fct_match_participant gerada com sucesso ({len(df_fct)} linhas) em {final_path}.")
    return df_fct