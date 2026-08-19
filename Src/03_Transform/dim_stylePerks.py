import os 
import json
import logging
import pandas as pd

class Dim_stylePerks_Error(Exception):
    """Classe base para erros da transformação"""

def transform_dim_stylePerks(json_path) -> pd.DataFrame:
    Error = Dim_stylePerks_Error()

    try:
        with open(json_path,"r",encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as e:
        logging.error(f'Erro ao abrir ou ler o arquivo JSON em {json_path}:')
        raise Dim_stylePerks_Error(f"Erro ao abrir ou ler o arquivo JSON em {json_path}: {e}")
        
    try: 
        # Json flatten - Style -> Slots -> Runes 
        df_stylePerks = pd.json_normalize(json_data,record_path=["slots","runes"],meta=["id","icon"],meta_prefix="style_")
        
        df_stylePerks = df_stylePerks.rename(columns={"id":"perk_id","icon":"perk_icon"})

        cols_order = ["style_id", "perk_id", "style_icon", "perk_icon"]
        df_stylePerks = df_stylePerks[cols_order]

        df_stylePerks.insert(0,"sk_perks",range(1,len(df_stylePerks) + 1))

        final_path = "03_Transform/dim_stylePerks.csv"
        df_stylePerks.to_csv(final_path,index=False)
        logging.info(f'Extração das informações do arquivo {json_path} concluída com sucesso')

        return df_stylePerks
    
    except Exception as e:
        logging.error(f'Erro ao transformar dados do stylePerks spell')
        raise Dim_stylePerks_Error(f"Erro ao transformar dados do stylePerks spell: {e}")