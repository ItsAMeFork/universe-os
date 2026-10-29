# Eigen profielfoto op je planeet in het inlogscherm (0.3.4)

Goedgekeurd door Axel op 28 okt 2026 ("ja klopt, ga maar bouwen").

## Wat de gebruiker ziet
- Controlecentrum → Gebruikers → eigen account → kaart **Profielfoto** (onder "Mijn planeet").
- **Foto kiezen…**: bestandskiezer (afbeeldingen). Daarna een rond voorbeeld zoals de planeet in het inlogscherm, het
  midden al automatisch uitgesneden; **slepen** verschuift, **schuifbalk/muiswiel** zoomt; **Opslaan** / **Annuleren**.
- **Foto verwijderen**: terug naar de gekleurde planeet.
- Alleen het eigen account. De foto verschijnt alleen op de eigen planeet in het inlogscherm (ook vergrendeld: groene
  gloed en stipje blijven). Geen foto of niet te laden: de gekleurde planeet zoals nu.

## Formaten
Alles wat GdkPixbuf kan lezen: JPG, PNG, GIF (eerste beeld), BMP, TIFF, ICO; WebP via `webp-pixbuf-loader`, HEIC/HEIF/AVIF
via `heif-gdk-pixbuf` + `libheif-plugin-libde265` (HEVC, iPhone) (pakket-afhankelijkheden). EXIF-draaiing wordt toegepast. Onleesbaar: melding "Dit bestand is
geen foto die Universe OS kan lezen." en niets verandert. Het voorbeeld is hooguit 1024 px (grote foto's blijven vlot);
het opslaan snijdt uit het origineel.

## Opslag
Vierkante PNG 512×512 via AccountsService (`org.freedesktop.Accounts.User.SetIconFile`) → `/var/lib/AccountsService/icons/<naam>`.
Eigen foto: geen beheerderswachtwoord (polkit `change-own-user-data`); andermans foto kan niet. Verwijderen:
`SetIconFile('')`.

## Onderdelen
- `shell/profielfoto.py`: `vierkant()` (uitsnede binnen de foto houden, puur), `voorbeeld(pad)`, `maak(pad,x,y,maat)`,
  `opslaan(...)`, `verwijderen()`, `data_url_bestand(pad)` (alleen PNG/JPEG/WebP/GIF, max 2 MB).
- `control_center.py`: `account.photo.choose|preview|save|remove`; `users.detail` geeft `photo` voor het eigen account.
- `ui/profielfoto-ui.js`: kaart + editor; rekenwerk (`beginBeeld`, `verschuif`, `zoom`, `uitsnede`) los testbaar.
- `greeter.py user_list`: `foto` (data-URL uit `LightDM.User.get_image()`); `gebruikersrij.js` + `login.css`: foto op
  de kleine planeet met dezelfde glans en schaduw.

## Testen
`docs/tests/profielfoto.py` (uitsnede, omzetten, kapot bestand), `docs/tests/profielfoto-ui.mjs` (rekenwerk editor);
VM: JPG, PNG, HEIC, groot en kapot bestand; slepen/zoomen; inlogscherm (ook vergrendeld); verwijderen.
