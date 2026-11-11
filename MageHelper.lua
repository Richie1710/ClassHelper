-- MageHelper v3.3 Arcane rotation (burn/conserve with time-to-die estimate), auto Fire/Arcane by talents; v3.2 color themes, flask choice; Molten Armor T9 swap by item ID; Ace3 base (settings window, profiles); Focus Magic target picker; German + English client support
-- WotLK 3.3.5 Fire and Arcane Mage helper. Fire: LB timing, Hot Streak/Pyro chain, Combustion prep, burst queue, Fireball/min, cast-gap warnings, buff checks, T9 Molten Armor prep and boss-mechanic Ice Block skips, 1s cast timing and Ice Block cancel helper, Sindragosa/Putricide/Blood Queen/Lady utility warnings plus raid test/debug report.

local ADDON = "MageHelper"
local MH = LibStub("AceAddon-3.0"):NewAddon(ADDON, "AceEvent-3.0", "AceTimer-3.0", "AceConsole-3.0")
-- KR is the main rotation bar. Its KR:<EVENT> handlers are registered through AceEvent in MH:OnEnable.
local KR = CreateFrame("Frame", "MageHelperFrame", UIParent)
-- Settings (AceDB, set in MH:OnInitialize): cfg = active profile, shareable between characters;
-- chr = data that belongs to this character only (FM partner/target, T9 swap, analyzer runs).
local cfg, chr
-- Constants and state of the newer features (T9 swap, flask choice, themes). Grouped in one table
-- because Lua 5.1 allows at most 200 local variables in a file's main chunk.
local M = {}

local defaults = {
    profile = {
        shown = true,
        locked = false,
        x = 0,
        y = -170,
        minimapShown = true,
        minimapX = -10,
        minimapY = -80,
        buffMinimapX = -10,
        buffMinimapY = -112,
        combustionLB = 10,
        rotationMode = "auto",    -- "auto" (talent tree with most points), "fire" or "arcane"
        arcaneBurnMode = "auto",  -- "auto" (time to die vs. time to OOM, like SimC) or "mana" (threshold only)
        arcaneBurnMana = 35,      -- burn while mana % >= this (mana mode, and auto while the estimate is unreliable)
        showMovementFireBlast = true,
        useGloves = true,
        buffBarShown = true,
        buffBarLocked = false,
        buffBarX = 0,
        buffBarY = -270,
        fmFilterMages = false,
        fmFilterHealers = false,
        language = "auto",
        theme = "standard",       -- color theme of the panels (signal colors never change)
        moltenT9 = true,          -- cast Molten Armor with the T9 2-piece bonus (swap T9 on and back)
        bossSkips = true,
        iceBlockLead = 1.0,
        iceCancelHelper = true,
        iccUtility = true,
        buffetStacks = 5,
        instabilityStacks = 5,
        debugMode = false,
        reportOnFightEnd = true,
        analyzerIconX = -10,
        analyzerIconY = -144,
    },
    char = {
        focusMagicTarget = "",   -- current Focus Magic target (used by the FM OUT button)
        focusMagicPartner = "",  -- saved mage buddy; "back to partner" restores it (migrated on login)
        flask = "auto",          -- flask the buff bar expects: "auto", "any" or a key of FLASKS
        moltenSwap = {},         -- [inventory slot] = { orig = link|false, t9 = link, at = time() } of a T9 swap
        moltenRestorePending = false, -- Molten Armor was cast in combat: put the original gear back after combat
        analyzer = {
            trainingA = nil,
            trainingB = nil,
            lastTraining = nil,
            bossFights = {},
            deathRecaps = {},
            menuShown = false,
        },
    },
}
local CHAR_KEYS = { focusMagicTarget = true, focusMagicPartner = true, analyzer = true }

-- Localization: the German UI texts are the keys. L() returns the English text when the
-- client is not German (or /mh lang en is set); a missing entry falls back to German.
-- Spell names never go through L(): they come from GetSpellInfo(id), which is already
-- in the client language.
local L_EN = {
    ["|cffff7d0aMageHelper Fight-Report|r"] = "|cffff7d0aMageHelper fight report|r",
    ["Dauer: %.0fs  Feuerbälle/min: %.1f  Feuerbälle: %d  Pyros: %d"] = "Duration: %.0fs  Fireballs/min: %.1f  Fireballs: %d  Pyros: %d",
    ["LB-Casts: %d  Combustion: %d  Spiegelbilder: %d  Eisblock: %d"] = "LB casts: %d  Combustion: %d  Mirror Images: %d  Ice Block: %d",
    ["Hot-Streak-Procs erkannt: %d  Cast-Gaps: %d"] = "Hot Streak procs detected: %d  Cast gaps: %d",
    ["FB/min Wertung: |cff33ff33gut|r"] = "FB/min rating: |cff33ff33good|r",
    ["FB/min Wertung: |cffffff33okay, aber Luft nach oben|r"] = "FB/min rating: |cffffff33okay, room for improvement|r",
    ["FB/min Wertung: |cffff3333zu niedrig - Fireball-Kette prüfen|r"] = "FB/min rating: |cffff3333too low - check your Fireball chain|r",
    ["Häufigste Empfehlungen/Gründe:"] = "Most frequent recommendations/reasons:",
    ["Sindragosa: Mystic Buffet x%d - Eisblock Reset"] = "Sindragosa: Mystic Buffet x%d - Ice Block reset",
    ["STOP CAST: Instabilität x%d"] = "STOP CAST: Instability x%d",
    ["Entfesselte Magie: casts mitzählen, nicht überziehen"] = "Unchained Magic: count your casts, don't overdo it",
    ["FORMBARES GLIBBER auf dir: bewegen / Cast abbrechen"] = "MALLEABLE GOO on you: move / cancel cast",
    ["FORMBARES GLIBBER: bewegen / Cast abbrechen"] = "MALLEABLE GOO: move / cancel cast",
    ["Blutkönigin-Essenz aktiv: Burst/Feuerball-Kette"] = "Blood Queen essence active: burst/Fireball chain",
    ["Burst nachziehen"] = "Follow up with burst",
    ["JETZT"] = "NOW",
    ["Rota"] = "Rotation",
    ["Zeigt die aktuelle Empfehlung der Rota."] = "Shows the current rotation recommendation.",
    ["Im Kampf kann WoW den Klick-Spell nicht immer wechseln; dann den leuchtenden Einzelbutton nutzen."] = "In combat WoW cannot always switch the click spell; use the glowing single button instead.",
    ["MF IN"] = "FM IN",
    ["MF OUT"] = "FM OUT",
    ["Wilde"] = "Wild",
    ["MF-Ziel: %s"] = "FM target: %s",
    ["MF-Ziel: kein Ziel gesetzt"] = "FM target: none set",
    ["MageHelper: Fokusmagie-Ziel gesetzt: %s"] = "MageHelper: Focus Magic target set: %s",
    ["Klick: Fokusmagie auf %s und danach zurück aufs letzte Ziel"] = "Click: Focus Magic on %s, then back to your last target",
    ["Klick: Fokusmagie auf Mouseover, Fokus oder Ziel. MF-Ziel auswählen über MF SET"] = "Click: Focus Magic on mouseover, focus or target. Pick an FM target via FM SET",
    ["Status: Habe ich Fokusmagie von einem anderen Mage?"] = "Status: do I have Focus Magic from another mage?",
    ["Statusanzeige: rot fehlt, grün aktiv"] = "Status only: red = missing, green = active",
    ["Klick: Buff wirken"] = "Click: cast buff",
    ["MF SET"] = "FM SET",
    ["MF-Ziel auswählen"] = "Choose FM target",
    ["Öffnet die Liste der Gruppe mit Filtern."] = "Opens the group list with filters.",
    ["Der MF-OUT-Button nutzt danach das gewählte Ziel."] = "The FM OUT button then uses the chosen target.",
    [" (Partner: %s)"] = " (partner: %s)",
    ["(gilt ab Kampfende)"] = "(applies after combat)",
    ["MageHelper: MF-Partner gespeichert: %s"] = "MageHelper: FM partner saved: %s",
    ["MageHelper: Im Kampf - das neue MF-Ziel gilt ab Kampfende."] = "MageHelper: In combat - the new FM target applies after combat.",
    ["MageHelper: Kein MF-Partner gespeichert."] = "MageHelper: No FM partner saved.",
    ["Nur Mages"] = "Only mages",
    ["Nur Heiler ohne MF"] = "Only healers without FM",
    ["Zurück zum Partner"] = "Back to partner",
    ["Ziel"] = "Target",
    ["Partner"] = "Partner",
    ["Jetzt als MF-Ziel nutzen (vorübergehend)"] = "Use as FM target now (temporary)",
    ["Als festen MF-Partner speichern (wird auch Ziel)"] = "Save as fixed FM partner (also becomes target)",
    ["offline"] = "offline",
    ["tot"] = "dead",
    ["Heiler"] = "Healer",
    ["Heiler?"] = "Healer?",
    ["MF von %s"] = "FM from %s",
    ["dir"] = "you",
    ["Du bist in keiner Gruppe."] = "You are not in a group.",
    ["Niemand passt zu den Filtern."] = "Nobody matches the filters.",
    ["Ziel: %s   Partner: %s"] = "Target: %s   Partner: %s",
    ["Talente werden geprüft: %d offen"] = "Checking talents: %d left",
    ["Heiler? = Skillung noch nicht geprüft (zu weit weg?)"] = "Healer? = spec not checked yet (out of range?)",
    ["Linksklick: Bar an/aus"] = "Left-click: toggle bar",
    ["Linksklick: Buff-Bar an/aus"] = "Left-click: toggle buff bar",
    ["Unbekannt"] = "Unknown",
    ["%s: kein Lauf"] = "%s: no run",
    ["|cff33ff33Training läuft...|r"] = "|cff33ff33Training running...|r",
    ["Training/Puppenmodus bereit"] = "Training/dummy mode ready",
    ["Letzter Test"] = "Last test",
    ["Lauf A"] = "Run A",
    ["Lauf B"] = "Run B",
    ["Vergleich B-A: DPS %+0.0f, Pyros %+d"] = "Comparison B-A: DPS %+0.0f, Pyros %+d",
    ["Letzter Boss: "] = "Last boss: ",
    ["Letzter Tod gespeichert: "] = "Last death saved: ",
    ["Trainingslauf"] = "Training run",
    ["MageHelper Analyse: Training gestartet"] = "MageHelper Analyzer: training started",
    ["MageHelper Analyse: Training gestoppt und als letzter Test gespeichert"] = "MageHelper Analyzer: training stopped and saved as last test",
    ["MageHelper Analyse: Es läuft kein Training"] = "MageHelper Analyzer: no training running",
    ["MageHelper Analyse: Kein letzter Test vorhanden"] = "MageHelper Analyzer: no last test available",
    ["MageHelper Analyse: Lauf %s gespeichert"] = "MageHelper Analyzer: run %s saved",
    ["MageHelper Analyse: Lauf A und B müssen gespeichert sein"] = "MageHelper Analyzer: runs A and B must be saved first",
    ["|cffff7d0aMageHelper Analyse Vergleich|r"] = "|cffff7d0aMageHelper Analyzer comparison|r",
    ["B-A DPS: %+0.0f, Schaden: %+0.0f, Pyros: %+d, Hot-Streak-Procs: %+d"] = "B-A DPS: %+0.0f, damage: %+0.0f, Pyros: %+d, Hot Streak procs: %+d",
    ["MageHelper Analyse: Kein Bossfight gespeichert"] = "MageHelper Analyzer: no boss fight saved",
    ["|cffff7d0aMageHelper letzter Bossfight|r"] = "|cffff7d0aMageHelper last boss fight|r",
    ["MageHelper Analyse: Kein Death Recap gespeichert"] = "MageHelper Analyzer: no death recap saved",
    ["Treffer"] = "Hit",
    ["Unsichtbarkeit aktiv - danach abbrechen"] = "Invisibility active - cancel it afterwards",
    ["LK: UNSICHTBARKEIT JETZT - Threat %.0f%%"] = "LK: INVISIBILITY NOW - threat %.0f%%",
    ["GEGENZAUBER JETZT: %s"] = "COUNTERSPELL NOW: %s",
    ["wichtiger Cast"] = "important cast",
    ["Als A speichern"] = "Save as A",
    ["Als B speichern"] = "Save as B",
    ["A/B vergleichen"] = "Compare A/B",
    ["MageHelper Analyse"] = "MageHelper Analyzer",
    ["Vergleich"] = "Compare",
    ["Tod"] = "Death",
    ["Schließen"] = "Close",
    ["Linksklick: Analysefenster"] = "Left-click: analyzer window",
    ["Rechtsklick: Schnellmenü"] = "Right-click: quick menu",
    ["Bossfight"] = "Boss fight",
    ["Nahkampf"] = "Melee",
    ["Feuerball-Kette halten"] = "Keep the Fireball chain going",
    ["EISBLOCK ABBRECHEN / weiter DPS"] = "CANCEL ICE BLOCK / keep DPSing",
    ["EISBLOCK JETZT: %s %.1fs"] = "ICE BLOCK NOW: %s %.1fs",
    ["Boss-Cast"] = "boss cast",
    ["Eisblock CD! %s in %.1fs"] = "Ice Block on CD! %s in %.1fs",
    ["Eisblock gleich bereit halten: %.1fs"] = "Get Ice Block ready: %.1fs",
    ["EISBLOCK: %s"] = "ICE BLOCK: %s",
    ["Bossmechanik"] = "boss mechanic",
    ["Eisblock CD! %s noch %.0fs"] = "Ice Block on CD! %s, %.0fs left",
    ["%s - Eisblock CD %.0fs"] = "%s - Ice Block CD %.0fs",
    ["Eisblock nötig"] = "Ice Block needed",
    ["Pyro zuerst, danach LB neu setzen"] = "Pyro first, then reapply LB",
    ["Pyro-Kette: Hot Streak sofort nutzen"] = "Pyro chain: use Hot Streak now",
    ["LB neu setzen - Explosion ist durch"] = "Reapply LB - it has exploded",
    ["LB wartet auf CD/GCD: %.1fs"] = "LB waiting for CD/GCD: %.1fs",
    ["LB Explosion abwarten - NICHT clippen"] = "Wait for the LB explosion - do NOT clip",
    ["Lady Schild aktiv: großen Burst halten"] = "Lady's shield up: hold big burst",
    ["Combustion starten, danach Burst-CDs"] = "Start Combustion, then burst CDs",
    ["Combustion-Fenster bereit"] = "Combustion window ready",
    ["Comb bald: LB auslaufen lassen, danach neu setzen"] = "Comb soon: let LB expire, then reapply",
    ["Bewegung: nur Notfall-Feuerschlag"] = "Moving: emergency Fire Blast only",
    ["Bewegung: Feuerschlag CD %.1fs"] = "Moving: Fire Blast CD %.1fs",
    ["Feuerball spammen"] = "Spam Fireball",
    ["Spiegelbilder/Burst-CDs vor Feuerball"] = "Mirror Image/burst CDs before Fireball",
    ["  |cff777777kein HS|r"] = "  |cff777777no HS|r",
    ["  FS cd: %.1fs"] = "  FBl cd: %.1fs",
    ["JA"] = "YES",
    ["NEIN"] = "NO",
    ["|cffff7d0aMageHelper v%s|r geladen. /mh help"] = "|cffff7d0aMageHelper v%s|r loaded. /mh help",
    ["MageHelper: Bar gesperrt"] = "MageHelper: bar locked",
    ["MageHelper: Bar verschiebbar"] = "MageHelper: bar unlocked",
    ["MageHelper: Buff-Bar gesperrt"] = "MageHelper: buff bar locked",
    ["MageHelper: Buff-Bar verschiebbar"] = "MageHelper: buff bar unlocked",
    ["MageHelper: Combustion-LB-Fenster = %ss"] = "MageHelper: Combustion LB window = %ss",
    ["MageHelper: Boss-Iceblock-Skips AUS"] = "MageHelper: boss Ice Block skips OFF",
    ["MageHelper: Boss-Iceblock-Skips AN"] = "MageHelper: boss Ice Block skips ON",
    ["MageHelper: ICC-Utility-Warnungen AUS"] = "MageHelper: ICC utility warnings OFF",
    ["MageHelper: ICC-Utility-Warnungen AN"] = "MageHelper: ICC utility warnings ON",
    ["MageHelper: Eisblock-Vorlauf = %ss"] = "MageHelper: Ice Block lead time = %ss",
    ["MageHelper: Eisblock-Abbruch-Hinweis AUS"] = "MageHelper: Ice Block cancel hint OFF",
    ["MageHelper: Eisblock-Abbruch-Hinweis AN"] = "MageHelper: Ice Block cancel hint ON",
    ["MageHelper: Mystic-Buffet-Eisblock ab %s Stacks"] = "MageHelper: Mystic Buffet Ice Block at %s stacks",
    ["MageHelper: Instabilität-STOP ab %s Stacks"] = "MageHelper: Instability STOP at %s stacks",
    ["MageHelper: Debug-Anzeige AN"] = "MageHelper: debug display ON",
    ["MageHelper: Debug-Anzeige AUS"] = "MageHelper: debug display OFF",
    ["MageHelper Debug: Hot Streak erkannt="] = "MageHelper Debug: Hot Streak detected=",
    ["MageHelper Debug: /mh debug on für Live-Anzeige, /mh report für Fight-Report"] = "MageHelper Debug: /mh debug on for the live display, /mh report for the fight report",
    ["MageHelper: Fight-Report nach Kampf AUS"] = "MageHelper: fight report after combat OFF",
    ["MageHelper: Fight-Report nach Kampf AN"] = "MageHelper: fight report after combat ON",
    ["MageHelper: /use 10 aktiv"] = "MageHelper: /use 10 enabled",
    ["MageHelper: /use 10 aus"] = "MageHelper: /use 10 disabled",
    ["MageHelper: Bitte freundliches Ziel anwählen und /mh fm set nutzen"] = "MageHelper: Target a friendly player and use /mh fm set",
    ["MageHelper: Fokusmagie-Ziel gelöscht"] = "MageHelper: Focus Magic target cleared",
    ["MageHelper: Sprache = %s (Buttons und Fenster nach /reload)"] = "MageHelper: language = %s (buttons and windows after /reload)",
    ["MageHelper Befehle:"] = "MageHelper commands:",
    ["/mh show|hide - Bar an/aus"] = "/mh show|hide - show/hide bar",
    ["/mh lock|unlock - Bar sperren/verschieben"] = "/mh lock|unlock - lock/move bar",
    ["/mh comb 10 - benötigte LB-Restzeit für Einäschern"] = "/mh comb 10 - LB time left required for Combustion",
    ["/mh gloves on|off - /use 10 in Spellbuttons"] = "/mh gloves on|off - /use 10 in spell buttons",
    ["/mh buffs show|hide|lock|unlock - zweite Buff-Bar"] = "/mh buffs show|hide|lock|unlock - second buff bar",
    ["/mh fm - MF-Ziel-Auswahl öffnen"] = "/mh fm - open the FM target picker",
    ["/mh fm set|NAME - Ziel bzw. NAME als MF-Partner speichern"] = "/mh fm set|NAME - save your target or NAME as FM partner",
    ["/mh fm back|clear - zurück zum Partner / alles löschen"] = "/mh fm back|clear - back to partner / clear everything",
    ["/mh skips on|off - Eisblock-Bossmechaniken an/aus"] = "/mh skips on|off - Ice Block boss mechanics on/off",
    ["/mh icelead 1 - Eisblock bei Boss-Casts 1 Sekunde vor Einschlag anzeigen"] = "/mh icelead 1 - show Ice Block 1 second before a boss cast lands",
    ["/mh icecancel on|off - Nach Eisblock Abbruch-Hinweis anzeigen"] = "/mh icecancel on|off - show cancel hint after Ice Block",
    ["/mh utility on|off - ICC-Utility: Sindra/Putri/BQ/Lady an/aus"] = "/mh utility on|off - ICC utility: Sindra/Putri/BQ/Lady on/off",
    ["/mh buffet 5 - Mystic Buffet Eisblock ab X Stacks"] = "/mh buffet 5 - Mystic Buffet Ice Block at X stacks",
    ["/mh instability 5 - Stopcasting ab X Instabilität-Stapeln"] = "/mh instability 5 - stop casting at X Instability stacks",
    ["/mh debug on|off - Live-Debug: warum empfiehlt das Addon etwas"] = "/mh debug on|off - live debug: why the addon recommends something",
    ["/mh debug - Hot-Streak/Buffnamen einmal ausgeben"] = "/mh debug - print Hot Streak/buff names once",
    ["v1.8: Hot Streak/Pyro hat Vorrang vor LB-Refresh, auch wenn LB gerade explodiert ist."] = "Hot Streak/Pyro takes priority over LB refresh, even right after LB exploded.",
    ["/mh analyse - Analysefenster öffnen (oder A-Icon unter der Minimap)"] = "/mh analyse - open the analyzer window (or the A icon below the minimap)",
    ["/mh analyse start|stop|a|b|compare|boss|death - Analyzer-Funktionen"] = "/mh analyse start|stop|a|b|compare|boss|death - analyzer functions",
    ["/mh report - letzten/aktuellen Fight-Report ausgeben"] = "/mh report - print the last/current fight report",
    ["/mh autoreport on|off - Report nach Kampf an/aus"] = "/mh autoreport on|off - report after combat on/off",
    ["/mh lang auto|de|en - Sprache (auto = Client-Sprache)"] = "/mh lang auto|de|en - language (auto = client language)",
    ["Glühende Rüstung aktiv, gewirkt mit 2 T9-Teilen."] = "Molten Armor active, cast with 2 T9 pieces.",
    ["Glühende Rüstung aktiv, aber ohne T9 gewirkt. Klick zieht T9 an, der nächste Klick erneuert die Rüstung."] = "Molten Armor active, but cast without T9. Click puts T9 on, the next click renews the armor.",
    ["Glühende Rüstung aktiv."] = "Molten Armor active.",
    ["T9 wird angelegt ..."] = "Equipping T9 ...",
    ["..."] = "...",
    ["MageHelper: %s ist nicht mehr in den Taschen, das T9-Teil bleibt angelegt."] = "MageHelper: %s is no longer in your bags, the T9 piece stays equipped.",
    ["MageHelper: Ausrüstung konnte nicht vollständig zurückgewechselt werden, bitte von Hand prüfen."] = "MageHelper: could not swap all gear back, please check by hand.",
    ["Jede Flask zählt"] = "Any flask counts",
    ["Automatisch (%s)"] = "Automatic (%s)",
    ["Flask für die Buff-Leiste"] = "Flask for the buff bar",
    ["Automatisch: beste Flask für Klasse und Skillung, Steinblut für Todesritter in Frostpräsenz und Druiden in Bärengestalt. Gilt pro Charakter."] = "Automatic: best flask for class and spec, Stoneblood for death knights in Frost Presence and druids in Bear Form. Per character.",
    ["MageHelper: Flask = %s"] = "MageHelper: flask = %s",
    ["/mh flask auto|frost|rage|stone|mojo|resi|any - welche Flask die Buff-Leiste erwartet"] = "/mh flask auto|frost|rage|stone|mojo|resi|any - which flask the buff bar expects",
    ["Farbschema"] = "Color theme",
    ["Signalfarben (grün, rot, orange, blau) bleiben in jedem Schema gleich."] = "Signal colors (green, red, orange, blue) stay the same in every theme.",
    ["Standard"] = "Standard",
    ["Rosa"] = "Pink",
    ["Blau"] = "Blue",
    ["Rot"] = "Red",
    ["MageHelper: Farbschema = %s"] = "MageHelper: color theme = %s",
    ["/mh theme standard|rosa|blau|rot - Farbschema der Leisten und Fenster"] = "/mh theme standard|pink|blue|red - color theme of bars and windows",
    ["T9 angelegt: Klick wirkt Glühende Rüstung, danach wechselt deine Ausrüstung zurück."] = "T9 equipped: click casts Molten Armor, then your gear is swapped back.",
    ["Klick 1 zieht T9-Teile aus den Taschen an, Klick 2 wirkt Glühende Rüstung."] = "Click 1 equips T9 pieces from your bags, click 2 casts Molten Armor.",
    ["Zu wenig T9-Teile für den Set-Bonus (%d von 2). Klick wirkt Glühende Rüstung ohne Bonus."] = "Not enough T9 pieces for the set bonus (%d of 2). Click casts Molten Armor without the bonus.",
    ["Klick wirkt Glühende Rüstung."] = "Click casts Molten Armor.",
    ["Rüstung"] = "Armor",
    ["Casten"] = "Cast",
    ["T9 an"] = "T9 on",
    ["kein T9"] = "no T9",
    ["MageHelper T9: %d Teile angelegt, in den Taschen: %s"] = "MageHelper T9: %d pieces equipped, in bags: %s",
    ["keine"] = "none",
    ["/mh t9 - T9-Teile und Status für Glühende Rüstung anzeigen"] = "/mh t9 - show T9 pieces and Molten Armor status",
    ["Glühende Rüstung"] = "Molten Armor",
    ["Mit T9-Set-Bonus wirken (T9 anziehen, danach automatisch zurückwechseln)"] = "Cast with the T9 set bonus (equip T9, then swap back automatically)",
    ["/mh config - Einstellungsfenster öffnen (auch unter Interface > AddOns)"] = "/mh config - open the settings window (also under Interface > AddOns)",
    ["Allgemein"] = "General",
    ["Rota-Leiste anzeigen"] = "Show rotation bar",
    ["Rota-Leiste sperren"] = "Lock rotation bar",
    ["Buff-Leiste anzeigen"] = "Show buff bar",
    ["Buff-Leiste sperren"] = "Lock buff bar",
    ["Sprache"] = "Language",
    ["Buttons und Fenster wechseln nach /reload."] = "Buttons and windows switch after /reload.",
    ["Automatisch (Client-Sprache)"] = "Automatic (client language)",
    ["Rotation"] = "Rotation",
    ["LB-Restzeit für Einäschern (Sekunden)"] = "LB time left for Combustion (seconds)",
    ["Feuerschlag in Bewegung vorschlagen"] = "Suggest Fire Blast while moving",
    ["Handschuhe (/use 10) in den Spell-Buttons"] = "Gloves (/use 10) in the spell buttons",
    ["Boss-Mechaniken"] = "Boss mechanics",
    ["Eisblock bei Boss-Mechaniken (Stechende Seuche, Kochendes Blut, Schwärmende Schatten)"] = "Ice Block for boss mechanics (Pungent Blight, Boiling Blood, Swarming Shadows)",
    ["Eisblock-Vorlauf vor Boss-Casts (Sekunden)"] = "Ice Block lead time before boss casts (seconds)",
    ["Nach Eisblock Abbruch-Hinweis zeigen"] = "Show cancel hint after Ice Block",
    ["ICC-Hinweise (Sindragosa, Putricide, Blutkönigin, Lady)"] = "ICC hints (Sindragosa, Putricide, Blood Queen, Lady)",
    ["Mystic Buffet: Eisblock ab Stapeln"] = "Mystic Buffet: Ice Block at stacks",
    ["Instabilität: Stopcasting ab Stapeln"] = "Instability: stop casting at stacks",
    ["Fokusmagie"] = "Focus Magic",
    ["MF-Partner (Name)"] = "FM partner (name)",
    ["Analyse"] = "Analyzer",
    ["Fight-Report nach jedem Kampf im Chat"] = "Fight report in chat after every fight",
    ["Debug-Zeile unter der Rota-Leiste"] = "Debug line below the rotation bar",
    ["Analysefenster öffnen"] = "Open analyzer window",
    ["MageHelper: Einstellungen sind im Kampf gesperrt."] = "MageHelper: settings are locked in combat.",
    -- Arcane rotation
    ["Arkan"] = "Arcane",
    ["Feuer"] = "Fire",
    ["Rota-Modus"] = "Rotation mode",
    ["Automatisch: der Talentbaum mit den meisten Punkten entscheidet (Arkan oder Feuer, Frost nutzt Feuer). Die Buttons wechseln nur außerhalb des Kampfes."] = "Automatic: the talent tree with the most points decides (Arcane or Fire, Frost uses Fire). The buttons only switch out of combat.",
    ["MageHelper: Rota = %s"] = "MageHelper: rotation = %s",
    ["MageHelper: Im Kampf - die Buttons wechseln nach dem Kampf."] = "MageHelper: In combat - the buttons switch after combat.",
    ["/mh rota auto|feuer|arkan - Feuer- oder Arkan-Rota (auto = nach Talenten)"] = "/mh rota auto|fire|arcane - Fire or Arcane rotation (auto = by talents)",
    ["Burn oder Sparen"] = "Burn or conserve",
    ["Automatisch (Zeit bis zum Tod gegen Mana)"] = "Automatic (time to die vs. mana)",
    ["Nur nach Mana"] = "By mana only",
    ["Burn ab Mana (%)"] = "Burn above mana (%)",
    ["Burn: Arkanschlag auch mit 4 Stapeln. Sparen: Arkanschlag bis 3 Stapel, dann Arkane Geschosse. Während Arkane Macht, Heldentum/Kampfrausch oder dem T10-Spiegelbild-Buff wird immer geburnt.\n\nAutomatisch: Burn, solange dein Mana über der Schwelle liegt, und darunter weiter, wenn die Schätzung (Lebensverlust des Bosses gegen deinen gemessenen Manaverbrauch) sagt, dass dein Mana bis zu seinem Tod reicht. Nur nach Mana: nur die Schwelle."] = "Burn: Arcane Blast, also at 4 stacks. Conserve: Arcane Blast up to 3 stacks, then Arcane Missiles. While Arcane Power, Heroism/Bloodlust or the T10 Mirror Image buff is up you always burn.\n\nAutomatic: burn while your mana is above the threshold, and below it keep burning when the estimate (the boss's health loss against your measured mana use) says your mana lasts until it dies. By mana only: the threshold alone.",
    ["Mana-Schwelle"] = "mana threshold",
    ["MageHelper: Burn-Modus = %s, Mana-Schwelle %d%%"] = "MageHelper: burn mode = %s, mana threshold %d%%",
    ["/mh burn auto|mana [Prozent] - Arkan: Burn/Sparen automatisch oder nur nach Mana"] = "/mh burn auto|mana [percent] - Arcane: burn/conserve automatic or by mana only",
    ["%s bereit"] = "%s ready",
    ["%s zuerst (T10: +18%% Schaden)"] = "%s first (T10: +18%% damage)",
    ["Manastein: %d Mana fehlen"] = "Mana gem: %d mana missing",
    ["%s: Mana %d%%"] = "%s: mana %d%%",
    ["Stapel abbauen, dann %s"] = "Drop the stacks, then %s",
    ["%s aktiv: %s"] = "%s up: %s",
    ["Bewegung: %s"] = "Moving: %s",
    ["Bewegung: %s CD %.1fs"] = "Moving: %s CD %.1fs",
    ["Burn: %s"] = "Burn: %s",
    ["Sparen: %s bis 3 Stapel"] = "Conserve: %s up to 3 stacks",
    ["Sparen: 3 Stapel, dann %s"] = "Conserve: 3 stacks, then %s",
    ["SPAREN"] = "CONSERVE",
    ["Burn: %s aktiv"] = "Burn: %s up",
    ["Burn: Mana %d%% >= Schwelle %d%%"] = "Burn: mana %d%% >= threshold %d%%",
    ["Burn: Mana reicht bis zum Tod"] = "Burn: mana lasts until the kill",
    ["Sparen: Mana %d%% < Schwelle %d%%"] = "Conserve: mana %d%% < threshold %d%%",
    ["Sparen: Mana reicht nicht bis zum Tod"] = "Conserve: mana does not last until the kill",
    ["TTD %.0fs (%s), Mana reicht %.0fs bei %.0f Mana/s (%s)"] = "TTD %.0fs (%s), mana lasts %.0fs at %.0f mana/s (%s)",
    ["Schätzung unsicher (%s)"] = "estimate unreliable (%s)",
    ["Schätzung unsicher (%s), letzte Entscheidung gilt noch %.0fs"] = "estimate unreliable (%s), last decision kept for %.0fs",
    ["gemessen"] = "measured",
    ["Modell"] = "model",
    ["Boss nicht angreifbar"] = "boss not attackable",
    ["Dauer: %.0fs  Arkan-Rota: keine Feuerball-Wertung"] = "Duration: %.0fs  Arcane rotation: no Fireball rating",
    ["zu wenig Daten"] = "too little data",
    ["Ziel verliert kein Leben"] = "target not losing health",
    ["kein Ziel"] = "no target",
}
local useEnglish = GetLocale() ~= "deDE"
local function L(s)
    if useEnglish then return L_EN[s] or s end
    return s
