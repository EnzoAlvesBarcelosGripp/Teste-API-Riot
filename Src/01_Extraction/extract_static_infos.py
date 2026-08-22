import json
import os
import logging
import gzip
from Static import DataDragon,DataDragonError

def save_json(data: dict | list, folder_path: str, filename: str) -> None:
    """
    Salva os dados retirados do endpoint da Riot Games em um arquivo JSON.
    """
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)    

    logging.info(f"Arquivo JSON salvo em: {file_path}")

def get_game_versions_from_matches(info_folder_path: str) -> list[str]:
    """
    Lê os arquivos JSONs de partidas em InfoMatch e extrai as versões únicas.
    """
    Versions = []

    if not os.path.exists(info_folder_path):
        logging.error(f'Pasta {info_folder_path} não foi encontrada.')
        raise DataDragonError(f'Falha ao procurar a pasta {info_folder_path}.')

    # os.listdir retorna uma lista com os nomes de todos os arquivos em um path
    for file_name in os.listdir(info_folder_path):
        # Passamos a buscar pelos arquivos comprimidos
        if file_name.endswith('.json.gz'):
            file_path = os.path.join(info_folder_path,file_name)
            try:
                # Usamos gzip.open em modo leitura de texto ('rt')
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)

                    # Acessa o 'gameVersion' da partida, dentro do Nó 'Info'
                    game_version = data.get("info", {}).get("gameVersion")
                    if game_version:
                        patch_base = ".".join(game_version.split(".")[:2])
                        Versions.append(patch_base)
                    if game_version:
                        Versions.append(game_version)
            except Exception as e:
                logging.error(f"Erro ao ler o arquivo {file_name}.")
                raise Exception(f'Falha ao ler arquivo {file_name}: {e} ')

    # Usa set para retirar as duplicadas, set são list sem valores duplicados
    return list(set(Versions)) 


def download_static_data_for_versions(load_dir: str, info_folder_path: str) -> None:
    """
    Extrai do Data Dragon apenas os dados estáticos das versões presentes nas partidas.
    """
    # pega as versões unicas para aquele conjunto de partidas
    game_versions = get_game_versions_from_matches(info_folder_path)

    # Verifca se a lista veio vazia
    if not game_versions:
            logging.error(f'Nenhuma versão de partida encontrada para processar dados estáticos.')
            raise DataDragonError(f'Nenhuma versão de partida encontrada para processar dados estáticos.')

    dragon = DataDragon()
    try:
        # lista com todas as versões do DDragon
        dragon_versions = dragon.get_list_versions()
    except DataDragonError as e:
        logging.error(f'Falha ao obter lista de versões: {e}')
        raise DataDragonError(f'Falha ao obter lista de versões, endpoint {dragon.url}/api/versions.json')

    unique_patches = {
        '.'.join(each_game_version.split('.')[:2])
        for each_game_version in game_versions
    }
    for each_game_version in game_versions:
        # Converte o formato de 'XX.XX.YYYYY.YYY' para 'XX.XX' - formato no DDragon
        patch_match = '.'.join(each_game_version.split('.')[:2])

        # Encontra o correspondente no Data Dragon
        matching_version = None
        for patch_ddragon in dragon_versions:
            if patch_ddragon.startswith(patch_match):
                matching_version = patch_ddragon
                break

        if matching_version:
            logging.info(f'Baixando dados estáticos para a versão {matching_version} (Patch {patch_match})')
            # Seta a version correta para poder puxar os dados
            dragon.set_version(matching_version)

            # Cria pasta organizada por versões
            version_folder = os.path.join(load_dir,"DataDragon",matching_version)

            # Extração das informações na versão correta
            try:
                # campeões
                champions = dragon.get_champion_data()
                save_json(champions, version_folder, 'champion.json.gz')

                # spells
                summoners = dragon.get_summoner_spell_data()
                save_json(summoners,version_folder,'summoner.json.gz')

                # runas
                runes = dragon.get_runes_reforged_data()
                save_json(runes,version_folder,'runesReforged.json.gz')

            except DataDragonError as e:
                logging.error(f"Erro ao baixar dados para a versão {matching_version}: {e}")
                raise DataDragonError(f'Erro ao baixar dados para a versão {matching_version}')
        else:
             logging.warning(f"Nenhuma versão compatível no Data Dragon para o patch {patch_match}.")   