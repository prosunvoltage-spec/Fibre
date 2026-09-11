# Herkunft

Dieser Skill stammt aus dem öffentlichen Repository
[Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), Ordner
`skills/taste-skill`, Stand Commit `ccbc156`. Lizenz: MIT, Text in `LICENSE`.

Übernommen wurde nur diese eine Variante. Das Repository enthält zwölf
weitere (brutalist, minimalist, soft, gpt, image-to-code und andere), die auf
andere Ästhetiken zielen und hier nichts beitragen.

## Was er ist

Ein reines Textregelwerk gegen schablonenhafte Oberflächen: Vorgaben zu
Layout, Typografie, Farbe, Bewegung und eine Prüfliste vor der Abgabe. Keine
Skripte, keine Daten, keine externen Dienste. Es gibt nichts auszuführen.

## Einordnung für dieses Projekt

Der Skill setzt React, Next.js, Tailwind und die Motion-Bibliothek voraus.
Diese Website ist reines HTML, CSS und JavaScript, der Architekturteil greift
also nicht. Die Gestaltungsregeln greifen sehr wohl, und die Seite erfüllt die
meisten bereits: Navi unter 80 px und einzeilig, Hero im ersten Bildschirm,
Labels über den Formularfeldern, Schatten nur wo sie Hierarchie zeigen, ein
einziger Akzent, abwechselnde Abschnittslayouts.

Bewusst nicht übernommen:

- **Dunkelmodus als Pflicht.** Der Skill verlangt ihn für Consumer-Seiten.
  Hier geht es um eine regionale Dienstleisterseite, deren Besucher einmal
  Kontakt aufnehmen. Ein zweites Farbschema wäre Aufwand ohne Nutzen.
- **Die Schriftvorschläge** Geist, Outfit, Satoshi. Hanken Grotesk ist gesetzt.
- **Die Bewegungsmuster** mit GSAP und ScrollTrigger. Sie widersprechen der
  Entscheidung, Bewegung auf einen Moment zu beschränken, und brauchen
  Bibliotheken, die die Seite nicht lädt.