end
local function ApplyLanguageSetting()
    local lang = cfg and cfg.language or "auto"
    if lang == "de" then useEnglish = false
    elseif lang == "en" then useEnglish = true
    else useEnglish = GetLocale() ~= "deDE" end
end


-- Item name in the client language when cached, otherwise an item:ID reference for macros.
local function ItemName(itemId)
    local name = GetItemInfo(itemId)
    return name or ("item:" .. itemId)
end
local function SpellName(spellId, fallback)
    local name = GetSpellInfo and GetSpellInfo(spellId)
    return name or fallback
end

local function SpellNames(spellId, ...)
    local list = { ... }
    local name = GetSpellInfo and GetSpellInfo(spellId)
    if name then table.insert(list, 1, name) end
    return list
end

local spells = {
    lb = SpellName(44457, "Lebende Bombe"),
    pyro = SpellName(42891, "Pyroschlag"),
    fireball = SpellName(42833, "Feuerball"),
    fireblast = SpellName(42873, "Feuerschlag"),
    combustion = SpellName(11129, "Ein\195\164schern"),
    manaGem = "Mana auff\195\188llen",
    mirror = SpellName(55342, "Spiegelbild"),
    iceblock = SpellName(45438, "Eisblock"),
    stop = SpellName(2139, "Gegenzauber"),
    invis = SpellName(66, "Unsichtbarkeit"),
    molten = SpellName(43046, "Glühende Rüstung"),
    brilliance = SpellName(43002, "Arkane Brillanz"),
    focusMagic = SpellName(54646, "Fokusmagie"),
    -- Arcane (max ranks, IDs checked on Wowhead WotLK)
    ab = SpellName(42897, "Arkanschlag"),
    am = SpellName(42846, "Arkane Geschosse"),
    abarr = SpellName(44781, "Arkanbeschuss"),
    ap = SpellName(12042, "Arkane Macht"),
    pom = SpellName(12043, "Geistesgegenwart"),
    iv = SpellName(12472, "Eisige Adern"),
    evo = SpellName(12051, "Hervorrufung"),
    mb = SpellName(44401, "Geschosssalve"),
}

local buffNames = {
    hotStreak = { "Kampfeshitze", "Kampfeshitze!", "Heißer Zündstoff", "Hot Streak", "Hot Streak!", "Pyroschlag!", "Pyroblast!" },
    wildMagic = { "Wilde Magie", "Wild Magic" },
    hyperspeed = { "Hypergeschwindigkeitsbeschleunigung", "Hyperspeed Acceleration" },
    heroism = { "Heldentum", "Heroism", "Kampfrausch", "Bloodlust" },
}

local trackedProcBuffs = {
    -- German + English common WotLK proc names; unknown names are harmless.
    "Phylakterium des namenlosen Lichs", "Phylactery of the Nameless Lich",
    "Verkohlte Zwielichtschuppe", "Charred Twilight Scale",
    "Splitter der Flamme", "Twilight Flames",
    "Entfesselte Magie", "Surge of Power",
    "Mächtiger Zauber", "Purified Lunar Dust",
    "Flüchtige Macht", "Volatile Power",
    "Siphoned Power", "Cultivated Power",
}
-- Proc buff SpellIDs (normal/heroic) so procs are found in every client language.
local trackedProcIds = {
    [71605]=true, [71636]=true, -- Phylactery of the Nameless Lich: Siphoned Power
    [75466]=true, [75473]=true, -- Charred Twilight Scale: Twilight Flames
    [71601]=true, [71644]=true, -- Dislodged Foreign Object: Surge of Power
    [71570]=true, [71572]=true, -- Muradin's Spyglass: Cultivated Power
}


local buffChecks = {
    -- Buffbar v2.0: status icons are intentionally red/green, not dimmed, so missing raid/proc buffs are obvious.
    { key="armor", label="Rüstung", iconSpell="Glühende Rüstung", iconSpellId=43046, names={"Glühende Rüstung", "Molten Armor"}, ids={[43046]=true, [30482]=true}, cast=spells.molten, required=true, special="molten" },
    { key="brilliance", label="Brill", iconSpell="Arkane Brillanz", iconSpellId=43002, names={"Arkane Brillanz", "Arcane Brilliance"}, ids={[43002]=true}, smallNames={"Arkane Intelligenz", "Arcane Intellect"}, smallIds={[42995]=true}, cast=spells.brilliance, required=true, special="brilliance" },
    -- MF IN = nur Status: Habe ICH Fokusmagie bekommen?
    { key="fmin", label="MF IN", iconSpell="Fokusmagie", iconSpellId=54646, names={"Fokusmagie", "Focus Magic"}, ids={[54646]=true}, required=true, special="focus_in" },
    -- MF OUT = klickbarer Button: Meine Fokusmagie auf Target/Mouseover/Focus bzw. gespeicherten Partner wirken.
    { key="fmout", label="MF OUT", iconSpell="Fokusmagie", iconSpellId=54646, names={"Fokusmagie", "Focus Magic"}, ids={[54646]=true}, cast=spells.focusMagic, required=true, special="focus_out" },
    { key="flask", label="Flask", special="flask", iconItemId=46376, names={"Fläschchen des Frostwyrms", "Flask of the Frost Wyrm"}, ids={[53755]=true}, required=true, statusOnly=true },
    { key="food", label="Food", iconSpell="Gut genährt", iconSpellId=57399, names={"Gut genährt", "Well Fed", "Satt"}, ids={[57399]=true, [57367]=true, [57360]=true}, required=true, statusOnly=true },
    { key="wild", label="Wilde", iconItemId=40212, names={"Wilde Magie", "Wild Magic"}, ids={[53909]=true}, required=true, statusOnly=true },
    { key="speed", label="Speed", iconSpell="Hypergeschwindigkeitsbeschleunigung", iconSpellId=54758, names={"Hypergeschwindigkeitsbeschleunigung", "Hyperspeed Acceleration"}, ids={[54758]=true}, required=true, statusOnly=true },
    { key="hero", label="Hero", iconSpell="Heldentum", iconSpellId=32182, names={"Heldentum", "Heroism", "Kampfrausch", "Bloodlust"}, ids={[32182]=true, [2825]=true}, required=true, statusOnly=true },
}

local buffButtons = {}
local buffBar
local analyzerFrame
local analyzerMenu
local analyzerButton
local analyzerButtonText
local oneButton
local pendingOneButtonKey

local buttons = {}
local lastCastEnd = 0
local lastCastName = nil
local lastPlayerMoving = false
local inCombatStart = nil
local fireballTimes = {}
local glowTime = 0
local gapActive = false
local burstQueueUntil = 0
local burstQueueReason = nil

-- v1.4 Raid-Test/Debug tracking
local lastHotState = false
local lastRecoKey = nil
local lastRecoReason = ""
local fightStats = {
    start = 0,
    fireballs = 0,
    pyros = 0,
    lbs = 0,
    combs = 0,
    mirrors = 0,
    iceblocks = 0,
    hotSeen = 0,
    castGaps = 0,
    lastGapAt = 0,
    reco = {},
    reason = {},
}

local function ResetFightStats()
    fightStats.start = GetTime()
    fightStats.fireballs = 0
    fightStats.pyros = 0
    fightStats.lbs = 0
    fightStats.combs = 0
    fightStats.mirrors = 0
    fightStats.iceblocks = 0
    fightStats.hotSeen = 0
    fightStats.castGaps = 0
    fightStats.lastGapAt = 0
    fightStats.reco = {}
    fightStats.reason = {}
    lastHotState = false
end

local function NoteRecommendation(key, reason)
    if not UnitAffectingCombat("player") then return end
    if key ~= lastRecoKey or reason ~= lastRecoReason then
        fightStats.reco[key or "?"] = (fightStats.reco[key or "?"] or 0) + 1
        if reason and reason ~= "" then fightStats.reason[reason] = (fightStats.reason[reason] or 0) + 1 end
        lastRecoKey = key
        lastRecoReason = reason or ""
    end
end

