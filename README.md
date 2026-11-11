# MageHelper

Fire, Arcane and Frost Mage helper for **World of Warcraft: Wrath of the Lich King 3.3.5a** (Interface 30300), made for private servers. Works on German and English clients.

*Deutsche Kurzfassung weiter unten.*

## Features

- **Rotation bar:** shows what to cast next – Living Bomb timing (never clip before the explosion), Hot Streak → Pyroblast, Combustion window, burst queue after Combustion (Mirror Image, potion, gloves), Fireballs per minute and cast-gap warnings. Includes a one-button that follows the recommendation.
- **Arcane rotation:** its own button set (Arcane Blast, Arcane Missiles, Arcane Barrage, Arcane Power with Icy Veins if known, Presence of Mind, Mirror Image, Evocation, Mana Gem). Cooldowns as soon as they are ready (Mirror Image first with the T10 4-piece, Presence of Mind only while burning), Mana Gem in combat when it fills up fully, Evocation in combat below 30% mana, Arcane Missiles on Missile Barrage, Arcane Barrage/Fire Blast while moving. **Burn vs. conserve:** burn (Arcane Blast at 4 stacks) always during Arcane Power, Heroism/Bloodlust or the T10 Mirror Image buff, and while your mana is above a threshold (default 35%); below it, *automatic* keeps burning when the boss's time to die (from its health loss, `boss1`-`boss4` before the target) is shorter than your mana lasts (measured drain while burning, or a Missile Barrage cycle model at the start of a fight, with Mana Gem and Evocation spread over their cooldowns); otherwise conserve (Arcane Blast to 3 stacks, then Arcane Missiles). *Mana* mode uses the threshold only. The info line shows stacks, mana, burn/conserve and cooldowns; `/mh debug on` explains the decision.
- **Frost rotation:** its own button set (Frostbolt, Ice Lance, Deep Freeze, Frostfire Bolt, a cooldown button for Icy Veins + Mirror Image + on-use trinkets, Cold Snap, Summon Water Elemental, Mana Gem, Evocation). Water Elemental whenever no pet is out, cooldowns as soon as they are ready (Mirror Image first with the T10 4-piece), Mana Gem in combat when it fills up fully, Deep Freeze on Fingers of Frost or a frozen target, Cold Snap when Deep Freeze has more than 15 s left, Frostfire Bolt on Brain Freeze, Frostbolt as filler; while moving Ice Lance (with Fingers of Frost or a frozen target), Fire Blast, then Ice Lance. Based on the SimulationCraft 3.3.3 frost list. The info line shows Fingers of Frost charges, Brain Freeze, the Deep Freeze cooldown, your pet and mana.
- **Fire, Arcane or Frost automatically:** the talent tree with the most points picks the rotation; it switches with your spec, out of combat. Can be fixed in the settings or with `/mh rota`.
- **Spellsteal helper (all rotations):** when your hostile target has a stealable buff worth taking (Lord Jaraxxus' Nether Power, Vampiric Might and Shroud of the Occult at Lady Deathwhisper, the Faction Champions' Heroism/Bloodlust, Earth Shield and Hand of Freedom, Paletress' Renew, Sjonnir's Lightning Shield), the Steal button glows red right after the emergencies (Ice Block, Counterspell) and before damage. Out of Spellsteal's 30 yd range it turns blue with a note in the info line; when only your focus has such a buff, the info line says so. The button casts on your mouseover, otherwise on your target. A small icon above the bar shows the target's first stealable buff (stacks, time left, orange border for the worth list); its tooltip lists all stealable buffs on target and focus. Optionally every stealable buff is recommended (not urgent).
- **Buff bar:** red/green status for Molten Armor, Arcane Brilliance, Focus Magic in/out, flask, food, Wild Magic, Hyperspeed and Heroism. The expected flask is configurable per character; *automatic* picks the best one for your class and spec (Frost Wyrm, Endless Rage or Stoneblood).
- **Molten Armor with the T9 2-piece bonus:** click 1 puts on T9 pieces from your bags (found by item ID, any T9 version) until two are worn, click 2 casts Molten Armor, then your previous gear goes back on automatically. The button color shows the step and whether the active armor has the bonus. Can be switched off in the settings.
- **Focus Magic target picker:** scrollable group list with the filters *only mages* and *only healers without Focus Magic* (healer specs are detected by inspecting talents – handy for Valithria). Save a fixed partner, pick a temporary target, switch back with one click.
- **ICC helpers:** Ice Block for boss mechanics (Pungent Blight, Boiling Blood, Swarming Shadows), Sindragosa stack warnings, Putricide Malleable Goo, Blood Queen essence, mandatory interrupts and Lich King threat.
- **Analyzer:** boss fight and training-dummy runs with A/B comparison, fight report and death recap.
- **Color themes:** Standard, Pink, Blue and Red for bars and windows. Signal colors (green, red, orange, blue) never change, and all themes keep readable contrast.
- **Settings window and profiles** (Ace3): `/mh config` or *Interface → AddOns → MageHelper*. Every character starts with its own profile; profiles can be shared or copied.

