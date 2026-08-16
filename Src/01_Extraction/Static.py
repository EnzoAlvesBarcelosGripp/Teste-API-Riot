import logging
from typing import Literal
import requests

class DataDragonError(Exception):
    """Exceção customizada para erros ao consumir dados do Data Dragon."""
    pass


class DataDragon:
    def __init__(self, url: str = "https://ddragon.leagueoflegends.com"):
        self.url = url
        self.version = None

    def get_list_versions(self) -> list:
        """
        Obtém a lista de versões disponíveis do Data Dragon.
        """
        url = f"{self.url}/api/versions.json"
        response = requests.get(url)

        if response.status_code == 200:
            versions = response.json()
            logging.info(f"Lista de versões obtida com sucesso ({len(versions)} versões encontradas).")
            return versions
        else:
            logging.error(f"Erro ao obter a lista de versões. Status Code: {response.status_code} | URL: {url}")
            raise DataDragonError(f'Falha na requisição para {url} - Status Code: {response.status_code}')

    def set_version(self, version: str):
        """
        Define a versão do Data Dragon a ser utilizada.
        """
        self.version = version
        logging.info(f"Versão do Data Dragon configurada para: {self.version}")

    def _fetch_static_data(self, endpoint: Literal["champion.json", "summoner.json", "runesReforged.json"]) -> dict | list | None:
        """
        Obtém os dados estáticos para o endpoint especificado.
        """
        if self.version is None:
            logging.warning("Tentativa de buscar dados estáticos sem definir a versão. Utilize set_version() primeiro.")
            raise DataDragonError('Versão do Data Dragon não definida. Utilize set_version() antes de buscar dados.')

        url = f"{self.url}/cdn/{self.version}/data/en_US/{endpoint}"
        response = requests.get(url)

        if response.status_code == 200:
            logging.info(f"Dados de '{endpoint}' obtidos com sucesso para a versão {self.version}.")
            return response.json()
        else:
            logging.error(f"Erro ao obter os dados de '{endpoint}'. Status Code: {response.status_code} | URL: {url}")
            raise DataDragonError(f"Falha na requisição para {url} - Status Code: {response.status_code}")

    def get_champion_data(self) -> dict | None:
        """
        Obtém os dados dos campeões para a versão definida.
        Vindas do endpoint: /cdn/{version}/data/en_US/champion.json
        """
        return self._fetch_static_data("champion.json")

    def get_summoner_spell_data(self) -> dict | None:
        """
        Obtém os dados das habilidades de invocador para a versão definida.
        Vindas do endpoint: /cdn/{version}/data/en_US/summoner.json
        """
        return self._fetch_static_data("summoner.json")

    def get_runes_reforged_data(self) -> dict | None:
        """
        Obtém os dados das runas reforjadas para a versão definida.
        Vindas do endpoint: /cdn/{version}/data/en_US/runesReforged.json
        """
        return self._fetch_static_data("runesReforged.json")
        

    def get_queuesId_list (self,url: str = "https://static.developer.riotgames.com/docs/lol/queues.json") -> list | dict: 
        """
        Obtém a lista de IDs de filas para a versão definida.
        Vindas do endpoint: /docs/lol/queues.json
        """
        response = requests.get(url)

        if response.status_code == 200:
            logging.info("Lista de IDs de filas obtida com sucesso.")
            return response.json()
        else:
            logging.error(f"Erro ao obter a lista de IDs de filas. Status Code: {response.status_code} | URL: {url}")
            raise DataDragonError(f'Falha na requisição para {url} - Status Code: {response.status_code}')