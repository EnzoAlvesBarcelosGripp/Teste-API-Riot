import os
import logging
from datetime import datetime

# Importação dos módulos de transformação das dimensões
from dim_champion import transform_dim_champion
from dim_stylePerks import transform_dim_stylePerks
from dim_summonerSpell import transform_dim_summonerSpell
from dim_time import transform_dim_time
from dim_player import transform_dim_player
from dim_info_match import transform_dim_info_match

# Importação dos módulos das tabelas fato
from fct_match_participants import transform_fct_match_participant
from fct_pdl import transform_fct_pdl_hist

# Mapeamento dinâmico dos diretórios do projeto
TRANSFORM_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(TRANSFORM_DIR)
LOAD_DIR = os.path.join(SRC_DIR, "02_Load")
OUTPUT_DIR = os.path.join(SRC_DIR, "04_Load_final")


def setup_logging() -> None:
    """Configura o sistema de logs para a etapa de transformação."""
    logs_dir = os.path.join(SRC_DIR, "Logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filepath = os.path.join(logs_dir, f"transform_pipeline_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y%m%d_%H%M%S",
        handlers=[
            logging.FileHandler(log_filepath, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


def run_transformations():
    """Executa o pipeline de transformação na ordem de dependências do Data Warehouse."""
    setup_logging()
    logging.info(" INICIANDO PIPELINE DE TRANSFORMAÇÃO (03_Transform) ")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        # 1. DIMENSÕES BASE (Dependentes apenas de dados estáticos/tempo)
        logging.info("[FASE 1/3] Gerando Dimensões Base")
        
        datadragon_dir = os.path.join(LOAD_DIR, "DataDragon")
        
        transform_dim_champion(datadragon_dir)
        logging.info("Dimensão Champion processada com sucesso.")

        transform_dim_stylePerks(datadragon_dir)
        logging.info("Dimensão StylePerks processada com sucesso.")

        transform_dim_summonerSpell(datadragon_dir)
        logging.info("Dimensão Summoner processada com sucesso.")

        # 2. DIMENSÕES DE NEGÓCIO (Dependentes de Partidas/Jogadores)
        logging.info("[FASE 2/3] Gerando Dimensões de Negócio ")
        match_info_dir = os.path.join(LOAD_DIR, "Match-V5", "InfoMatch")
        
        transform_dim_time(match_info_dir)
        logging.info("Dimensão Time processada com sucesso.")

        transform_dim_player(match_info_dir)
        logging.info("Dimensão Player processada com sucesso.")

        transform_dim_info_match(match_info_dir)
        logging.info("Dimensão InfoMatch processada com sucesso.")

        # 3. TABELAS FATO (Dependentes de todas as dimensões anteriores)
        logging.info("[FASE 3/3] Gerando Tabelas Fato ")

        match_timeline_dir = os.path.join(LOAD_DIR, "Match-V5", "TimelineMatch")
        pdl_folder_dir = os.path.join(LOAD_DIR, "League-V4")

        # Fato 1: Partidas e Desempenho dos Participantes
        transform_fct_match_participant(
            matches_folder=match_info_dir,
            timelines_folder=match_timeline_dir
        )
        logging.info("Tabela Fato Match Participant gerada com sucesso.")

        #2. Histórico e Variação de PDL da Conta Principal
        transform_fct_pdl_hist(pdl_folder_dir)
        logging.info("Tabela Fato PDL Hist gerada com sucesso.")

        logging.info("PIPELINE DE TRANSFORMAÇÃO CONCLUÍDO COM SUCESSO")

    except Exception as e:
        logging.critical(f"Falha crítica durante o pipeline de transformação: {e}", exc_info=True)


if __name__ == "__main__":
    run_transformations()