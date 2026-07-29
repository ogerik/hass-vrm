# VRM API — forecast- en Dynamic ESS-endpoints (Kraagstuk 15)

> **Let op:** alle voorbeelden gebruiken installatie-id `996376`; vervang die door je eigen id.

Vastgelegd op 2026-07-28 door de netwerk-calls van het VRM-dashboard af te kijken en elk endpoint
buiten de browser met `curl` te bewijzen (alle calls gaven `"success": true`).

- **Installatie:** Kraagstuk 15, `idSite = 996376`
- **Base URL:** `https://vrmapi.victronenergy.com/v2`
- **Auth-header:** `x-authorization: Token <VRM_TOKEN>` (token staat in `.env`, nooit in git of deze doc)
- **Timestamp-eenheid:**
  - Queryparams `start` / `end`: **Unix-seconden**
  - Timestamps in de response-reeksen: **Unix-milliseconden**
- **Reeks-formaat:** elk record-veld is een array van `[timestamp_ms, waarde]`-paren, één per interval.
  `waarde` kan `null` zijn (geen data). Een veld dat helemaal geen data heeft is `false` in plaats van een array.
- **`totals`:** elke stats-response bevat naast `records` ook een `totals`-object met dezelfde veldnamen
  (som over de opgevraagde periode).
- **Let op:** met `show_instance=true` verandert de vorm: `records` wordt dan een *lijst* van
  `{"instance": 0, "stats": {...}}` in plaats van een object. Voor HA-sensoren: weglaten.

---

## 1. Forecast (zon- en verbruiksvoorspelling per uur)

**Doel:** voorspelde zonopbrengst en voorspeld verbruik per uur, vandaag + morgen.

```
GET /v2/installations/996376/stats?type=forecast&interval=hours&start=<epoch_s>&end=<epoch_s>
```

| Param | Waarde |
|---|---|
| `type` | `forecast` |
| `interval` | `hours` |
| `start` / `end` | Unix-seconden; het dashboard gebruikt 00:00 lokaal vandaag t/m 48 u later |

**Header:** `x-authorization: Token <VRM_TOKEN>` — **timestamps:** `start`/`end` in seconden, reeksen in de response in milliseconden.

**Eenheid: Wh per uur** (let op: de gerealiseerde reeksen hieronder zijn in kWh!).

**Bewezen met curl (2026-07-28):**

```bash
curl -s -H "x-authorization: Token <VRM_TOKEN>" \
  "https://vrmapi.victronenergy.com/v2/installations/996376/stats?type=forecast&interval=hours&start=1785189600&end=1785362400"
```

```
{"success":true,"records":{"vrm_consumption_fc":[[1785189600000,641.4052441873067],
[1785193200000,644.0375836648458],[1785196800000,654.983071790676],...
→ HTTP 200
```

Ingekort voorbeeldantwoord:

```json
{
  "success": true,
  "records": {
    "vrm_consumption_fc": [
      [1785189600000, 641.4052441873067],
      [1785193200000, 644.0375836648458]
    ],
    "solar_yield_forecast": [
      [1785189600000, 0],
      [1785214800000, 246.17322214516727]
    ],
    "vrm_consumption_fc_adj": false
  },
  "totals": {
    "vrm_consumption_fc": 33941.97212583401,
    "solar_yield_forecast": 73590.65483923581
  }
}
```

| Veld | Betekenis | Eenheid |
|---|---|---|
| `solar_yield_forecast` | voorspelde zonopbrengst per uur | Wh |
| `vrm_consumption_fc` | voorspeld verbruik per uur | Wh |
| `vrm_consum_hp_fc`, `vrm_consum_evcs_fc`, `*_adj` | warmtepomp/EV-varianten; hier niet actief (`false`) | — |

---

## 2. Gerealiseerd (zon en verbruik per uur)

**Doel:** gerealiseerde zonopbrengst en verbruik per uur.

