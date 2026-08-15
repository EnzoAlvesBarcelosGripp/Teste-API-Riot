from typing import Literal
import requests

class DataDragon:
    def __init__(self,url: str = "https://ddragon.leagueoflegends.com"):
        self.url = url
        self.version = None

    def get_list_versions(self) -> list:
        """
        Obtém a lista de versões disponíveis do Data Dragon.
        """
        response = requests.get(f"{self.url}/api/versions.json")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro ao obter a lista de versões: {response.status_code}")
            return []

    def set_version(self, version: str) -> None:
        """
        Define a versão do Data Dragon a ser utilizada.
        """
        self.version = version

    def _fetch_static_data(self, endpoint: Literal["champion.json", "summoner.json", "runesReforged.json"]) -> dict | None:
        """
        Obtém os dados estáticos para o endpoint especificado.
        Endpoint pode ser "champion.json", "summoner.json" ou "runesReforged.json".
        """
        if self.version is None:
            print("Versão não definida. Use o método set_version() para definir uma versão.")
            return None
        response = requests.get(f"{self.url}/cdn/{self.version}/data/en_US/{endpoint}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro ao obter os dados {endpoint.replace('.json', '')}: {response.status_code}")
            return None

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
        

    def get_queuesId_list (self,url: str = "https://static.developer.riotgames.com/docs/lol/queues.json") -> dict | None:
        """
        Obtém a lista de IDs de filas para a versão definida.
        Vindas do endpoint: /docs/lol/queues.json
        """
        response = requests.get(f"{url}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro ao obter a lista de IDs de filas: {response.status_code}")
            return None