local function PrintTopReasons()
    local items = {}
    for k,v in pairs(fightStats.reason or {}) do table.insert(items, {k=k, v=v}) end
    table.sort(items, function(a,b) return a.v > b.v end)
    local max = math.min(#items, 5)
    for i=1,max do print(string.format("  %d) %s (%dx)", i, items[i].k, items[i].v)) end
end

local function PrintFightReport(force)
    local dur = (fightStats.start and fightStats.start > 0) and (GetTime() - fightStats.start) or 0
    if dur <= 5 and not force then return end
    local fbpm = dur > 0 and (fightStats.fireballs / dur * 60) or 0
    print(L("|cffff7d0aMageHelper Fight-Report|r"))
    if M.activeRota == "arcane" then -- Fireballs and their rating mean nothing in the Arcane rotation
        print(string.format(L("Dauer: %.0fs  Arkan-Rota: keine Feuerball-Wertung"), dur))
        print(string.format(L("LB-Casts: %d  Combustion: %d  Spiegelbilder: %d  Eisblock: %d"), fightStats.lbs or 0, fightStats.combs or 0, fightStats.mirrors or 0, fightStats.iceblocks or 0))
        if next(fightStats.reason or {}) then print(L("Häufigste Empfehlungen/Gründe:")); PrintTopReasons() end
        return
    end
    print(string.format(L("Dauer: %.0fs  Feuerbälle/min: %.1f  Feuerbälle: %d  Pyros: %d"), dur, fbpm, fightStats.fireballs or 0, fightStats.pyros or 0))
    print(string.format(L("LB-Casts: %d  Combustion: %d  Spiegelbilder: %d  Eisblock: %d"), fightStats.lbs or 0, fightStats.combs or 0, fightStats.mirrors or 0, fightStats.iceblocks or 0))
    print(string.format(L("Hot-Streak-Procs erkannt: %d  Cast-Gaps: %d"), fightStats.hotSeen or 0, fightStats.castGaps or 0))
    if fbpm >= 23 then print(L("FB/min Wertung: |cff33ff33gut|r")) elseif fbpm >= 20 then print(L("FB/min Wertung: |cffffff33okay, aber Luft nach oben|r")) else print(L("FB/min Wertung: |cffff3333zu niedrig - Fireball-Kette prüfen|r")) end
    if next(fightStats.reason or {}) then print(L("Häufigste Empfehlungen/Gründe:")); PrintTopReasons() end
end


local function SpellReady(name)
    local start, duration, enabled = GetSpellCooldown(name)
    if not start or enabled == 0 then return false, 999 end
    if start == 0 or duration == 0 then return true, 0 end
    local remain = start + duration - GetTime()
    return remain <= 0, math.max(remain, 0)
end

-- v1.9: true clickable cooldown check.
-- SpellReady() is still used for planning, but these helpers make sure buttons only glow as
-- usable when the real spell cooldown/GCD has fully finished. This avoids clicking LB or
-- Fire Blast into nothing during cooldown/GCD.
local function SpellCooldownRemaining(name)
    if not name then return 999 end
    local start, duration, enabled = GetSpellCooldown(name)
    if not start or enabled == 0 then return 999 end
    if start == 0 or duration == 0 then return 0 end
    return math.max((start + duration) - GetTime(), 0)
end

local function SpellUsableNow(name)
    return SpellCooldownRemaining(name) <= 0.05
end

-- Remaining cooldown of an item (Mana Gem button), 0 when ready.
function M.ItemCooldownRemaining(itemId)
    local start, duration, enabled = GetItemCooldown(itemId)
    if not start or enabled == 0 then return 999 end
    if start == 0 or duration == 0 then return 0 end
    return math.max((start + duration) - GetTime(), 0)
end

local function ButtonSpellCooldownRemaining(btn)
    if btn and btn.itemId then return M.ItemCooldownRemaining(btn.itemId) end
    if btn and btn.cooldownRemaining then return btn.cooldownRemaining() end
    if not btn or not btn.spellName then return 0 end
    return SpellCooldownRemaining(btn.spellName)
end

local function ButtonUsableNow(btn)
    if not btn or (not btn.spellName and not btn.itemId) then return true, 0 end
    local remain = ButtonSpellCooldownRemaining(btn)
    return remain <= 0.05, remain
end

local function HasBuff(unit, names, ids)
    if type(names) == "string" then names = { names } end
    names = names or {}
    ids = ids or {}
    for i=1,40 do
        local n, _, _, _, _, _, expires, caster, _, _, spellId = UnitBuff(unit, i)
        if not n then break end
        if spellId and ids[spellId] then
            local remain = expires and expires > 0 and (expires - GetTime()) or 999
            return true, remain, n, spellId
        end
        for _, wanted in ipairs(names) do
            if n == wanted then
                local remain = expires and expires > 0 and (expires - GetTime()) or 999
                return true, remain, n, spellId
            end
        end
    end
    return false, 0, nil, nil
end


local hotStreakSpellIds = {
    [48108] = true, -- WotLK Hot Streak proc aura
    [48107] = true, -- fallback/private-server variants
    [44448] = true, [44449] = true, -- extra fallback variants seen on some clients
}

local function LowerSafe(v)
    return v and string.lower(v) or ""
end

local function HasHotStreak()
    for i=1,40 do
        local n, _, _, count, _, duration, expires, _, _, _, spellId = UnitBuff("player", i)
        if not n then break end
        local lname = LowerSafe(n)
        if hotStreakSpellIds[spellId or 0]
            or lname == "kampfeshitze" or lname == "kampfeshitze!"
            or lname == "hot streak" or lname == "hot streak!"
            or lname == "pyroschlag!" or lname == "pyroblast!"
            or string.find(lname, "kampfeshitze", 1, true)
            or string.find(lname, "hot streak", 1, true) then
            local remain = expires and expires > 0 and (expires - GetTime()) or 999
            return true, remain, n, spellId, count or 0
        end
    end
    return false, 0, nil, nil, 0
end

local function HasAnyProc()
    for i=1,40 do
        local n, _, _, _, _, _, expires, _, _, _, spellId = UnitBuff("player", i)
        if not n then break end
        if spellId and trackedProcIds[spellId] then
            local remain = expires and expires > 0 and (expires - GetTime()) or 999
            return true, remain, n
        end
        for _, wanted in ipairs(trackedProcBuffs) do
            if n == wanted then
                local remain = expires and expires > 0 and (expires - GetTime()) or 999
                return true, remain, n
            end
        end
    end
    local lust = HasBuff("player", buffNames.heroism)
    return lust, 0, lust and "Hero/Bloodlust" or nil
end

local function ItemSlotReady(slot)
    local start, duration, enabled = GetInventoryItemCooldown("player", slot)
    if not start or enabled == 0 then return false, 999 end
    if start == 0 or duration == 0 then return true, 0 end
    local remain = start + duration - GetTime()
    return remain <= 0, math.max(remain, 0)
end

local function BurstCDReady()
    local mirrorReady, mirrorCD = SpellReady(spells.mirror)
    local glovesReady, glovesCD = ItemSlotReady(10)
    -- Potions/Flame Cap cannot be reliably checked by name in all clients here,
    -- so the Burst button remains useful whenever one tracked burst piece is ready.
    if mirrorReady or glovesReady then return true, math.min(mirrorCD or 999, glovesCD or 999) end
    return false, math.min(mirrorCD or 999, glovesCD or 999)
end


local bossSkipDebuffs = {
    -- ICC utility skips. Names are primary so it works on German clients/private servers;
    -- SpellIDs are included as fallback when the server exposes them.
    { key="swarm", label="Schw\195\164rmende Schatten", boss="Lady Todeswisper", names={"Schw\195\164rmende Schatten", "Schwärmende Schatten", "Swarming Shadows"}, ids={[71265]=true, [71266]=true, [71289]=true, [71204]=true} },
    { key="boil", label="Kochendes Blut", boss="Todesbringer Saurfang", names={"Kochendes Blut", "Boiling Blood"}, ids={[72385]=true, [72441]=true, [72442]=true, [72443]=true} },
}

local bossSkipCasts = {
    -- Festergut: Pungent Blight is a cast; Ice Block should be used shortly BEFORE it lands.
    -- German clients/private servers vary, so keep several likely localized names plus the WotLK SpellID.
    { key="pungent", label="Stechende Seuche", boss="Festergut", names=SpellNames(69195, "Pungent Blight", "Stechende Seuche", "Scharfe Seuche", "\195\156belriechende Seuche", "Bei\195\159ende Seuche"), partialNames={"pungent", "blight", "stechende", "scharfe", "riechende", "beissende", "bei\195\159ende"}, ids={[69195]=true, [73031]=true, [73032]=true, [73033]=true} },
}

local utilityDebuffs = {
    -- Sindragosa: reset Mystic Buffet stacks with Ice Block when stacks get too high.
    buffet = { key="buffet", label="Mystic Buffet", names={"Mystischer Puffer", "Mystic Buffet"}, ids={[70127]=true, [72528]=true, [72529]=true, [72530]=true} },
    -- Sindragosa: Unchained Magic creates Instability stacks. At high stacks: stop casting.
    unchained = { key="unchained", label="Unchained Magic", names={"Entfesselte Magie", "Unchained Magic"}, ids={[69762]=true} },
    instability = { key="instability", label="Instabilit\195\164t", names={"Instabilit\195\164t", "Instabilität", "Instability"}, ids={[69766]=true, [71044]=true} },
}

local utilityBossCasts = {
    -- Professor Putricide: Malleable Goo is a movement/DPS-killer mechanic.
    goo = { key="goo", label="Formbares Glibber", names={"Formbares Glibber", "Malleable Goo", "Malleable Ooze"}, partialNames={"formbares", "glibber", "malleable", "goo", "ooze"}, ids={[72295]=true, [72297]=true, [70852]=true, [72615]=true, [74280]=true, [74281]=true, [72549]=true, [72550]=true, [72551]=true} },
}

local utilityBuffs = {
    bqEssence = { key="bq", label="Essenz der Blutk\195\182nigin", names={"Essenz der Blutk\195\182nigin", "Essenz der Blutkönigin", "Essence of the Blood Queen"}, ids={[70867]=true, [70871]=true, [71525]=true, [71533]=true} },
    ladyShield = { key="ladyshield", label="Manabarriere", names={"Manabarriere", "Mana Barrier"}, ids={[70842]=true} },
}

local function PlayerDebuffByNamesOrIds(names, ids)
    for i=1,40 do
        local n, _, _, _, _, _, expires, caster, _, _, spellId = UnitDebuff("player", i)
        if not n then break end
        if ids and ids[spellId or 0] then
            local remain = expires and expires > 0 and math.max(expires - GetTime(), 0) or 999
            return true, remain, n, spellId
        end
        if names then
            for _, wanted in ipairs(names) do
                if n == wanted then
                    local remain = expires and expires > 0 and math.max(expires - GetTime(), 0) or 999
                    return true, remain, n, spellId
                end
            end
        end
    end
    return false, 0, nil, nil
end

local function PlayerDebuffFull(names, ids)
    for i=1,40 do
        local n, _, _, count, _, _, expires, caster, _, _, spellId = UnitDebuff("player", i)
        if not n then break end
        local matched = ids and ids[spellId or 0]
        if not matched and names then
            for _, wanted in ipairs(names) do if n == wanted then matched = true; break end end
        end
        if matched then
            local remain = expires and expires > 0 and math.max(expires - GetTime(), 0) or 999
            return true, remain, n, spellId, count or 0
        end
    end
    return false, 0, nil, nil, 0
end

local function UnitBuffByNamesOrIds(unit, names, ids)
    if not UnitExists(unit) then return false end
    for i=1,40 do
        local n, _, _, count, _, _, expires, caster, _, _, spellId = UnitBuff(unit, i)
        if not n then break end
        local matched = ids and ids[spellId or 0]
        if not matched and names then
            for _, wanted in ipairs(names) do if n == wanted then matched = true; break end end
        end
        if matched then
            local remain = expires and expires > 0 and math.max(expires - GetTime(), 0) or 999
            return true, remain, n, spellId, count or 0
        end
    end
    return false, 0, nil, nil, 0
end

local function HasIceBlockAura()
    return HasBuff("player", {"Eisblock", "Ice Block"}, {[45438]=true})
end

local function IterateBossCastUnits()
    local units = {"target", "focus", "mouseover", "targettarget", "focustarget"}
    for i=1,5 do table.insert(units, "boss"..i) end
    return units
end

local function UnitCastingByNamesOrIds(unit, names, ids, partialNames)
    if not UnitExists(unit) then return false end
    local name, _, _, _, startMS, endMS, _, _, notInterruptible, spellId = UnitCastingInfo(unit)
    if not name then return false end
    local matched = false
    if ids and ids[spellId or 0] then matched = true end
    if not matched and names then
        for _, wanted in ipairs(names) do
            if wanted and name == wanted then matched = true; break end
        end
    end
    if not matched and partialNames then
        local lname = LowerSafe(name)
        for _, wanted in ipairs(partialNames) do
            wanted = LowerSafe(wanted)
            if wanted ~= "" and string.find(lname, wanted, 1, true) then matched = true; break end
        end
    end
    if not matched then return false end
    local nowMS = GetTime() * 1000
    local remain = endMS and math.max((endMS - nowMS) / 1000, 0) or 0
    local total = (startMS and endMS) and math.max((endMS - startMS) / 1000, 0) or 0
    return true, remain, name, spellId, total, unit
end

local function ActiveIceblockCastSkip()
    if not cfg or not cfg.bossSkips then return false end
    local lead = cfg.iceBlockLead or 1.0
    for _, data in ipairs(bossSkipCasts) do
        for _, unit in ipairs(IterateBossCastUnits()) do
            local active, remain, found, spellId, total, foundUnit = UnitCastingByNamesOrIds(unit, data.names, data.ids, data.partialNames)
            if active then
                local ready, cd = SpellReady(spells.iceblock)
                local shouldBlock = remain <= lead
                return true, remain, found or data.label, spellId, ready, cd, data, shouldBlock, foundUnit
            end
        end
    end
    return false
end

local function ActiveIceblockSkip()
    if not cfg or not cfg.bossSkips then return false end
    for _, data in ipairs(bossSkipDebuffs) do
        local active, remain, found, spellId = PlayerDebuffByNamesOrIds(data.names, data.ids)
        if active then
            local ready, cd = SpellReady(spells.iceblock)
            return true, remain, found or data.label, spellId, ready, cd, data
        end
    end
    return false
end

local function ActiveIccUtility()
    if not cfg or not cfg.iccUtility then return false end
    -- Sindragosa: Mystic Buffet stack reset via Ice Block.
    local b = utilityDebuffs.buffet
    local active, remain, found, spellId, stacks = PlayerDebuffFull(b.names, b.ids)
    if active and stacks >= (cfg.buffetStacks or 5) then
        local ready, cd = SpellReady(spells.iceblock)
        return "ice", true, string.format(L("Sindragosa: Mystic Buffet x%d - Eisblock Reset"), stacks), ready, cd
    end

    -- Sindragosa: stop casting when Instability stacks get high from Unchained Magic.
    local inst = utilityDebuffs.instability
    local ia, ir, inf, iid, istacks = PlayerDebuffFull(inst.names, inst.ids)
    local un = utilityDebuffs.unchained
    local ua = PlayerDebuffByNamesOrIds(un.names, un.ids)
    if ia and istacks >= (cfg.instabilityStacks or 5) then
        return "stop", true, string.format(L("STOP CAST: Instabilität x%d"), istacks)
    elseif ua then
        return "warn", false, L("Entfesselte Magie: casts mitzählen, nicht überziehen")
    end

    -- Professor Putricide: Malleable Goo cast/debuff -> move warning.
    local goo = utilityBossCasts.goo
    local ga, gr, gn = PlayerDebuffByNamesOrIds(goo.names, goo.ids)
    if ga then return "move", true, L("FORMBARES GLIBBER auf dir: bewegen / Cast abbrechen") end
    for _, unit in ipairs(IterateBossCastUnits()) do
        local ca, cr, cn = UnitCastingByNamesOrIds(unit, goo.names, goo.ids, goo.partialNames)
        if ca then return "move", true, L("FORMBARES GLIBBER: bewegen / Cast abbrechen") end
    end

    -- Blood Queen Lana'thel: bite essence is a major DPS window.
    local q = utilityBuffs.bqEssence
    local qa, qr, qn = UnitBuffByNamesOrIds("player", q.names, q.ids)
    if qa then return "burst", false, L("Blutkönigin-Essenz aktiv: Burst/Feuerball-Kette") end

    return false
end

local function LadyShieldActive()
    if not cfg or not cfg.iccUtility then return false end
    local data = utilityBuffs.ladyShield
    for _, unit in ipairs(IterateBossCastUnits()) do
        local a, r, n = UnitBuffByNamesOrIds(unit, data.names, data.ids)
        if a then return true, r, n, unit end
    end
    return false
end

local function StartBurstQueue(reason)
    burstQueueUntil = GetTime() + 8
    burstQueueReason = reason or L("Burst nachziehen")
end

local function ClearBurstQueue()
    burstQueueUntil = 0
    burstQueueReason = nil
end

local function BurstQueueActive()
    if burstQueueUntil and burstQueueUntil > GetTime() then return true end
    ClearBurstQueue()
    return false
end


local function HasBuffFromCaster(unit, names, casterUnit)
    if type(names) == "string" then names = { names } end
    for i=1,40 do
        local n, _, _, _, _, _, expires, caster = UnitBuff(unit, i)
        if not n then break end
        for _, wanted in ipairs(names) do
            if n == wanted and ((not casterUnit) or caster == casterUnit) then
                local remain = expires and expires > 0 and (expires - GetTime()) or 999
                return true, remain, n
            end
        end
    end
    return false, 0, nil
end

local function IterateGroupUnits()
    local units = {}
    if GetNumRaidMembers and GetNumRaidMembers() > 0 then
        for i=1,GetNumRaidMembers() do table.insert(units, "raid"..i) end
    elseif GetNumPartyMembers and GetNumPartyMembers() > 0 then
        table.insert(units, "player")
        for i=1,GetNumPartyMembers() do table.insert(units, "party"..i) end
    else
        table.insert(units, "player")
    end
    return units
end

local function FindMyFocusMagicOut()
    for _, unit in ipairs(IterateGroupUnits()) do
        if UnitExists(unit) and not UnitIsUnit(unit, "player") then
            local active, remain = HasBuffFromCaster(unit, {"Fokusmagie", "Focus Magic"}, "player")
            if active then return true, remain, UnitName(unit) end
        end
    end
    return false, 0, nil
end

local function DebuffRemaining(unit, name, casterOnly)
    for i=1,40 do
        local n, _, _, _, _, _, expires, caster = UnitDebuff(unit, i)
        if not n then break end
        if n == name and ((not casterOnly) or caster == "player") then
            return expires and expires > 0 and math.max(expires - GetTime(), 0) or 999
        end
    end
    return 0
end

local function PlayerMoving()
    local speed = GetUnitSpeed and GetUnitSpeed("player") or 0
    return speed and speed > 0
end

local function SetMacro(btn, macroText)
    btn.macroText = macroText
    btn:SetAttribute("type", "macro")
    btn:SetAttribute("macrotext", macroText)
end

local function MakeMacro(spell, extraTop, extraBottom)
    local t = { "#showtooltip " .. spell }
    if cfg.useGloves then table.insert(t, "/use 10") end
    if extraTop then for _, line in ipairs(extraTop) do table.insert(t, line) end end
    table.insert(t, "/cast " .. spell)
    if extraBottom then for _, line in ipairs(extraBottom) do table.insert(t, line) end end
    return table.concat(t, "\n")
end

local function ColorText(text, r,g,b)
    return string.format("|cff%02x%02x%02x%s|r", r*255, g*255, b*255, text)
end

-- =============================
-- Color themes
-- =============================
-- Themes color only the panels: background, a thin accent stripe, titles, labels and the MF SET
-- button. Signal colors (green active, red missing/urgent, orange act now, blue prepare, yellow,
-- grey) never change. Contrast (WCAG, checked over a dark and a medium game world behind the
-- translucent panels): titles/labels >= 7.7:1, every signal color >= 3.7:1, button text >= 4.6:1.
M.THEMES = {
    standard = { bg = { 0, 0, 0 }, accent = { 1.00, 0.82, 0.00 }, title = { 1.00, 0.82, 0.00 }, text = { 1.00, 0.82, 0.00 },
                 button = { 0.08, 0.35, 0.95 }, buttonText = { 1.00, 0.82, 0.00 } },
    pink = { bg = { 0.13, 0.03, 0.10 }, barAlpha = 0.55, stripe = true, accent = { 1.00, 0.42, 0.74 },
             title = { 1.00, 0.62, 0.86 }, text = { 1.00, 0.84, 0.94 }, button = { 0.58, 0.10, 0.40 }, buttonText = { 1, 1, 1 } },
    blue = { bg = { 0.02, 0.06, 0.16 }, barAlpha = 0.55, stripe = true, accent = { 0.30, 0.62, 1.00 },
             title = { 0.55, 0.80, 1.00 }, text = { 0.84, 0.93, 1.00 }, button = { 0.07, 0.28, 0.70 }, buttonText = { 1, 1, 1 } },
    -- wine-red accent, so the stripe is never mistaken for the signal red "missing"
    red = { bg = { 0.14, 0.03, 0.03 }, barAlpha = 0.55, stripe = true, accent = { 0.80, 0.24, 0.38 },
            title = { 1.00, 0.62, 0.52 }, text = { 1.00, 0.88, 0.82 }, button = { 0.52, 0.10, 0.22 }, buttonText = { 1, 1, 1 } },
}
M.THEME_ORDER = { "standard", "pink", "blue", "red" }
M.THEME_NAMES = { standard = "Standard", pink = "Rosa", blue = "Blau", red = "Rot" }
M.themed = { panels = {}, titles = {}, texts = {}, buttons = {} }

local function Theme()
    return M.THEMES[cfg and cfg.theme or "standard"] or M.THEMES.standard
end

-- Register a panel whose .bg texture takes the theme color. alpha = its usual background alpha;
-- bars (isBar) are a bit more opaque in colored themes so labels keep their contrast.
local function ThemePanel(frame, alpha, isBar)
    local stripe = frame:CreateTexture(nil, "BORDER")
    stripe:SetTexture("Interface\\Buttons\\WHITE8x8")
    stripe:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
    stripe:SetPoint("TOPRIGHT", frame, "TOPRIGHT", 0, 0)
    stripe:SetHeight(2)
    frame.themeStripe = stripe
    table.insert(M.themed.panels, { frame = frame, alpha = alpha, isBar = isBar })
end
local function ThemeTitle(fontString) table.insert(M.themed.titles, fontString) end
local function ThemeText(fontString) table.insert(M.themed.texts, fontString) end
local function ThemeButton(bgTexture, fontString) table.insert(M.themed.buttons, { bg = bgTexture, text = fontString }) end

local function ApplyTheme()
    local t = Theme()
    for _, p in ipairs(M.themed.panels) do
        p.frame.bg:SetTexture(t.bg[1], t.bg[2], t.bg[3], (p.isBar and t.barAlpha) or p.alpha)
        if t.stripe then
            p.frame.themeStripe:SetVertexColor(t.accent[1], t.accent[2], t.accent[3], 0.9)
            p.frame.themeStripe:Show()
        else
            p.frame.themeStripe:Hide()
        end
    end
    for _, fs in ipairs(M.themed.titles) do fs:SetTextColor(t.title[1], t.title[2], t.title[3]) end
    for _, fs in ipairs(M.themed.texts) do fs:SetTextColor(t.text[1], t.text[2], t.text[3]) end
    for _, b in ipairs(M.themed.buttons) do
        b.bg:SetVertexColor(t.button[1], t.button[2], t.button[3], 0.75)
        b.text:SetTextColor(t.buttonText[1], t.buttonText[2], t.buttonText[3])
    end
end

local function ButtonSetState(btn, state, alpha)
    btn.state = state
    btn:SetAlpha(alpha or 0.45)
    if btn.glowBack then btn.glowBack:Hide() end
    if state == "glow" then
        btn.overlay:Show()
        btn.overlay:SetVertexColor(0.00, 1.00, 0.25, 1.00)
        if btn.glowBack then btn.glowBack:Show(); btn.glowBack:SetVertexColor(0.00, 0.90, 0.25, 0.55) end
        if btn.text then btn.text:SetTextColor(0.2, 1, 0.2, 1) end
    elseif state == "urgent" then
        btn.overlay:Show()
        btn.overlay:SetVertexColor(1.00, 0.05, 0.00, 1.00)
        if btn.glowBack then btn.glowBack:Show(); btn.glowBack:SetVertexColor(1.00, 0.00, 0.00, 0.70) end
        if btn.text then btn.text:SetTextColor(1, 0.25, 0.1, 1) end
    elseif state == "prep" then
        btn.overlay:Show()
        btn.overlay:SetVertexColor(0.15, 0.55, 1.00, 1.00)
        if btn.glowBack then btn.glowBack:Show(); btn.glowBack:SetVertexColor(0.10, 0.45, 1.00, 0.60) end
        if btn.text then btn.text:SetTextColor(0.35, 0.75, 1, 1) end
    else
        btn.overlay:Hide()
        if btn.glowBack then btn.glowBack:Hide() end
        if btn.text then local c = Theme().text; btn.text:SetTextColor(c[1], c[2], c[3], 1) end
    end
end

local function PulseRecommendationButtons()
    local pulse = 0.45 + 0.55 * math.abs(math.sin(GetTime() * 5.5))
    for _, btn in pairs(buttons) do
        if btn.state == "glow" or btn.state == "urgent" or btn.state == "prep" then
            if btn.overlay then btn.overlay:SetAlpha(0.55 + 0.45 * pulse) end
            if btn.glowBack then btn.glowBack:SetAlpha(0.30 + 0.55 * pulse) end
        end
    end
end


local function GetBestIcon(data)
    if data.iconSpellId then
        local tex = select(3, GetSpellInfo(data.iconSpellId))
        if tex then return tex end
    end
    if data.iconSpell then
        local tex = select(3, GetSpellInfo(data.iconSpell))
        if tex then return tex end
    end
    if data.cast then
        local tex = select(3, GetSpellInfo(data.cast))
        if tex then return tex end
    end
    if data.iconItemId then
        local tex = GetItemIcon and GetItemIcon(data.iconItemId)
        if not tex then tex = select(10, GetItemInfo(data.iconItemId)) end
        if tex then return tex end
    end
    return "Interface\\Icons\\INV_Misc_QuestionMark"
end

local function CreateSpellButton(parent, key, label, spell, macro)
    local btn = CreateFrame("Button", "MageHelperButton_"..key, parent, "SecureActionButtonTemplate")
    btn:SetWidth(44); btn:SetHeight(44)
    btn.icon = btn:CreateTexture(nil, "BACKGROUND")
    btn.icon:SetAllPoints(btn)
    local tex = select(3, GetSpellInfo(spell))
    btn.icon:SetTexture(tex or "Interface\\Icons\\INV_Misc_QuestionMark")
    btn.overlay = btn:CreateTexture(nil, "OVERLAY")
    btn.overlay:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    btn.overlay:SetBlendMode("ADD")
    btn.overlay:SetWidth(70); btn.overlay:SetHeight(70)
    btn.overlay:SetPoint("CENTER")
    btn.overlay:Hide()
    btn.text = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    btn.text:SetPoint("TOP", btn, "BOTTOM", 0, -2)
    btn.text:SetText(label)
    btn.spellName = spell
    btn.cooldown = CreateFrame("Cooldown", nil, btn, "CooldownFrameTemplate")
    btn.cooldown:SetAllPoints(btn)
    btn.cdText = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    btn.cdText:SetPoint("CENTER", btn, "CENTER", 0, 0)
    btn.cdText:SetTextColor(1, 0.85, 0.1, 1)
    btn.cdText:Hide()
    btn.customMacro = macro
    SetMacro(btn, macro or MakeMacro(spell))
    buttons[key] = btn
    return btn
end
-- Re-creates the standard macros (e.g. after the gloves option changed). Not possible in combat.
local function RebuildSpellMacros()
    if InCombatLockdown() then return end
    for _, btn in pairs(buttons) do
        if btn.macroBuilder then SetMacro(btn, btn.macroBuilder())
        elseif not btn.customMacro and btn.spellName then SetMacro(btn, MakeMacro(btn.spellName)) end
    end
end

local function CreateOneButton(parent)
    local btn = CreateFrame("Button", "MageHelperOneButton", parent)
    btn:SetWidth(62); btn:SetHeight(62)
    btn.icon = btn:CreateTexture(nil, "BACKGROUND")
    btn.icon:SetAllPoints(btn)
    btn.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")
    btn.border = btn:CreateTexture(nil, "OVERLAY")
    btn.border:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    btn.border:SetBlendMode("ADD")
    btn.border:SetWidth(92); btn.border:SetHeight(92)
    btn.border:SetPoint("CENTER")
    btn.border:SetVertexColor(0.15, 0.85, 1, 0.95)
    btn.label = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    btn.label:SetPoint("TOP", btn, "BOTTOM", 0, -2)
    btn.label:SetText(L("JETZT"))
    btn.spellText = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    btn.spellText:SetPoint("BOTTOM", btn, "TOP", 0, 2)
    btn.spellText:SetWidth(86)
    btn.spellText:SetJustifyH("CENTER")
    btn.spellText:SetText(L("Rota"))
    btn.lockText = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    btn.lockText:SetPoint("CENTER", btn, "CENTER", 0, 0)
    btn.lockText:SetTextColor(1, 0.2, 0.1, 1)
    btn.lockText:SetText("")
    btn:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:SetText("MageHelper One-Button")
        GameTooltip:AddLine(L("Zeigt die aktuelle Empfehlung der Rota."), 0.7,0.9,1, true)
        GameTooltip:AddLine(L("Im Kampf kann WoW den Klick-Spell nicht immer wechseln; dann den leuchtenden Einzelbutton nutzen."), 1,0.8,0.2, true)
        GameTooltip:Show()
    end)
    btn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    btn:RegisterForClicks("LeftButtonUp")
    btn.dynamicMacroText = MakeMacro(spells.fireball)
    btn:SetScript("OnClick", function(self)
        local macro = self.dynamicMacroText
        if macro and RunMacroText then
            RunMacroText(macro)
        elseif self.spellName then
            CastSpellByName(self.spellName)
        end
    end)
    btn.currentKey = "fireball"
    oneButton = btn
    return btn
end

local function UpdateOneButton(key, urgent, note)
    if not oneButton or not key or not buttons[key] then return end
    local src = buttons[key]
    local tex = src.icon and src.icon:GetTexture() or nil
    oneButton.icon:SetTexture(tex or "Interface\\Icons\\INV_Misc_QuestionMark")
    oneButton.spellText:SetText(src.text and src.text:GetText() or key)
    oneButton.border:SetVertexColor(urgent and 1 or 0.15, urgent and 0.05 or 0.85, urgent and 0.00 or 1, 0.95)

    pendingOneButtonKey = nil
    oneButton.currentKey = key
    oneButton.lockText:SetText("")
    oneButton:SetAlpha(1)
    oneButton:EnableMouse(true)

    -- Privatserver-Modus: normaler Button, der beim Klick das aktuell empfohlene Makro ausführt.
    -- Das umgeht das eingefrorene SecureActionButton-Attribut; falls der Client RunMacroText schützt,
    -- meldet WoW trotzdem einen geschützte-Aktion-Fehler.
    oneButton.dynamicMacroText = src.macroText or MakeMacro(src.spellName or spells.fireball)
    oneButton.spellName = src.spellName or spells.fireball
end

local function RefreshOneButtonAfterCombat()
    if pendingOneButtonKey then
        UpdateOneButton(pendingOneButtonKey, false)
    end
end


-- =============================
-- Flask choice (per character)
-- =============================
-- Which flask the buff bar expects. "auto" picks the best flask for the class and active talent
-- tree, "any" accepts every flask below. Matched by buff spell ID, so it works in any language.
M.FLASKS = {
    frostwyrm = { buff = 53755, item = 46376 },   -- Flask of the Frost Wyrm: +125 spell power
    endlessrage = { buff = 53760, item = 46377 }, -- Flask of Endless Rage: +180 attack power
    stoneblood = { buff = 53758, item = 46379 },  -- Flask of Stoneblood: +1300 health
    puremojo = { buff = 54212, item = 46378 },    -- Flask of Pure Mojo: +45 mana per 5 sec
    resistance = { buff = 62380, item = 44939 },  -- Lesser Flask of Resistance: +50 all resistances
}
M.FLASK_ORDER = { "frostwyrm", "endlessrage", "stoneblood", "puremojo", "resistance" }
-- Best flask per class and talent tree (tree order as in the talent frame). Druid and death knight
-- tanks share their trees with damage specs; they are recognised by form instead (InTankForm).
M.FLASK_BY_SPEC = {
    MAGE = { "frostwyrm", "frostwyrm", "frostwyrm" },
    WARLOCK = { "frostwyrm", "frostwyrm", "frostwyrm" },
    PRIEST = { "frostwyrm", "frostwyrm", "frostwyrm" },       -- Discipline, Holy, Shadow
    DRUID = { "frostwyrm", "endlessrage", "frostwyrm" },      -- Balance, Feral, Restoration
    SHAMAN = { "frostwyrm", "endlessrage", "frostwyrm" },     -- Elemental, Enhancement, Restoration
    PALADIN = { "frostwyrm", "stoneblood", "endlessrage" },   -- Holy, Protection, Retribution
    WARRIOR = { "endlessrage", "endlessrage", "stoneblood" }, -- Arms, Fury, Protection
    DEATHKNIGHT = { "endlessrage", "endlessrage", "endlessrage" },
    HUNTER = { "endlessrage", "endlessrage", "endlessrage" },
    ROGUE = { "endlessrage", "endlessrage", "endlessrage" },
}
M.FLASK_ALIASES = { auto = "auto", any = "any", jede = "any", frost = "frostwyrm", frostwyrm = "frostwyrm",
    rage = "endlessrage", wut = "endlessrage", endlessrage = "endlessrage", stone = "stoneblood", stein = "stoneblood",
    stoneblood = "stoneblood", mojo = "puremojo", puremojo = "puremojo", resi = "resistance", resistance = "resistance" }

-- Frost Presence (death knight tank), Bear Form, Dire Bear Form: matched by spell name from the ID.
M.TANK_FORM_SPELLS = { 48263, 5487, 9634 }
local function InTankForm()
    local form = GetShapeshiftForm and GetShapeshiftForm() or 0
    if form == 0 then return false end
    local _, name = GetShapeshiftFormInfo(form)
    for _, id in ipairs(M.TANK_FORM_SPELLS) do
        if name and name == GetSpellInfo(id) then return true end
    end
    return false
end

M.autoFlaskCache, M.autoFlaskAt = nil, -10
local function AutoFlask()
    local now = GetTime()
    if M.autoFlaskCache and now - M.autoFlaskAt < 5 then return M.autoFlaskCache end
    local _, class = UnitClass("player")
    local group = GetActiveTalentGroup and GetActiveTalentGroup(false, false) or nil
    local tree, most = 1, -1
    for tab = 1, 3 do
        local _, _, points = GetTalentTabInfo(tab, false, false, group)
        if (points or 0) > most then tree, most = tab, points or 0 end
    end
    local bySpec = M.FLASK_BY_SPEC[class or ""]
    local flask = bySpec and bySpec[tree] or "frostwyrm"
    if InTankForm() then flask = "stoneblood" end
    M.autoFlaskCache, M.autoFlaskAt = flask, now
    return M.autoFlaskCache
end

-- Flask keys the buff bar accepts right now.
local function ExpectedFlasks()
    local choice = chr and chr.flask or "auto"
    if choice == "any" then return M.FLASK_ORDER end
    if M.FLASKS[choice] then return { choice } end
    return { AutoFlask() }
end

local function FlaskName(key)
    return GetSpellInfo(M.FLASKS[key].buff) or key
end

local function FlaskActive()
    local ids, names = {}, {}
    for _, key in ipairs(ExpectedFlasks()) do
        ids[M.FLASKS[key].buff] = true
        table.insert(names, FlaskName(key))
    end
    return HasBuff("player", names, ids)
end

local function FlaskChoiceText()
    local choice = chr and chr.flask or "auto"
    if choice == "any" then return L("Jede Flask zählt") end
    if M.FLASKS[choice] then return FlaskName(choice) end
    return string.format(L("Automatisch (%s)"), FlaskName(AutoFlask()))
end

local function SetFlaskChoice(choice)
    chr.flask = choice
    M.autoFlaskCache = nil
end

-- =============================
-- Molten Armor with the T9 2-piece bonus
-- =============================
-- The T9 2-piece bonus raises Molten Armor's crit. Whether the stronger buff survives swapping the
-- T9 back off is up to the server core (retail 3.3.5: yes; some private cores fixed it), so the
-- button only claims "cast with 2 T9 pieces". Click 1 equips T9 pieces from the bags until 2 are
-- worn, click 2 casts Molten Armor, and after a successful cast the previous items go back on.
-- T9 is found by item ID only (any language).
-- Mage T9 IDs 47748-47777 -> inventory slot (1 head, 3 shoulder, 5 chest, 7 legs, 10 hands).
M.T9_SLOT_BY_ID = {
    [47748] = 1, [47749] = 5, [47750] = 7, [47751] = 3, [47752] = 10, -- Khadgar's ... of Conquest (232)
    [47753] = 10, [47754] = 1, [47755] = 7, [47756] = 5, [47757] = 3, -- Khadgar's ... of Triumph (245)
    [47758] = 3, [47759] = 5, [47760] = 7, [47761] = 1, [47762] = 10, -- Khadgar's ... of Triumph (258)
    [47763] = 10, [47764] = 1, [47765] = 7, [47766] = 5, [47767] = 3, -- Sunstrider's ... of Triumph (258)
    [47768] = 3, [47769] = 5, [47770] = 7, [47771] = 1, [47772] = 10, -- Sunstrider's ... of Triumph (245)
    [47773] = 10, [47774] = 1, [47775] = 7, [47776] = 5, [47777] = 3, -- Sunstrider's ... of Conquest (232)
}
M.T9_SLOT_ORDER = { 7, 10, 3, 1, 5 } -- which slots to swap first: legs, hands, shoulders, head, chest
M.MOLTEN_BUFF_NAMES = { "Glühende Rüstung", "Molten Armor" }
M.MOLTEN_BUFF_IDS = { [43046] = true, [43045] = true, [30482] = true }
M.SWAP_MAX_AGE = 600       -- seconds a swap stays valid; an aborted click 1 is forgotten after that
M.SWAP_SETTLE = 1.5        -- seconds after click 1 in which further clicks do nothing (server equips)
M.swapPendingUntil = 0
M.restoreTries = 0
M.lastMoltenCast = -10         -- GetTime() of the last successful Molten Armor cast
M.moltenStateCache, M.moltenStateAt = nil, 0

local function ItemIdFromLink(link)
    return link and tonumber(link:match("item:(%d+)"))
end

local function EquippedT9()
    local count, worn = 0, {}
    for _, slot in ipairs(M.T9_SLOT_ORDER) do
        local id = ItemIdFromLink(GetInventoryItemLink("player", slot))
        if id and M.T9_SLOT_BY_ID[id] then count = count + 1; worn[slot] = true end
    end
    return count, worn
end

-- One T9 piece per slot from the bags: [slot] = item link.
local function BagT9()
    local found = {}
    for bag = 0, 4 do
        for i = 1, GetContainerNumSlots(bag) or 0 do
            local link = GetContainerItemLink(bag, i)
            local slot = M.T9_SLOT_BY_ID[ItemIdFromLink(link) or 0]
            if slot and not found[slot] then found[slot] = link end
        end
    end
    return found
end

-- What a click on the Molten Armor button would do now:
-- "cast" (2+ T9 worn), "equip" (put T9 on first; picks = pieces to equip), "missing" (fewer than 2 T9 in total).
local function MoltenPlan()
    local count, worn = EquippedT9()
    if count >= 2 then return "cast", count end
    local bag, picks = BagT9(), {}
    for _, slot in ipairs(M.T9_SLOT_ORDER) do
        if count + #picks < 2 and bag[slot] and not worn[slot] then
            table.insert(picks, { slot = slot, link = bag[slot] })
        end
    end
    if count + #picks < 2 then return "missing", count + #picks end
    return "equip", count, picks
end

local function IsT9InSlot(slot)
    local id = ItemIdFromLink(GetInventoryItemLink("player", slot))
    return id ~= nil and M.T9_SLOT_BY_ID[id] ~= nil
end

-- Forget swap entries that are too old, in an old format, or whose T9 piece is no longer worn
-- (the player swapped back by hand): they must never put old gear back on later. keepOld: a
-- restore is pending because the cast happened in combat; then the age does not count (long fights).
local function CleanSwap(keepOld)
    for slot, e in pairs(chr.moltenSwap) do
        local tooOld = type(e) == "table" and not keepOld and time() - (e.at or 0) > M.SWAP_MAX_AGE
        if type(e) ~= "table" or tooOld or not IsT9InSlot(slot) then
            chr.moltenSwap[slot] = nil
        end
    end