```
GET /v2/installations/996376/stats?type=custom&interval=hours&attributeCodes[]=total_solar_yield&attributeCodes[]=total_consumption&start=<epoch_s>&end=<epoch_s>
```

| Param | Waarde |
|---|---|
| `type` | `custom` |
| `interval` | `hours` (ook `15mins` / `days` mogelijk) |
| `attributeCodes[]` | herhaalbaar; `total_solar_yield`, `total_consumption` |
| `start` / `end` | Unix-seconden |

**Header:** `x-authorization: Token <VRM_TOKEN>` — **timestamps:** `start`/`end` in seconden, reeksen in de response in milliseconden.

**Eenheid: kWh per uur.**

**Bewezen met curl (2026-07-28):**

```bash
curl -s -H "x-authorization: Token <VRM_TOKEN>" \
  "https://vrmapi.victronenergy.com/v2/installations/996376/stats?type=custom&interval=hours&attributeCodes[]=total_solar_yield&attributeCodes[]=total_consumption&start=1785189600&end=1785253520"
```

```
{"success":true,"records":{"total_solar_yield":[[1785211200000,0.10000000149011612],
[1785214800000,0.8000000044703484],[1785218400000,1.5999999940395355],...
→ HTTP 200
```

Ingekort voorbeeldantwoord:

```json
{
  "success": true,
  "records": {
    "total_solar_yield": [
      [1785211200000, 0.10000000149011612],
      [1785214800000, 0.8000000044703484]
    ],
    "total_consumption": [
      [1785189600000, 0.24179840087890625],
      [1785193200000, 0.251800537109375]
    ]
  },
  "totals": {
    "total_solar_yield": 31.89999999664724,
    "total_consumption": 10.966975590214133
  }
}
```

Uren zonder productie (nacht) ontbreken gewoon in de `total_solar_yield`-reeks.

---

## 3. Dynamic ESS (SOC-plan, prijzen, kosten en besparingen)

**Doel:** alles wat het "Dynamic ESS"-blok op het dashboard voedt: SOC-plan per uur,
energieprijzen, gerealiseerde energiestromen én de forecast-stromen. Dit is de bron voor de
tabs "Kosten en besparingen" en "Planning".

```
GET /v2/installations/996376/stats?type=dynamic_ess&interval=hours&start=<epoch_s>&end=<epoch_s>
```

| Param | Waarde |
|---|---|
| `type` | `dynamic_ess` |
| `interval` | `hours` (zo gebruikt het dashboard hem) |
| `start` / `end` | Unix-seconden; dashboard gebruikt 00:00 lokaal t/m einde van de dag |

**Header:** `x-authorization: Token <VRM_TOKEN>` — **timestamps:** `start`/`end` in seconden, reeksen in de response in milliseconden.

**Bewezen met curl (2026-07-28):**

```bash
curl -s -H "x-authorization: Token <VRM_TOKEN>" \
  "https://vrmapi.victronenergy.com/v2/installations/996376/stats?type=dynamic_ess&interval=hours&start=1785189600&end=1785275939"
```

```
{"success":true,"records":{"vrm_to_grid_fc":[[1785189600000,-641.4052441873067],
[1785193200000,-644.0375836648458],[1785196800000,-654.983071790676],...
→ HTTP 200
```

Ingekort voorbeeldantwoord (relevante velden):

```json
{
  "success": true,
  "records": {
    "vrm_soc_plan":       [[1785189600000, 34], [1785193200000, 33.25]],
    "deGb":               [[1785189600000, 0.38851043]],
    "deGs":               [[1785189600000, 0.38851043]],
    "deBc":               [[1785189600000, 0.005]],
    "grid_history_from":  [[1785189600000, 0.26000213623046875]],
    "grid_history_to":    [[1785211200000, 0.350006103515625]],
    "vrm_to_grid_fc":     [[1785189600000, -641.4052441873067]],
    "vrm_to_battery_fc":  [[1785189600000, 0]],
    "total_solar_yield":  [[1785211200000, 0.10000000149011612]],
    "total_consumption":  [[1785189600000, 0.24179840087890625]]
  },
  "totals": { "vrm_soc_plan": 1129.65, "deGb": 8.06, "grid_history_to": 16.43 }
}
```

