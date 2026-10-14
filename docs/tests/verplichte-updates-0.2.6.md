# Test verplichte updates (8–9 oktober 2026)

**Systeem:** test-VM, geïnstalleerd systeem (ISO 0.2.3 + pakket), pakket 0.2.6 uit commit f9f8102 (systeemkant spoor A +
knop/voortgang PR #35 spoor B). Ingelogd via het inlogscherm als gewone gebruiker `tester`.

| Test | Uitkomst |
|---|---|
| Na installeren van het pakket: timer `universe-updates.timer` aan, eerste run | ✅ 3 echte Debian-updates automatisch geïnstalleerd, status "3 updates geïnstalleerd." |
| `updates.install()` als gewone gebruiker (polkit) | ✅ geen wachtwoordvraag; `checking → current` |
| Twee keer snel starten | ✅ één taak |
| `universe-updates-helper kanaal test` | ✅ geweigerd: "Testupdates bestaan niet meer…" |
| Zonder internet | ✅ `error` met Nederlandse tekst, unit wacht op nieuwe poging (SubState auto-restart) |
| Klik tijdens die wachttijd, netwerk weer aan | ✅ start direct een nieuwe poging: `checking → current` |
| Controle bij inloggen (status gewist, timer gestopt) | ✅ shell.log: "Updatecontrole bij inloggen gestart." → "Alles is bijgewerkt." |
| Controlecentrum > Software en updates (echte WebKit) | ✅ uitleg verplichte updates, klik "Nu controleren" → "Updates controleren…" (knoppen uit) → "Alles is bijgewerkt.", tijd bijgewerkt |

Nog niet getest: een echte universe-os-update via de eigen bron (komt bij publicatie van 0.2.6 naar een systeem met een
oudere versie); de knop "Updates installeren" verschijnt alleen bij `available`/bezig, en de systeemtaak installeert meteen.