end

-- A swap from a recent click 1 that has not been cast yet.
local function HasFreshSwap()
    for _, e in pairs(chr.moltenSwap) do
        if type(e) == "table" and time() - (e.at or 0) <= M.SWAP_MAX_AGE then return true end
    end
    return false
end

local function CancelVerify()
    if M.verifyTimer then MH:CancelTimer(M.verifyTimer, true); M.verifyTimer = nil end
end

local function EquipT9ForMolten(picks)
    CancelVerify() -- a restore check from an earlier cast must not undo this new swap
    for _, p in ipairs(picks) do
        chr.moltenSwap[p.slot] = { orig = GetInventoryItemLink("player", p.slot) or false, t9 = p.link, at = time() }
        EquipItemByName(p.link, p.slot)
    end
    M.swapPendingUntil = GetTime() + M.SWAP_SETTLE
    M.moltenStateCache = nil
end

-- Put the items taken off for the swap back on. Armor can't be changed in combat: then it waits
-- for PLAYER_REGEN_ENABLED (saved, so it also survives a reload). One second later VerifyRestore
-- checks the slots; 3 attempts in total.
local VerifyRestore
local function RestoreAfterMolten(isRetry)
    if not isRetry then CleanSwap(chr.moltenRestorePending); M.restoreTries = 0 end
    if not next(chr.moltenSwap) then chr.moltenRestorePending = false; return end
    if InCombatLockdown() then chr.moltenRestorePending = true; return end
    chr.moltenRestorePending = false
    for slot, e in pairs(chr.moltenSwap) do
        if not e.orig then
            chr.moltenSwap[slot] = nil -- the slot was empty before: leave the T9 piece on
        elseif GetItemCount(ItemIdFromLink(e.orig) or 0) == 0 then
            print(string.format(L("MageHelper: %s ist nicht mehr in den Taschen, das T9-Teil bleibt angelegt."), e.orig))
            chr.moltenSwap[slot] = nil
        else
            EquipItemByName(e.orig, slot)
        end
    end
    M.moltenStateCache = nil
    CancelVerify()
    if next(chr.moltenSwap) then M.verifyTimer = MH:ScheduleTimer(VerifyRestore, 1) end
end

VerifyRestore = function()
    M.verifyTimer = nil
    for slot, e in pairs(chr.moltenSwap) do
        if ItemIdFromLink(GetInventoryItemLink("player", slot)) == ItemIdFromLink(e.orig) then chr.moltenSwap[slot] = nil end
    end
    M.moltenStateCache = nil
    if not next(chr.moltenSwap) then return end
    M.restoreTries = M.restoreTries + 1
    if M.restoreTries < 3 then
        RestoreAfterMolten(true)
    else
        print(L("MageHelper: Ausrüstung konnte nicht vollständig zurückgewechselt werden, bitte von Hand prüfen."))
        wipe(chr.moltenSwap)
    end
end

-- State of the Molten Armor button:
--   buff up:      "bonus" / "nobonus" (cast with / without 2 T9 pieces), "ok" (swap option off),
--                 "ready" (click 1 for a rebuff done: T9 worn, click casts)
--   buff missing: "ready", "equip" (click puts T9 on), "missing" (fewer than 2 T9), "off" (option off)
--   "wait":       click 1 just happened, the server is still equipping
local function MoltenState()
    local now = GetTime()
    if M.moltenStateCache and now - M.moltenStateAt < 0.5 then return unpack(M.moltenStateCache) end
    local state, extra
    local active, remain = HasBuff("player", M.MOLTEN_BUFF_NAMES, M.MOLTEN_BUFF_IDS)
    -- buff gone (expired, dispelled, death): forget the bonus. Not right after a cast, the aura may
    -- arrive a moment after UNIT_SPELLCAST_SUCCEEDED.
    if not active and now - M.lastMoltenCast > 3 then chr.moltenBonus = false end
    if now < M.swapPendingUntil then
        state = "wait"
    elseif not cfg.moltenT9 then
        state = active and "ok" or "off"
        extra = remain
    else
        local plan, n = MoltenPlan()
        local rebuffing = active and plan == "cast" and HasFreshSwap() and not chr.moltenRestorePending
        if active and not rebuffing then
            state = chr.moltenBonus and "bonus" or "nobonus"
            extra = remain
        else
            state = (plan == "cast" and "ready") or plan
            extra = n
        end
    end
    M.moltenStateCache, M.moltenStateAt = { state, extra, active }, now
    return state, extra, active
end

M.MOLTEN_TIPS = {
    bonus = "Glühende Rüstung aktiv, gewirkt mit 2 T9-Teilen.",
    nobonus = "Glühende Rüstung aktiv, aber ohne T9 gewirkt. Klick zieht T9 an, der nächste Klick erneuert die Rüstung.",
    ok = "Glühende Rüstung aktiv.",
    ready = "T9 angelegt: Klick wirkt Glühende Rüstung, danach wechselt deine Ausrüstung zurück.",
    equip = "Klick 1 zieht T9-Teile aus den Taschen an, Klick 2 wirkt Glühende Rüstung.",
    missing = "Zu wenig T9-Teile für den Set-Bonus (%d von 2). Klick wirkt Glühende Rüstung ohne Bonus.",
    off = "Klick wirkt Glühende Rüstung.",
    wait = "T9 wird angelegt ...",
}
M.MOLTEN_LABELS = { bonus = "Rüstung", nobonus = "Rüstung", ok = "Rüstung", ready = "Casten", equip = "T9 an",
    missing = "kein T9", off = "Rüstung", wait = "..." }


local function EscapeMacroName(name)
    name = tostring(name or "")
    name = name:gsub("\n", ""):gsub("\r", "")
    return name
end

-- Set when the FM target changed in combat; PLAYER_REGEN_ENABLED applies it to the secure button.
local fmPendingAfterCombat = false
local RefreshFMPicker -- assigned in the Focus Magic picker section below

local function RefreshFocusMagicButton()
    local btn = buffButtons and buffButtons.fmout
    if not btn then return end
    -- SecureActionButton attributes must not be changed in combat. Keep the last valid macro until combat ends.
    if InCombatLockdown and InCombatLockdown() then fmPendingAfterCombat = true; return end
    fmPendingAfterCombat = false

    local target = EscapeMacroName(chr.focusMagicTarget or "")
    btn:SetAttribute("type", "macro")

    -- Important: WotLK macros do not reliably accept arbitrary saved player names as @unit tokens.
    -- Therefore the stored MF partner is handled via /targetexact + /cast + /targetlasttarget.
    -- Mouseover/focus still take priority and do not change your current target.
    local lines = {
        "#showtooltip " .. spells.focusMagic,
        "/cast [@mouseover,help,nodead][@focus,help,nodead] " .. spells.focusMagic,
    }
    if target ~= "" then
        table.insert(lines, "/targetexact " .. target)
        table.insert(lines, "/cast [help,nodead] " .. spells.focusMagic)
        table.insert(lines, "/targetlasttarget")
    else
        table.insert(lines, "/cast [@target,help,nodead] " .. spells.focusMagic)
    end
    btn:SetAttribute("macrotext", table.concat(lines, "\n"))
end

local function RefreshFocusMagicLabel()
    if not buffBar or not buffBar.fmTargetText then return end
    local target = chr.focusMagicTarget or ""
    local partner = chr.focusMagicPartner or ""
    local text
    if target ~= "" then
        text = string.format(L("MF-Ziel: %s"), target)
        if partner ~= "" and partner ~= target then text = text .. string.format(L(" (Partner: %s)"), partner) end
        buffBar.fmTargetText:SetTextColor(0.25, 1.0, 0.25)
    else
        text = L("MF-Ziel: kein Ziel gesetzt")
        buffBar.fmTargetText:SetTextColor(1.0, 0.25, 0.25)
    end
    if fmPendingAfterCombat then text = text .. " |cffffaa00" .. L("(gilt ab Kampfende)") .. "|r" end
    buffBar.fmTargetText:SetText(text)
end

-- asPartner: also save as the fixed partner. The target change is what the FM OUT button casts on;
-- nothing is cast here. In combat the secure button keeps its old target until combat ends.
local function SetFocusMagicTarget(name, asPartner)
    name = name or ""
    chr.focusMagicTarget = name
    if asPartner then chr.focusMagicPartner = name end
    RefreshFocusMagicButton()
    RefreshFocusMagicLabel()
    if RefreshFMPicker then RefreshFMPicker() end
    if name == "" then
        print(L("MageHelper: Fokusmagie-Ziel gelöscht"))
    elseif asPartner then
        print(string.format(L("MageHelper: MF-Partner gespeichert: %s"), name))
    else
        print(string.format(L("MageHelper: Fokusmagie-Ziel gesetzt: %s"), name))
    end
    if fmPendingAfterCombat then print(L("MageHelper: Im Kampf - das neue MF-Ziel gilt ab Kampfende.")) end
end

local function BackToPartner()
    local partner = chr.focusMagicPartner or ""
    if partner == "" then print(L("MageHelper: Kein MF-Partner gespeichert.")); return end
    SetFocusMagicTarget(partner, false)
end

local function CreateBuffButton(parent, data)
    local btn = CreateFrame("Button", "MageHelperBuff_"..data.key, parent, data.cast and "SecureActionButtonTemplate" or nil)
    btn:SetWidth(34); btn:SetHeight(34)
    btn.data = data
    btn.icon = btn:CreateTexture(nil, "BACKGROUND")
    btn.icon:SetAllPoints(btn)
    btn.icon:SetTexture(GetBestIcon(data))
    btn.shade = btn:CreateTexture(nil, "ARTWORK")
    btn.shade:SetAllPoints(btn)
    btn.shade:SetTexture("Interface\\Tooltips\\UI-Tooltip-Background")
    btn.shade:SetVertexColor(0,0,0,0.35)
    -- v2.1: clear red/green status overlay. The old white border was too weak and did not show state reliably.
    btn.status = btn:CreateTexture(nil, "OVERLAY")
    btn.status:SetAllPoints(btn)
    btn.status:SetTexture("Interface\\Buttons\\WHITE8x8")
    btn.status:SetBlendMode("ADD")
    btn.border = btn:CreateTexture(nil, "OVERLAY")
    btn.border:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    btn.border:SetBlendMode("ADD")
    btn.border:SetWidth(54); btn.border:SetHeight(54)
    btn.border:SetPoint("CENTER")
    btn.text = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    btn.text:SetPoint("TOP", btn, "BOTTOM", 0, -1)
    btn.text:SetText(L(data.label))
    ThemeText(btn.text)
    btn.timer = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    btn.timer:SetPoint("CENTER", btn, "CENTER", 0, 0)
    if data.cast then btn:RegisterForClicks("LeftButtonUp", "RightButtonUp") end
    if data.special == "molten" then
        -- Default action casts Molten Armor (also in combat). Out of combat, PreClick may turn this
        -- click into the T9 swap instead (no cast), and PostClick restores the cast action.
        btn:SetAttribute("type", "spell")
        btn:SetAttribute("spell", spells.molten)
        btn:RegisterForClicks("LeftButtonUp")
        btn:SetScript("PreClick", function(self)
            if InCombatLockdown() or not cfg.moltenT9 then return end
            if GetTime() < M.swapPendingUntil then self:SetAttribute("type", nil); return end
            local plan, _, picks = MoltenPlan()
            if plan == "equip" then
                self:SetAttribute("type", nil)
                EquipT9ForMolten(picks)
            end
        end)
        btn:SetScript("PostClick", function(self)
            if not InCombatLockdown() then self:SetAttribute("type", "spell") end
            M.moltenStateCache = nil
        end)
    elseif data.special == "focus_out" then
        btn:SetAttribute("type", "macro")
        btn:RegisterForClicks("LeftButtonUp")
        -- real macro text is set in RefreshFocusMagicButton() after all buttons exist
        btn:SetScript("PostClick", function()
            if MageHelper_UpdateBuffBar then MageHelper_UpdateBuffBar() end
        end)
    elseif data.cast then
        btn:SetAttribute("type", "spell")
        btn:SetAttribute("spell", data.cast)
    end
    btn:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:SetText(L(self.data.label))
        -- names lists are {German, English, ...}; show the buff name in the display language.
        local buffName = (self.data.iconSpellId and GetSpellInfo(self.data.iconSpellId)) or self.data.names[useEnglish and 2 or 1]
        if self.data.special == "flask" then buffName = FlaskChoiceText() end
        GameTooltip:AddLine(buffName or "", 1,1,1, true)
        if self.data.special == "molten" then
            local state, extra = MoltenState()
            GameTooltip:AddLine(string.format(L(M.MOLTEN_TIPS[state]), extra or 0), 0.7,0.9,1, true)
        elseif self.data.special == "focus_out" then
            local target = chr.focusMagicTarget or ""
            if target ~= "" then GameTooltip:AddLine(string.format(L("Klick: Fokusmagie auf %s und danach zurück aufs letzte Ziel"), target), 0.7,0.9,1, true)
            else GameTooltip:AddLine(L("Klick: Fokusmagie auf Mouseover, Fokus oder Ziel. MF-Ziel auswählen über MF SET"), 0.7,0.9,1, true) end
        elseif self.data.special == "focus_in" then
            GameTooltip:AddLine(L("Status: Habe ich Fokusmagie von einem anderen Mage?"), 0.7,0.9,1, true)
        elseif self.data.statusOnly then
            GameTooltip:AddLine(L("Statusanzeige: rot fehlt, grün aktiv"), 0.7,0.9,1, true)
        elseif self.data.cast then GameTooltip:AddLine(L("Klick: Buff wirken"), 0.7,0.9,1) end
        GameTooltip:Show()
    end)
    btn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    buffButtons[data.key] = btn
    return btn
end

-- =============================
-- Focus Magic target picker
-- =============================
-- Scrollable, alphabetical list of the raid/party with two optional filters ("only mages",
-- "only healers without FM"). Healers are found by inspecting the active talent spec of
-- healing classes while the window is open; not yet inspected ones show as "Heiler?".
local FM_ROWS = 12
local FM_ROW_HEIGHT = 22
local FM_LIST_WIDTH = 352
local fmPicker
local fmRoster = {}
local fmRoles = {}           -- [guid] = "healer" | "other", filled by inspection, kept for the session
local fmInspectQueue = {}    -- GUIDs still to inspect
local fmInspectPending       -- { unit, guid, started } while waiting for INSPECT_TALENT_READY
local fmNextInspectAt = 0
local fmRefreshAt = 0

-- Talent tabs that count as healing specs (WotLK tab order).
local HEALER_TABS = {
    PRIEST = { [1] = true, [2] = true }, -- Discipline, Holy
    PALADIN = { [1] = true },            -- Holy
    DRUID = { [3] = true },              -- Restoration
    SHAMAN = { [3] = true },             -- Restoration
}

local function FocusMagicOn(unit)
    for i = 1, 40 do
        local n, _, _, _, _, _, _, caster, _, _, spellId = UnitBuff(unit, i)
        if not n then break end
        if spellId == 54646 or n == spells.focusMagic or n == "Fokusmagie" or n == "Focus Magic" then
            return true, caster and UnitName(caster) or "?"
        end
    end
    return false
end

local function BuildFMRoster()
    wipe(fmRoster)
    for _, unit in ipairs(IterateGroupUnits()) do
        if UnitExists(unit) and not UnitIsUnit(unit, "player") then
            local _, class = UnitClass(unit)
            local guid = UnitGUID(unit)
            local role = "other"
            if HEALER_TABS[class or ""] then role = (guid and fmRoles[guid]) or "unknown" end
            local hasFM, fmFrom = FocusMagicOn(unit)
            table.insert(fmRoster, {
                unit = unit, name = UnitName(unit) or "?", class = class, guid = guid, role = role,
                hasFM = hasFM, fmFrom = fmFrom,
                online = UnitIsConnected(unit) and true or false, dead = UnitIsDeadOrGhost(unit) and true or false,
            })
        end
    end
    table.sort(fmRoster, function(a, b) return a.name < b.name end)
end

local function FilteredFMRoster()
    local list = {}
    for _, e in ipairs(fmRoster) do
        local ok = true
        if cfg.fmFilterMages and e.class ~= "MAGE" then ok = false end
        if cfg.fmFilterHealers and (e.role == "other" or e.hasFM) then ok = false end
        if ok then table.insert(list, e) end
    end
    return list
end

local function UnitFromGUID(guid)
    for _, unit in ipairs(IterateGroupUnits()) do
        if UnitGUID(unit) == guid then return unit end
    end
end

-- Re-check every healing-class member each time the window opens (people respec at Valithria).
local function QueueFMInspects()
    wipe(fmInspectQueue)
    fmInspectPending = nil
    for _, e in ipairs(fmRoster) do
        if HEALER_TABS[e.class or ""] and e.guid then table.insert(fmInspectQueue, e.guid) end
    end
end

local function ProcessFMInspect()
    local now = GetTime()
    if fmInspectPending then
        if now - fmInspectPending.started < 2.5 then return end
        fmInspectPending = nil -- no answer: keep the previous result, try the next one
    end
    if now < fmNextInspectAt then return end
    if InspectFrame and InspectFrame:IsShown() then return end -- don't hijack the player's own inspect
    while #fmInspectQueue > 0 do
        local guid = table.remove(fmInspectQueue, 1)
        local unit = UnitFromGUID(guid)
        if unit and UnitIsConnected(unit) and CanInspect(unit) and CheckInteractDistance(unit, 1) then
            fmInspectPending = { unit = unit, guid = guid, started = now }
            NotifyInspect(unit)
            return
        end
    end
end

local function OnFMInspectReady()
    local p = fmInspectPending
    if not p then return end
    fmInspectPending = nil
    fmNextInspectAt = GetTime() + 0.3
    if UnitGUID(p.unit) ~= p.guid then return end
    local _, class = UnitClass(p.unit)
    local healTabs = HEALER_TABS[class or ""]
    if not healTabs then return end
    local group = GetActiveTalentGroup and GetActiveTalentGroup(true) or nil
    local best, bestPoints, total = nil, -1, 0
    for tab = 1, 3 do
        local _, _, points = GetTalentTabInfo(tab, true, false, group)
        points = points or 0
        total = total + points
        if points > bestPoints then best, bestPoints = tab, points end
    end
    if total > 0 then fmRoles[p.guid] = healTabs[best] and "healer" or "other" end
    if RefreshFMPicker then RefreshFMPicker() end
end

RefreshFMPicker = function()
    if not fmPicker or not fmPicker:IsShown() then return end
    BuildFMRoster()
    local list = FilteredFMRoster()
    FauxScrollFrame_Update(fmPicker.scroll, #list, FM_ROWS, FM_ROW_HEIGHT)
    local offset = FauxScrollFrame_GetOffset(fmPicker.scroll)
    local target = chr.focusMagicTarget or ""
    local partner = chr.focusMagicPartner or ""
    local me = UnitName("player")
    for i = 1, FM_ROWS do
        local row = fmPicker.rows[i]
        local e = list[offset + i]
        if e then
            row.entryName = e.name
            row.name:SetText(e.name)
            local c = RAID_CLASS_COLORS and RAID_CLASS_COLORS[e.class or ""]
            if not e.online or e.dead then row.name:SetTextColor(0.5, 0.5, 0.5)
            elseif c then row.name:SetTextColor(c.r, c.g, c.b)
            else row.name:SetTextColor(1, 1, 1) end
            local parts = {}
            if e.name == target then table.insert(parts, "|cff33ff33" .. L("Ziel") .. "|r") end
            if e.name == partner then table.insert(parts, "|cff66ccff" .. L("Partner") .. "|r") end
            if not e.online then table.insert(parts, L("offline")) elseif e.dead then table.insert(parts, L("tot")) end
            if e.role == "healer" then table.insert(parts, L("Heiler")) elseif e.role == "unknown" then table.insert(parts, L("Heiler?")) end
            if e.hasFM then table.insert(parts, string.format(L("MF von %s"), e.fmFrom == me and L("dir") or e.fmFrom)) end
            row.info:SetText(table.concat(parts, ", "))
            row:Show()
        else
            row.entryName = nil
            row:Hide()
        end
    end
    if #list == 0 then
        fmPicker.empty:SetText(#fmRoster == 0 and L("Du bist in keiner Gruppe.") or L("Niemand passt zu den Filtern."))
        fmPicker.empty:Show()
    else
        fmPicker.empty:Hide()
    end
    local status = string.format(L("Ziel: %s   Partner: %s"), target ~= "" and target or "-", partner ~= "" and partner or "-")
    if fmPendingAfterCombat then status = status .. "  |cffffaa00" .. L("(gilt ab Kampfende)") .. "|r" end
    fmPicker.status:SetText(status)
    if partner ~= "" and partner ~= target then fmPicker.backButton:Enable() else fmPicker.backButton:Disable() end
    local open = #fmInspectQueue + (fmInspectPending and 1 or 0)
    fmPicker.inspectText:SetText(open > 0 and string.format(L("Talente werden geprüft: %d offen"), open) or "")
end

local function CreateFMPicker()
    local f = CreateFrame("Frame", "MageHelperFMPicker", UIParent)
    f:SetWidth(FM_LIST_WIDTH + 48); f:SetHeight(122 + FM_ROWS * FM_ROW_HEIGHT)
    f:SetPoint("CENTER", UIParent, "CENTER", 0, 60)
    f:SetFrameStrata("DIALOG")
    f:SetClampedToScreen(true)
    f:SetMovable(true); f:EnableMouse(true)
    f:RegisterForDrag("LeftButton")
    f:SetScript("OnDragStart", function(self) self:StartMoving() end)
    f:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    f.bg = f:CreateTexture(nil, "BACKGROUND"); f.bg:SetAllPoints(f); f.bg:SetTexture(0, 0, 0, 0.85)
    ThemePanel(f, 0.85)
    f.title = f:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    ThemeTitle(f.title)
    f.title:SetPoint("TOPLEFT", 12, -10)
    f.title:SetText(L("MF-Ziel auswählen"))
    local close = CreateFrame("Button", nil, f, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", f, "TOPRIGHT", 2, 2)

    local function MakeFilter(name, key, label, x)
        local cb = CreateFrame("CheckButton", name, f, "UICheckButtonTemplate")
        cb:SetWidth(24); cb:SetHeight(24)
        cb:SetPoint("TOPLEFT", f, "TOPLEFT", x, -34)
        local text = _G[name .. "Text"]
        if text then text:SetText(label) end
        cb:SetChecked(cfg[key])
        cb:SetScript("OnClick", function(self)
            cfg[key] = self:GetChecked() and true or false
            FauxScrollFrame_SetOffset(f.scroll, 0)
            RefreshFMPicker()
        end)
        return cb
    end
    f.filterMages = MakeFilter("MageHelperFMFilterMages", "fmFilterMages", L("Nur Mages"), 10)
    f.filterHealers = MakeFilter("MageHelperFMFilterHealers", "fmFilterHealers", L("Nur Heiler ohne MF"), 160)
    f.filterHealers:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:SetText(L("Nur Heiler ohne MF"))
        GameTooltip:AddLine(L("Heiler? = Skillung noch nicht geprüft (zu weit weg?)"), 0.7, 0.9, 1, true)
        GameTooltip:Show()
    end)
    f.filterHealers:SetScript("OnLeave", function() GameTooltip:Hide() end)

    f.status = f:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    f.status:SetPoint("TOPLEFT", f, "TOPLEFT", 14, -64)
    f.status:SetWidth(FM_LIST_WIDTH); f.status:SetJustifyH("LEFT")

    f.scroll = CreateFrame("ScrollFrame", "MageHelperFMScroll", f, "FauxScrollFrameTemplate")
    f.scroll:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -82)
    f.scroll:SetWidth(FM_LIST_WIDTH); f.scroll:SetHeight(FM_ROWS * FM_ROW_HEIGHT)
    f.scroll:SetScript("OnVerticalScroll", function(self, offset)
        FauxScrollFrame_OnVerticalScroll(self, offset, FM_ROW_HEIGHT, RefreshFMPicker)
    end)

    f.rows = {}
    for i = 1, FM_ROWS do
        local row = CreateFrame("Frame", nil, f)
        row:SetWidth(FM_LIST_WIDTH); row:SetHeight(FM_ROW_HEIGHT)
        row:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -82 - (i - 1) * FM_ROW_HEIGHT)
        row.name = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        row.name:SetPoint("LEFT", row, "LEFT", 2, 0)
        row.name:SetWidth(100); row.name:SetHeight(FM_ROW_HEIGHT); row.name:SetJustifyH("LEFT")
        row.info = row:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        row.info:SetPoint("LEFT", row, "LEFT", 104, 0)
        row.info:SetWidth(138); row.info:SetHeight(FM_ROW_HEIGHT); row.info:SetJustifyH("LEFT")
        local function MakeRowButton(label, x, w, tip, asPartner)
            local b = CreateFrame("Button", nil, row, "UIPanelButtonTemplate")
            b:SetWidth(w); b:SetHeight(18)
            b:SetPoint("LEFT", row, "LEFT", x, 0)
            b:SetText(label)
            b:SetScript("OnClick", function() if row.entryName then SetFocusMagicTarget(row.entryName, asPartner) end end)
            b:SetScript("OnEnter", function(self)
                GameTooltip:SetOwner(self, "ANCHOR_TOP")
                GameTooltip:SetText(tip, 1, 1, 1, true)
                GameTooltip:Show()
            end)
            b:SetScript("OnLeave", function() GameTooltip:Hide() end)
            return b
        end
        row.targetButton = MakeRowButton(L("Ziel"), 244, 50, L("Jetzt als MF-Ziel nutzen (vorübergehend)"), false)
        row.partnerButton = MakeRowButton(L("Partner"), 296, 56, L("Als festen MF-Partner speichern (wird auch Ziel)"), true)
        row:Hide()
        f.rows[i] = row
    end

    f.empty = f:CreateFontString(nil, "OVERLAY", "GameFontDisable")
    f.empty:SetPoint("TOP", f, "TOP", 0, -120)

    f.backButton = CreateFrame("Button", nil, f, "UIPanelButtonTemplate")
    f.backButton:SetWidth(140); f.backButton:SetHeight(22)
    f.backButton:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 10, 10)
    f.backButton:SetText(L("Zurück zum Partner"))
    f.backButton:SetScript("OnClick", BackToPartner)

    f.inspectText = f:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    f.inspectText:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -12, 16)

    f:SetScript("OnShow", function()
        fmRefreshAt = 0
        BuildFMRoster()
        QueueFMInspects()
        RefreshFMPicker()
    end)
    f:SetScript("OnUpdate", function()
        ProcessFMInspect()
        if GetTime() >= fmRefreshAt then
            fmRefreshAt = GetTime() + 0.5
            RefreshFMPicker()
        end
    end)
    f:Hide()
    tinsert(UISpecialFrames, "MageHelperFMPicker") -- Escape closes the window
    fmPicker = f
    ApplyTheme()
end

local function ToggleFMPicker()
    if not fmPicker then CreateFMPicker() end
    if fmPicker:IsShown() then fmPicker:Hide() else fmPicker:Show() end
end

