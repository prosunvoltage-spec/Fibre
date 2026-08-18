# Foto-Leitfaden für die NVT-Aufnahme

Diese Vorlage sagt, **welche Fotos pro NVT gebraucht werden**, damit das System
eine belastbare VRA erzeugen kann — statt auf `UNKNOWN` zu laufen und den
Fall in die manuelle Prüfung zu schieben.

Der Leitfaden ist nicht frei erfunden: Er leitet sich aus den Feldern ab, die
die Vision-Pipeline befüllen muss (`app/vision/schema.py`,
`VisionEnvironmentResponse`) und aus den Prädikaten, mit denen die Rule Engine
Regelpläne auswählt (`app/rules/predicates.py`).

---

## 1. Warum es auf die Perspektive ankommt

Die Rule Engine wählt einen Regelplan nur dann, wenn die geforderten
Eigenschaften **belegt** sind. Jedes Feld, das die KI nicht sicher aus dem Foto
ablesen kann, wird konservativ auf `UNKNOWN` gesetzt (Projektregel: im Zweifel
nicht raten). Zu viele `UNKNOWN` → kein Regelplan → `MANUELLE_PRÜFUNG`.

Zwei reale Beispiele aus dem Testbetrieb:

| Fall | Problem | Folge |
|---|---|---|
| Böttcherstraße 4 | Fahrbahnbreite auf dem Foto nicht messbar | VZP1 nur als Vorschlag, keine Auto-Freigabe |
| Nisinghoverweg 13–29 | Gehweg am Kasten nicht zweifelsfrei erkennbar (Gegenlicht, harte Schatten) | Gar kein Regelplan gefunden |

Beide Fälle wären mit den unten stehenden Fotos eindeutig gewesen.

---

## 2. Pflicht-Set: 6 Fotos pro NVT

| # | Foto | Standpunkt / Blickrichtung | Klärt diese Felder |
|---|---|---|---|
| 1 | **Übersicht frontal** | Von der gegenüberliegenden Straßenseite, NVT mittig. Der **komplette Querschnitt** muss drauf sein: Fahrbahn – Bordstein – Gehweg – NVT – Hintergrund | `road_present`, `sidewalk_present`, `cycleway_present`, `parking_lane_present`, `nvt_position`, `road_class` |
| 2 | **NVT-Nahaufnahme** | 2–3 m Abstand, Kasten formatfüllend, **Typenschild/Nummer lesbar** | NVT-Nummer (OCR), `nvt_position`, Zustand/Öffnungsrichtung der Türen |
| 3 | **Blick entlang der Straße – Richtung A** | Kamera **am NVT-Standort**, Blick die Fahrbahn entlang | `curve_present`, `intersection_present`, `junction_present`, `bus_stop_nearby`, `sight_relations_affected`, `parked_vehicles_in_workarea` |
| 4 | **Blick entlang der Straße – Richtung B** | Gleicher Standpunkt, **Gegenrichtung** | wie #3, zusätzlich `cul_de_sac` |
| 5 | **Fahrbahnbreite quer** | Vom Bordstein aus quer über die Fahrbahn, **Zollstock oder Bandmaß im Bild** | `roadway_width_m` ← **das Maß, an dem VZP1 hängt** (Voraussetzung ≥ 6,00 m) |
| 6 | **Arbeitsfläche / Bulli-Standort** | Auf Kopfhöhe (~1,5 m) auf die Fläche, wo der Einblasbulli stehen soll, Boden gut sichtbar | `driveway_present`, `private_property`, `fire_access`, Standort für die Absperr-Visualisierung |

### Zusätzlich messen und **als Text mitliefern**

Die KI kann aus einem Foto keine Meter ableiten. Diese vier Werte bitte notieren
(Zollstock im Bild hilft der späteren Kontrolle, ersetzt die Angabe aber nicht):

- **Fahrbahnbreite** in m ← wichtigster Wert
- **Gehwegbreite** in m
- **Abstand NVT ↔ Fahrbahnkante** in m
- **Radwegbreite** in m, falls vorhanden

> Bis die Review-Oberfläche steht (Phase 7), gehen diese Werte formlos als Liste
> mit — z. B. `NVT 9002: Fahrbahn 6,80 m / Gehweg 2,10 m / Abstand 0,40 m`.

---

## 3. Situative Zusatzfotos

Nur aufnehmen, wenn zutreffend — dann aber unbedingt:

