import time
import requests
import os
from dotenv import load_dotenv, find_dotenv
from urllib.parse import quote

class RiotAPIClient:

    def __init__(self):
        load_dotenv(find_dotenv())
        self.region = os.getenv('SERVER_REGION')
        self.plataform = os.getenv('PLATAFORM') 
        self.api_key = os.getenv('RIOT_API_KEY')
        self.headers = {'X-Riot-Token': self.api_key}
        self.base_url = f'https://{self.region}.api.riotgames.com'
        self.base_url_br = f'https://{self.plataform}.api.riotgames.com'

    def _request(self, url: str, params: dict | None = None) -> dict | list | None:
        """
        Executa a requisição para a API da Riot Games e retorna o resultado em formato JSON.
        Caso ocorra algum erro, retorna chama a função de tratamento de erros.
        """
        response = requests.get(url, headers=self.headers, params=params)

        handlers = {
            200: self._handle_200,
            400: self._handle_400,
            401: self._handle_401,
            403: self._handle_403,
            404: self._handle_404,
            415: self._handle_415,
            429: lambda resp, u: self._handle_429(resp, u, params=params),
            500: self._handle_500,
            503: self._handle_503
        }

        handler = handlers.get(response.status_code, self._handle_default_error)
        return handler(response, url)

    def _handle_200(self, response, url:str) -> dict | list:
        """
        Trata a resposta de sucesso (código 200) da API da Riot Games.
        Retorna o conteúdo da resposta em formato JSON.
        """
        return response.json()

    def _handle_400(self, response, url:str) -> None:
        """
        Trata a resposta de erro (código 400, 'Bad Request') da API da Riot Games.
        Se trata de um erro de requisição inválida, geralmente causado por parâmetros incorretos.[]
        ou erros de sintaxe na URL. Retorna None.
        """
        print(f"Erro 400: Requisição inválida para a URL: {url}. Verifique os parâmetros e a sintaxe da URL.")
        return None

    def _handle_401(self, response, url:str) -> None:
        """
        Trata a resposta de erro (código 401, 'Unauthorized') da API da Riot Games.
        A chave de API fornecida é inválida ou não foi incluída na requisição. Retorna None.
        """
        print(f"Erro 401: Chave de API inválida ou não incluída na requisição para a URL: {url}.")
        return None

    def _handle_403(self, response, url:str) -> None:
        """
        Trata a resposta de erro (código 403, 'Forbidden') da API da Riot Games.
        A chave de API fornecida não tem permissão para acessar o recurso solicitado. Retorna None.
        """
        print(f"Erro 403: Acesso negado para a URL: {url}. Verifique as permissões da chave de API.")
        return None

    def _handle_404(self, response, url:str) -> None:
        """
        Trata a resposta de erro (código 404, 'Not Found') da API da Riot Games.
        O recurso solicitado não foi encontrado. Retorna None.
        """
        print(f"Erro 404: Recurso não encontrado para a URL: {url}.")
        return None

    def _handle_415(self, response, url:str) -> None:
        """
        Trata a resposta de erro (código 415, 'Unsupported Media Type') da API da Riot Games.
        O tipo de mídia da requisição não é suportado. Retorna None.
        """
        print(f"Erro 415: Tipo de mídia não suportado para a URL: {url}.")
        return None

    def _handle_429(self, response: requests.Response, url: str, params: dict | None = None, attempt: int = 1) -> dict | list | None:
        max_attempts = 3
        retry_after = int(response.headers.get("Retry-After", 1))
        rate_limit_type = response.headers.get("X-Rate-Limit-Type", "other")

        if attempt > max_attempts:
            print(f"Erro 429: Número máximo de tentativas ({max_attempts}) atingido para: {url}.")
            return None

        if rate_limit_type in ["application", "method", "other"]:
            print(f"Erro 429 ({rate_limit_type.capitalize()}) - Tentativa {attempt} | {max_attempts}: Aguardando {retry_after}s...")
            time.sleep(retry_after)
            return self._request(url, params=params, attempt=attempt + 1)
        else: 
            if retry_after > 120:
                print(f"Erro 429 (Service): Tempo de espera muito alto ({retry_after}s > 120s). Interrompendo a requisição.")
                return None
            print(f"Erro 429 (Service) - Tentativa {attempt} | {max_attempts}: Aguardando {retry_after}s...")
            time.sleep(retry_after)
            return self._request(url, params=params, attempt=attempt + 1)       

    def _handle_500(self, response, url:str) -> None:
        """
        Trata a resposta de erro (código 500, 'Internal Server Error') da API da Riot Games.
        Ocorreu um erro interno no servidor da Riot Games. Retorna None.
        """
        print(f"Erro 500: Erro interno do servidor para a URL: {url}.")
        return None

    def _handle_503(self, response, url:str) -> None:
        """
        Trata a resposta de erro (código 503, 'Service Unavailable') da API da Riot Games.
        O serviço está temporariamente indisponível. Retorna None.
        """
        print(f"Erro 503: Serviço indisponível para a URL: {url}.")
        return None

    def _handle_default_error(self, response, url:str) -> None:
        """
        Trata respostas de erro não especificadas da API da Riot Games.
        Retorna None.
        """
        print(f"Erro {response.status_code}: Ocorreu um erro inesperado para a URL: {url}.")
        return None

    def get_puuid_by_gamename_tagline (self, gamename: str, tagline: str) -> str | None:
        """
        Obtém o PUUID (Player Universally Unique Identifier) de um jogador usando seu gamename e tagline.
        Retorna o PUUID como string se encontrado, caso contrário retorna None.
        """
        gamename = quote(gamename) 
        tagline = quote(tagline)


        url = f"{self.base_url}/riot/account/v1/accounts/by-riot-id/{gamename}/{tagline}"
        response = self._request(url)

        if response and 'puuid' in response:
            return response['puuid']
        return None

    def get_summonerid_by_puuid(self, puuid: str) -> str | None:
        """
        Obtém o Summoner ID de um jogador usando seu PUUID.
        Retorna o Summoner ID como string se encontrado, caso contrário retorna None.
        """
        url = f"{self.base_url_br}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        response = self._request(url)

        if response and 'id' in response:
            return response['id']
        return None

    def get_match_ids_by_puuid(self, 
        puuid: str, 
        start_time: int | None = None, 
        end_time: int | None = None,  
        match_type: str | None = None, 
        start: int = 0, 
        count: int = 20,
        queue: int | None = 420) -> list[str] | None:
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
            print(f"Obtidos {len(response)} IDs de partidas para o PUUID: {puuid}.")
            return response
        print(f"Erro ao obter IDs de partidas para o PUUID: {puuid}. Resposta: {response}")
        return None

    def get_match_info_by_matchid(self, match_id: str) -> dict | None:
        """
        Obtém os detalhes completos de uma partida pelo seu matchId.
        Retorna um dicionário contendo os nós 'metadata' e 'info' da partida.
        """
        url = f"{self.base_url}/lol/match/v5/matches/{match_id}"
        
        response = self._request(url)

        # Valida se a resposta é um dicionário e se contém a chave essencial 'info'
        if isinstance(response, dict) and "info" in response:
            print(f"Dados da partida {match_id} obtidos com sucesso.")
            return response
        
        print(f"Erro ao obter dados da partida {match_id}. Resposta: {response}")
        return None

    def get_match_timeline_by_id(self, match_id: str) -> dict | None:
        """
        Obtém a linha do tempo (timeline) detalhada de uma partida pelo seu matchId.
        
        Retorna um dicionário contendo os quadros (frames) minuto a minuto 
        e os eventos ocorridos ao longo do jogo.
        """
        url = f"{self.base_url}/lol/match/v5/matches/{match_id}/timeline"
        
        response = self._request(url)

        if isinstance(response, dict) and "info" in response:
            print(f"Timeline da partida {match_id} obtida com sucesso.")
            return response
        
        print(f"Erro ao obter timeline completo da partida {match_id}. Resposta: {response}")
        return None

    def extract_early_game_timeline(self, match_id: str, max_minute: int = 15) -> dict | None:
        """
        Obtém a timeline detalhada da partida e filtra apenas os quadros (frames) 
        e eventos ocorridos do minuto 0 até o minuto desejado (padrão: 15 minutos).
        """
        full_timeline = self.get_match_timeline_by_id(match_id)
        
        if not full_timeline or "info" not in full_timeline:
            return None

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
        print(f"Timeline da partida {match_id} filtrada com sucesso (0 a {last_minute} min).")
        
        return filtered_timeline

    def get_league_entries_by_puuid(self, puuid: str) -> list[dict] | None:
        """
        Obtém o histórico de elo e PDL de um jogador (Ranked Solo/Duo, Flex, etc.) pelo PUUID.
        
        Atenção: Utiliza self.base_url_br (plataforma regional, ex: BR1).
        """
        url = f"{self.base_url_br}/lol/league/v4/entries/by-puuid/{puuid}"
        
        response = self._request(url)

        if isinstance(response, list):
            print(f"Entradas de liga obtidas com sucesso para o PUUID: {puuid}.")
            return response
        
        print(f"Erro ao obter entradas de liga para o PUUID: {puuid}. Resposta: {response}")
        return None