local function CreateBuffBar()
    buffBar = CreateFrame("Frame", "MageHelperBuffBar", UIParent)
    buffBar:SetWidth(500); buffBar:SetHeight(82)
    buffBar:SetPoint("CENTER", UIParent, "CENTER", cfg.buffBarX, cfg.buffBarY)
    buffBar:SetMovable(true); buffBar:EnableMouse(true)
    buffBar:RegisterForDrag("LeftButton")
    buffBar:SetScript("OnDragStart", function(self) if not cfg.buffBarLocked then self:StartMoving() end end)
    buffBar:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local _,_,_,x,y = self:GetPoint()
        cfg.buffBarX, cfg.buffBarY = x or 0, y or -270
    end)
    buffBar.bg = buffBar:CreateTexture(nil, "BACKGROUND")
    buffBar.bg:SetAllPoints(buffBar)
    buffBar.bg:SetTexture(0,0,0,0.30)
    ThemePanel(buffBar, 0.30, true)
    buffBar.title = buffBar:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    ThemeTitle(buffBar.title)
    buffBar.title:SetPoint("BOTTOMLEFT", buffBar, "TOPLEFT", 4, 2)
    buffBar.title:SetText("MageHelper Buffs")
    local x = 8
    for _, data in ipairs(buffChecks) do
        local b = CreateBuffButton(buffBar, data)
        b:SetPoint("TOPLEFT", buffBar, "TOPLEFT", x, -8)
        x = x + 43
    end

    -- Opens the Focus Magic target picker. Not a secure button: it only chooses the target of FM OUT.
    buffBar.fmSetButton = CreateFrame("Button", "MageHelperBuff_FMSet", buffBar)
    buffBar.fmSetButton:SetWidth(54); buffBar.fmSetButton:SetHeight(24)
    buffBar.fmSetButton:SetPoint("TOPLEFT", buffBar, "TOPLEFT", x + 4, -12)
    buffBar.fmSetButton.bg = buffBar.fmSetButton:CreateTexture(nil, "BACKGROUND")
    buffBar.fmSetButton.bg:SetAllPoints(buffBar.fmSetButton)
    buffBar.fmSetButton.bg:SetTexture("Interface\\Buttons\\WHITE8x8")
    buffBar.fmSetButton.bg:SetVertexColor(0.08, 0.35, 0.95, 0.75)
    buffBar.fmSetButton.text = buffBar.fmSetButton:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    buffBar.fmSetButton.text:SetPoint("CENTER")
    buffBar.fmSetButton.text:SetText(L("MF SET"))
    ThemeButton(buffBar.fmSetButton.bg, buffBar.fmSetButton.text)
    buffBar.fmSetButton:SetScript("OnClick", ToggleFMPicker)
    buffBar.fmSetButton:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:SetText(L("MF-Ziel auswählen"))
        GameTooltip:AddLine(L("Öffnet die Liste der Gruppe mit Filtern."), 0.7,0.9,1, true)
        GameTooltip:AddLine(L("Der MF-OUT-Button nutzt danach das gewählte Ziel."), 0.7,0.9,1, true)
        GameTooltip:Show()
    end)
    buffBar.fmSetButton:SetScript("OnLeave", function() GameTooltip:Hide() end)

    buffBar.fmTargetText = buffBar:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    buffBar.fmTargetText:SetPoint("TOPLEFT", buffBar, "TOPLEFT", 8, -58)
    buffBar.fmTargetText:SetWidth(480)
    buffBar.fmTargetText:SetJustifyH("LEFT")

    RefreshFocusMagicButton()
    RefreshFocusMagicLabel()
    if not cfg.buffBarShown then buffBar:Hide() end
end

local function CreateUI()
    KR:SetWidth(580); KR:SetHeight(104)
    KR:SetPoint("CENTER", UIParent, "CENTER", cfg.x, cfg.y)
    KR:SetMovable(true); KR:EnableMouse(true)
    KR:RegisterForDrag("LeftButton")
    KR:SetScript("OnDragStart", function(self) if not cfg.locked then self:StartMoving() end end)
    KR:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local _,_,_,x,y = self:GetPoint()
        cfg.x, cfg.y = x or 0, y or -170
    end)

    KR.bg = KR:CreateTexture(nil, "BACKGROUND")
    KR.bg:SetAllPoints(KR)
    KR.bg:SetTexture(0,0,0,0.35)
    ThemePanel(KR, 0.35, true)

    local order = {
        {"lb", "LB", spells.lb},
        {"pyro", "Pyro", spells.pyro},
        {"fireball", "FB", spells.fireball},
        {"comb", "Comb", spells.combustion},
        -- Items by ID: 33312 Mana Sapphire, 40212 Potion of Wild Magic, 22788 Flame Cap.
        {"cd", "CD", spells.mirror, table.concat({"#showtooltip " .. spells.mirror, "/use 10", "/use " .. ItemName(33312), "/use " .. ItemName(40212), "/use " .. ItemName(22788), "/cast " .. spells.mirror}, "\n")},
        {"fb_move", "Move", spells.fireblast},
        {"ice", "IB", spells.iceblock, "#showtooltip " .. spells.iceblock .. "\n/cancelaura " .. spells.iceblock .. "\n/cast " .. spells.iceblock},
        {"invis", "Invis", spells.invis, "#showtooltip " .. spells.invis .. "\n/cancelaura " .. spells.invis .. "\n/cast " .. spells.invis},
        {"stop", "CS", spells.stop, "#showtooltip " .. spells.stop .. "\n/stopcasting\n/cast [@mouseover,harm,nodead][] " .. spells.stop},
    }
    local x = 8
    for _, data in ipairs(order) do
        local b = CreateSpellButton(KR, data[1], data[2], data[3], data[4])
        b:SetPoint("TOPLEFT", KR, "TOPLEFT", x, -8)
        x = x + 53
    end
    -- Arcane set (Ice Block, Invisibility, Counterspell and the Fire Blast move button are shared).
    -- M.LayoutRota shows only the buttons of the active rotation.
    for _, data in ipairs({
        {"ab", "AB", spells.ab}, {"am", "AM", spells.am}, {"abarr", "ABarr", spells.abarr},
        {"ap", "AP", spells.ap}, {"pom", "PoM", spells.pom}, {"mirror", "MI", spells.mirror},
        {"evo", "Evo", spells.evo},
    }) do
        CreateSpellButton(KR, data[1], data[2], data[3], data[4])
    end
    buttons.ap.macroBuilder = M.ArcanePowerMacro -- Arcane Power + Icy Veins when known (off the GCD)
    buttons.ap.cooldownRemaining = M.ApCooldownRemaining -- usable when either of the two is
    SetMacro(buttons.ap, M.ArcanePowerMacro())
    local gem = CreateSpellButton(KR, "gem", "Gem", ItemName(M.MANA_GEM_ITEM),
        "#showtooltip " .. ItemName(M.MANA_GEM_ITEM) .. "\n/use " .. ItemName(M.MANA_GEM_ITEM))
    gem.spellName, gem.itemId = nil, M.MANA_GEM_ITEM
    gem.icon:SetTexture((GetItemIcon and GetItemIcon(M.MANA_GEM_ITEM)) or "Interface\\Icons\\INV_Misc_Gem_Stone_01")
    M.LayoutRota(M.DesiredRota())

    local ob = CreateOneButton(KR)
    ob:SetPoint("TOPRIGHT", KR, "TOPRIGHT", -10, -18)

    KR.info = KR:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    KR.info:SetPoint("TOPLEFT", KR, "BOTTOMLEFT", 4, -18)
    KR.info:SetJustifyH("LEFT")
    KR.info:SetText("MageHelper")

    KR.debugInfo = KR:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    KR.debugInfo:SetPoint("TOPLEFT", KR.info, "BOTTOMLEFT", 0, -2)
    KR.debugInfo:SetJustifyH("LEFT")
    KR.debugInfo:SetTextColor(0.7, 0.9, 1)
    KR.debugInfo:SetText("")

    KR.gap = KR:CreateTexture(nil, "OVERLAY")
    KR.gap:SetTexture("Interface\\Tooltips\\UI-Tooltip-Background")
    KR.gap:SetVertexColor(1,0,0,0.35)
    KR.gap:SetAllPoints(KR)
    KR.gap:Hide()

    -- Simple minimap toggle button; no menu.
    local mm = CreateFrame("Button", "MageHelperMinimapButton", Minimap)
    mm:SetWidth(28); mm:SetHeight(28)
    mm:SetFrameStrata("MEDIUM")
    mm:SetPoint("TOPRIGHT", Minimap, "BOTTOMRIGHT", cfg.minimapX, cfg.minimapY)
    mm.icon = mm:CreateTexture(nil, "BACKGROUND")
    mm.icon:SetAllPoints(mm)
    mm.icon:SetTexture(select(3, GetSpellInfo(spells.fireball)) or "Interface\\Icons\\Spell_Fire_FlameBolt")
    mm.border = mm:CreateTexture(nil, "OVERLAY")
    mm.border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    mm.border:SetWidth(54); mm.border:SetHeight(54)
    mm.border:SetPoint("TOPLEFT", -12, 12)
    mm:RegisterForClicks("LeftButtonUp")
    mm:SetScript("OnClick", function()
        cfg.shown = not cfg.shown
        if cfg.shown then KR:Show() else KR:Hide() end
    end)
    mm:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:SetText("MageHelper")
        GameTooltip:AddLine(L("Linksklick: Bar an/aus"), 1,1,1)
        GameTooltip:Show()
    end)
    mm:SetScript("OnLeave", function() GameTooltip:Hide() end)
    -- Second small minimap toggle button for Buff-Bar only.
    local bm = CreateFrame("Button", "MageHelperBuffMinimapButton", Minimap)
    bm:SetWidth(24); bm:SetHeight(24)
    bm:SetFrameStrata("MEDIUM")
    bm:SetPoint("TOPRIGHT", Minimap, "BOTTOMRIGHT", cfg.buffMinimapX, cfg.buffMinimapY)
    bm.icon = bm:CreateTexture(nil, "BACKGROUND")
    bm.icon:SetAllPoints(bm)
    bm.icon:SetTexture(select(3, GetSpellInfo(spells.molten)) or "Interface\\Icons\\Spell_Fire_Incinerate")
    bm.border = bm:CreateTexture(nil, "OVERLAY")
    bm.border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    bm.border:SetWidth(50); bm.border:SetHeight(50)
    bm.border:SetPoint("TOPLEFT", -12, 12)
    bm:RegisterForClicks("LeftButtonUp")
    bm:SetScript("OnClick", function()
        cfg.buffBarShown = not cfg.buffBarShown
        if buffBar then if cfg.buffBarShown then buffBar:Show() else buffBar:Hide() end end
    end)
    bm:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:SetText("MageHelper Buffs")
        GameTooltip:AddLine(L("Linksklick: Buff-Bar an/aus"), 1,1,1)
        GameTooltip:Show()
    end)
    bm:SetScript("OnLeave", function() GameTooltip:Hide() end)
    KR.buffMinimap = bm

    KR.minimap = mm

    CreateBuffBar()

    if not cfg.shown then KR:Hide() end
end

local function UpdateFireballCount()
    local now = GetTime()
    while #fireballTimes > 0 and now - fireballTimes[1] > 60 do table.remove(fireballTimes, 1) end
    return #fireballTimes
end


-- =============================
-- MageHelper Analyzer / Recorder
-- =============================
local analyzer = {
    current = nil,
    training = nil,
    incoming = {},
    lastDeath = nil,
    lastThreatWarn = 0,
    lastInvisOverride = 0,
    lastInterruptOverride = 0,
}

local importantInterrupts = {
    names = {
        ["Frostblitz"] = true, ["Frostbolt"] = true,
        ["Dunkle Heilung"] = true, ["Dark Mending"] = true,
        ["Seelenrei\195\159en"] = true, ["Seelenreißen"] = true, ["Soul Rip"] = true,
    },
    partialNames = { "frostblitz", "frostbolt", "dunkle heilung", "dark mending", "seelenrei", "soul rip" },
    ids = { [69397] = true, [17613] = true, [16588] = true },
}

local function AnalyzerDB()
    chr.analyzer = chr.analyzer or {}
    chr.analyzer.bossFights = chr.analyzer.bossFights or {}
    chr.analyzer.deathRecaps = chr.analyzer.deathRecaps or {}
    return chr.analyzer
end

local function NewRun(mode, name)
    return {
        mode = mode or "boss",
        name = name or (UnitName("target") or L("Unbekannt")),
        start = GetTime(),
        duration = 0,
        damageDone = 0,
        damageTaken = 0,
        incomingDamage = 0,
        pyroCasts = 0,
        hotProcs = 0,
        lbApplications = 0,
        lbTicks = 0,
        counterspellUses = 0,
        interrupts = 0,
        invisWarnings = 0,
        threatWarnings = 0,
        deaths = 0,
    }
end

local function FinishRun(run)
    if not run then return nil end
    run.duration = math.max((GetTime() - (run.start or GetTime())), 0)
    run.dps = run.duration > 0 and (run.damageDone / run.duration) or 0
    return run
end

local function CopyRun(src)
    if not src then return nil end
    local dst = {}
    for k,v in pairs(src) do
        if type(v) ~= "table" then dst[k] = v end
    end
    return dst
end

local function SaveBossRun(run)
    local db = AnalyzerDB()
    local copy = CopyRun(FinishRun(run))
    if not copy or (copy.duration or 0) < 5 then return end
    table.insert(db.bossFights, 1, copy)
    while #db.bossFights > 10 do table.remove(db.bossFights) end
end

local function AnalyzerActiveRun()
    return analyzer.training or analyzer.current
end

local function AnalyzerAdd(field, amount)
    local run = AnalyzerActiveRun()
    if run then run[field] = (run[field] or 0) + (amount or 1) end
end

local function FormatRunLine(label, r)
    if not r then return string.format(L("%s: kein Lauf"), label) end
    return string.format("%s: %.0fs  %.0f dmg  %.0f DPS  Pyro %d  HS %d  LB %d/%d  CS %d  Invis %d  DmgTaken %.0f", label, r.duration or 0, r.damageDone or 0, r.dps or 0, r.pyroCasts or 0, r.hotProcs or 0, r.lbApplications or 0, r.lbTicks or 0, r.counterspellUses or 0, r.invisWarnings or 0, r.damageTaken or 0)
end

local function RefreshAnalyzerWindow()
    if not analyzerFrame then return end
    local db = AnalyzerDB()
    local lines = {}
    table.insert(lines, analyzer.training and L("|cff33ff33Training läuft...|r") or L("Training/Puppenmodus bereit"))
    if db.lastTraining then table.insert(lines, FormatRunLine(L("Letzter Test"), db.lastTraining)) end
    table.insert(lines, FormatRunLine(L("Lauf A"), db.trainingA))
    table.insert(lines, FormatRunLine(L("Lauf B"), db.trainingB))
    if db.trainingA and db.trainingB then
        local ddps = (db.trainingB.dps or 0) - (db.trainingA.dps or 0)
        local dfb = (db.trainingB.pyroCasts or 0) - (db.trainingA.pyroCasts or 0)
        table.insert(lines, string.format(L("Vergleich B-A: DPS %+0.0f, Pyros %+d"), ddps, dfb))
    end
    if db.bossFights and db.bossFights[1] then table.insert(lines, L("Letzter Boss: ") .. FormatRunLine(db.bossFights[1].name or "Boss", db.bossFights[1])) end
    if db.deathRecaps and db.deathRecaps[1] then table.insert(lines, L("Letzter Tod gespeichert: ") .. (db.deathRecaps[1].timeText or "?")) end
    analyzerFrame.text:SetText(table.concat(lines, "\n"))
end

local function AnalyzerStartTraining()
    analyzer.training = NewRun("training", UnitName("target") or L("Trainingslauf"))
    print(L("MageHelper Analyse: Training gestartet"))
    RefreshAnalyzerWindow()
end

local function AnalyzerStopTraining()
    local db = AnalyzerDB()
    if analyzer.training then
        db.lastTraining = CopyRun(FinishRun(analyzer.training))
        analyzer.training = nil
        print(L("MageHelper Analyse: Training gestoppt und als letzter Test gespeichert"))
    else
        print(L("MageHelper Analyse: Es läuft kein Training"))
    end
    RefreshAnalyzerWindow()
end

local function AnalyzerSaveSlot(slot)
    local db = AnalyzerDB()
    if not db.lastTraining then print(L("MageHelper Analyse: Kein letzter Test vorhanden")); return end
    if slot == "A" then db.trainingA = CopyRun(db.lastTraining) else db.trainingB = CopyRun(db.lastTraining) end
    print(string.format(L("MageHelper Analyse: Lauf %s gespeichert"), slot))
    RefreshAnalyzerWindow()
end

local function AnalyzerCompare()
    local db = AnalyzerDB()
    if not db.trainingA or not db.trainingB then print(L("MageHelper Analyse: Lauf A und B müssen gespeichert sein")); return end
    print(L("|cffff7d0aMageHelper Analyse Vergleich|r"))
    print(FormatRunLine("A", db.trainingA))
    print(FormatRunLine("B", db.trainingB))
    print(string.format(L("B-A DPS: %+0.0f, Schaden: %+0.0f, Pyros: %+d, Hot-Streak-Procs: %+d"), (db.trainingB.dps or 0)-(db.trainingA.dps or 0), (db.trainingB.damageDone or 0)-(db.trainingA.damageDone or 0), (db.trainingB.pyroCasts or 0)-(db.trainingA.pyroCasts or 0), (db.trainingB.hotProcs or 0)-(db.trainingA.hotProcs or 0)))
    RefreshAnalyzerWindow()
end

local function AnalyzerReportLastBoss()
    local db = AnalyzerDB()
    local r = db.bossFights and db.bossFights[1]
    if not r then print(L("MageHelper Analyse: Kein Bossfight gespeichert")); return end
    print(L("|cffff7d0aMageHelper letzter Bossfight|r"))
    print(FormatRunLine(r.name or "Boss", r))
end

local function AnalyzerShowDeathRecap()
    local db = AnalyzerDB()
    local recap = db.deathRecaps and db.deathRecaps[1]
    if not recap then print(L("MageHelper Analyse: Kein Death Recap gespeichert")); return end
    print("|cffff3333MageHelper Death Recap|r " .. (recap.timeText or ""))
    for i,hit in ipairs(recap.hits or {}) do
        print(string.format("%2d) %.1fs %s - %s: %s%s", i, hit.age or 0, hit.source or "?", hit.spell or L("Treffer"), tostring(hit.amount or 0), hit.overkill and hit.overkill > 0 and (" Overkill "..hit.overkill) or ""))
    end
end

local function AddIncomingHit(source, spell, amount, overkill)
    local now = GetTime()
    table.insert(analyzer.incoming, {t=now, source=source, spell=spell, amount=amount or 0, overkill=overkill or 0})
    while analyzer.incoming[1] and now - analyzer.incoming[1].t > 15 do table.remove(analyzer.incoming, 1) end
end

local function SaveDeathRecap()
    local db = AnalyzerDB()
    local now = GetTime()
    local hits = {}
    for _,h in ipairs(analyzer.incoming or {}) do
        table.insert(hits, {age=now-h.t, source=h.source, spell=h.spell, amount=h.amount, overkill=h.overkill})
    end
    local recap = { timeText = date and date("%H:%M:%S") or tostring(now), hits = hits }
    table.insert(db.deathRecaps, 1, recap)
    while #db.deathRecaps > 5 do table.remove(db.deathRecaps) end
    analyzer.lastDeath = recap
end

local function ImportantInterruptActive()
    local units = {"mouseover", "focus", "target"}
    for _,unit in ipairs(units) do
        if UnitExists(unit) and UnitCanAttack("player", unit) then
            local name, _, _, _, startMS, endMS, _, _, notInterruptible, spellId = UnitCastingInfo(unit)
            local castMatch = name and (importantInterrupts.ids[spellId or 0] or importantInterrupts.names[name])
            if name and not castMatch and importantInterrupts.partialNames then
                local lname = LowerSafe(name)
                for _, wanted in ipairs(importantInterrupts.partialNames) do
                    wanted = LowerSafe(wanted)
                    if wanted ~= "" and string.find(lname, wanted, 1, true) then castMatch = true; break end
                end
            end
            if name and not notInterruptible and castMatch then
                local remain = endMS and math.max((endMS - GetTime()*1000)/1000, 0) or 0
                return true, unit, name, spellId, remain
            end
            local cname, _, _, _, cstartMS, cendMS, _, notInterruptibleChannel, cspellId = UnitChannelInfo(unit)
            local channelMatch = cname and (importantInterrupts.ids[cspellId or 0] or importantInterrupts.names[cname])
            if cname and not channelMatch and importantInterrupts.partialNames then
                local lname = LowerSafe(cname)
                for _, wanted in ipairs(importantInterrupts.partialNames) do
                    wanted = LowerSafe(wanted)
                    if wanted ~= "" and string.find(lname, wanted, 1, true) then channelMatch = true; break end
                end
            end
            if cname and not notInterruptibleChannel and channelMatch then
                local remain = cendMS and math.max((cendMS - GetTime()*1000)/1000, 0) or 0
                return true, unit, cname, cspellId, remain
            end
        end
    end
    return false
end

local function ThreatCritical()
    if not UnitExists("target") or not UnitCanAttack("player", "target") then return false end
    local isTanking, status, scaledPercent, rawPercent = UnitDetailedThreatSituation("player", "target")
    local p = rawPercent or scaledPercent or 0
    if isTanking or (p and p >= 85) then return true, p or 100, isTanking end
    return false, p or 0, false
end

local function IsLichKingEncounter()
    -- Threat/Invisibility should only be allowed to override the rotation on Lich King.
    -- We check common visible units because private servers/clients differ in boss-frame support.
    local lkPartials = { "lichk", "lich king", "arthas" }
    local units = {"target", "focus", "mouseover", "targettarget", "focustarget"}
    for i=1,5 do table.insert(units, "boss"..i) end
    for _, unit in ipairs(units) do
        if UnitExists(unit) then
            local n = LowerSafe(UnitName(unit))
            for _, wanted in ipairs(lkPartials) do
                if n ~= "" and string.find(n, wanted, 1, true) then return true end
            end
        end
    end
    return false
end

function MageHelperAnalyzer_GetPriorityOverride()
    -- Analyzer overrides must never suppress Hot Streak by returning a harmless Fireball fallback.
    -- Only true emergency/utility actions return an override.

    -- 1. Threat/Invis: LK-only, because outside LK this was stealing Pyro/Fireball uptime.
    local invisActive = HasBuff("player", {"Unsichtbarkeit", "Invisibility"}, {[66]=true, [32612]=true})
    if invisActive then
        return { spell=spells.invis, icon=select(3, GetSpellInfo(spells.invis)), reason=L("Unsichtbarkeit aktiv - danach abbrechen"), type="invis", button="invis" }
    end

    if IsLichKingEncounter() then
        local threat, percent, tanking = ThreatCritical()
        local invisReady = SpellReady(spells.invis)
        if threat and invisReady then
            local now = GetTime()
            if now - (analyzer.lastInvisOverride or 0) > 2 then AnalyzerAdd("invisWarnings", 1); AnalyzerAdd("threatWarnings", 1); analyzer.lastInvisOverride = now end
            return { spell=spells.invis, icon=select(3, GetSpellInfo(spells.invis)), reason=string.format(L("LK: UNSICHTBARKEIT JETZT - Threat %.0f%%"), percent or 100), type="invis", button="invis" }
        elseif threat then
            -- Count it for the report, but do NOT override the rotation with Fireball.
            local now = GetTime()
            if now - (analyzer.lastInvisOverride or 0) > 2 then AnalyzerAdd("threatWarnings", 1); analyzer.lastInvisOverride = now end
            return nil
        end
    end

    -- 2. Pflichtinterrupt
    local ia, unit, castName, spellId, remain = ImportantInterruptActive()
    if ia then
        local now = GetTime()
        if now - (analyzer.lastInterruptOverride or 0) > 1 then analyzer.lastInterruptOverride = now end
        return { spell=spells.stop, icon=select(3, GetSpellInfo(spells.stop)), reason=string.format(L("GEGENZAUBER JETZT: %s"), castName or L("wichtiger Cast")), type="stop", button="stop" }
    end
    return nil
end

local function CreateAnalyzerButton(parent, text, x, y, w, fn)
    local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    b:SetWidth(w or 92); b:SetHeight(22); b:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
    b:SetText(text)
    b:SetScript("OnClick", fn)
    return b
end

local function ToggleAnalyzerMenu(anchor)
    if not analyzerMenu then
        analyzerMenu = CreateFrame("Frame", "MageHelperAnalyzerMenu", UIParent)
        analyzerMenu:SetWidth(150); analyzerMenu:SetHeight(150)
        analyzerMenu.bg = analyzerMenu:CreateTexture(nil, "BACKGROUND"); analyzerMenu.bg:SetAllPoints(analyzerMenu); analyzerMenu.bg:SetTexture(0,0,0,0.85)
        ThemePanel(analyzerMenu, 0.85)
        CreateAnalyzerButton(analyzerMenu, "Training Start", 8, -8, 132, AnalyzerStartTraining)
        CreateAnalyzerButton(analyzerMenu, "Training Stop", 8, -34, 132, AnalyzerStopTraining)
        CreateAnalyzerButton(analyzerMenu, L("Als A speichern"), 8, -60, 132, function() AnalyzerSaveSlot("A") end)
        CreateAnalyzerButton(analyzerMenu, L("Als B speichern"), 8, -86, 132, function() AnalyzerSaveSlot("B") end)
        CreateAnalyzerButton(analyzerMenu, L("A/B vergleichen"), 8, -112, 132, AnalyzerCompare)
        ApplyTheme()
        analyzerMenu:Hide()
    end
    if analyzerMenu:IsShown() then analyzerMenu:Hide() else analyzerMenu:ClearAllPoints(); analyzerMenu:SetPoint("TOPRIGHT", anchor or UIParent, "BOTTOMLEFT", -4, 0); analyzerMenu:Show() end
end

local function CreateAnalyzerWindow()
    analyzerFrame = CreateFrame("Frame", "MageHelperAnalyzerWindow", UIParent)
    analyzerFrame:SetWidth(520); analyzerFrame:SetHeight(245)
    analyzerFrame:SetPoint("CENTER", UIParent, "CENTER", 0, 20)
    analyzerFrame:SetMovable(true); analyzerFrame:EnableMouse(true)
    analyzerFrame:RegisterForDrag("LeftButton")
    analyzerFrame:SetScript("OnDragStart", function(self) self:StartMoving() end)
    analyzerFrame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    analyzerFrame.bg = analyzerFrame:CreateTexture(nil, "BACKGROUND"); analyzerFrame.bg:SetAllPoints(analyzerFrame); analyzerFrame.bg:SetTexture(0,0,0,0.78)
    ThemePanel(analyzerFrame, 0.78)
    analyzerFrame.title = analyzerFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge"); analyzerFrame.title:SetPoint("TOPLEFT", 12, -10); analyzerFrame.title:SetText(L("MageHelper Analyse")); ThemeTitle(analyzerFrame.title)
    analyzerFrame.text = analyzerFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall"); analyzerFrame.text:SetPoint("TOPLEFT", 12, -42); analyzerFrame.text:SetJustifyH("LEFT"); analyzerFrame.text:SetWidth(496); analyzerFrame.text:SetText(""); ThemeText(analyzerFrame.text)
    CreateAnalyzerButton(analyzerFrame, "Start", 12, -178, 70, AnalyzerStartTraining)
    CreateAnalyzerButton(analyzerFrame, "Stop", 88, -178, 70, AnalyzerStopTraining)
    CreateAnalyzerButton(analyzerFrame, "A", 164, -178, 42, function() AnalyzerSaveSlot("A") end)
    CreateAnalyzerButton(analyzerFrame, "B", 212, -178, 42, function() AnalyzerSaveSlot("B") end)
    CreateAnalyzerButton(analyzerFrame, L("Vergleich"), 260, -178, 82, AnalyzerCompare)
    CreateAnalyzerButton(analyzerFrame, "Boss", 348, -178, 70, AnalyzerReportLastBoss)
    CreateAnalyzerButton(analyzerFrame, L("Tod"), 424, -178, 70, AnalyzerShowDeathRecap)
    CreateAnalyzerButton(analyzerFrame, L("Schließen"), 414, -212, 82, function() analyzerFrame:Hide() end)
    analyzerFrame:Hide()
