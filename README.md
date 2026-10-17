# hass-vrm

Het **Victron VRM-dashboard nagebouwd in Home Assistant** — inclusief de data
die de officiële integraties niet leveren: Dynamic ESS-planning, kosten &
besparingen in euro's, zon/verbruik-voorspelling per uur, en day-ahead
energieprijzen. Met een echte datumkiezer om dagen terug te bladeren.

Dit is een **template-repo**, geen HACS-integratie: je kopieert een package en
een dashboard-view naar je eigen Home Assistant en past een paar id's aan.
De kern is [`docs/vrm-api.md`](docs/vrm-api.md): reverse-engineered documentatie
van de (onofficiële) VRM API-endpoints achter het VRM-portaal, inclusief de
€-formules achter de Dynamic ESS-tegels.

## Wat je krijgt

1. **Installatie gegevens** — zon en verbruik per uur (gerealiseerd als balk,
   voorspelling doorzichtig) + accu-SOC live en gepland als lijn.
2. **Dynamic ESS — kosten en besparingen** — groene/rode €-balken per uur +
   blauwe accu-lijn (kWh, + = laden / − = ontladen) + vier €-totalen met uitleg.
3. **Planning** — day-ahead uurprijs + gepland accu-SOC, 36 uur vooruit.
4. **Datumkiezer** — alle grafieken en tegels schuiven mee naar elke gekozen
   dag; de data wordt on-demand bij VRM opgehaald.

## Vereisten

- Victron-installatie met VRM-account (en optioneel Dynamic ESS aan)
- Home Assistant met **HACS**, en daaruit: `apexcharts-card` en
  `config-template-card`
- **EnergyZero** core-integratie voor day-ahead prijzen (ANWB, EnergyZero e.a.;
  gebruik anders Nord Pool/ENTSO-E en pas de prijzen-sensor aan)
- Voor de live SOC-lijn: een lokale Victron-integratie
  ([sfstar/hass-victron](https://github.com/sfstar/hass-victron), Modbus TCP)
  of een andere SOC-sensor
- `packages:` include in `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

## Installatie

1. **VRM-token aanmaken:** VRM-portaal → Voorkeuren → Integraties → Access
   tokens. Zet hem in `secrets.yaml` als de *volledige headerwaarde*:

   ```yaml
   vrm_token: "Token <jouw token>"
   ```

2. **Package plaatsen:** kopieer
   [`packages/victron_vrm.yaml`](packages/victron_vrm.yaml) naar
   `/config/packages/` en volg het `AANPASSEN`-blok bovenin (installatie-id,
   EnergyZero entry-id). Herstart HA en controleer dat
   `sensor.vrm_forecast_raw`, `sensor.vrm_dess` en `sensor.energieprijzen`
   zich vullen.

3. **Dashboard aanmaken en view pushen** (vanaf je werkstation):

   ```sh
   cp .env.example .env      # vul HA_URL + HA_TOKEN (long-lived token) in
   pip install -r requirements.txt
   python3 create_dashboard.py victron-vrm VRM mdi:sine-wave
   python3 apply_dashboard.py victron-vrm dashboard/vrm-view.yaml
   ```

   Pas eerst het `AANPASSEN`-blok bovenin
   [`dashboard/vrm-view.yaml`](dashboard/vrm-view.yaml) aan (je eigen
   meter-/zon-/SOC-sensoren). De view gebruikt HA's sections-layout en werkt
   op desktop én mobiel.

## Eigen verbruiksvoorspelling voor DESS (optioneel)

VRM voorspelt je verbruik uit een meerweeks gemiddelde. Eén drukke dag of een
vakantie trekt dat weken scheef, en Dynamic ESS houdt dan accu achter voor
verbruik dat niet komt. [`packages/dess_verbruik.yaml`](packages/dess_verbruik.yaml)
vervangt die voorspelling elk uur door een eigen profiel: per uur het 60e
percentiel van de laatste 6 vergelijkbare dagen, zonder vakantiedagen. De
komende 36 uur gaan naar VRM via `POST /installations/<id>/adjust-consumption`,
hetzelfde als het potlood bij "Verbruik" in de VRM-app.

1. Zet je installatie-id bij `vrm_site:` in het package (één plek) en kopieer
   het naar `/config/packages/`. Zelfde `vrm_token`-secret als hierboven.
2. Herstart HA (of herlaad YAML) en vul de helpers in:

| Helper | Voorbeeld | Betekenis |
|---|---|---|
| DESS: daggroepen | `ma,di,wo,do,vr\|za,zo` | Welke dagen vergelijkbaar zijn. Leeg = werkdag/weekend. Iemand thuis op wo/vr: `ma,di,do\|wo,vr\|za,zo` |
| DESS: vakantiedagen | `2026-10-10/2026-10-16, 2026-12-24/2026-12-31` | Tellen niet mee in het normale profiel |
| DESS: vakantie | aan/uit | Aan = gebruik juist het profiel van de vakantiedagen |
| DESS: data vanaf | `2026-09-11` | Oudere dagen negeren, bijv. na een wijziging in je meters |
| DESS: eigen verbruiksvoorspelling | aan/uit | Hoofdschakelaar. Uit = terug naar VRM's eigen voorspelling |

`sensor.dess_verbruik_voorspelling` toont wat er het laatst is verstuurd
(kWh komende 24 uur, per uur in het attribute `uren`).

Backtest op één installatie (1 sep t/m 9 okt 2026): VRM zat gemiddeld
11,1 kWh/dag te hoog, dit profiel −0,4 kWh/dag (fout per uur 0,40 kWh i.p.v.
0,76). Beperking: alleen de totale voorspelling wordt aangepast. Heb je in VRM
een aparte EV-lader- of warmtepompvoorspelling, dan klopt VRM's splitsing
daarna niet meer met het totaal.

## Kanttekeningen

- De DESS-endpoints (`type=dynamic_ess` e.d.) zijn **niet officieel
  gedocumenteerd** door Victron en kunnen zonder aankondiging wijzigen. Zie
  [`docs/vrm-api.md`](docs/vrm-api.md) voor alles wat er wel over bekend is
  (met curl-bewijs).
- De vier €-totalen zijn client-side berekend, net als het VRM-portaal zelf
  doet; kleine afrondingsverschillen met VRM zijn normaal (VRM rekent intern
  deels op 15-minuten-resolutie).
- Bij het wisselen van datum bouwen de grafieken zichzelf opnieuw op en wordt
  de data vers bij VRM opgehaald; 5-15 seconden "Loading..." is normaal.

## Herkomst

Gebouwd voor de thuisinstallatie "Kraagstuk 15" (3x Quattro-II, 16 kWh accu,
Dynamic ESS + ANWB dynamisch). Vragen of verbeteringen: open een issue.
