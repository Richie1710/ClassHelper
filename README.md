# ClassHelper

Class rotation helper for **World of Warcraft: Wrath of the Lich King 3.3.5a** (Interface 30300), made for private servers. Works on German and English clients. It picks the module for your class and the rotation for your spec automatically. Currently: **Mage** (Fire, Arcane, Frost) and **Paladin** (Protection, Retribution, Holy buff bar; the Paladin rotations are still being built). Other classes get the shared parts (buff bar with flask and food, analyzer). Formerly called *MageHelper*.

*Deutsche Kurzfassung weiter unten.*

## Features

- **Rotation bar:** shows what to cast next – Living Bomb timing (never clip before the explosion), Hot Streak → Pyroblast, Combustion window, burst queue after Combustion (Mirror Image, potion, gloves), Fireballs per minute and cast-gap warnings. Includes a one-button that follows the recommendation.
- **Arcane rotation:** its own button set (Arcane Blast, Arcane Missiles, Arcane Barrage, Arcane Power with Icy Veins if known, Presence of Mind, Mirror Image, Evocation, Mana Gem). Cooldowns as soon as they are ready (Mirror Image first with the T10 4-piece, Presence of Mind only while burning), Mana Gem in combat when it fills up fully, Evocation in combat below 30% mana, Arcane Missiles on Missile Barrage, Arcane Barrage/Fire Blast while moving. **Burn vs. conserve:** burn (Arcane Blast at 4 stacks) always during Arcane Power, Heroism/Bloodlust or the T10 Mirror Image buff, and while your mana is above a threshold (default 35%); below it, *automatic* keeps burning when the boss's time to die (from its health loss, `boss1`-`boss4` before the target) is shorter than your mana lasts (measured drain while burning, or a Missile Barrage cycle model at the start of a fight, with Mana Gem and Evocation spread over their cooldowns); otherwise conserve (Arcane Blast to 3 stacks, then Arcane Missiles). *Mana* mode uses the threshold only. The info line shows stacks, mana, burn/conserve and cooldowns; `/ch debug on` explains the decision.
- **Frost rotation:** its own button set (Frostbolt, Ice Lance, Deep Freeze, Frostfire Bolt, a cooldown button for Icy Veins + Mirror Image + on-use trinkets, Cold Snap, Summon Water Elemental, Mana Gem, Evocation). Water Elemental when no pet is out (in combat urgent, out of combat only as a pre-pull hint with an attackable target), cooldowns as soon as they are ready (Mirror Image first with the T10 4-piece; only on-use trinkets get a `/use` line), Mana Gem in combat when it fills up fully, Deep Freeze on Fingers of Frost or a frozen target, then Frostbolt on Fingers of Frost or a frozen target, Cold Snap when Deep Freeze has more than 15 s left and Icy Veins is on cooldown, Frostfire Bolt on Brain Freeze (Fireball before you learn Frostfire Bolt), Frostbolt as filler; while moving Ice Lance (with Fingers of Frost or a frozen target), Fire Blast, then Ice Lance. Order as in the SimulationCraft 3.3 frost list. The info line shows Fingers of Frost charges, Brain Freeze, the Deep Freeze cooldown, your pet and mana.
- **Fire, Arcane or Frost automatically:** the talent tree with the most points picks the rotation; it switches with your spec, out of combat. Can be fixed in the settings or with `/ch rota`.
- **Spellsteal helper (all rotations):** when your hostile target has a stealable buff worth taking (Lord Jaraxxus' Nether Power, Vampiric Might and Shroud of the Occult at Lady Deathwhisper, the Faction Champions' Heroism/Bloodlust, Earth Shield and Hand of Freedom, Paletress' Renew, Sjonnir's Lightning Shield), the Steal button glows red right after the emergencies (Ice Block, Counterspell) and before damage. Out of Spellsteal's 30 yd range it turns blue with a note in the info line; when only your focus has such a buff, the info line says so. The button casts on your target (the unit the recommendation checks); hold Shift to cast on your mouseover instead, e.g. the focus mob. A small icon above the bar shows the target's first stealable buff (stacks, time left, orange border for the worth list); its tooltip lists all stealable buffs on target and focus. Optionally every stealable buff is recommended (not urgent).
- **Buff bar:** red/green status for Molten Armor, Arcane Brilliance, Focus Magic in/out, flask, food, potion, Hyperspeed and Heroism. The expected flask is configurable per character; *automatic* picks the best one for your class and spec (Frost Wyrm, Endless Rage or Stoneblood).
- **Potion per character:** the cooldown buttons of all three rotations (Fire: Mirror Image + Mana Sapphire, Arcane: Arcane Power, Frost: Icy Veins + Mirror Image) also use the chosen potion – *automatic* follows the active rotation (Fire: Wild Magic, Arcane and Frost: Speed), or fixed Speed, Wild Magic, Runic Mana, Indestructible or none. The buff bar's potion icon checks that potion's buff; Runic Mana (no buff) and *none* show grey. A change in combat applies after the fight.
- **Molten Armor with the T9 2-piece bonus:** click 1 puts on T9 pieces from your bags (found by item ID, any T9 version) until two are worn, click 2 casts Molten Armor, then your previous gear goes back on automatically. The button color shows the step and whether the active armor has the bonus. Can be switched off in the settings.
- **Focus Magic target picker:** scrollable group list with the filters *only mages* and *only healers without Focus Magic* (healer specs are detected by inspecting talents – handy for Valithria). Save a fixed partner, pick a temporary target, switch back with one click.
- **ICC helpers:** Ice Block for boss mechanics (Pungent Blight, Boiling Blood, Swarming Shadows), Sindragosa stack warnings, Putricide Malleable Goo, Blood Queen essence, mandatory interrupts and Lich King threat.
- **Putricide Tear Gas (normal 10/25 only):** just above 80% / 35% of his health (lead adjustable, 0.5–5%) the Invisibility button turns red so you are invisible before the gas stuns the raid; once it lands, cancel Invisibility and damage him alone. The info line counts down to his re-engage (drink casts and yells as in DBM) and, if your threat is too high then, suggests Ice Block or stop casting (`/ch teargas on|off|0.5-5`).
- **Analyzer:** boss fight and training-dummy runs with A/B comparison, fight report and death recap.
- **Color themes:** Standard, Pink, Blue and Red for bars and windows. Signal colors (green, red, orange, blue) never change, and all themes keep readable contrast.
- **Settings window and profiles** (Ace3): `/ch config` or *Interface → AddOns → ClassHelper*. Every character starts with its own profile; profiles can be shared or copied.