end

local function UpdateAnalyzerIcon(status)
    if not analyzerButton then return end
    local tex = select(3, GetSpellInfo(spells.fireball)) or "Interface\\Icons\\Spell_Fire_FlameBolt"
    local text = "A"
    if status == "interrupt" then tex = select(3, GetSpellInfo(spells.stop)) or tex; text = "!"
    elseif status == "invis" then tex = select(3, GetSpellInfo(spells.invis)) or tex; text = "!"
    elseif analyzer.training then text = "T"
    elseif analyzer.lastDeath then tex = "Interface\\Icons\\Ability_Creature_Cursed_02"; text = "X" end
    analyzerButton.icon:SetTexture(tex)
    if analyzerButtonText then analyzerButtonText:SetText(text) end
end

local function CreateAnalyzerMinimapButton()
    local am = CreateFrame("Button", "MageHelperAnalyzerMinimapButton", Minimap)
    analyzerButton = am
    am:SetWidth(24); am:SetHeight(24); am:SetFrameStrata("MEDIUM")
    am:SetPoint("TOPRIGHT", Minimap, "BOTTOMRIGHT", cfg.analyzerIconX or -10, cfg.analyzerIconY or -144)
    am.icon = am:CreateTexture(nil, "BACKGROUND"); am.icon:SetAllPoints(am); am.icon:SetTexture(select(3, GetSpellInfo(spells.fireball)) or "Interface\\Icons\\Spell_Fire_FlameBolt")
    am.border = am:CreateTexture(nil, "OVERLAY"); am.border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder"); am.border:SetWidth(50); am.border:SetHeight(50); am.border:SetPoint("TOPLEFT", -12, 12)
    analyzerButtonText = am:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall"); analyzerButtonText:SetPoint("CENTER", am, "CENTER", 0, 0); analyzerButtonText:SetText("A")
    am:EnableMouse(true)
    am:SetMovable(true)
    am:RegisterForDrag("LeftButton")
    am:SetScript("OnDragStart", function(self) self:StartMoving() end)
    am:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local _,_,_,x,y = self:GetPoint()
        cfg.analyzerIconX, cfg.analyzerIconY = x or -10, y or -144
    end)
    am:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    am:SetScript("OnClick", function(self, button)
        if button == "RightButton" then ToggleAnalyzerMenu(self)
        else if analyzerFrame:IsShown() then analyzerFrame:Hide() else RefreshAnalyzerWindow(); analyzerFrame:Show() end end
    end)
    am:SetScript("OnEnter", function(self) GameTooltip:SetOwner(self, "ANCHOR_LEFT"); GameTooltip:SetText(L("MageHelper Analyse")); GameTooltip:AddLine(L("Linksklick: Analysefenster"),1,1,1); GameTooltip:AddLine(L("Rechtsklick: Schnellmenü"),1,1,1); GameTooltip:Show() end)
    am:SetScript("OnLeave", function() GameTooltip:Hide() end)
end

local function UpdateButtonCooldownVisuals()
    for _, b in pairs(buttons) do
        local remain = ButtonSpellCooldownRemaining(b)
        if b.cooldown and (b.spellName or b.itemId) then
            local start, duration
            if b.itemId then start, duration = GetItemCooldown(b.itemId) else start, duration = GetSpellCooldown(b.spellName) end
            if start and duration and duration > 0 and remain > 0.05 then
                b.cooldown:SetCooldown(start, duration)
                b.cooldown:Show()
            else
                b.cooldown:Hide()
            end
        end
        if b.cdText then
            if remain and remain > 0.05 and remain < 10 then
                b.cdText:SetText(string.format("%.1f", remain))
                b.cdText:Show()
            elseif remain and remain >= 10 and remain < 999 then
                b.cdText:SetText(string.format("%.0f", remain))
                b.cdText:Show()
            else
                b.cdText:Hide()
            end
        end
    end
end

local function MarkRecommended(key, urgent)
    for k,b in pairs(buttons) do ButtonSetState(b, "normal", 0.35) end
    if key and buttons[key] then
        local usable, remain = ButtonUsableNow(buttons[key])
        if usable then
            ButtonSetState(buttons[key], urgent and "urgent" or "glow", 1)
        else
            -- Not really clickable yet: blue prep state instead of strong usable glow.
            ButtonSetState(buttons[key], "prep", 0.80)
        end
        UpdateOneButton(key, urgent)
    end
    UpdateButtonCooldownVisuals()
end


local function FormatRemain(remain)
    if not remain or remain == 999 then return "" end
    if remain >= 60 then return string.format("%dm", remain/60) end
    return string.format("%.0f", remain)
end

-- Molten Armor button colors: r, g, b, pulse. While the buff is missing the fill is always the
-- signal red and only the border shows the T9 step.
M.MOLTEN_COLORS = {
    bonus = { 0.10, 1.00, 0.10 },          -- green: buff cast with 2 T9 pieces
    ok = { 0.10, 1.00, 0.10 },             -- green: buff up, swap option off
    nobonus = { 1.00, 0.85, 0.05 },        -- yellow: buff cast without T9
    ready = { 1.00, 0.50, 0.00, true },    -- orange, pulsing: T9 on, click casts
    equip = { 0.15, 0.55, 1.00 },          -- blue: click puts T9 on
    wait = { 0.15, 0.55, 1.00, true },     -- blue, pulsing: T9 is being equipped
    missing = { 0.55, 0.55, 0.55 },        -- grey: fewer than 2 T9 pieces
    off = { 1.00, 0.05, 0.05 },            -- red: buff missing (swap option off)
}
M.MISSING_RED = { 1.00, 0.02, 0.02 }

local function UpdateBuffBar()
    if not buffBar or not buffBar:IsShown() then return end
    for _, data in ipairs(buffChecks) do
        local btn = buffButtons[data.key]
        if btn then
            local active, remain, found = HasBuff("player", data.names, data.ids)
            if data.special == "flask" then
                active, remain, found = FlaskActive()
                local key = ExpectedFlasks()[1]
                if btn.flaskKey ~= key then
                    btn.flaskKey = key
                    btn.icon:SetTexture((GetItemIcon and GetItemIcon(M.FLASKS[key].item)) or "Interface\\Icons\\INV_Misc_QuestionMark")
                end
            end
            local warnSmall = false
            local displayName = found
            if data.special == "brilliance" and not active and data.smallNames then
                local small, smallRemain, smallFound = HasBuff("player", data.smallNames, data.smallIds)
                if small then active = true; remain = smallRemain; warnSmall = true; displayName = smallFound end
            elseif data.special == "focus_out" then
                active, remain, displayName = FindMyFocusMagicOut()
            end

            local moltenColor, moltenFill
            if data.special == "molten" then
                local state, extra, buffUp = MoltenState()
                btn.text:SetText(L(M.MOLTEN_LABELS[state]))
                if state == "missing" then btn.timer:SetText(string.format("%d/2", extra or 0))
                elseif state == "bonus" or state == "nobonus" or state == "ok" then btn.timer:SetText(FormatRemain(extra))
                elseif buffUp then btn.timer:SetText("")
                else btn.timer:SetText("!") end
                moltenColor = M.MOLTEN_COLORS[state]
                moltenFill = (not buffUp) and M.MISSING_RED or nil
            else
                btn.timer:SetText(active and (warnSmall and "AI" or FormatRemain(remain)) or "!")
            end
            if moltenColor then
                local r, g, b, pulse = unpack(moltenColor)
                local a = pulse and (0.25 + 0.25 * math.abs(math.sin(GetTime() * 5))) or 0.34
                btn:SetAlpha(1)
                btn.shade:SetVertexColor(0, 0, 0, 0.15)
                if moltenFill then
                    btn.status:SetVertexColor(moltenFill[1], moltenFill[2], moltenFill[3], 0.36)
                else
                    btn.status:SetVertexColor(r, g, b, a)
                end
                btn.border:Show(); btn.border:SetVertexColor(r, g, b, pulse and (0.55 + 0.4 * math.abs(math.sin(GetTime() * 5))) or 0.95)
            elseif active and not warnSmall then
                btn:SetAlpha(1)
                btn.shade:SetVertexColor(0,0,0,0.05)
                btn.status:SetVertexColor(0.05, 0.95, 0.05, 0.28)
                if remain and remain ~= 999 and remain < 30 then
                    btn.status:SetVertexColor(1, 0.85, 0.05, 0.33)
                    btn.border:Show(); btn.border:SetVertexColor(1,0.9,0.1,0.95)
                else
                    btn.border:Show(); btn.border:SetVertexColor(0.1,1,0.1,0.95)
                end
            elseif active and warnSmall then
                btn:SetAlpha(0.95)
                btn.shade:SetVertexColor(0,0,0,0.25)
                btn.status:SetVertexColor(1, 0.75, 0.05, 0.36)
                btn.border:Show(); btn.border:SetVertexColor(1,0.75,0.05,0.95)
            else
                btn:SetAlpha(data.required and 1 or 0.45)
                btn.shade:SetVertexColor(0,0,0,0.50)
                btn.status:SetVertexColor(1, 0.02, 0.02, data.required and 0.36 or 0.18)
                btn.border:Show(); btn.border:SetVertexColor(data.required and 1 or 0.45,0.05,0.05,data.required and 0.95 or 0.35)
            end
        end
    end
end

-- Emergencies and utility shared by every rotation: analyzer override (LK Invisibility, mandatory
-- interrupts), Ice Block cancel, boss-cast and debuff Ice Block skips, ICC utility. filler = key of
-- the rotation's filler (shown with a warning when Ice Block is on cooldown), moveKey = its instant
-- for "move now". Returns nil when nothing applies.
function M.EmergencyReco(filler, moveKey, utilType, utilNote, utilReady, utilCD)
    local override = MageHelperAnalyzer_GetPriorityOverride and MageHelperAnalyzer_GetPriorityOverride()
    local iceAura = cfg.iceCancelHelper and HasIceBlockAura()
    local castSkipActive, castRemain, castName, castId, castIceReady, castIceCD, castData, castShouldBlock = ActiveIceblockCastSkip()
    local skipActive, skipRemain, skipName, skipId, iceReady, iceCD = ActiveIceblockSkip()
    if override then
        return override.button or override.type or filler, true, override.reason or "Analyzer Override"
    elseif iceAura then
        return "ice", true, L("EISBLOCK ABBRECHEN / weiter DPS")
    elseif castSkipActive and castShouldBlock and castIceReady then
        return "ice", true, string.format(L("EISBLOCK JETZT: %s %.1fs"), castName or L("Boss-Cast"), castRemain or 0)
    elseif castSkipActive and castShouldBlock and not castIceReady then
        return filler, true, string.format(L("Eisblock CD! %s in %.1fs"), castName or L("Boss-Cast"), castRemain or 0)
    elseif castSkipActive and castRemain <= ((cfg.iceBlockLead or 1.0) + 1.0) then
        if buttons.ice then ButtonSetState(buttons.ice, "prep", 0.95) end
        return filler, true, string.format(L("Eisblock gleich bereit halten: %.1fs"), castRemain or 0)
    elseif skipActive and iceReady then
        return "ice", true, string.format(L("EISBLOCK: %s"), skipName or L("Bossmechanik"))
    elseif skipActive and not iceReady then
        return filler, true, string.format(L("Eisblock CD! %s noch %.0fs"), skipName or L("Bossmechanik"), iceCD or 0)
    elseif utilType == "ice" and utilReady then
        return "ice", true, utilNote
    elseif utilType == "ice" and not utilReady then
        return filler, true, string.format(L("%s - Eisblock CD %.0fs"), utilNote or L("Eisblock nötig"), utilCD or 0)
    elseif utilType == "stop" then
        return "stop", true, utilNote
    elseif utilType == "move" then
        return moveKey, true, utilNote
    end
    return nil
end

-- =============================
-- Arcane rotation
-- =============================
-- IDs checked on Wowhead WotLK: Arcane Blast 42897 (rank 4, 7% base mana, 2.5 s) and its stacking
-- aura on the player 36032 (debuff, +15% damage and +175% Arcane Blast cost per stack, up to 4, gone
-- after 6 s or another Arcane damage spell), Arcane Missiles 42846 (rank 13), Missile Barrage 44401,
-- Arcane Barrage 44781 (rank 3), Arcane Power 12042, Presence of Mind 12043, Icy Veins 12472,
-- Evocation 12051 (15% max mana every 2 s for 8 s), Mirror Image 55342, Mana Sapphire 33312
-- (3330-3500 mana, 2 min cooldown). T10 4-piece (spell 70748): Mirror Image also gives +18% damage for 30 s.
M.AB_STACK_IDS = { [36032] = true }
M.AB_STACK_NAMES = SpellNames(36032, "Arkanschlag", "Arcane Blast")
M.MB_IDS = { [44401] = true }
M.MB_NAMES = SpellNames(44401, "Geschosssalve", "Missile Barrage")
M.SPELL_ID = { ab = 42897, ap = 12042, pom = 12043, iv = 12472, evo = 12051, mirror = 55342, abarr = 44781 }
M.MANA_GEM_ITEM = 33312
M.MANA_GEM_YIELD = 3500       -- use the gem only when at least this much mana is missing (no waste)
M.EVO_SHARE = 0.60            -- Evocation restores 4 x 15% of max mana
M.EVO_BELOW = 0.30            -- Evocation below 30% mana
M.AB_BASE_COST_FALLBACK = 229 -- 7% of a level 80 mage's base mana (3268), until the client reports it
M.AB_STACK_COST = 1.75        -- each stack adds 175% of the base cost
-- Burn drain model (used until enough burning has been measured): 3.3 Missile Barrage procs from 40%
-- of Arcane Blasts and makes the next Arcane Missiles free (2.5 s channel), which also drops the
-- stacks. Cycle: AB at 0, 1, 2, 3, 4, 4, ... stacks until a proc, then free AM. Expected 2.5 AB
-- (8.2 x base cost) in 8.75 s: about 215 mana/s, not the 730 of "every AB at 4 stacks".
M.MB_CHANCE = 0.40
M.AM_MB_TIME = 2.5
M.GCD_MAX = 1.5               -- a running cooldown this short is only the global cooldown
M.GEM_CD = 120
M.EVO_CD_DEFAULT = 240        -- Evocation cooldown without Arcane Flows; the real one is read when seen
-- Measured drain (SimC choose_rotation style): net mana lost per second while burning, without
-- Arcane Power/Heroism/Icy Veins (they would distort it), Evocation channels and single jumps of
-- DRAIN_JUMP or more (gem, potion). Replaces the model after DRAIN_MIN_TIME s of burning, reset
-- per fight (raid buffs such as Replenishment differ), and only the last DRAIN_WINDOW s count.
M.DRAIN_MIN_TIME, M.DRAIN_WINDOW, M.DRAIN_JUMP = 20, 120, 2500
M.BURN_HOLD = 15              -- an unreliable estimate keeps the last estimate decision this long
-- Always burn while one of these is up: Arcane Power, Heroism, Bloodlust, T10 4-piece "Quad Core"
-- (70747, +18% damage for 30 s after Mirror Image). Icy Veins only pauses the drain measurement.
M.FORCE_BURN_IDS = { [12042] = true, [32182] = true, [2825] = true, [70747] = true }
M.FORCE_BURN_NAMES = SpellNames(12042, "Arkane Macht", "Arcane Power", "Heldentum", "Heroism", "Kampfrausch", "Bloodlust", "Quad Core")
M.IV_IDS = { [12472] = true }
M.IV_NAMES = SpellNames(12472, "Eisige Adern", "Icy Veins")
-- Bloodmage's Regalia (mage T10): 251 = 50275-50279 and 51712-51716 (Wowhead item set 883),
-- Sanctified 264 = 51155-51159, Sanctified 277 = 51280-51284
M.T10_IDS = {}
for _, first in ipairs({ 50275, 51712, 51155, 51280 }) do for id = first, first + 4 do M.T10_IDS[id] = true end end
M.T10_SLOTS = { 1, 3, 5, 7, 10 }
-- Time to die: health fraction of the target sampled every TTD_STEP s over the last TTD_WINDOW s.
M.TTD_WINDOW, M.TTD_STEP, M.TTD_MIN_SAMPLES, M.TTD_MIN_SPAN = 12, 0.5, 6, 4
M.TTD_MIN_RATE = 0.0005       -- slower than 0.05% health per second counts as "not dropping"
M.TTD_STALL = 3               -- no health loss in the last 3 s = immune/phase: estimate unreliable
M.BURN_EVAL = 1.0             -- burn/conserve is re-decided once per second ...
M.BURN_HYST = 0.10            -- ... and in auto mode only flips with a 10% margin
M.BURN_MANA_HYST = 3          -- mana mode: conserve -> burn needs threshold + 3 percentage points
M.ROTA_SETS = {
    fire = { "lb", "pyro", "fireball", "comb", "cd", "fb_move", "ice", "invis", "stop" },
    arcane = { "ab", "am", "abarr", "ap", "pom", "mirror", "evo", "gem", "fb_move", "ice", "invis", "stop" },
}
M.ttdSamples, M.ttdGuid, M.ttdLastAt, M.ttdBoss = {}, nil, -10, false
M.burn, M.burnAt, M.burnWhy = nil, -10, ""
M.ttdBurn, M.ttdBurnAt = nil, -100 -- last decision of the estimate rule, kept while unreliable
M.drain = { t = 0, loss = 0 }
M.arcane = {}

function M.KnowsSpell(id)
    if IsSpellKnown then return IsSpellKnown(id) and true or false end
    local name = GetSpellInfo(id)
    return name ~= nil and GetSpellInfo(name) ~= nil
end

-- Arcane Power button: Icy Veins rides along in the same macro when known (both are off the GCD).
function M.ArcanePowerMacro()
    local extra = M.KnowsSpell(M.SPELL_ID.iv) and { "/cast " .. spells.iv } or nil
    return MakeMacro(spells.ap, nil, extra)
end

-- "fire" or "arcane": fixed by cfg.rotationMode, or by the talent tree with the most points
-- (Arcane -> arcane; Fire, Frost, no talents -> fire).
function M.DesiredRota()
    local mode = cfg and cfg.rotationMode or "auto"
    if mode == "fire" or mode == "arcane" then return mode end
    local group = GetActiveTalentGroup and GetActiveTalentGroup(false, false) or nil
    local best, most = 2, 0
    for tab = 1, 3 do
        local _, _, points = GetTalentTabInfo(tab, false, false, group)
        if (points or 0) > most then best, most = tab, points end
    end
    return best == 1 and "arcane" or "fire"
end

-- Show the buttons of one rotation in a row and resize the bar. Secure buttons: out of combat only.
function M.LayoutRota(rota)
    local wanted = {}
    for _, key in ipairs(M.ROTA_SETS[rota]) do wanted[key] = true end
    for key, btn in pairs(buttons) do if not wanted[key] then btn:Hide() end end
    local x = 8
    for _, key in ipairs(M.ROTA_SETS[rota]) do
        local btn = buttons[key]
        btn:ClearAllPoints()
        btn:SetPoint("TOPLEFT", KR, "TOPLEFT", x, -8)
        btn:Show()
        x = x + 53
    end
    KR:SetWidth(x + 95)
    M.activeRota = rota
    RebuildSpellMacros()
end

-- Re-evaluate the rotation (talents, setting, profile). In combat the switch waits for PLAYER_REGEN_ENABLED.
function M.ApplyRotaMode()
    local want = M.DesiredRota()
    if want == M.activeRota then M.rotaPending = false; return true end
    if InCombatLockdown() then M.rotaPending = true; return false end
    M.rotaPending = false
    M.LayoutRota(want)
    return true
end

function M.RotaName(rota) return rota == "arcane" and L("Arkan") or L("Feuer") end

function M.RotaModeText()
    local mode = cfg.rotationMode or "auto"
    if mode == "auto" then return string.format(L("Automatisch (%s)"), M.RotaName(M.DesiredRota())) end
    return M.RotaName(mode)
end

function M.ArcaneBlastStacks()
    local active, _, _, _, count = PlayerDebuffFull(M.AB_STACK_NAMES, M.AB_STACK_IDS)
    if active then return math.max(count or 0, 1) end
    -- some cores show the stacks as a buff: by ID only (the name equals the spell itself)
    for i = 1, 40 do
        local n, _, _, c, _, _, _, _, _, _, spellId = UnitBuff("player", i)
        if not n then break end
        if M.AB_STACK_IDS[spellId or 0] then return math.max(c or 0, 1) end
    end
    return 0
end

-- Worn T10 pieces, cached; UNIT_INVENTORY_CHANGED clears the cache.
function M.T10Count()
    if M.t10Count then return M.t10Count end
    local n = 0
    for _, slot in ipairs(M.T10_SLOTS) do
        if M.T10_IDS[ItemIdFromLink(GetInventoryItemLink("player", slot)) or 0] then n = n + 1 end
    end
    M.t10Count = n
    return n
end

-- Ready for the recommendation = known and off cooldown. A running cooldown no longer than the GCD
-- is only the global cooldown and counts as ready, so on-GCD spells (Mirror Image, Evocation) don't
-- flicker; the button itself still shows "not yet" until it is clickable (ButtonUsableNow).
-- "enabled == 0" (the cooldown starts when the aura fades) is not ready.
function M.KnownReady(key)
    if not M.KnowsSpell(M.SPELL_ID[key]) then return false, 999 end
    local start, duration, enabled = GetSpellCooldown(spells[key])
    if not start or enabled == 0 then return false, 999 end
    if start == 0 or duration == 0 or duration <= M.GCD_MAX then return true, 0 end
    local remain = start + duration - GetTime()
    return remain <= 0, math.max(remain, 0)
end

-- Arcane Power button: usable as soon as Arcane Power or (known) Icy Veins is (the macro casts both).
function M.ApCooldownRemaining()
    local r = SpellCooldownRemaining(spells.ap)
    if M.KnowsSpell(M.SPELL_ID.iv) then r = math.min(r, SpellCooldownRemaining(spells.iv)) end
    return r
end

