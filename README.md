# TP3 – Intégration Continue

A minimal **FastAPI** application from the *Plateforme collaborative et intégration continue (DevOps)* lab (ISIMS – A.U. 2026-2027).
TP3 adds a **subtraction** feature, **unit tests**, **code coverage**, **code-quality scanning (Pylint)**, and a **GitLab CI pipeline** that runs all of them on every push. It also adds a **deployment to Render** that runs only on `main`.

## Endpoints

| Method | Path | Description | Example response |
|---|---|---|---|
| GET | `/` | Health check | `{"message": "it works !"}` |
| GET | `/addition?a=1&b=2` | a + b | `{"result a+b=": 3, "developer": "Dev1"}` |
| GET | `/soustraction?a=10&b=4` | a − b **(new in TP3)** | `{"result a-b=": 6, "developer": "Dev1"}` |
| GET | `/greeting?name=X` | Greeting with hostname and IP | `{"message": "Hello, X", "developer": "Dev2", "hostname": "...", "IP": "..."}` |
| POST | `/multiply` `{"a":3,"b":4}` | a × b | `{"result a*b=": 12.0, "developer": "Dev1"}` |
| POST | `/divide` `{"a":10,"b":4}` | a ÷ b (400 if b = 0) | `{"result a/b=": 2.5, "developer": "Dev2"}` |
| GET | `/items` | List items | `[{"id": 1, "name": "item1", ...}]` |
| DELETE | `/remove/{id}` | Delete an item (404 if missing) | `{"deleted": 2, "developer": "Dev1"}` |

Interactive docs: <http://127.0.0.1:8000/docs>

## Getting started

