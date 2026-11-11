# uses-certifier

Certificatore del software che produciamo. Analizza i sorgenti, applica le
regole YAML di [uses-rules](https://github.com/manvalan/uses-rules) e
**bollina ogni metodo, ogni classe e ogni sorgente** con un livello (Oro,
Argento, Bronzo o Non certificato), un punteggio e un'impronta SHA-256 che
lega il bollino al codice esatto che è stato giudicato.

Le regole vengono da *Code That Fits in Your Head* (Mark Seemann): regola del
sette, regola 80/24, oggetti attivati, annidamento. A queste si aggiungono
quelle di *Clean Code* e di PEP 8 / PEP 257.

## Installazione

```bash
pip install git+https://github.com/manvalan/uses-certifier
git clone https://github.com/manvalan/uses-rules
```

Richiede Python 3.10 o successivo.

## Uso

```bash
# Certifica una cartella e mostra gli elementi con violazioni
uses-certifier certify src/ --rules ../uses-rules

# Tutti gli elementi, anche quelli senza violazioni
uses-certifier certify src/ --rules ../uses-rules --verbose

# Scrive il certificato JSON e fallisce se il progetto è sotto Argento
uses-certifier certify src/ --rules ../uses-rules \
    --certificate uses-certificate.json --min-level silver

# Rapporto Markdown (per pull request) o SARIF (per GitHub code scanning)
uses-certifier certify src/ --rules ../uses-rules --format markdown --output report.md
uses-certifier certify src/ --rules ../uses-rules --format sarif --output report.sarif

# Controlla che il codice non sia cambiato dopo la certificazione
uses-certifier verify uses-certificate.json

# Elenca le regole attive per il progetto
uses-certifier rules . --rules ../uses-rules
```

Invece di `--rules` si può impostare la variabile `USES_RULES_PATH`.

Esempio di uscita:

```
[ARG] shop/cart.py (punteggio 100)
    [NO ] function Cart.checkout r.42 punteggio 73
        - CTF-001 Complessità ciclomatica al massimo 7 (misurato 9, soglia <= 7)
        - CTF-002 Al massimo 7 oggetti attivati per metodo (misurato 11, soglia <= 7)

Riepilogo:
  sorgenti             Oro              17
  metodi e funzioni    Oro              108
  metodi e funzioni    Non certificato  1
Livello del progetto: Non certificato
```

## Come funziona il bollino

1. **Analisi.** Python viene letto con l'AST. Gli altri linguaggi (C, C++,
   C#, Java, JavaScript, TypeScript, Go, Rust, Kotlin, Swift, PHP, Ruby,
   Scala, Lua...) con [lizard](https://github.com/terryyin/lizard). Per ogni
   elemento si calcolano le metriche elencate nel README di uses-rules.
2. **Regole.** Ogni regola confronta una metrica con una soglia. Le
   violazioni costano 20 punti (error), 7 (warning) o 2 (info).
3. **Livello.** Ogni elemento riceve il primo livello di
   `certification.yaml` che soddisfa. Una classe vale quanto il peggiore tra
   lei e i suoi metodi, un sorgente quanto il peggiore di ciò che contiene,
   il progetto quanto il suo sorgente peggiore.
4. **Bollino.** Il certificato JSON registra per ogni elemento l'impronta
   SHA-256 del codice, il livello e un timbro che combina codice, regole e
   livello. Se il codice o le regole cambiano, il timbro decade e
   `uses-certifier verify` lo segnala.

### Metriche approssimate

- Con lizard le classi sono ricostruite dai nomi dei metodi
  (`Classe::metodo`, `Classe.metodo`). Annidamento, oggetti attivati,
  docstring, flag booleani e campi sono calcolati solo per Python.
- **Oggetti attivati** (Python): parametri, variabili locali e campi di
  `self` usati dal metodo. Non contano le variabili delle comprehension e le
  chiamate ai metodi di `self`.
- **Annidamento**: `if`, `for`, `while`, `with`, `try`, `match`; un `elif`
  resta allo stesso livello dell'`if`.

## Eccezioni motivate

Quando una regola non ha senso per un caso preciso, si sopprime con un
commento sulla riga sopra la definizione (o sopra i decoratori), sempre con
una motivazione:

```python
# uses-cert: ignore[CC-008] i campi rispecchiano il formato YAML
@dataclass
class Rule:
    ...
```

`# uses-cert: ignore-file[CC-010]` vale per tutto il sorgente. Funziona con
qualunque sintassi di commento (`//`, `#`, `--`). Le violazioni soppresse
restano nel certificato con `"suppressed": true`, così sono sempre visibili
in revisione.

## Configurazione del progetto

Un file `.uses-certifier.yaml` nella radice del progetto sceglie i ruleset,
esclude percorsi, adatta le soglie e fissa il livello minimo. Vedi
[`.uses-certifier.example.yaml`](.uses-certifier.example.yaml).

## In GitHub Actions

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with: {python-version: "3.12"}
- uses: manvalan/uses-certifier@main
  with:
    path: src
    min-level: silver
```

L'azione scarica uses-rules, certifica, scrive il rapporto nel riepilogo del
job e lascia `uses-certificate.json` nella cartella di lavoro. Se uses-rules
è privato, passare in `token` un token con accesso in lettura.

## Il certificatore certifica se stesso

La CI esegue il certificatore sul proprio codice e richiede il livello Oro.

## Sviluppo

```bash
pip install -e ".[test]"
pytest
```

Struttura:

| Modulo | Compito |
|---|---|
| `analyzers/` | estrazione di elementi e metriche (Python con AST, altri linguaggi con lizard) |
| `rules.py`, `config.py` | caricamento delle regole YAML e della configurazione del progetto |
| `evaluator.py` | confronto tra metriche e soglie |
| `scoring.py` | punteggio, livello e timbro |
| `certificate.py`, `verify.py` | certificato JSON e verifica delle impronte |
| `reporters/` | uscita console, Markdown e SARIF |