-- Unit for the time-to-die estimate: an attackable boss1-4 when boss units exist (the targeted one
-- first), so adds (Deathwhisper adds, oozes, Val'kyr) don't count; the target only when there is no
-- boss unit. Boss units that exist but can't be attacked (Valithria) give no estimate.
-- Returns unit, isBoss.
function M.TtdUnit(targetOK)
    local anyBoss, first = false, nil
    for i = 1, 4 do
        local u = "boss" .. i
        if UnitExists(u) then
            anyBoss = true
            if UnitCanAttack("player", u) and not UnitIsDead(u) then
                if targetOK and UnitIsUnit("target", u) then return u, true end
                first = first or u
            end
        end
    end
    if anyBoss then return first, first ~= nil end
    return targetOK and "target" or nil, false
end

-- Sample the estimate unit's health; a new unit, a heal or a phase reset (health going up) start over.
function M.SampleTargetHealth(now, targetOK)
    local unit, isBoss = M.TtdUnit(targetOK)
    M.ttdBoss = isBoss
    M.ttdNoBoss = unit == nil and UnitExists("boss1")
    local guid = unit and UnitGUID(unit)
    if guid ~= M.ttdGuid then wipe(M.ttdSamples); M.ttdGuid = guid; M.ttdLastAt = -10; M.ttdBurn = nil end
    if not unit or now - M.ttdLastAt < M.TTD_STEP then return end
    local maxHp = UnitHealthMax(unit) or 0
    if maxHp <= 0 then return end
    local s = M.ttdSamples
    local f = (UnitHealth(unit) or 0) / maxHp
    if s[#s] and f > s[#s].f + 0.01 then wipe(s) end
    s[#s + 1] = { t = now, f = f }
    M.ttdLastAt = now
    while s[1] and now - s[1].t > M.TTD_WINDOW do table.remove(s, 1) end
end

-- Seconds until the sampled unit dies (least-squares slope of the health fraction), or nil and a
-- reason while the estimate is unreliable.
function M.TimeToDie()
    local s = M.ttdSamples
    local n = #s
    if not M.ttdGuid then return nil, M.ttdNoBoss and L("Boss nicht angreifbar") or L("kein Ziel") end
    if n < M.TTD_MIN_SAMPLES or s[n].t - s[1].t < M.TTD_MIN_SPAN then return nil, L("zu wenig Daten") end
    local mt, mf = 0, 0
    for i = 1, n do mt = mt + s[i].t; mf = mf + s[i].f end
    mt, mf = mt / n, mf / n
    local num, den = 0, 0
    for i = 1, n do num = num + (s[i].t - mt) * (s[i].f - mf); den = den + (s[i].t - mt) ^ 2 end
    local rate = den > 0 and -num / den or 0
    if rate < M.TTD_MIN_RATE then return nil, L("Ziel verliert kein Leben") end
    for i = n - 1, 1, -1 do
        if s[n].t - s[i].t >= M.TTD_STALL - 0.05 then
            if s[n].f >= s[i].f then return nil, L("Ziel verliert kein Leben") end
            break
        end
    end
    return s[n].f / rate
end

-- Modelled burn drain in mana/s (see M.MB_CHANCE): unbuffed Arcane Blast cost and cast time
-- (cached by M.ArcaneState only without Arcane Power/Heroism/Icy Veins), minus the in-combat regen
-- the client reports (GetManaRegen, if the API exists).
function M.ModelBurnDrain()
    local base = M.abBaseCost or M.AB_BASE_COST_FALLBACK
    local cast = M.abCast or 2.5
    local cost, p, casts = 0, 1, 0
    for n = 0, 40 do
        cost = cost + p * base * (1 + M.AB_STACK_COST * math.min(n, 4))
        casts = casts + p
        p = p * (1 - M.MB_CHANCE)
    end
    local regen = 0
    if GetManaRegen then local _, casting = GetManaRegen(); regen = casting or 0 end
    return cost / (casts * cast + M.AM_MB_TIME) - regen
end

-- Net burn drain in mana/s: measured once DRAIN_MIN_TIME s of burning were seen, else the model.
function M.BurnDrain()
    local d = M.drain
    if d.t >= M.DRAIN_MIN_TIME then return d.loss / d.t, true end
    return M.ModelBurnDrain(), false
end

-- Measure the net drain while burning (see M.DRAIN_MIN_TIME).
function M.TrackDrain(now, A)
    local d = M.drain
    local ok = A.inCombat and M.burn and not A.forceBurn and not A.ivUp and not A.evoChannel
    if ok and d.last and now - d.lastAt < 1 then
        local delta = d.last - A.mana
        if math.abs(delta) < M.DRAIN_JUMP then
            d.loss, d.t = d.loss + delta, d.t + (now - d.lastAt)
            if d.t > M.DRAIN_WINDOW then
                local f = M.DRAIN_WINDOW / d.t
                d.loss, d.t = d.loss * f, d.t * f
            end
        end
    end
    if ok then d.last, d.lastAt = A.mana, now else d.last = nil end
end

function M.ResetDrain() M.drain = { t = 0, loss = 0 } end

-- Mana Gem and Evocation spread over their cooldowns (mana/s), like SimC: Evocation's real cooldown
-- (GetSpellBaseCooldown where it exists, else the last full cooldown seen; Arcane Flows makes it 2 min).
function M.RestoreRates(A)
    local evoCd = M.EVO_CD_DEFAULT
    if GetSpellBaseCooldown then
        local ms = GetSpellBaseCooldown(M.SPELL_ID.evo)
        if ms and ms > 0 then evoCd = ms / 1000 end
    elseif M.evoCdSeen then
        evoCd = M.evoCdSeen
    end
    local evo = A.evoKnown and M.EVO_SHARE * A.maxMana / evoCd or 0
    local gem = GetItemCount(M.MANA_GEM_ITEM) > 0 and M.MANA_GEM_YIELD / M.GEM_CD or 0
    return gem, evo
end

-- Seconds the mana lasts at a net drain (huge when the drain is covered by regen).
function M.ManaLasts(mana, drain)
    if drain <= 0 then return 99999 end
    return mana / drain
end

-- The burn/conserve rule (owner's decision 2026-11-11). Burn when
--   a) a burst buff is up (Arcane Power, Heroism/Bloodlust, T10 Quad Core), in both modes, or
--   b) mana % >= threshold (conserve -> burn needs threshold + BURN_MANA_HYST), or
--   c) "auto" only: the estimate says the mana lasts until the boss dies. estimateBurn is that
--      decision (already with its hysteresis, kept for BURN_HOLD s while the estimate is unreliable)
--      or nil when there is none.
-- So the estimate only extends burning below the threshold, it never stops it above.
-- Returns burn, rule ("force", "mana", "ttd").
function M.ArcaneShouldBurn(mode, wasBurning, forced, manaPct, threshold, estimateBurn)
    if forced then return true, "force" end
    if manaPct >= threshold + (wasBurning and 0 or M.BURN_MANA_HYST) then return true, "mana" end
    if mode ~= "mana" and estimateBurn then return true, "ttd" end
    return false, (mode ~= "mana" and estimateBurn == false) and "ttd" or "mana"
end

-- Burn or conserve, re-decided once per second (at once when a burst buff appears).
function M.UpdateBurn(now, A)
    if M.burn ~= nil and now - M.burnAt < M.BURN_EVAL and not (A.forceBurn and not M.burn) then return end
    M.burnAt = now
    local thr = cfg.arcaneBurnMana or 35
    local mode = cfg.arcaneBurnMode == "mana" and "mana" or "auto"
    A.ttd, A.oom, A.oomNoEvo = nil, nil, nil
    local est, why
    if mode == "auto" then
        local ttd
        ttd, why = M.TimeToDie()
        if ttd then
            local drain, measured = M.BurnDrain()
            local gemRate, evoRate = M.RestoreRates(A)
            A.ttd, A.drain, A.measured = ttd, drain, measured
            A.oom = M.ManaLasts(A.mana, drain - gemRate - evoRate)
            A.oomNoEvo = M.ManaLasts(A.mana, drain - gemRate)
            local margin = M.burn and (1 - M.BURN_HYST) or (1 + M.BURN_HYST)
            M.ttdBurn, M.ttdBurnAt = A.oom >= ttd * margin, now
            est = M.ttdBurn
        elseif M.ttdBurn ~= nil and now - M.ttdBurnAt <= M.BURN_HOLD then
            est = M.ttdBurn -- unreliable (shield, phase change, immune): keep the last decision a while
        else
            M.ttdBurn = nil
        end
    end
    local rule
    M.burn, rule = M.ArcaneShouldBurn(mode, M.burn, A.forceBurn, A.manaPct, thr, est)
    local text
    if rule == "force" then text = string.format(L("Burn: %s aktiv"), A.forceName or "?")
    elseif rule == "mana" and M.burn then text = string.format(L("Burn: Mana %d%% >= Schwelle %d%%"), A.manaPct, thr)
    elseif rule == "ttd" and M.burn then text = L("Burn: Mana reicht bis zum Tod")
    elseif rule == "ttd" then text = L("Sparen: Mana reicht nicht bis zum Tod")
    else text = string.format(L("Sparen: Mana %d%% < Schwelle %d%%"), A.manaPct, thr) end
    if A.ttd then
        text = text .. " | " .. string.format(L("TTD %.0fs (%s), Mana reicht %.0fs bei %.0f Mana/s (%s)"), A.ttd,
            M.ttdBoss and "Boss" or L("Ziel"), math.min(A.oom, 9999), A.drain, A.measured and L("gemessen") or L("Modell"))
    elseif est ~= nil then
        text = text .. " | " .. string.format(L("Schätzung unsicher (%s), letzte Entscheidung gilt noch %.0fs"), why or "?", M.BURN_HOLD - (now - M.ttdBurnAt))
    elseif why then
        text = text .. " | " .. string.format(L("Schätzung unsicher (%s)"), why)
    end
    M.burnWhy = text
end

function M.ArcaneState(now, targetOK)
    local A = M.arcane
    A.stacks = M.ArcaneBlastStacks()
    A.mana, A.maxMana = UnitPower("player", 0) or 0, UnitPowerMax("player", 0) or 0
    if A.maxMana <= 0 then A.maxMana = 1 end
    A.manaPct = math.floor(A.mana / A.maxMana * 100 + 0.5)
    A.inCombat = UnitAffectingCombat("player") and true or false
    A.mb = HasBuff("player", M.MB_NAMES, M.MB_IDS)
    local forced, _, forceName = HasBuff("player", M.FORCE_BURN_NAMES, M.FORCE_BURN_IDS)
    A.forceBurn, A.forceName = forced, forceName
    A.ivUp = HasBuff("player", M.IV_NAMES, M.IV_IDS)
    local channel = UnitChannelInfo("player")
    A.evoChannel = channel ~= nil and channel == spells.evo
    -- unbuffed Arcane Blast cost (at 0 stacks) and cast time for the drain model
    if not forced and not A.ivUp then
        local _, _, _, cost, _, _, castMs = GetSpellInfo(M.SPELL_ID.ab)
        if A.stacks == 0 and cost and cost > 0 then M.abBaseCost = cost end
        if castMs and castMs > 0 then M.abCast = math.max(castMs / 1000, 1.0) end
    end
    A.apReady, A.apCD = M.KnownReady("ap")
    A.ivReady = M.KnownReady("iv")
    A.pomReady, A.pomCD = M.KnownReady("pom")
    A.mirrorReady, A.mirrorCD = M.KnownReady("mirror")
    A.evoKnown = M.KnowsSpell(M.SPELL_ID.evo)
    A.evoReady, A.evoCD = M.KnownReady("evo")
    local _, evoDur = GetSpellCooldown(spells.evo)
    if evoDur and evoDur > M.GCD_MAX then M.evoCdSeen = evoDur end
    A.gemReady = GetItemCount(M.MANA_GEM_ITEM) > 0 and M.ItemCooldownRemaining(M.MANA_GEM_ITEM) <= 0
    A.abarrKnown = M.KnowsSpell(M.SPELL_ID.abarr)
    A.abarrUsable = targetOK and A.abarrKnown and SpellUsableNow(spells.abarr)
    A.abarrCD = A.abarrKnown and SpellCooldownRemaining(spells.abarr) or 999
    A.fireblastUsable = targetOK and SpellUsableNow(spells.fireblast)
    A.targetOK = targetOK
    A.cdsAllowed = targetOK and A.inCombat
    A.t10 = M.T10Count() >= 4
    return A
end

-- Arcane priority model (after the shared emergencies in M.EmergencyReco; research: SimulationCraft 3.3.3):
-- 1) Cooldowns as soon as they are ready (in combat, with a target; no waiting for trinket procs):
--    with the T10 4-piece Mirror Image first (+18% damage for 30 s), then Presence of Mind (only
--    while burning, as in SimC), then Arcane Power (the button also casts Icy Veins if known; PoM
--    and AP share a cooldown category, so PoM goes first), Mirror Image last without T10.
--    A cooldown that only shows the GCD counts as ready (M.KnownReady), so nothing flickers.
-- 2) Mana Gem (in combat) when the missing mana >= the gem's yield.
-- 3) Moving: Arcane Barrage (known, target), then Fire Blast, then Arcane Barrage's cooldown;
--    without either no move hint (placed above the casts and channels below, which can't be used
--    while moving; it only replaces them).
-- 4) Evocation (in combat) below 30% mana without Arcane Blast stacks (with stacks: Arcane
--    Barrage/Missiles first to drop them). Skipped only while a reliable estimate of a boss unit
--    (never an add or a plain target) says the mana lasts to the kill without it.
-- 5) Arcane Missiles when Missile Barrage is up.
-- 6) Burn (M.ArcaneShouldBurn): Arcane Blast, also at 4 stacks. Conserve: Arcane Blast up to 3
--    stacks, then Arcane Missiles.
function M.ArcaneReco(A, moving)
    local missing = A.maxMana - A.mana
    local evoNeeded = not (A.ttd and M.ttdBoss and A.oomNoEvo and A.oomNoEvo >= A.ttd)
    if A.cdsAllowed and A.t10 and A.mirrorReady then
        return "mirror", true, string.format(L("%s zuerst (T10: +18%% Schaden)"), spells.mirror)
    elseif A.cdsAllowed and M.burn and A.pomReady then
        return "pom", true, string.format(L("%s bereit"), spells.pom)
    elseif A.cdsAllowed and A.apReady then
        return "ap", true, string.format(L("%s bereit"), spells.ap)
    elseif A.cdsAllowed and A.ivReady then
        return "ap", true, string.format(L("%s bereit"), spells.iv)
    elseif A.cdsAllowed and A.mirrorReady then
        return "mirror", true, string.format(L("%s bereit"), spells.mirror)
    elseif A.inCombat and A.gemReady and missing >= M.MANA_GEM_YIELD then
        return "gem", true, string.format(L("Manastein: %d Mana fehlen"), missing)
    elseif moving and A.abarrUsable then
        return "abarr", false, string.format(L("Bewegung: %s"), spells.abarr)
    elseif moving and cfg.showMovementFireBlast and A.fireblastUsable then
        return "fb_move", false, string.format(L("Bewegung: %s"), spells.fireblast)
    elseif moving and A.targetOK and A.abarrKnown and A.abarrCD < 999 then
        return "abarr", false, string.format(L("Bewegung: %s CD %.1fs"), spells.abarr, A.abarrCD)
    elseif A.inCombat and A.evoReady and A.manaPct < M.EVO_BELOW * 100 and evoNeeded then
        if A.stacks == 0 then return "evo", true, string.format(L("%s: Mana %d%%"), spells.evo, A.manaPct) end
        return A.abarrUsable and "abarr" or "am", false, string.format(L("Stapel abbauen, dann %s"), spells.evo)
    elseif A.mb then
        return "am", true, string.format(L("%s aktiv: %s"), spells.mb, spells.am)
    elseif M.burn then
        return "ab", false, string.format(L("Burn: %s"), spells.ab)
    elseif A.stacks < 3 then
        return "ab", false, string.format(L("Sparen: %s bis 3 Stapel"), spells.ab)
    end
    return "am", false, string.format(L("Sparen: 3 Stapel, dann %s"), spells.am)
end

function M.ArcaneCdHint(label, ready, cd)
    if ready then return "  |cff33ff33" .. label .. "|r" end
    if cd and cd < 999 then return "  " .. label .. " " .. FormatRemain(cd) end
    return ""
end

function M.UpdateArcane(now, targetOK, moving, utilType, utilNote, utilReady, utilCD)
    local A = M.ArcaneState(now, targetOK)
    M.SampleTargetHealth(now, targetOK)
    M.UpdateBurn(now, A)
    M.TrackDrain(now, A)
    local reco, urgent, note = M.EmergencyReco("ab", A.abarrKnown and "abarr" or "fb_move", utilType, utilNote, utilReady, utilCD)
    if not reco then reco, urgent, note = M.ArcaneReco(A, moving) end

    MarkRecommended(reco, urgent)
    NoteRecommendation(reco, note)
    if reco == "stop" then UpdateAnalyzerIcon("interrupt") elseif reco == "invis" then UpdateAnalyzerIcon("invis") else UpdateAnalyzerIcon(nil) end
    RefreshAnalyzerWindow()
    if utilType == "warn" and buttons.stop then ButtonSetState(buttons.stop, "prep", 0.80) end

    local stackColor = A.stacks >= 4 and "|cffff8020" or (A.stacks >= 3 and "|cffffff33" or "|cffcccccc")
    local manaColor = A.manaPct >= 60 and "|cff33ff33" or (A.manaPct >= 30 and "|cffffff33" or "|cffff3333")
    local burnText = M.burn and "|cffff5050BURN|r" or ("|cff66ccff" .. L("SPAREN") .. "|r")
    local mbText = A.mb and "  |cffff40ffMB!|r" or ""
    local cds = M.ArcaneCdHint("AP", A.apReady, A.apCD) .. M.ArcaneCdHint("PoM", A.pomReady, A.pomCD)
        .. M.ArcaneCdHint("MI", A.mirrorReady, A.mirrorCD) .. M.ArcaneCdHint("Evo", A.evoReady, A.evoCD)
    local gapText = gapActive and " |cffff3333CAST-GAP!|r" or ""
    KR.info:SetText(string.format("AB: %s%d/4|r  Mana: %s%d%%|r  %s%s%s  %s%s", stackColor, A.stacks, manaColor, A.manaPct, burnText, mbText, cds, note or "", gapText))
    if KR.debugInfo then
        if cfg.debugMode then
            KR.debugInfo:SetText(string.format("DBG reco=%s reason=%s | %s | Util=%s", tostring(reco), tostring(note), M.burnWhy or "", tostring(utilType or "-")))
        else
            KR.debugInfo:SetText("")
        end
    end
end

local function UpdateDisplay()
    UpdateBuffBar()
    UpdateButtonCooldownVisuals()
    if not KR:IsShown() then return end
    local now = GetTime()
    local targetOK = UnitExists("target") and not UnitIsDead("target") and UnitCanAttack("player", "target")
    local moving = PlayerMoving()
    lastPlayerMoving = moving

    local lbRemain = targetOK and DebuffRemaining("target", spells.lb, true) or 0
    local hot, hotRemain, hotName, hotId = HasHotStreak()
    local combReady, combCD = SpellReady(spells.combustion)
    local lbUsable, lbCD = SpellUsableNow(spells.lb), SpellCooldownRemaining(spells.lb)
    local fireblastUsable, fireblastCD = SpellUsableNow(spells.fireblast), SpellCooldownRemaining(spells.fireblast)
    local procActive, procRemain, procName = HasAnyProc()
    local burstReady, burstCD = BurstCDReady()
    local burstQueued = BurstQueueActive()
    local fbpm = UpdateFireballCount()
    local utilType, utilUrgent, utilNote, utilReady, utilCD = ActiveIccUtility()
    local ladyShield = LadyShieldActive()

    if UnitAffectingCombat("player") then
        if hot and not lastHotState then fightStats.hotSeen = (fightStats.hotSeen or 0) + 1; AnalyzerAdd("hotProcs", 1) end
        lastHotState = hot and true or false
    end

    local reco, urgent, note = "fireball", false, L("Feuerball-Kette halten")

    -- Cast gap warning: after a completed cast, >0.5 sec without current cast/channel.
    local casting = UnitCastingInfo("player") or UnitChannelInfo("player")
    gapActive = false
    if UnitAffectingCombat("player") and lastCastEnd > 0 and not casting and (now - lastCastEnd) > 0.5 then
        gapActive = true
        if now - (fightStats.lastGapAt or 0) > 1.0 then
            fightStats.castGaps = (fightStats.castGaps or 0) + 1
            fightStats.lastGapAt = now
        end
    end
    if gapActive then KR.gap:Show() else KR.gap:Hide() end

    if M.activeRota == "arcane" then
        M.UpdateArcane(now, targetOK, moving, utilType, utilNote, utilReady, utilCD)
        return
    end

    -- Priority model v1.8:
    -- 0) Boss utility skip with Ice Block overrides DPS rotation when configured debuffs are on you.
    -- 1) Hot Streak/Pyro chain is always above LB refresh. If LB has exploded and Hot Streak is active, Pyro first, then LB.
    -- 2) LB only refreshes when missing and no Hot Streak is active; never clip before explosion.
    -- 3) Combustion starts a short Burst Queue. After Combustion, keep Mirror/Potion/Gloves
    --    in focus before returning to Fireball spam, so burst pieces do not fall out of sight.
    -- 4) Movement mode only replaces Fireball filler, not Pyro/LB emergencies.
    -- 5) v1.9: LB and Fire Blast are only shown as clickable when their cooldown/GCD is really ready.
    -- Emergencies (analyzer override, Ice Block cancel/skips, ICC utility) are shared with Arcane: M.EmergencyReco.
    local eReco, eUrgent, eNote = M.EmergencyReco("fireball", "fb_move", utilType, utilNote, utilReady, utilCD)
    if eReco then
        reco, urgent, note = eReco, eUrgent, eNote
    elseif hot then
        reco, urgent, note = "pyro", true, (targetOK and lbRemain <= 0) and L("Pyro zuerst, danach LB neu setzen") or L("Pyro-Kette: Hot Streak sofort nutzen")
    elseif targetOK and lbRemain <= 0 and lbUsable then
        reco, urgent, note = "lb", true, L("LB neu setzen - Explosion ist durch")
    elseif targetOK and lbRemain <= 0 and not lbUsable then
        reco, urgent, note = "fireball", false, string.format(L("LB wartet auf CD/GCD: %.1fs"), lbCD or 0)
        if buttons.lb then ButtonSetState(buttons.lb, "prep", 0.75) end
    elseif targetOK and lbRemain > 0 and lbRemain < 1.0 then
        reco, urgent, note = "fireball", false, L("LB Explosion abwarten - NICHT clippen")
        if buttons.lb then ButtonSetState(buttons.lb, "prep", 0.65) end
    elseif burstQueued and burstReady then
        reco, urgent, note = "cd", true, burstQueueReason or L("Burst nachziehen")
    elseif ladyShield then
        reco, urgent, note = "fireball", false, L("Lady Schild aktiv: großen Burst halten")
    elseif combReady and targetOK and lbRemain >= (cfg.combustionLB or 10) and not moving then
        reco, urgent, note = "comb", procActive or burstReady, (procActive or burstReady) and L("Combustion starten, danach Burst-CDs") or L("Combustion-Fenster bereit")
    elseif (not combReady) and combCD <= 5 and targetOK and lbRemain > 0 and lbRemain < (cfg.combustionLB or 10) then
        reco, urgent, note = "fireball", false, L("Comb bald: LB auslaufen lassen, danach neu setzen")
        if buttons.lb then ButtonSetState(buttons.lb, "prep", 0.75) end
    elseif moving and cfg.showMovementFireBlast and fireblastUsable then
        reco, urgent, note = "fb_move", false, L("Bewegung: nur Notfall-Feuerschlag")
    elseif moving and cfg.showMovementFireBlast and not fireblastUsable then
        reco, urgent, note = "fireball", false, string.format(L("Bewegung: Feuerschlag CD %.1fs"), fireblastCD or 0)
        if buttons.fb_move then ButtonSetState(buttons.fb_move, "prep", 0.55) end
    else
        reco, urgent, note = "fireball", false, L("Feuerball spammen")
    end

    MarkRecommended(reco, urgent)
    NoteRecommendation(reco, note)
    if reco == "stop" then UpdateAnalyzerIcon("interrupt") elseif reco == "invis" then UpdateAnalyzerIcon("invis") else UpdateAnalyzerIcon(nil) end
    RefreshAnalyzerWindow()
    if (note == L("Comb bald: LB auslaufen lassen, danach neu setzen") or note == L("LB Explosion abwarten - NICHT clippen")) and buttons.lb then ButtonSetState(buttons.lb, "prep", 0.75) end
    if utilType == "warn" and buttons.stop then ButtonSetState(buttons.stop, "prep", 0.80) end
    if utilType == "burst" and buttons.cd and reco ~= "cd" then ButtonSetState(buttons.cd, "glow", 0.95) end

    -- CDs glow in parallel when useful/ready, but never downgrade the button if it is the actual queued recommendation.
    if buttons.cd and reco ~= "cd" then
        if burstQueued and burstReady then
            ButtonSetState(buttons.cd, "urgent", 1.00)
        elseif burstReady and (utilType == "burst" or procActive or (combReady and lbRemain >= (cfg.combustionLB or 10))) then
            ButtonSetState(buttons.cd, "glow", 0.95)
        else
            ButtonSetState(buttons.cd, "normal", 0.45)
        end
    end

    local lbColor = "|cffff3333"
    if lbRemain >= 10 then lbColor = "|cff33ff33" elseif lbRemain >= 3 then lbColor = "|cffffff33" elseif lbRemain > 0 then lbColor = "|cffff3333" end
    local fbColor = "|cffff3333"
    if fbpm >= 23 then fbColor = "|cff33ff33" elseif fbpm >= 20 then fbColor = "|cffffff33" end
    local procText = procActive and (" Proc: " .. procName) or ""
    local gapText = gapActive and " |cffff3333CAST-GAP!|r" or ""

    local hotText = hot and ("  |cffff2020HOT STREAK:" .. (hotName or "?") .. "|r") or L("  |cff777777kein HS|r")
    local queueText = burstQueued and "  |cffffaa00BURST QUEUE|r" or ""
    local cdText = ""
    if lbCD and lbCD > 0.05 and lbCD < 999 then cdText = cdText .. string.format("  LBcd: %.1fs", lbCD) end
    if fireblastCD and fireblastCD > 0.05 and fireblastCD < 999 then cdText = cdText .. string.format(L("  FS cd: %.1fs"), fireblastCD) end
    KR.info:SetText(string.format("LB: %s%.1fs|r  FB/min: %s%d|r  CombCD: %.0fs  %s%s", lbColor, lbRemain or 0, fbColor, fbpm, combCD or 0, note or "", gapText) .. cdText .. procText .. hotText .. queueText)
    if KR.debugInfo then
        if cfg.debugMode then
            KR.debugInfo:SetText(string.format("DBG reco=%s reason=%s | HS=%s %.1fs id=%s | Proc=%s | Util=%s | Queue=%s", tostring(reco), tostring(note), hot and L("JA") or L("NEIN"), hotRemain or 0, tostring(hotId or "-"), tostring(procName or "-"), tostring(utilType or "-"), burstQueued and L("JA") or L("NEIN")))
        else
            KR.debugInfo:SetText("")
        end
    end
end


function KR:PLAYER_REGEN_DISABLED()
    inCombatStart = GetTime()
    wipe(fireballTimes)
    lastCastEnd = 0
    M.ResetDrain() -- Arcane: measure the burn drain per fight (raid buffs differ)
    ResetFightStats()
    analyzer.current = NewRun("boss", UnitName("target") or L("Bossfight"))
end

function KR:PLAYER_REGEN_ENABLED()
    RefreshOneButtonAfterCombat()
    if M.rotaPending then M.ApplyRotaMode() end
    RebuildSpellMacros() -- Icy Veins learned/unlearned in combat: Arcane Power macro
    if chr.moltenRestorePending then RestoreAfterMolten() end
    if fmPendingAfterCombat then
        RefreshFocusMagicButton()
        RefreshFocusMagicLabel()
        RefreshFMPicker()
    end
    if cfg.reportOnFightEnd then PrintFightReport(false) end
    if analyzer.current then SaveBossRun(analyzer.current); analyzer.current = nil; RefreshAnalyzerWindow() end
end

function KR:COMBAT_LOG_EVENT_UNFILTERED(...)
    local timestamp, event, hideCaster, sourceGUID, sourceName, sourceFlags, sourceRaidFlags, destGUID, destName, destFlags, destRaidFlags = ...
    local playerGUID = UnitGUID("player")

    -- Analyzer damage / incoming / death recap ringbuffer
    if event == "SPELL_DAMAGE" or event == "RANGE_DAMAGE" then
        local sid, sname, school, amount, overkill = select(12, ...)
        if sourceGUID == playerGUID then AnalyzerAdd("damageDone", amount or 0) end
        if destGUID == playerGUID then AnalyzerAdd("damageTaken", amount or 0); AnalyzerAdd("incomingDamage", amount or 0); AddIncomingHit(sourceName, sname, amount, overkill) end
    elseif event == "SPELL_PERIODIC_DAMAGE" then
        local sid, sname, school, amount, overkill = select(12, ...)
        if sourceGUID == playerGUID then AnalyzerAdd("damageDone", amount or 0); if sname == spells.lb then AnalyzerAdd("lbTicks", 1) end end
        if destGUID == playerGUID then AnalyzerAdd("damageTaken", amount or 0); AnalyzerAdd("incomingDamage", amount or 0); AddIncomingHit(sourceName, sname, amount, overkill) end
    elseif event == "SWING_DAMAGE" then
        local amount, overkill = select(12, ...)
        if sourceGUID == playerGUID then AnalyzerAdd("damageDone", amount or 0) end
        if destGUID == playerGUID then AnalyzerAdd("damageTaken", amount or 0); AnalyzerAdd("incomingDamage", amount or 0); AddIncomingHit(sourceName, L("Nahkampf"), amount, overkill) end
    elseif event == "SPELL_INTERRUPT" then
        if sourceGUID == playerGUID then AnalyzerAdd("interrupts", 1) end
    elseif event == "SPELL_HEAL" or event == "SPELL_PERIODIC_HEAL" then
        -- intentionally ignored for DPS comparison
    end

    local spellId, spellName = select(12, ...)
    if sourceGUID ~= playerGUID then return end
    if event == "SPELL_CAST_SUCCESS" then
        if spellName == spells.fireball then
            table.insert(fireballTimes, GetTime())
            fightStats.fireballs = (fightStats.fireballs or 0) + 1
            UpdateFireballCount()
        elseif spellName == spells.pyro then
            fightStats.pyros = (fightStats.pyros or 0) + 1
            AnalyzerAdd("pyroCasts", 1)
        elseif spellName == spells.lb then
            fightStats.lbs = (fightStats.lbs or 0) + 1
            AnalyzerAdd("lbApplications", 1)
        elseif spellName == spells.stop then
            AnalyzerAdd("counterspellUses", 1)
        elseif spellName == spells.invis then
            -- use counted via warnings; cast success still useful for later review
        elseif spellName == spells.combustion then
            fightStats.combs = (fightStats.combs or 0) + 1
        elseif spellName == spells.mirror then
            fightStats.mirrors = (fightStats.mirrors or 0) + 1
        elseif spellName == spells.iceblock then
            fightStats.iceblocks = (fightStats.iceblocks or 0) + 1
        end
    end
end