## Paladin

- **Mode by talents:** Protection and Retribution get their own button sets, Holy only the buff bar. Fixed with `/ch rota auto|prot|ret|holy` or in the settings.
- **Buttons:** secure buttons with fixed macros; only the glow shows the recommendation. Protection: taunt (Hand of Reckoning, Righteous Defense on the boss's target) and defensive buttons first, then Righteous Fury, seal, Seal of Command for AoE, Holy Shield, Judgement, Hammer of the Righteous, Consecration, Shield of Righteousness, Hammer of Wrath, Avenger's Shield, Divine Plea. Retribution: seal, Seal of Command, Avenging Wrath, Judgement, Crusader Strike, Divine Storm, Consecration, Hammer of Wrath, Exorcism, Holy Wrath, Divine Plea.
- **Judgement:** Wisdom or Light (`/ch judgement wisdom|light`). **AoE mode:** `/ch aoe on|off`.
- **Protection rotation:** Righteous Fury (always, regardless of PallyPower) > seal > Avenger's Shield on the pull > Holy Shield > 969 (Judgement > Hammer of the Righteous > Consecration > Shield of Righteousness; AoE mode: Hammer and Consecration first) > Hammer of Wrath (target at 20 % or less) > Avenger's Shield > Divine Plea. Real cooldowns (the GCD ignored), usability and range are checked; an ability ready within 0.3 s keeps the glow (blue until clickable).
- **Taunt (Protection):** Hand of Reckoning glows red, Righteous Defense on the boss's target while it is on cooldown, when the boss attacks another player who carries the swap debuff at the threshold and your own stacks are gone: Lady Deathwhisper (Touch of Insignificance, 3), Saurfang (Rune of Blood on the other tank), Festergut (Gastric Bloat, 6), Putricide (Mutated Plague, 2), Sindragosa (Mystic Buffet, 3), Gormok (Impale, 3 / heroic 2), Lich King heroic (Soul Reaper, off by default). Never while the boss attacks you; the boss must be your target. Each rule and threshold can be changed in the settings (*Protection: taunt*).
- **Defensives (Protection):** Divine Protection on Saurfang's Frenzy, Festergut's Pungent Blight, Soul Reaper on you, Gormok's Staggering Stomp and high Mystic Buffet stacks on you; health thresholds for Divine Protection (35 %), Lay on Hands (15 %) and optionally Divine Shield. Only when ready and without Forbearance (settings: *Protection: defensives*).
- **Buff bar:** seal, aura, Righteous Fury (Protection: missing = red; otherwise red while active, a click cancels it), Holy Shield and Divine Plea (Protection), flask (Stoneblood for Protection, Endless Rage for Retribution), food, and one icon per blessing you should have.
- **PallyPower (optional):** if [PallyPower](https://www.curseforge.com/wow/addons/pally-power) is loaded, ClassHelper reads (never changes) your seal, aura and Righteous Fury setting and the blessings assigned to you there. Switch it off with `/ch pallypower off` or in the settings; without PallyPower your own defaults are used (Seal of Vengeance / Corruption, Devotion or Retribution Aura, Kings + Sanctuary or Kings + Might). `/ch pal` shows what is used.

## Installation

1. Download `ClassHelper-vX.Y.zip` from the [latest release](https://github.com/Richie1710/ClassHelper/releases/latest).
2. Unzip it into `World of Warcraft\Interface\AddOns\` – it already contains the `ClassHelper` folder.
3. Restart the game completely (a new addon folder is not picked up by `/reload`).

Updating: unzip the new release over the old folder; your settings are kept.

**Coming from MageHelper:** delete the old `MageHelper` folder in `Interface\AddOns`. To keep your settings, before starting the game rename `MageHelper.lua` to `ClassHelper.lua` in `WTF\Account\<account>\SavedVariables\` and in each character's `SavedVariables` folder, and inside those files replace `MageHelperDB` with `ClassHelperDB` and `MageHelperLegacyDB` with `ClassHelperLegacyDB`. The old commands `/mh` and `/magehelper` keep working next to `/ch` and `/classhelper`.

From source instead: clone into a folder named exactly `ClassHelper` (WoW only loads it when the folder matches `ClassHelper.toc`):

```bash
git clone https://github.com/Richie1710/ClassHelper.git ClassHelper
```

Ace3 is embedded – no other addons are required.

## Usage

| Command | What it does |
| --- | --- |
| `/ch help` | List all commands |
| `/ch config` | Open the settings window |
| `/ch rota auto\|fire\|arcane\|frost` | Rotation: automatic by talents, or fixed (Paladin: `auto\|prot\|ret\|holy`) |
| `/ch judgement wisdom\|light`, `/ch aoe on\|off` | Paladin: Judgement, AoE mode |
| `/ch pallypower on\|off`, `/ch pal` | Paladin: use PallyPower's settings; show seal, aura and blessings in use |
| `/ch burn auto\|mana [percent]` | Arcane burn/conserve: time-to-die estimate or mana threshold only (10–90%) |
| `/ch steal on\|off\|all\|worth` | Spellsteal hint on/off; *all* also recommends unlisted stealable buffs, *worth* only the list (German: `/ch raub an\|aus\|alle\|lohnend`) |
| `/ch fm` | Open the Focus Magic target picker |
| `/ch t9` | Show T9 pieces found and the Molten Armor status |
| `/ch theme standard\|pink\|blue\|red` | Color theme |
| `/ch flask auto\|frost\|rage\|stone\|mojo\|resi\|any` | Which flask the buff bar expects |
| `/ch potion auto\|speed\|wild\|mana\|indestructible\|none` | Potion for the cooldown buttons and the buff bar (German: `/ch trank auto\|tempo\|wild\|mana\|unzerstoerbar\|aus`) |
| `/ch lang auto\|de\|en` | Display language (default: client language) |
| `/ch analyse` | Open the analyzer window |
| `/ch debug on` | Live line explaining why something is recommended |

`/magehelper` works as an alias for `/ch`.

## Development

There is no build step; the game loads the files straight from the folder. `tools/smoke.py` runs the addon (including the embedded Ace3) outside the game in Lua 5.1 against a fake WoW API (`tools/wowstub.lua`), once as a German and once as an English client:

```bash
py -m venv venv
venv\Scripts\pip install lupa
venv\Scripts\python -I tools\smoke.py
```

It replays a fight, every slash command, the settings window, profile switching, the Focus Magic picker and the Spellsteal helper, and exits with code 1 on any failed check or Lua error. It does not replace testing in the game.

**Releases:** bump `## Version` in `ClassHelper.toc`, then push a matching tag (`git tag v3.4 && git push origin v3.4`). A GitHub Action runs the smoke test, checks that the tag matches the TOC version and attaches `ClassHelper-v3.4.zip` (just the addon folder) to the release.

## Credits

- Embedded libraries: [Ace3](https://www.wowace.com/projects/ace3) (Release-r960) by the Ace3 Development Team, see [`Libs/Ace3-LICENSE.txt`](Libs/Ace3-LICENSE.txt).
- Original addon (KahuRota) by Kahu/Shiro.

## AI disclaimer

Parts of this addon's source code, its tests and this README were created or revised with the help of generative AI (an AI coding assistant), under the direction of the maintainer. This includes the German/English localization, the Focus Magic target picker, the move to Ace3 and the out-of-game smoke test. Changes are checked with the automated smoke test outside the game; they are not guaranteed to have been tested in every in-game situation. Please report problems as an issue.

This notice is given voluntarily for transparency.

## License

ClassHelper is released under the [MIT License](LICENSE) – you may use, change and share it as long as the copyright notice (Kahu/Shiro) and the license text stay included. The embedded Ace3 libraries keep their own license ([`Libs/Ace3-LICENSE.txt`](Libs/Ace3-LICENSE.txt)).

---

## Deutsch (Kurzfassung)

Helfer für Feuer-, Arkan- und Frostmagier in **WotLK 3.3.5a**, für deutsche und englische Clients:

- **Rota-Leiste** mit Empfehlung für den nächsten Zauber
- **Arkan- und Frost-Rota** mit eigenen Buttons; Feuer, Arkan oder Frost wird automatisch nach der Skillung gewählt (`/ch rota auto|feuer|arkan|frost`)
- **Frost:** Wasserelementar, wenn kein Pet da ist (im Kampf dringend, außerhalb nur als Hinweis vor dem Pull mit angreifbarem Ziel); Eisige Adern, Spiegelbild und Schmuckstücke mit Benutzen-Effekt sofort; Tiefkühlen, dann Frostblitz bei Eisige Finger oder eingefrorenem Ziel; Kälteeinbruch, wenn Tiefkühlen noch über 15 s Abklingzeit hat und Eisige Adern abklingt; Frostfeuerblitz bei Hirnfrost (vorher Feuerball); sonst Frostblitz
- **Burn oder Sparen** bei Arkan: Burn über der Mana-Schwelle und während Arkane Macht/Heldentum; automatisch darunter weiter, solange dein Mana bis zum Tod des Bosses reicht, oder nur nach Mana-Schwelle (`/ch burn auto|mana [Prozent]`)
- **Zauberraub-Hilfe** (Feuer und Arkan): lohnende stehlbare Buffs auf dem Ziel (z. B. Netherkraft bei Jaraxxus, Heldentum/Kampfrausch der Fraktionschampions) lassen den Raub-Button rot leuchten, außer Reichweite (30 m) blau; der Button wirkt aufs Ziel, mit Shift auf Mouseover; Hinweis, wenn nur der Fokus so einen Buff hat; Symbol mit dem stehlbaren Buff über der Leiste (`/ch raub an|aus|alle|lohnend`)
- **Buff-Leiste**
- **Glühende Rüstung mit T9-Bonus:** T9 automatisch an- und danach wieder ausziehen
- **Farbschemata** Standard, Rosa, Blau und Rot (`/ch theme`); die Signalfarben bleiben immer gleich
- **Flask pro Charakter einstellbar** (`/ch flask`), automatisch passend zu Klasse und Skillung
- **Trank pro Charakter** (`/ch trank auto|tempo|wild|mana|unzerstoerbar|aus`): die Cooldown-Buttons aller Rotas benutzen ihn mit; automatisch Wilde Magie für Feuer, Geschwindigkeit für Arkan und Frost; die Buff-Leiste prüft seinen Buff
- **MF-Ziel-Auswahl** mit den Filtern „nur Mages“ und „nur Heiler ohne MF“
- **ICC-Hinweise**
- **Seuchenmord-Tränengas** (nur normal): knapp über 80 % / 35 % Unsichtbarkeit, nach dem Gas abbrechen und allein Schaden machen; Countdown bis zum Wiederangriff, bei zu hoher Bedrohung Eisblock (`/ch tränengas an|aus|0.5-5`)
- **Analyzer**
- **Einstellungsfenster mit Profilen** (`/ch config`)

Klassen-Rotationshelfer für WotLK 3.3.5a, früher *MageHelper*. Er wählt das Modul passend zu Klasse und Skillung; derzeit **Magier** (Feuer, Arkan, Frost) und **Paladin** (Schutz, Vergeltung, Heilig nur Buff-Leiste; die Paladin-Rotas entstehen noch). Paladine: Buttons und Buff-Leiste je Skillung, Richturteil wählbar (`/ch richturteil weisheit|licht`), AoE-Modus (`/ch aoe an|aus`); ist **PallyPower** geladen, werden Siegel, Aura, Zorn der Gerechtigkeit und die dir zugewiesenen Segen von dort gelesen (nie verändert, abschaltbar mit `/ch pallypower aus`).

**Installation:**
1. `ClassHelper-vX.Y.zip` aus dem [neuesten Release](https://github.com/Richie1710/ClassHelper/releases/latest) laden und nach `Interface\AddOns\` entpacken – der Ordner `ClassHelper` ist schon drin.
2. Das Spiel komplett neu starten.

Alle Befehle zeigt `/ch help`.

**Lizenz:** MIT (siehe [LICENSE](LICENSE)). Nutzen, ändern und weitergeben ist erlaubt, solange der Copyright-Hinweis (Kahu/Shiro) und der Lizenztext erhalten bleiben.

**KI-Hinweis:** Teile des Quellcodes, der Tests und dieser README wurden unter Anleitung des Maintainers mit Unterstützung generativer KI (eines KI-Programmierassistenten) erstellt oder überarbeitet. Das betrifft unter anderem:
- die deutsch-englische Lokalisierung
- die MF-Ziel-Auswahl
- den Umbau auf Ace3
- den Test außerhalb des Spiels

Änderungen werden mit dem automatisierten Test außerhalb des Spiels geprüft. Dass sie in jeder Spielsituation getestet wurden, ist nicht garantiert. Probleme bitte als Issue melden. Dieser Hinweis erfolgt freiwillig zur Transparenz.