Alle velden in `records`:

| Veld | Betekenis | Eenheid |
|---|---|---|
| `vrm_soc_plan` | gepland accu-SOC per uur (Planning-tab) | % (0–100) |
| `deGb` | inkoopprijs stroom per uur (Dynamic ESS "grid buy") | €/kWh |
| `deGs` | verkoopprijs stroom per uur ("grid sell") | €/kWh |
| `deBc` | accu-slijtagekosten per uur ("battery costs") | € |
| `grid_history_from` | gerealiseerde import van net per uur | kWh |
| `grid_history_to` | gerealiseerde export naar net per uur | kWh |
| `Gc` / `Gb` | net → verbruik / net → accu | kWh |
| `Bc` / `Bg` | accu → verbruik / accu → net | kWh |
| `Pb` / `Pg` | PV → accu / PV → net | kWh |
| `total_battery_flow` / `total_grid_flow` | netto accu-/netstroom per uur | kWh |
| `total_solar_yield` / `total_consumption` | gerealiseerde zon / verbruik (zelfde als endpoint 2) | kWh |
| `solar_yield_forecast` / `vrm_consumption_fc` | zelfde forecast-reeksen als endpoint 1 | Wh |
| `vrm_to_grid_fc` / `vrm_to_battery_fc` | gepland naar net (negatief = import) / naar accu | Wh |
| `vrm_ffcs` | uren geforceerd volladen (periodic full charge); vrijwel altijd 0 | — |

### €-tegels "Kosten en besparingen" (geen apart endpoint!)

Het dashboard doet **geen** aparte API-call voor de vier €-tegels; ze worden client-side uit
bovenstaande reeksen berekend. Benadering (op uurbasis; VRM rekent intern deels op
15-min-resolutie en laat het lopende uur soms weg, dus verwacht kleine afwijkingen):

- **Net kosten** = Σ `grid_history_from[h]` × `deGb[h]`
- **Net besparing** = Σ `grid_history_to[h]` × `deGs[h]`
- **Accu kosten** = Σ `deBc[h]` over uren met accugebruik
- **Totaal resultaat** = Net besparing − Net kosten − Accu kosten
- **Per-uur-resultaat** = `grid_history_to[h] × deGs[h] − grid_history_from[h] × deGb[h]` — het saldo van de groene (besparing) en rode (kosten) balk per uur, die het dashboard als aparte balken tekent; in de mappingtabel heet deze afgeleide reeks `cost_savings`.

Gevalideerd tegen het dashboard (2026-07-28 ± 17:40): tegels € 3.70 / € 1.25 / € 0.06 / € 2.39;
formules hierboven gaven 3.70 / 1.25 / 0.05–0.09 / ≈ 2.4.

---

## 4. Dynamic ESS-prijzen (15 min, Planning-tab "Energie prijzen")

```
GET /v2/installations/996376/stats?type=dynamic_ess_prices&interval=15mins&start=<epoch_s>&end=<epoch_s>
```

| Param | Waarde |
|---|---|
| `type` | `dynamic_ess_prices` |
| `interval` | `15mins` (zo gebruikt het dashboard hem) |
| `start` / `end` | Unix-seconden |

**Header:** `x-authorization: Token <VRM_TOKEN>` — **timestamps:** `start`/`end` in seconden, reeksen in de response in milliseconden.

**Bewezen met curl (2026-07-28):**

```bash
curl -s -H "x-authorization: Token <VRM_TOKEN>" \
  "https://vrmapi.victronenergy.com/v2/installations/996376/stats?type=dynamic_ess_prices&interval=15mins&start=1785189600&end=1785276000"
```