function KR:UNIT_SPELLCAST_SUCCEEDED(unit, spell)
    if unit ~= "player" then return end
    lastCastEnd = GetTime()
    lastCastName = spell
    if spell == spells.combustion then
        StartBurstQueue(L("Spiegelbilder/Burst-CDs vor Feuerball"))
    elseif spell == spells.mirror then
        ClearBurstQueue()
    elseif spell == spells.molten then
        -- the bonus is decided by what is worn when the cast lands; then swap back
        chr.moltenBonus = EquippedT9() >= 2
        M.lastMoltenCast = GetTime()
        M.moltenStateCache = nil
        RestoreAfterMolten()
    end
end

function KR:INSPECT_TALENT_READY() OnFMInspectReady() end
function KR:UNIT_INVENTORY_CHANGED(unit) if unit == "player" then M.t10Count = nil end end -- T10 count cache
-- Talents or spec changed: auto rotation mode may switch (out of combat), Icy Veins may be new.
function KR:PLAYER_TALENT_UPDATE() M.ApplyRotaMode(); RebuildSpellMacros() end
KR.ACTIVE_TALENT_GROUP_CHANGED = KR.PLAYER_TALENT_UPDATE
KR.CHARACTER_POINTS_CHANGED = KR.PLAYER_TALENT_UPDATE
function KR:UNIT_SPELLCAST_INTERRUPTED(unit) if unit == "player" then lastCastEnd = GetTime() end end
function KR:UNIT_SPELLCAST_FAILED(unit) if unit == "player" then lastCastEnd = GetTime() end end
function KR:PLAYER_DEAD()
    AnalyzerAdd("deaths", 1)
    SaveDeathRecap()
    UpdateAnalyzerIcon(nil)
    RefreshAnalyzerWindow()
end

-- /mh and /magehelper, registered through AceConsole in MH:OnInitialize.
local function HandleSlash(msg)
    msg = msg or ""
    local cmd, arg = msg:match("^(%S*)%s*(.-)$")
    cmd = string.lower(cmd or "")
    if cmd == "show" then cfg.shown = true; KR:Show()
    elseif cmd == "hide" then cfg.shown = false; KR:Hide()
    elseif cmd == "lock" then cfg.locked = true; print(L("MageHelper: Bar gesperrt"))
    elseif cmd == "unlock" then cfg.locked = false; print(L("MageHelper: Bar verschiebbar"))
    elseif cmd == "buffs" then
        if arg == "show" or arg == "on" then cfg.buffBarShown = true; if buffBar then buffBar:Show() end
        elseif arg == "hide" or arg == "off" then cfg.buffBarShown = false; if buffBar then buffBar:Hide() end
        elseif arg == "lock" then cfg.buffBarLocked = true; print(L("MageHelper: Buff-Bar gesperrt"))
        elseif arg == "unlock" then cfg.buffBarLocked = false; print(L("MageHelper: Buff-Bar verschiebbar"))
        else print("MageHelper: /mh buffs show|hide|lock|unlock") end
    elseif cmd == "comb" then
        local n = tonumber(arg)
        if n then cfg.combustionLB = n; print(string.format(L("MageHelper: Combustion-LB-Fenster = %ss"), n)) end
    elseif cmd == "skips" then
        if arg == "off" or arg == "aus" then
            cfg.bossSkips = false
            print(L("MageHelper: Boss-Iceblock-Skips AUS"))
        else
            cfg.bossSkips = true
            print(L("MageHelper: Boss-Iceblock-Skips AN"))
        end
    elseif cmd == "utility" then
        if arg == "off" or arg == "aus" then
            cfg.iccUtility = false
            print(L("MageHelper: ICC-Utility-Warnungen AUS"))
        else
            cfg.iccUtility = true
            print(L("MageHelper: ICC-Utility-Warnungen AN"))
        end
    elseif cmd == "icelead" then
        local n = tonumber(arg)
        if n then
            cfg.iceBlockLead = n
            print(string.format(L("MageHelper: Eisblock-Vorlauf = %ss"), n))
        else
            print("MageHelper: /mh icelead 1")
        end
    elseif cmd == "icecancel" then
        if arg == "off" or arg == "aus" then
            cfg.iceCancelHelper = false
            print(L("MageHelper: Eisblock-Abbruch-Hinweis AUS"))
        else
            cfg.iceCancelHelper = true
            print(L("MageHelper: Eisblock-Abbruch-Hinweis AN"))
        end
    elseif cmd == "buffet" then
        local n = tonumber(arg)
        if n then cfg.buffetStacks = n; print(string.format(L("MageHelper: Mystic-Buffet-Eisblock ab %s Stacks"), n)) end
    elseif cmd == "instability" then
        local n = tonumber(arg)
        if n then cfg.instabilityStacks = n; print(string.format(L("MageHelper: Instabilität-STOP ab %s Stacks"), n)) end
    elseif cmd == "debug" then
        local sub = string.lower(arg or "")
        if sub == "on" or sub == "an" then
            cfg.debugMode = true
            print(L("MageHelper: Debug-Anzeige AN"))
        elseif sub == "off" or sub == "aus" then
            cfg.debugMode = false
            if KR.debugInfo then KR.debugInfo:SetText("") end
            print(L("MageHelper: Debug-Anzeige AUS"))
        else
            local h, r, n, id = HasHotStreak()
            print(L("MageHelper Debug: Hot Streak erkannt="), h and L("JA") or L("NEIN"), " Name=", n or "-", " SpellID=", id or "-")
            print(L("MageHelper Debug: /mh debug on für Live-Anzeige, /mh report für Fight-Report"))
            for i=1,40 do
                local bn, _, _, _, _, _, _, _, _, _, bid = UnitBuff("player", i)
                if not bn then break end
                print(i .. ": " .. bn .. " (" .. tostring(bid) .. ")")
            end
        end
    elseif cmd == "analyze" or cmd == "analyse" then
        local sub = string.lower(arg or "")
        if sub == "show" or sub == "open" or sub == "" then RefreshAnalyzerWindow(); analyzerFrame:Show()
        elseif sub == "hide" or sub == "close" then analyzerFrame:Hide()
        elseif sub == "start" then AnalyzerStartTraining()
        elseif sub == "stop" then AnalyzerStopTraining()
        elseif sub == "a" then AnalyzerSaveSlot("A")
        elseif sub == "b" then AnalyzerSaveSlot("B")
        elseif sub == "compare" or sub == "vergleich" then AnalyzerCompare()
        elseif sub == "boss" then AnalyzerReportLastBoss()
        elseif sub == "death" or sub == "tod" then AnalyzerShowDeathRecap()
        else print("MageHelper Analyse: show|start|stop|a|b|compare|boss|death") end
    elseif cmd == "report" then
        PrintFightReport(true)
    elseif cmd == "autoreport" then
        if arg == "off" or arg == "aus" then cfg.reportOnFightEnd = false; print(L("MageHelper: Fight-Report nach Kampf AUS"))
        else cfg.reportOnFightEnd = true; print(L("MageHelper: Fight-Report nach Kampf AN")) end
    elseif cmd == "gloves" then
        cfg.useGloves = (arg ~= "off")
        RebuildSpellMacros()
        print(cfg.useGloves and L("MageHelper: /use 10 aktiv") or L("MageHelper: /use 10 aus"))
    elseif cmd == "fm" then
        local sub = string.lower(arg or "")
        if sub == "" or sub == "list" or sub == "liste" then
            ToggleFMPicker()
        elseif sub == "set" then
            if UnitExists("target") and UnitIsFriend("player", "target") and UnitIsPlayer("target") then
                SetFocusMagicTarget(UnitName("target"), true)
            else
                print(L("MageHelper: Bitte freundliches Ziel anwählen und /mh fm set nutzen"))
            end
        elseif sub == "back" then
            BackToPartner()
        elseif sub == "clear" then
            SetFocusMagicTarget("", true)
        else
            SetFocusMagicTarget(arg, true)
        end
    elseif cmd == "t9" or cmd == "molten" then
        local count = EquippedT9()
        local links = {}
        for _, link in pairs(BagT9()) do table.insert(links, link) end
        print(string.format(L("MageHelper T9: %d Teile angelegt, in den Taschen: %s"), count, #links > 0 and table.concat(links, " ") or L("keine")))
        local state, extra = MoltenState()
        print(string.format(L(M.MOLTEN_TIPS[state]), extra or 0))
    elseif cmd == "flask" then
        local key = M.FLASK_ALIASES[string.lower(arg or "")]
        if key then SetFlaskChoice(key) end
        print(string.format(L("MageHelper: Flask = %s"), FlaskChoiceText()))
        if not key then print(L("/mh flask auto|frost|rage|stone|mojo|resi|any - welche Flask die Buff-Leiste erwartet")) end
    elseif cmd == "theme" or cmd == "farbe" or cmd == "farbschema" then
        local aliases = { standard = "standard", pink = "pink", rosa = "pink", blue = "blue", blau = "blue", red = "red", rot = "red" }
        local key = aliases[string.lower(arg or "")]
        if key then
            cfg.theme = key
            ApplyTheme()
            print(string.format(L("MageHelper: Farbschema = %s"), L(M.THEME_NAMES[key])))
        else
            print(L("/mh theme standard|rosa|blau|rot - Farbschema der Leisten und Fenster"))
        end
    elseif cmd == "config" or cmd == "options" or cmd == "optionen" then
        MH:OpenOptions()
    elseif cmd == "rota" or cmd == "rotation" then
        local aliases = { auto = "auto", fire = "fire", feuer = "fire", arcane = "arcane", arkan = "arcane" }
        local mode = aliases[string.lower(arg or "")]
        if mode then
            cfg.rotationMode = mode
            if not M.ApplyRotaMode() then print(L("MageHelper: Im Kampf - die Buttons wechseln nach dem Kampf.")) end
        end
        print(string.format(L("MageHelper: Rota = %s"), M.RotaModeText()))
        if not mode then print(L("/mh rota auto|feuer|arkan - Feuer- oder Arkan-Rota (auto = nach Talenten)")) end
    elseif cmd == "burn" then
        local sub, pct = string.match(string.lower(arg or ""), "^(%a*)%s*(%d*)")
        if sub == "auto" or sub == "mana" then cfg.arcaneBurnMode = sub end
        pct = tonumber(pct)
        if pct then cfg.arcaneBurnMana = math.max(10, math.min(90, pct)) end
        M.burn = nil -- decide again with the new setting
        print(string.format(L("MageHelper: Burn-Modus = %s, Mana-Schwelle %d%%"), cfg.arcaneBurnMode == "mana" and L("Nur nach Mana") or L("Automatisch (Zeit bis zum Tod gegen Mana)"), cfg.arcaneBurnMana))
        if sub ~= "auto" and sub ~= "mana" and not pct then print(L("/mh burn auto|mana [Prozent] - Arkan: Burn/Sparen automatisch oder nur nach Mana")) end
    elseif cmd == "lang" or cmd == "sprache" then
        local sub = string.lower(arg or "")
        if sub == "de" or sub == "en" or sub == "auto" then
            cfg.language = sub
            ApplyLanguageSetting()
            print(string.format(L("MageHelper: Sprache = %s (Buttons und Fenster nach /reload)"), sub))
        else
            print(L("/mh lang auto|de|en - Sprache (auto = Client-Sprache)"))
        end
    elseif cmd == "help" or cmd == "" then
        print(L("MageHelper Befehle:"))
        print(L("/mh config - Einstellungsfenster öffnen (auch unter Interface > AddOns)"))
        print(L("/mh show|hide - Bar an/aus"))
        print(L("/mh lock|unlock - Bar sperren/verschieben"))
        print(L("/mh comb 10 - benötigte LB-Restzeit für Einäschern"))
        print(L("/mh gloves on|off - /use 10 in Spellbuttons"))
        print(L("/mh buffs show|hide|lock|unlock - zweite Buff-Bar"))
        print(L("/mh fm - MF-Ziel-Auswahl öffnen"))
        print(L("/mh fm set|NAME - Ziel bzw. NAME als MF-Partner speichern"))
        print(L("/mh fm back|clear - zurück zum Partner / alles löschen"))
        print(L("/mh skips on|off - Eisblock-Bossmechaniken an/aus"))
        print(L("/mh icelead 1 - Eisblock bei Boss-Casts 1 Sekunde vor Einschlag anzeigen"))
        print(L("/mh icecancel on|off - Nach Eisblock Abbruch-Hinweis anzeigen"))
        print(L("/mh utility on|off - ICC-Utility: Sindra/Putri/BQ/Lady an/aus"))
        print(L("/mh buffet 5 - Mystic Buffet Eisblock ab X Stacks"))
        print(L("/mh instability 5 - Stopcasting ab X Instabilität-Stapeln"))
        print(L("/mh debug on|off - Live-Debug: warum empfiehlt das Addon etwas"))
        print(L("/mh debug - Hot-Streak/Buffnamen einmal ausgeben"))
        print(L("v1.8: Hot Streak/Pyro hat Vorrang vor LB-Refresh, auch wenn LB gerade explodiert ist."))
        print(L("/mh analyse - Analysefenster öffnen (oder A-Icon unter der Minimap)"))
        print(L("/mh analyse start|stop|a|b|compare|boss|death - Analyzer-Funktionen"))
        print(L("/mh report - letzten/aktuellen Fight-Report ausgeben"))
        print(L("/mh autoreport on|off - Report nach Kampf an/aus"))
        print(L("/mh t9 - T9-Teile und Status für Glühende Rüstung anzeigen"))
        print(L("/mh lang auto|de|en - Sprache (auto = Client-Sprache)"))
        print(L("/mh theme standard|rosa|blau|rot - Farbschema der Leisten und Fenster"))
        print(L("/mh flask auto|frost|rage|stone|mojo|resi|any - welche Flask die Buff-Leiste erwartet"))
        print(L("/mh rota auto|feuer|arkan - Feuer- oder Arkan-Rota (auto = nach Talenten)"))
        print(L("/mh burn auto|mana [Prozent] - Arkan: Burn/Sparen automatisch oder nur nach Mana"))
    end
end

-- =============================
-- Ace3: startup, settings (AceDB profiles), options window
-- =============================

-- Settings from MageHelper <= 2.3 were one flat per-character table. The update renamed it to
-- MageHelperLegacyDB in each character's SavedVariables file; a flat MageHelperDB (rename missed)
-- is recognised too. Copied once into this character's profile / char data, then dropped.
local function TakeLegacySettings()
    local legacy = MageHelperLegacyDB
    if type(MageHelperDB) == "table" and MageHelperDB.profiles == nil and MageHelperDB.profileKeys == nil and MageHelperDB.shown ~= nil then
        legacy = legacy or MageHelperDB
        MageHelperDB = nil
    end
    MageHelperLegacyDB = nil
    return legacy
end

local function ApplyLegacySettings(db, legacy)
    if type(legacy) ~= "table" then return end
    -- Before the partner existed, the saved FM target was the buddy: keep it as partner.
    if legacy.focusMagicPartner == nil and (legacy.focusMagicTarget or "") ~= "" then
        legacy.focusMagicPartner = legacy.focusMagicTarget
    end
    for k, v in pairs(legacy) do
        if CHAR_KEYS[k] then db.char[k] = v
        elseif defaults.profile[k] ~= nil then db.profile[k] = v end
    end
end

local optionsFrame

local function SetupOptions(db)
    local function get(info) return cfg[info[#info]] end
    local function set(info, value) cfg[info[#info]] = value end
    local function toggle(name, order, setter) return { type = "toggle", name = name, order = order, width = "full", set = setter } end
    local function range(name, order, min, max, step) return { type = "range", name = name, order = order, min = min, max = max, step = step, width = "double" } end
    local function inCombat()
        if InCombatLockdown() then print(L("MageHelper: Einstellungen sind im Kampf gesperrt.")); return true end
    end

    local options = {
        type = "group", name = "MageHelper",
        args = {
            general = { type = "group", name = L("Allgemein"), order = 1, get = get, set = set, args = {
                shown = toggle(L("Rota-Leiste anzeigen"), 1, function(_, v) cfg.shown = v; if v then KR:Show() else KR:Hide() end end),
                locked = toggle(L("Rota-Leiste sperren"), 2),
                buffBarShown = toggle(L("Buff-Leiste anzeigen"), 3, function(_, v)
                    cfg.buffBarShown = v
                    if buffBar then if v then buffBar:Show() else buffBar:Hide() end end
                end),
                buffBarLocked = toggle(L("Buff-Leiste sperren"), 4),
                language = { type = "select", name = L("Sprache"), desc = L("Buttons und Fenster wechseln nach /reload."), order = 5,
                    values = { auto = L("Automatisch (Client-Sprache)"), de = "Deutsch", en = "English" },
                    set = function(_, v) cfg.language = v; ApplyLanguageSetting() end },
                theme = { type = "select", name = L("Farbschema"), order = 6,
                    desc = L("Signalfarben (grün, rot, orange, blau) bleiben in jedem Schema gleich."),
                    values = function()
                        local v = {}
                        for _, key in ipairs(M.THEME_ORDER) do v[key] = L(M.THEME_NAMES[key]) end
                        return v
                    end,
                    set = function(_, v) cfg.theme = v; ApplyTheme() end },
                flask = { type = "select", name = L("Flask für die Buff-Leiste"), order = 7,
                    desc = L("Automatisch: beste Flask für Klasse und Skillung, Steinblut für Todesritter in Frostpräsenz und Druiden in Bärengestalt. Gilt pro Charakter."),
                    values = function()
                        local v = { auto = string.format(L("Automatisch (%s)"), FlaskName(AutoFlask())), any = L("Jede Flask zählt") }
                        for _, key in ipairs(M.FLASK_ORDER) do v[key] = FlaskName(key) end
                        return v
                    end,
                    get = function() return (chr.flask == "any" or M.FLASKS[chr.flask]) and chr.flask or "auto" end,
                    set = function(_, v) SetFlaskChoice(v) end },
            } },
            rotation = { type = "group", name = L("Rotation"), order = 2, get = get, set = set, args = {
                rotationMode = { type = "select", name = L("Rota-Modus"), order = 0,
                    desc = L("Automatisch: der Talentbaum mit den meisten Punkten entscheidet (Arkan oder Feuer, Frost nutzt Feuer). Die Buttons wechseln nur außerhalb des Kampfes."),
                    values = function()
                        return { auto = string.format(L("Automatisch (%s)"), M.RotaName(M.DesiredRota())), fire = L("Feuer"), arcane = L("Arkan") }
                    end,
                    set = function(_, v)
                        cfg.rotationMode = v
                        if not M.ApplyRotaMode() then print(L("MageHelper: Im Kampf - die Buttons wechseln nach dem Kampf.")) end
                    end },
                combustionLB = range(L("LB-Restzeit für Einäschern (Sekunden)"), 1, 0, 12, 1),
                showMovementFireBlast = toggle(L("Feuerschlag in Bewegung vorschlagen"), 2),
                useGloves = toggle(L("Handschuhe (/use 10) in den Spell-Buttons"), 3, function(_, v)
                    if inCombat() then return end
                    cfg.useGloves = v; RebuildSpellMacros()
                end),
            } },
            arcane = { type = "group", name = L("Arkan"), order = 2.5, get = get, set = function(info, v) cfg[info[#info]] = v; M.burn = nil end, args = {
                help = { type = "description", order = 1, fontSize = "medium",
                    name = L("Burn: Arkanschlag auch mit 4 Stapeln. Sparen: Arkanschlag bis 3 Stapel, dann Arkane Geschosse. Während Arkane Macht, Heldentum/Kampfrausch oder dem T10-Spiegelbild-Buff wird immer geburnt.\n\nAutomatisch: Burn, solange dein Mana über der Schwelle liegt, und darunter weiter, wenn die Schätzung (Lebensverlust des Bosses gegen deinen gemessenen Manaverbrauch) sagt, dass dein Mana bis zu seinem Tod reicht. Nur nach Mana: nur die Schwelle.") },
                arcaneBurnMode = { type = "select", name = L("Burn oder Sparen"), order = 2,
                    values = { auto = L("Automatisch (Zeit bis zum Tod gegen Mana)"), mana = L("Nur nach Mana") } },
                arcaneBurnMana = range(L("Burn ab Mana (%)"), 3, 10, 90, 1),
            } },
            bosses = { type = "group", name = L("Boss-Mechaniken"), order = 3, get = get, set = set, args = {
                bossSkips = toggle(L("Eisblock bei Boss-Mechaniken (Stechende Seuche, Kochendes Blut, Schwärmende Schatten)"), 1),
                iceBlockLead = range(L("Eisblock-Vorlauf vor Boss-Casts (Sekunden)"), 2, 0, 3, 0.1),
                iceCancelHelper = toggle(L("Nach Eisblock Abbruch-Hinweis zeigen"), 3),
                iccUtility = toggle(L("ICC-Hinweise (Sindragosa, Putricide, Blutkönigin, Lady)"), 4),
                buffetStacks = range(L("Mystic Buffet: Eisblock ab Stapeln"), 5, 1, 20, 1),
                instabilityStacks = range(L("Instabilität: Stopcasting ab Stapeln"), 6, 1, 20, 1),
            } },
            focusMagic = { type = "group", name = L("Fokusmagie"), order = 4, args = {
                status = { type = "description", order = 1, fontSize = "medium", name = function()
                    local t, p = chr.focusMagicTarget or "", chr.focusMagicPartner or ""
                    return string.format(L("Ziel: %s   Partner: %s"), t ~= "" and t or "-", p ~= "" and p or "-")
                end },
                open = { type = "execute", name = L("MF-Ziel auswählen"), order = 2, func = function() ToggleFMPicker() end },
                back = { type = "execute", name = L("Zurück zum Partner"), order = 3, func = function() BackToPartner() end },
                partner = { type = "input", name = L("MF-Partner (Name)"), order = 4,
                    get = function() return chr.focusMagicPartner end,
                    set = function(_, v) SetFocusMagicTarget(strtrim(v or ""), true) end },
            } },
            molten = { type = "group", name = L("Glühende Rüstung"), order = 5, args = {
                moltenT9 = { type = "toggle", order = 1, width = "full",
                    name = L("Mit T9-Set-Bonus wirken (T9 anziehen, danach automatisch zurückwechseln)"),
                    get = function() return cfg.moltenT9 end,
                    set = function(_, v) cfg.moltenT9 = v; M.moltenStateCache = nil end },
                status = { type = "description", order = 2, fontSize = "medium", name = function()
                    local state, extra = MoltenState()
                    return string.format(L(M.MOLTEN_TIPS[state]), extra or 0)
                end },
            } },
            analyzer = { type = "group", name = L("Analyse"), order = 6, get = get, set = set, args = {
                reportOnFightEnd = toggle(L("Fight-Report nach jedem Kampf im Chat"), 1),
                debugMode = toggle(L("Debug-Zeile unter der Rota-Leiste"), 2, function(_, v)
                    cfg.debugMode = v
                    if not v and KR.debugInfo then KR.debugInfo:SetText("") end
                end),
                open = { type = "execute", name = L("Analysefenster öffnen"), order = 3,
                    func = function() RefreshAnalyzerWindow(); analyzerFrame:Show() end },
            } },
            profiles = LibStub("AceDBOptions-3.0"):GetOptionsTable(db),
        },
    }
    options.args.profiles.order = 10
    LibStub("AceConfig-3.0"):RegisterOptionsTable(ADDON, options)
    optionsFrame = LibStub("AceConfigDialog-3.0"):AddToBlizOptions(ADDON, "MageHelper")
end

function MH:OpenOptions()
    -- 3.3.5 needs the second call when the Interface Options panel was never opened before.
    InterfaceOptionsFrame_OpenToCategory(optionsFrame)
    InterfaceOptionsFrame_OpenToCategory(optionsFrame)
end

-- Called after the profile was switched, copied or reset: move and show/hide the frames.
function MH:ApplyProfile()
    cfg = self.db.profile
    ApplyLanguageSetting()
    KR:ClearAllPoints()
    KR:SetPoint("CENTER", UIParent, "CENTER", cfg.x, cfg.y)
    if cfg.shown then KR:Show() else KR:Hide() end
    if buffBar then
        buffBar:ClearAllPoints()
        buffBar:SetPoint("CENTER", UIParent, "CENTER", cfg.buffBarX, cfg.buffBarY)
        if cfg.buffBarShown then buffBar:Show() else buffBar:Hide() end
    end
    if analyzerButton then
        analyzerButton:ClearAllPoints()
        analyzerButton:SetPoint("TOPRIGHT", Minimap, "BOTTOMRIGHT", cfg.analyzerIconX or -10, cfg.analyzerIconY or -144)
    end
    if not cfg.debugMode and KR.debugInfo then KR.debugInfo:SetText("") end
    M.burn = nil
    M.ApplyRotaMode()
    RebuildSpellMacros()
    ApplyTheme()
end

function MH:OnInitialize()
    local legacy = TakeLegacySettings()
    -- No default profile name: every character starts with its own profile ("Name - Realm");
    -- profiles can be shared or copied in the options window.
    self.db = LibStub("AceDB-3.0"):New("MageHelperDB", defaults)
    ApplyLegacySettings(self.db, legacy)
    cfg, chr = self.db.profile, self.db.char
    ApplyLanguageSetting()
    -- leftovers of the old leg-name swap (v3.0) and of the first T9 version (v3.1)
    chr.moltenStep, chr.moltenT9Legs, chr.moltenMainLegs, chr.moltenCastAt = nil, nil, nil, nil
    self.db.RegisterCallback(self, "OnProfileChanged", "ApplyProfile")
    self.db.RegisterCallback(self, "OnProfileCopied", "ApplyProfile")
    self.db.RegisterCallback(self, "OnProfileReset", "ApplyProfile")
    SetupOptions(self.db)
    self:RegisterChatCommand("mh", HandleSlash)
    self:RegisterChatCommand("magehelper", HandleSlash)
end

local EVENTS = { "PLAYER_REGEN_DISABLED", "PLAYER_REGEN_ENABLED", "COMBAT_LOG_EVENT_UNFILTERED", "PLAYER_DEAD", "UNIT_SPELLCAST_SUCCEEDED", "UNIT_SPELLCAST_INTERRUPTED", "UNIT_SPELLCAST_FAILED", "INSPECT_TALENT_READY",
    "PLAYER_TALENT_UPDATE", "UNIT_INVENTORY_CHANGED", "ACTIVE_TALENT_GROUP_CHANGED", "CHARACTER_POINTS_CHANGED" }

function MH:OnEnable()
    CreateUI()
    CreateAnalyzerWindow()
    CreateAnalyzerMinimapButton()
    ApplyTheme()
    for _, event in ipairs(EVENTS) do
        self:RegisterEvent(event, function(e, ...) KR[e](KR, ...) end)
    end
    -- After a fresh login the equipment may not be readable yet: tidy the T9 swap a bit later.
    self:ScheduleTimer(function()
        CleanSwap(chr.moltenRestorePending)
        M.ApplyRotaMode() -- talents may not have been readable at login
        if chr.moltenRestorePending then RestoreAfterMolten() end -- cast in combat before a reload
    end, 5)
    KR:SetScript("OnUpdate", PulseRecommendationButtons) -- glow pulse every frame
    self:ScheduleRepeatingTimer(UpdateDisplay, 0.1)        -- recommendation + buff bar 10x per second
    print(string.format(L("|cffff7d0aMageHelper v%s|r geladen. /mh help"), GetAddOnMetadata(ADDON, "Version") or "?"))
end










