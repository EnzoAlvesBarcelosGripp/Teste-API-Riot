# Documentação Técnica 

> Esta documentação tem como objetivo detalhar todo o fluxo de extração e especificar cada função dos arquivos
---

## `Endpoints.py`

* **Responsabilidade:** Cria a classe para realizar as requisições e tratamentos para a Riot Games API. Concentra autenticação, retry/rate-limit e todas as chamadas de endpoint, que estejam na [documentação oficial](https://developer.riotgames.com/apis) 

* **Erros**: `RiotAPIError`.

* **Classes principal:** `RiotAPIClient`

### Metodos
| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `_request(url, params=None, attempt=1)` | `url`: endpoint completo; `params`: query params | `dict \| list` | Executa o `GET`, trata `429` com backoff via header `Retry-After` (até 3 tentativas) e levanta `RiotAPIError` para qualquer outro status ≠ 200. Usado internamente por todos os demais métodos. |
| `get_puuid_by_gamename_tagline(gamename=None, tagline=None)` | Opcionais; se omitidos, usa `GAME_NAME`/`TAG_LINE` do `.env` | `str` (PUUID) | Resolve o Riot ID (`gamename#tagline`) para o PUUID do jogador. Faz `quote()` dos parâmetros antes de montar a URL. |
| `get_summonerid_by_puuid(puuid)` | `puuid: str` | `str` (Summoner ID) | Retorna o ID de invocador (plataforma) a partir do PUUID. |
| `get_match_ids_by_puuid(puuid, start_time=None, end_time=None, match_type=None, start=0, count=20, queue=420)` | Ver assinatura | `list[str]` | Retorna IDs de partidas do jogador. Internamente pagina em lotes de 100 (limite da API): calcula quantos lotes completos são necessários, faz uma chamada por lote e, se houver resto, faz uma chamada final com o restante. Interrompe cedo se um lote vier com menos de 100 resultados (sinal de que não há mais partidas). |
| `get_match_info_by_matchid(match_id)` | `match_id: str` | `dict` (`metadata` + `info` do json) | Detalhes completos de uma partida. |
| `get_match_timeline_by_id(match_id)` | `match_id: str` | `dict` | Timeline completa (todos os frames/minutos) da partida. |
| `extract_early_game_timeline(match_id, max_minute=15)` | `match_id`, `max_minute` | `dict` | Chama `get_match_timeline_by_id` internamente e filtra apenas os frames de `0` até `max_minute`, preservando `metadata`, `frameInterval`, `gameId` e `participants`. |
| `get_league_entries_by_puuid(puuid)` | `puuid: str` | `list[dict]` | Entradas de ranqueada (Solo/Duo, Flex etc.) do jogador. Usa `base_url_br` (rota de plataforma), diferente dos demais métodos que usam `base_url` (rota regional). |
---
## `Static.py`

* **Responsabilidade**: Cria a classe para realizar as requisições e tratamentos para o Data Dragon (DDragon) - CDN pública de dados estáticos do jogo — não requer API key. Contém todas as requisições e retém a versão usada para extrair as informações.

* **Classe Principal**: `DataDragon`

* **Erros**: `DataDragonError`.
### Métodos

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `_fetch_static_data(endpoint)` | `endpoint`: `"champion.json"`, `"summoner.json"` ou `"runesReforged.json"` | `dict \| list \| None` | Faz o `GET` em `/cdn/{version}/data/en_US/{endpoint}`. Exige que `set_version()` tenha sido chamado antes; caso contrário levanta `DataDragonError`. |
| `get_list_versions()` | — | `list[str]` | Lista todas as versões (patches) disponíveis no Data Dragon, da mais recente à mais antiga. |
| `set_version(version)` | `version: str` | `None` | Define a versão ativa (`self.version`) usada nas chamadas seguintes. |
| `get_champion_data()` | — | `dict` | Retorna os dados de todos os campeões, chamando `_fetch_static_data("champion.json")`. |
| `get_summoner_spell_data()` | — | `dict` | Retorna os dados dos feitiços de invocador, chamando `_fetch_static_data("summoner.json")`. |
| `get_runes_reforged_data()` | — | `dict` | Retorna os dados  das runas, chamando `_fetch_static_data("runesReforged.json")` |
| `get_queuesId_list(url=...)` | `url` opcional | `list \| dict` | Tabela de referência de IDs de fila (endpoint separado, fora do CDN versionado). |
---

## `extract_static_infos.py`

**Responsabilidade:** identificar quais versões do jogo aparecem nas partidas já baixadas e acionar o `DataDragon` para baixar os dados estáticos correspondentes a cada uma, evitando **requests** desnecessárias.

* Estruturado apenas com funções.

| Função | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `save_json(data, folder_path, filename)` | `data`, pasta de destino, nome do arquivo | `None` | Utilitário genérico de persistência (`json.dump`, `indent=4`, `ensure_ascii=False`). Cria a pasta se não existir. Duplicado de `main.py::save_json`. |
| `get_game_versions_from_matches(info_folder_path)` | Caminho da pasta `Match-V5/InfoMatch/` | `list[str]` | Percorre todos os `.json` da pasta, lê `info.gameVersion` de cada partida e retorna as versões **únicas** encontradas (usa `set()` para desduplicar). Levanta `DataDragonError` se a pasta não existir. |
| `download_static_data_for_versions(load_dir, info_folder_path)` | Pasta raiz de saída; pasta com os JSONs de partidas | `None` | Fluxo: <br>1. Chama `get_game_versions_from_matches` para obter as versões presentes nas partidas.<br>2. Instancia `DataDragon` e busca a lista completa de versões via `get_list_versions()` em `Static.py`.<br>3. Para cada versão de partida (formato `XX.YY.build.id`), converte para o formato de patch do Data Dragon (`XX.YY`) e procura a primeira versão do Data Dragon que começa com esse patch.<br>4. Se encontrar correspondência, define a versão (`set_version`) e baixa `champion.json`, `summoner.json` e `runesReforged.json` em `{load_dir}/DataDragon/{versão}/`.<br>5. Se não encontrar, apenas loga um aviso (`warning`) e segue para a próxima versão. |

---

## `main.py`

* **Responsabilidade**: funciona como um orquestrador de todos os outros arquivos, requisiciona todos os arquivos dos endpoints e salva eles em forma `RAW`, dentro de `Src/02_Load`, com cada endpoint tendo sua pasta dedicada e faz o acompanhamento com **logs**, salvo em `Src/Logs`.

* **Fluxo de execução** (`main()`)

1. **Logging** — `make_logging()` cria a pasta `Logs/` e configura handlers de arquivo + console. Se falhar, o erro é apenas impresso no console (não interrompe o pipeline).
2. **Cliente** — instancia `RiotAPIClient()`, que carrega o `.env`.
3. **PUUID** — `get_puuid_by_gamename_tagline()`. Esta é a **única etapa crítica**: se falhar, loga `CRITICAL` e a função `main()` retorna imediatamente, sem executar o restante.
4. **League-V4** — busca as entradas de liga do jogador e salva em `League-V4/{puuid}_{timestamp}.json`. Falha aqui é logada como `error` e o pipeline continua.
5. **Lista de partidas** — busca até `count=120` IDs de partida (fila 420 por padrão) e salva em `Match-V5/listMatchId/{puuid}_matches.json`. Se falhar, `match_ids` permanece como lista vazia (`[]`) e o loop seguinte simplesmente não executa nenhuma iteração.
6. **Loop por partida** (`for i, match_id in enumerate(match_ids, start=1)`):
   - Monta os paths `path_info` e `path_timeline`.
   - Se `{match_id}_info.json` já existe em disco, pula a chamada de API (idempotência); caso contrário, baixa via `get_match_info_by_matchid` e salva.
   - Se `{match_id}_timeline.json` já existe, pula; caso contrário, baixa a timeline já filtrada (0–15 min) via `extract_early_game_timeline` e salva.
   - Qualquer `RiotAPIError` na iteração é logada e o loop segue (`continue`) para a próxima partida, sem interromper o pipeline.
7. **Dados estáticos** — chama `download_static_data_for_versions(LOAD_DIR, path_info)`, que varre os JSONs de `InfoMatch` para descobrir as versões do jogo presentes e baixa os arquivos estáticos correspondentes do Data Dragon.
8. **Fim** — a função retorna `None` (`return` implícito no final).