| Situation | Zusatzfoto |
|---|---|
| Bushaltestelle in Sichtweite | Haltestelle mit Abstand zum NVT im Bild |
| Feuerwehrzufahrt / Rettungsweg | Beschilderung + Zufahrt |
| Radweg oder gemeinsamer Geh-/Radweg | **Beschilderung** (Z 237/240/241) — die Zeichen entscheiden, nicht die Pflasterfarbe |
| NVT auf Privatgrund / Betriebsgelände | Grundstücksgrenze, Zaun, Tor, Firmenschild |
| Sackgasse | Wendehammer bzw. Sackgassen-Schild |
| Parkstreifen betroffen | Parkende Fahrzeuge + vorhandene Beschilderung |
| Sonstige Hindernisse | Baumscheibe, Poller, Hydrant, Schacht im Arbeitsbereich |

---

## 4. Aufnahme-Regeln

**Technik**

- Kamerahöhe ~1,5 m (Augenhöhe), Gerät gerade halten — keine starke Aufsicht
- Adress-/Zeitstempel-Einblendung der Foto-App **anlassen** (wird per OCR gelesen)
- GPS/Geotag aktiviert lassen
- Übersichtsfotos (#1, #3, #4, #5) gern im **Querformat**

**Licht**

- **Gegenlicht vermeiden.** Beim Nisinghoverweg-Foto hat die tiefstehende Sonne
  den Gehweg in den Schatten gelegt — die Analyse konnte ihn nicht bestätigen
- Bei harten Schlagschatten: zweite Aufnahme aus anderem Winkel

**Inhalt**

- **Keine bereits eingezeichneten Absperrungen.** Das System zeichnet sie selbst;
  vorhandene rote Linien im Foto stören die Analyse
- Absperrmaterial, das schon vor Ort steht, ist dagegen in Ordnung und wird als
  `existing_barriers` erfasst
- Personen und Kennzeichen möglichst vermeiden (Datenschutz)

**Dateinamen** — die NVT-Nummer wird aus dem Dateinamen gelesen
(`app/classification/nvt_detector.py`, Priorität: User > Dateiname > Ordner > OCR):

```
NVT_9002_1_uebersicht.jpg
NVT_9002_2_nahaufnahme.jpg
NVT_9002_3_richtung_a.jpg
NVT_9002_4_richtung_b.jpg
NVT_9002_5_fahrbahnbreite.jpg
NVT_9002_6_arbeitsflaeche.jpg
```

Alternativ ein Ordner pro NVT (`NVT_9002/…`) — auch das erkennt das System.
Erkannt wird das Muster `NVT` + 4-stellige Nummer.

---

## 5. Kurz-Checkliste zum Abhaken (vor Ort)

```
NVT-Nummer: ________     Adresse: ______________________________

[ ] 1  Übersicht frontal (ganzer Querschnitt im Bild)
[ ] 2  NVT-Nahaufnahme (Nummer lesbar)
[ ] 3  Blick Straße Richtung A
[ ] 4  Blick Straße Richtung B
[ ] 5  Fahrbahnbreite quer (mit Zollstock)
[ ] 6  Arbeitsfläche / Bulli-Standort

Maße:  Fahrbahn ______ m   Gehweg ______ m
       Abstand NVT–Fahrbahn ______ m   Radweg ______ m

Zusatzfotos:
[ ] Bushaltestelle   [ ] Feuerwehrzufahrt   [ ] Radweg-Beschilderung
[ ] Privatgrund      [ ] Sackgasse          [ ] Parkstreifen
[ ] Hindernisse: ____________________________________________
```

---

## 6. Was das System daraus macht

Mit dem vollständigen Pflicht-Set liegen alle 19 auswertbaren Felder vor
(`data_completeness` = 1,0). Damit ist die Voraussetzung für
`AUTO_FREIGABE_VORBEREITET` erfüllt — die menschliche Freigabe bleibt
trotzdem Pflicht (Projektregel 4), das System bereitet sie nur vor, statt den
Fall vorher in die manuelle Prüfung zu schieben.

Fehlen Fotos, passiert nichts Schlimmes: Die betroffenen Felder bleiben
`UNKNOWN`, die Entscheidung landet bei `AUTO_VORSCHLAG` oder
`MANUELLE_PRÜFUNG` — nachvollziehbar begründet im internen HTML-Bericht.
