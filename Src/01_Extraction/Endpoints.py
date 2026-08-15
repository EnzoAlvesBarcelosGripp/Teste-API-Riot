import time
import requests
import os
from dotenv import load_dotenv, find_dotenv
from urllib.parse import quote
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class RiotAPIError(Exception):
    """Classe base para erros da API da Riot Games."""
    pass


class RiotAPIClient:

    def __init__(self):
        load_dotenv(find_dotenv())
        self.region = os.getenv('SERVER_REGION')
        self.plataform = os.getenv('PLATAFORM') 
        self.api_key = os.getenv('RIOT_API_KEY')
        self.headers = {'X-Riot-Token': self.api_key}
        self.base_url = f'https://{self.region}.api.riotgames.com'
        self.base_url_br = f'https://{self.plataform}.api.riotgames.com'

    def _request(self, url: str, params: dict | None = None, attempt: int = 1) -> dict | list:
        """
        Executa a requisição para a API da Riot Games e retorna o resultado em formato JSON.
        Caso ocorra algum erro, retorna chama a função de tratamento de erros.
        """
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):  # Tenta no máximo 3 vezes
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                logging.warning(f"Erro 429 - Tentativa {attempt} | {max_attempts}: Aguardando {retry_after}s...")
                time.sleep(retry_after)
            else:
                # Trata todos os outros erros (400, 401, 404, 500, etc.)
                logging.error(f"Erro {response.status_code}: Requisição falhou para a URL: {url}.")
                raise RiotAPIError(f"Erro {response.status_code}: Requisição falhou para a URL: {url}.")
        raise RiotAPIError(f"Erro 429: Número máximo de tentativas ({max_attempts}) atingido para: {url}.")

    def get_puuid_by_gamename_tagline (self, gamename: str | None = None, tagline: str | None = None) -> str:
        """
        Obtém o PUUID (Player Universally Unique Identifier) de um jogador usando seu gamename e tagline.
        Se gamename e tagline não forem fornecidos, eles serão obtidos do arquivo .env.
        Retorna o PUUID como string se encontrado, caso contrário retorna None.
        """
        gamename = gamename or os.getenv('GAME_NAME')   
        tagline = tagline or os.getenv('TAG_LINE')

        gamename = quote(gamename) 
        tagline = quote(tagline)


        url = f"{self.base_url}/riot/account/v1/accounts/by-riot-id/{gamename}/{tagline}"
        response = self._request(url)

        if response and 'puuid' in response:
            return response['puuid']
        raise RiotAPIError(f"PUUID não encontrado para o gamename/tagline fornecido, endpoint: {url}.")

    def get_summonerid_by_puuid(self, puuid: str) -> str:
        """
        Obtém o Summoner ID de um jogador usando seu PUUID.
        Retorna o Summoner ID como string se encontrado, caso contrário retorna None.
        """
        url = f"{self.base_url_br}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        response = self._request(url)

        if response and 'id' in response:
            return response['id']
        raise RiotAPIError(f"Summoner ID não encontrado para o PUUID fornecido, endpoint: {url}.")

    def get_match_ids_by_puuid(self, 
        puuid: str, 
        start_time: int | None = None, 
        end_time: int | None = None,  
        match_type: str | None = None, 
        start: int = 0, 
        count: int = 20,
        queue: int | None = 420) -> list[str] :
        """
        Obtém uma lista de IDs de partidas para um determinado PUUID.
        
        Parâmetros opcionais:
        - start_time: Epoch timestamp em segundos.
        - end_time: Epoch timestamp em segundos.
        - queue: ID da fila (ex: 420 para Ranked Solo/Duo, padrão: 420).
        - match_type: Tipo de partida (ex: 'ranked', 'normal', 'tourney', 'tutorial').
        - start: Índice inicial (padrão: 0).
        - count: Quantidade de IDs a retornar (0 a 100, padrão: 20).
        """
        url = f"{self.base_url}/lol/match/v5/matches/by-puuid/{puuid}/ids"

        params = {
            "startTime": start_time,
            "endTime": end_time,
            "queue": queue,
            "type": match_type,
            "start": start,
            "count": count
        }
        params = {key: value for key, value in params.items() if value is not None}

        response = self._request(url, params=params)

        if isinstance(response, list):
            logging.info(f"Obtidos {len(response)} IDs de partidas para o PUUID: {puuid}.")
            return response
        logging.error(f"Erro ao obter IDs de partidas para o PUUID: {puuid}. Resposta: {response}")
        raise RiotAPIError(f"Erro ao obter IDs de partidas para o PUUID: {puuid}, endpoint: {url}.")
    def get_match_info_by_matchid(self, match_id: str) -> dict :
        """
        Obtém os detalhes completos de uma partida pelo seu matchId.
        Retorna um dicionário contendo os nós 'metadata' e 'info' da partida.
        """
        url = f"{self.base_url}/lol/match/v5/matches/{match_id}"
        
        response = self._request(url)

        # Valida se a resposta é um dicionário e se contém a chave essencial 'info'
        if isinstance(response, dict) and "info" in response:
            logging.info(f"Dados da partida {match_id} obtidos com sucesso.")
            return response
        
        logging.error(f"Erro ao obter dados da partida {match_id}. Resposta: {response}")
        raise RiotAPIError(f"Erro ao obter dados da partida {match_id}, endpoint: {url}.")

    def get_match_timeline_by_id(self, match_id: str) -> dict :
        """
        Obtém a linha do tempo (timeline) detalhada de uma partida pelo seu matchId.
        
        Retorna um dicionário contendo os quadros (frames) minuto a minuto 
        e os eventos ocorridos ao longo do jogo.
        """
        url = f"{self.base_url}/lol/match/v5/matches/{match_id}/timeline"
        
        response = self._request(url)

        if isinstance(response, dict) and "info" in response:
            logging.info(f"Timeline da partida {match_id} obtida com sucesso.")
            return response
        
        logging.error(f"Erro ao obter timeline completo da partida {match_id}. Resposta: {response}")
        raise RiotAPIError(f"Erro ao obter timeline completo da partida {match_id}, endpoint: {url}.")

    def extract_early_game_timeline(self, match_id: str, max_minute: int = 15) -> dict :
        """
        Obtém a timeline detalhada da partida e filtra apenas os quadros (frames) 
        e eventos ocorridos do minuto 0 até o minuto desejado (padrão: 15 minutos).
        """
        full_timeline = self.get_match_timeline_by_id(match_id)
        
        if not full_timeline or "info" not in full_timeline:
            raise RiotAPIError(f"Erro ao obter timeline filtrada para a partida {match_id}, endpoint: {self.base_url}/lol/match/v5/matches/{match_id}/timeline")

        frames = full_timeline["info"].get("frames", [])
        
        early_frames = frames[: max_minute + 1]

        filtered_timeline = {
            "metadata": full_timeline.get("metadata", {}),
            "info": {
                "frameInterval": full_timeline["info"].get("frameInterval"),
                "gameId": full_timeline["info"].get("gameId"),
                "participants": full_timeline["info"].get("participants", []),
                "frames": early_frames
            }
        }

        frames_count = len(early_frames)
        last_minute = frames_count - 1 if frames_count > 0 else 0
        logging.info(f"Timeline da partida {match_id} filtrada com sucesso (0 a {last_minute} min).")
        
        return filtered_timeline

    def get_league_entries_by_puuid(self, puuid: str) -> list[dict] :
        """
        Obtém o histórico de elo e PDL de um jogador (Ranked Solo/Duo, Flex, etc.) pelo PUUID.
        Atenção: Utiliza self.base_url_br (plataforma regional, ex: BR1).
        """

        url = f"{self.base_url_br}/lol/league/v4/entries/by-puuid/{puuid}"
        
        response = self._request(url)

        if isinstance(response, list):
            logging.info(f"Entradas de liga obtidas com sucesso para o PUUID: {puuid}.")
            return response
        
        logging.error(f"Erro ao obter entradas de liga para o PUUID: {puuid}. Resposta: {response}")
        raise RiotAPIError(f"Erro ao obter entradas de liga para o PUUID: {puuid}, endpoint: {url}.")