```
{"success":true,"records":{"deGb":[[1785189600000,0.38851043],[1785190500000,0.38851043],
[1785191400000,0.38851043],[1785192300000,0.38851043],[1785193200000,0.37337332999999995],...
→ HTTP 200
```

Ingekort voorbeeldantwoord:

```json
{
  "success": true,
  "records": {
    "deGb": [[1785189600000, 0.38851043], [1785190500000, 0.38851043]],
    "deGs": [[1785189600000, 0.38851043], [1785190500000, 0.38851043]]
  },
  "totals": { "deGb": 32.24268849999998, "deGs": 32.24268849999998 }
}
```

Zelfde prijzen als `deGb`/`deGs` in endpoint 3, maar op 15-minutenresolutie (96 punten/dag), €/kWh.

---

## 5. Dynamic ESS-instellingen

```
GET /v2/installations/996376/dynamic-ess-settings
```

Geen queryparams. **Header:** `x-authorization: Token <VRM_TOKEN>`. Geen tijdreeks, dus geen
timestamp-eenheid; datums in de response (`createdOn`/`updatedOn`) zijn strings `YYYY-MM-DD HH:MM:SS`.

**Bewezen met curl (2026-07-28):**

```bash
curl -s -H "x-authorization: Token <VRM_TOKEN>" \
  "https://vrmapi.victronenergy.com/v2/installations/996376/dynamic-ess-settings"
```

```
{"success":true,"data":{"idSite":996376,"gridSell":1,...
→ HTTP 200
```

Ingekort voorbeeldantwoord:

```json
{
  "success": true,
  "data": {
    "idSite": 996376,
    "batteryCapacity": 16,
    "dischargePower": 16,
    "chargePower": 16,
    "batteryCosts": 0.01,
    "maxPowerFromGrid": 17,
    "maxPowerToGrid": 16,
    "buyPriceFormula": "(p+0.03+0.13)*1.21",
    "sellPriceFormula": "(p+0.03+0.13)*1.21",
    "idBiddingZone": 26,
    "isOn": true,
    "isGreenModeOn": false
  }
}
```

Nuttige velden: `isOn` (DESS aan/uit), `batteryCapacity` (16 kWh), `chargePower`/`dischargePower` (kW),
`batteryCosts` (0.01 €/kWh, bron van `deBc`), `buyPriceFormula`/`sellPriceFormula`
(`(p+0.03+0.13)*1.21`), `idBiddingZone` (26 = NL).

---

## Mappingtabel API-veld → interface-attribute

| Interface-attribute | API-veld (endpoint) | Eenheid | Opmerking |
|---|---|---|---|
| `total_solar_yield` | `records.total_solar_yield` (2 of 3) | kWh/uur | gerealiseerde zon; totaal in `totals.total_solar_yield` |
| `solar_yield_forecast` | `records.solar_yield_forecast` (1 of 3) | **Wh**/uur | voorspelde zon; deel door 1000 voor kWh |
| `total_consumption` | `records.total_consumption` (2 of 3) | kWh/uur | gerealiseerd verbruik |
| `vrm_consumption_fc` | `records.vrm_consumption_fc` (1 of 3) | **Wh**/uur | voorspeld verbruik |
| `soc_plan` | `records.vrm_soc_plan` (3) | % | gepland SOC per uur (Planning-tab) |
| `cost_savings` | afgeleid (3): `grid_history_to×deGs − grid_history_from×deGb` per uur | €/uur | de groene/rode balken; geen direct API-veld |
| `total_result` | afgeleid (3): `net_saving − grid_costs − battery_costs` | € | tegel "Totaal resultaat" |
| `net_saving` | afgeleid (3): Σ `grid_history_to × deGs` | € | tegel "Net besparing" |
| `battery_costs` | `records.deBc` (3), gesommeerd | € | tegel "Accu kosten"; config in `dynamic-ess-settings.batteryCosts` |
| `grid_costs` | afgeleid (3): Σ `grid_history_from × deGb` | € | tegel "Net kosten" |
