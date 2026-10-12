# Radar AI Big Tech: aggiornamento automatico

`generate.py` legge feed pubblici (Google News e blog ufficiali) e crea `index.html`.
Serve solo Python 3, nessuna libreria da installare.

## Opzione A: link condivisibile che si aggiorna da solo (GitHub Pages, gratis)
1. Crea un repository su github.com e carica `generate.py` e la cartella `.github`.
2. Nel repository: Settings > Pages > Source: **GitHub Actions**.
3. Scheda Actions > "Aggiorna Radar AI" > Run workflow (primo avvio manuale).
4. L'indirizzo della pagina compare nel job "deploy". Condividilo con il team.
   Si aggiorna ogni giorno alle 05:00 UTC. Cambia l'orario nella riga `cron` del file.
Nota: GitHub Pages su repository privati richiede un piano a pagamento. Su un repository
pubblico la pagina è visibile a chiunque abbia il link.

## Opzione B: solo sul tuo computer
- Esegui `python generate.py` e apri `index.html`.
- Per l'esecuzione giornaliera: su Windows usa l'Utilità di pianificazione, su Mac/Linux `crontab -e`
  con `0 7 * * * cd /percorso/radar-ai && python3 generate.py`.
- Per condividerla, salva la cartella in OneDrive, SharePoint o Drive: i colleghi aprono `index.html`.

## Personalizzare
In `generate.py` modifica `COMPANIES` (aziende, feed, colori), `DAYS` (giorni mostrati, ora 7), `MAX_PER_CO` e le parole chiave `AI_RE` / `NOISE_RE` che decidono quali notizie restano.
Se un feed non risponde, lo script lo salta e scrive un avviso. Se nessun feed risponde non sovrascrive la pagina.
