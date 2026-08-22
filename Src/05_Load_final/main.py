import os
import csv
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configuração de caminhos
LOAD_FINAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DBLoader:
    def __init__(self):
        load_dotenv()
        self.db_host = "localhost" 
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.schema = "dw_riot"
        print("USUÁRIO LIDO:", os.getenv("DB_USER"))
        print("PORTA LIDA:", os.getenv("DB_PORT"))

        # Criação da engine do SQLAlchemy
        self.db_url = f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        self.engine = create_engine(self.db_url)

    def load_table(self, conn, table_name: str, csv_filename: str) -> None:
        """Lê o CSV nativamente e insere no banco via SQLAlchemy Bulk Insert."""
        file_path = os.path.join(LOAD_FINAL_DIR, csv_filename)
        
        if not os.path.exists(file_path):
            logging.error(f"Arquivo não encontrado: {file_path}")
            return

        # 1. Leitura nativa do CSV
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Limpeza rápida: converte strings vazias do CSV para None (que viram NULL no banco)
            data = []
            for row in reader:
                cleaned_row = {k: (v if v != '' else None) for k, v in row.items()}
                data.append(cleaned_row)

        if not data:
            logging.warning(f"O arquivo {csv_filename} está vazio. Nenhuma linha inserida.")
            return

        # 2. Construção dinâmica da query de INSERT baseada nos cabeçalhos do CSV
        columns = reader.fieldnames
        reserved_words = ["full","rank","year", "month", "day", "hour", "minute", "second"]
        
        col_names_str = ", ".join([f'"{col}"' if col in reserved_words else col for col in columns])        
        placeholders_str = ", ".join([f":{col}" for col in columns])
        
        insert_query = text(f"INSERT INTO {self.schema}.{table_name} ({col_names_str}) VALUES ({placeholders_str})")

        # 3. Execução em massa (Bulk Insert) pelo SQLAlchemy
        conn.execute(insert_query, data)
        logging.info(f"✔ Tabela {table_name} carregada com sucesso ({len(data)} linhas).")

    def run_load(self):
        """Carrega todas as tabelas na ordem correta de dependência."""
        tables_to_load = [
            ("dim_time", "dim_time.csv"),
            ("dim_player", "dim_player.csv"),
            ("dim_champion", "dim_champion.csv"),
            ("dim_summoner", "dim_summoner.csv"),
            ("dim_stylePerks", "dim_stylePerks.csv"),
            ("dim_info_match", "dim_info_match.csv"),
            ("fct_match_participant", "fct_match_participant.csv"),
            ("fct_pdl_hist", "fct_pdl_hist.csv")
        ]

        try:
            # Gerencia a transação automaticamente (commit se der certo, rollback se falhar)
            with self.engine.begin() as conn:
                logging.info("Conectado ao banco de dados usando SQLAlchemy.")

                for table_name, csv_filename in tables_to_load:
                    # Limpa os dados antigos antes de inserir os novos
                    conn.execute(text(f"TRUNCATE TABLE {self.schema}.{table_name} CASCADE;"))
                    
                    # Chama o método passando a conexão transacional
                    self.load_table(conn, table_name, csv_filename)

            logging.info("TODOS OS DADOS FORAM CARREGADOS COM SUCESSO PARA O DATA WAREHOUSE!")

        except Exception as e:
            # O .exception imprime o "Traceback" completo (o caminho até a linha que deu erro)
            logging.exception("Erro crítico ao carregar dados no banco:")

if __name__ == "__main__":
    loader = DBLoader()
    loader.run_load()