The project uses [uv](https://docs.astral.sh/uv/) (Python 3.11, see `.python-version`).

```bash
uv sync                               # create .venv and install app + dev dependencies
uv run uvicorn main:app --reload      # http://127.0.0.1:8000
```

Without uv: `python -m venv .venv`, activate it, then `pip install "fastapi[standard]" pytest pytest-cov pylint`.

## Quality checks (run them locally before pushing)

| What | Command | Result |
|---|---|---|
| Unit tests | `uv run pytest -v` | 13 passed |
| JUnit report | `uv run pytest -v --junitxml=report.xml` | `report.xml` |
| Coverage | `uv run pytest -v --cov=. --cov-report term --cov-report xml:coverage.xml --cov-report html` | **100 %** (`htmlcov/index.html` shows uncovered lines) |
| Code quality | `uv run pylint main.py test_main.py` | **10.00/10** |

Tests live in `test_main.py` and use FastAPI's `TestClient` ([docs](https://fastapi.tiangolo.com/tutorial/testing/)). They cover every endpoint, including the error paths (division by zero, unknown item, invalid input) and the `current_ip()` fallback when there is no network (simulated with `monkeypatch`).

### Interpreting the coverage

With only the first subtraction test, `pytest --cov` reported **63 % for `main.py`** (19 of 51 statements missed). The module-level code ran, but every route body except `/` and `/soustraction` never ran, so a bug in `/divide` or `/remove` would not have been caught. Coverage shows *which* code no test exercises. It does not prove the tested code is correct. Adding tests for each endpoint and each error branch raised it to **100 %**.

## CI/CD pipeline (`.gitlab-ci.yml`)

```
code_quality ──► test ──────────────────► deploy (main only)
  pylint          run-test                 deploy-render
                  calculate-coverage
```

| Stage | Job | What it does |
|---|---|---|
| `code_quality` | `pylint` | `pylint --fail-under=10`: the pipeline fails if the score drops below 10/10 |
| `test` | `run-test` | Runs pytest and publishes `report.xml` as a **JUnit artifact** (pipeline **Tests** tab) |
| `test` | `calculate-coverage` | Runs pytest with coverage. The `coverage:` regex shows the % in the **Jobs** list and the MR. `coverage.xml` (Cobertura) and `htmlcov/` are kept as artifacts |
| `deploy` | `deploy-render` | Calls the Render deploy hook. Runs only on the default branch, only if every previous job passed |

Python jobs use the `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` image and install the exact versions from `uv.lock` (`uv sync --frozen`). The uv cache is shared between pipelines.

### Git workflow used

```bash
git checkout -b feature/soustraction-with-unit-tests
# code + tests, verify locally (pytest, coverage, pylint)
git push -u origin feature/soustraction-with-unit-tests
# pipeline green on the branch → open a Merge Request → merge → pipeline runs again on main (+ deploy)
```

## Deployment on Render (free tier)

Render service settings (Web Service, *Free* instance):

- **Build command:** `pip install uv && uv sync --frozen --no-dev`
- **Start command:** `.venv/bin/uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Auto-Deploy:** *Off*. The GitLab pipeline triggers the deploy through the **Deploy Hook**, so code that fails Pylint or the tests is never deployed.
- GitLab → *Settings → CI/CD → Variables*: `RENDER_DEPLOY_HOOK_URL` (masked).

A free instance sleeps after ~15 min without traffic, so the first request after that takes a while to respond. The `items` store is in memory and resets on every restart.

## Validation des acquis

**1. Pourquoi développe-t-on des tests unitaires et quel est leur impact sur la qualité du code ?**
Un test unitaire vérifie automatiquement qu'une petite partie du code (ici un endpoint) donne le résultat attendu, y compris dans les cas d'erreur. Les tests détectent les bugs tôt, quand ils coûtent le moins cher à corriger. Ils servent aussi de documentation exécutable, et ils permettent de refactorer sans crainte : si un test casse, on le voit immédiatement. Comme un code testable doit être découpé en fonctions simples et indépendantes, ils améliorent aussi la conception.

**2. Comment la couverture de code aide-t-elle à détecter les régressions ?**
La couverture indique quelles lignes sont exécutées par les tests. Une ligne non couverte peut être modifiée ou cassée sans qu'aucun test n'échoue : la régression passe inaperçue. Un taux élevé (> 90 %) garantit que presque tout le code est exécuté à chaque pipeline. Toute modification qui change le comportement d'une partie couverte fait alors échouer un test avant le merge. Le rapport HTML montre précisément les lignes et branches oubliées. Attention cependant : 100 % de couverture ne garantit pas l'absence de bugs, il faut aussi de bonnes assertions.

**3. Est-ce que le fait de créer un repository pour chaque développeur est une bonne pratique ?**
Non. L'intégration continue repose sur **un dépôt central partagé**, où le code de tous est intégré et vérifié par le même pipeline. Avec un dépôt par développeur, on intègre rarement, les divergences s'accumulent et les conflits deviennent énormes (« integration hell »). Les tests ne valident jamais le code réel combiné. Chaque développeur travaille plutôt sur une **branche** du même dépôt (ou un fork qui ouvre des merge requests vers le dépôt central).

**4. Faut-il merger fréquemment sur main ou laisser le travail de chaque développeur sur une branche séparée ?**
Il faut merger **fréquemment**, via des branches de fonctionnalité **courtes** (quelques heures à quelques jours). Chaque merge passe par une merge request dont le pipeline (Pylint, tests, couverture) est vert. De petits changements fréquents donnent des conflits rares et simples, des bugs faciles à localiser et une branche `main` toujours déployable. Les branches longues font exactement l'inverse et vont à l'encontre du principe même de l'intégration continue.

## Project structure

```
.
├── main.py          # FastAPI application
├── test_main.py     # Unit tests (pytest + TestClient)
├── .gitlab-ci.yml   # CI/CD pipeline: pylint → tests + coverage → deploy
├── pyproject.toml   # Dependencies (app + dev group: pytest, pytest-cov, pylint)
├── uv.lock          # Locked versions
└── README.md
```
