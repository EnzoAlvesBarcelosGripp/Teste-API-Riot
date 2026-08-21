import os
import logging
from datetime import datetime

from val_dim import DimValidator, DimValidationError
from val_fct_match_participants import FctMatchParticipantValidator, FctMatchParticipantValidationError
from val_pdl_hist import FctPdlValidator, FctPdlValidationError

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def setup_logging() -> None:
    """Configura a exibição de logs no terminal e o salvamento na pasta Src/Logs."""
    logs_dir = os.path.join(SRC_DIR, "Logs")
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"homologacao_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y%m%d_%H%M%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


def main() -> None:
    setup_logging()
    logging.info("Iniciando homolagação dos dados")

    try:
        # 1. Homologação Nível 1: Dimensões Base e de Negócio
        dim_validator = DimValidator()
        dim_validator.run_all_dim_validations()

        # 2. Homologação Nível 2A: Fato Match Participant
        fct_match_validator = FctMatchParticipantValidator()
        fct_match_validator.run_validations()

        # 3. Homologação Nível 2B: Fato PDL Histórico
        fct_pdl_validator = FctPdlValidator()
        fct_pdl_validator.run_validations()

        logging.info("HOMOLOGAÇÃO CONCLUÍDA SEM NENHUMA FALHA!")
        logging.info("Os dados em '05_Load_final' estão 100% validados.")

    except (DimValidationError, FctMatchParticipantValidationError, FctPdlValidationError) as e:
        logging.critical(f"A validação falhou: {e}")


if __name__ == "__main__":
    main()