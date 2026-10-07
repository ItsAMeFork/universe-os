# Updatekanaal-interface

🧪 UI toont actieve stable/test-bron of nog niet actief. Testupdates ontvangen
vraagt bevestiging bij inschakelen. Polkit 126 → Niet gewijzigd, 127 → Geen
toestemming. Na bevestigd helperresultaat wordt updates.refresh aangeroepen;
een verversfout wordt onderscheiden van een geslaagde kanaalwijziging. Terug
naar stable belooft geen downgrade. Bronlabels wachten op echte pkcon-fixture.

Lokale helper-contracttests updatekanaal.py en syntax/diffcontrole slagen.
Claude: native polkit bevestigen/annuleren/weigeren, bron nog niet actief,
stable/test/stable, onbekend kanaal, herlogin, verversfout en installbare versies
testen. Rotatie/migratie-rollback blijven jouw open systeemtests.