## Installation

1. Download or clone this repository into `World of Warcraft\Interface\AddOns\`.
2. The folder must be named exactly **`MageHelper`** (WoW only loads it when the folder matches `MageHelper.toc`). If you downloaded the ZIP, rename `MageHelper-main` to `MageHelper`.
3. Restart the game completely (a new addon folder is not picked up by `/reload`).

```bash
git clone https://github.com/Richie1710/MageHelper.git MageHelper
```

Ace3 is embedded – no other addons are required.

## Usage

| Command | What it does |
| --- | --- |
| `/mh help` | List all commands |
| `/mh config` | Open the settings window |
| `/mh rota auto\|fire\|arcane\|frost` | Rotation: automatic by talents, or fixed |
| `/mh burn auto\|mana [percent]` | Arcane burn/conserve: time-to-die estimate or mana threshold only (10–90%) |
| `/mh steal on\|off\|all\|worth` | Spellsteal hint on/off; *all* also recommends unlisted stealable buffs, *worth* only the list (German: `/mh raub an\|aus\|alle\|lohnend`) |
| `/mh fm` | Open the Focus Magic target picker |
| `/mh t9` | Show T9 pieces found and the Molten Armor status |
| `/mh theme standard\|pink\|blue\|red` | Color theme |
| `/mh flask auto\|frost\|rage\|stone\|mojo\|resi\|any` | Which flask the buff bar expects |
| `/mh lang auto\|de\|en` | Display language (default: client language) |
| `/mh analyse` | Open the analyzer window |
| `/mh debug on` | Live line explaining why something is recommended |

`/magehelper` works as an alias for `/mh`.

## Development

There is no build step; the game loads the files straight from the folder. `tools/smoke.py` runs the addon (including the embedded Ace3) outside the game in Lua 5.1 against a fake WoW API (`tools/wowstub.lua`), once as a German and once as an English client:

```bash
py -m venv venv
venv\Scripts\pip install lupa
venv\Scripts\python -I tools\smoke.py
```

It replays a fight, every slash command, the settings window, profile switching, the Focus Magic picker and the Spellsteal helper, and exits with code 1 on any failed check or Lua error. It does not replace testing in the game.

## Credits

- Embedded libraries: [Ace3](https://www.wowace.com/projects/ace3) (Release-r960) by the Ace3 Development Team, see [`Libs/Ace3-LICENSE.txt`](Libs/Ace3-LICENSE.txt).
- Original addon (KahuRota) by Kahu/Shiro.

## AI disclaimer

Parts of this addon's source code, its tests and this README were created or revised with the help of generative AI (an AI coding assistant), under the direction of the maintainer. This includes the German/English localization, the Focus Magic target picker, the move to Ace3 and the out-of-game smoke test. Changes are checked with the automated smoke test outside the game; they are not guaranteed to have been tested in every in-game situation. Please report problems as an issue.

This notice is given voluntarily for transparency.

## License

MageHelper is released under the [MIT License](LICENSE) – you may use, change and share it as long as the copyright notice (Kahu/Shiro) and the license text stay included. The embedded Ace3 libraries keep their own license ([`Libs/Ace3-LICENSE.txt`](Libs/Ace3-LICENSE.txt)).

---

## Deutsch (Kurzfassung)

Helfer für Feuer-, Arkan- und Frostmagier in **WotLK 3.3.5a**, für deutsche und englische Clients:

- **Rota-Leiste** mit Empfehlung für den nächsten Zauber
- **Arkan- und Frost-Rota** mit eigenen Buttons; Feuer, Arkan oder Frost wird automatisch nach der Skillung gewählt (`/mh rota auto|feuer|arkan|frost`)
- **Frost:** Wasserelementar, wenn kein Pet da ist; Eisige Adern, Spiegelbild und Schmuckstücke sofort; Tiefkühlen bei Eisige Finger; Kälteeinbruch, wenn Tiefkühlen noch über 15 s Abklingzeit hat; Frostfeuerblitz bei Hirnfrost; sonst Frostblitz
- **Burn oder Sparen** bei Arkan: Burn über der Mana-Schwelle und während Arkane Macht/Heldentum; automatisch darunter weiter, solange dein Mana bis zum Tod des Bosses reicht, oder nur nach Mana-Schwelle (`/mh burn auto|mana [Prozent]`)
- **Zauberraub-Hilfe** (Feuer und Arkan): lohnende stehlbare Buffs auf dem Ziel (z. B. Netherkraft bei Jaraxxus, Heldentum/Kampfrausch der Fraktionschampions) lassen den Raub-Button rot leuchten, außer Reichweite (30 m) blau; Hinweis, wenn nur der Fokus so einen Buff hat; Symbol mit dem stehlbaren Buff über der Leiste (`/mh raub an|aus|alle|lohnend`)
- **Buff-Leiste**
- **Glühende Rüstung mit T9-Bonus:** T9 automatisch an- und danach wieder ausziehen
- **Farbschemata** Standard, Rosa, Blau und Rot (`/mh theme`); die Signalfarben bleiben immer gleich
- **Flask pro Charakter einstellbar** (`/mh flask`), automatisch passend zu Klasse und Skillung
- **MF-Ziel-Auswahl** mit den Filtern „nur Mages“ und „nur Heiler ohne MF“
- **ICC-Hinweise**
- **Analyzer**
- **Einstellungsfenster mit Profilen** (`/mh config`)

**Installation:**
1. Den Ordner als **`MageHelper`** nach `Interface\AddOns\` legen. Beim ZIP-Download `MageHelper-main` in `MageHelper` umbenennen.
2. Das Spiel komplett neu starten.

Alle Befehle zeigt `/mh help`.

**Lizenz:** MIT (siehe [LICENSE](LICENSE)). Nutzen, ändern und weitergeben ist erlaubt, solange der Copyright-Hinweis (Kahu/Shiro) und der Lizenztext erhalten bleiben.

**KI-Hinweis:** Teile des Quellcodes, der Tests und dieser README wurden unter Anleitung des Maintainers mit Unterstützung generativer KI (eines KI-Programmierassistenten) erstellt oder überarbeitet. Das betrifft unter anderem:
- die deutsch-englische Lokalisierung
- die MF-Ziel-Auswahl
- den Umbau auf Ace3
- den Test außerhalb des Spiels

Änderungen werden mit dem automatisierten Test außerhalb des Spiels geprüft. Dass sie in jeder Spielsituation getestet wurden, ist nicht garantiert. Probleme bitte als Issue melden. Dieser Hinweis erfolgt freiwillig zur Transparenz.
