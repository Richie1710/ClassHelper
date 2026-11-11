# Smoke test: loads MageHelper (TOC order, incl. embedded Ace3) in Lua 5.1 against tools/wowstub.lua,
# once as deDE and once as enUS client, and runs scenarios with check() assertions.
# Usage (from the addon folder, with lupa installed):
#   python -I tools/smoke.py [-v]
import os, re, sys
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STUB = open(os.path.join(HERE, "wowstub.lua"), encoding="utf-8").read()


def toc_files():
    """Files in load order: TOC entries, XML <Script>/<Include> expanded recursively."""
    version, files = "?", []
    def add(rel, base):
        p = os.path.normpath(os.path.join(base, rel.replace("\\", "/")))
        if p.lower().endswith(".xml"):
            xml = open(p, encoding="utf-8").read()
            xml = re.sub(r"<!--.*?-->", "", xml, flags=re.S)
            for m in re.finditer(r'<(Script|Include)\s+file="([^"]+)"', xml):
                add(m.group(2), os.path.dirname(p))
        else:
            files.append(p)
    for line in open(os.path.join(ROOT, "MageHelper.toc"), encoding="utf-8"):
        line = line.strip()
        if line.startswith("## Version:"): version = line.split(":", 1)[1].strip()
        elif line and not line.startswith("#"): add(line, ROOT)
    return version, files


# Old (<= 2.3) flat per-character settings, as the update leaves them in the character's file.
LEGACY = r'''
return { shown = true, combustionLB = 7, x = 50, y = -100, focusMagicTarget = "Anya",
         moltenT9Legs = "Meine T9", moltenMainLegs = "Meine T10", moltenStep = 2, iceBlockLead = 1.5,
         analyzer = { bossFights = { { name = "Lord Mark'gar", duration = 100 } }, deathRecaps = {} } }
'''

COMMON = r'''
MH = LibStub("AceAddon-3.0"):GetAddon("MageHelper")
function check(cond, msg) if not cond then error("CHECK FAILED: " .. msg, 2) end end
function Slash(cmd) SlashCmdList.ACECONSOLE_MH(cmd) end
'''

# Legacy settings were taken over (variant: MageHelperLegacyDB for deDE, flat MageHelperDB for enUS).
MIGRATION = r'''
local p, c = MH.db.profile, MH.db.char
check(MageHelperLegacyDB == nil, "legacy table dropped")
check(MageHelperDB.profiles ~= nil, "MageHelperDB is an AceDB database")
check(p.combustionLB == 7 and p.x == 50 and p.iceBlockLead == 1.5, "profile settings taken over")
check(c.focusMagicTarget == "Anya" and c.focusMagicPartner == "Anya", "FM target taken over and used as partner")
check(c.moltenT9Legs == nil and c.moltenStep == nil and p.moltenT9Legs == nil, "old leg-name settings are dropped")
check(type(c.moltenSwap) == "table" and p.moltenT9 == true, "T9 swap defaults")
check(c.analyzer.bossFights[1].name == "Lord Mark'gar", "analyzer data per character")
check(MH.db:GetCurrentProfile() == "Kahuchan - Rising-Gods", "own profile per character: " .. MH.db:GetCurrentProfile())
OUT[#OUT + 1] = "MIGRATION OK"
'''

SCRIPT = r'''
local function upd(n) for i = 1, (n or 3) do Tick(0.15) end end
upd()
INCOMBAT = true
FireEvent("PLAYER_REGEN_DISABLED"); upd()
AURAS.player = { {"Hot Streak", 0, nil, 48108} }; upd()
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SPELL_CAST_SUCCESS", nil, "GUID-player", "Kahuchan", 0, 0, "GUID-target", "Dummy", 0, 0, 42833, GetSpellInfo(42833), 4)
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SPELL_DAMAGE", nil, "GUID-target", "Dummy", 0, 0, "GUID-player", "Kahuchan", 0, 0, 1, "Hit", 1, 500, 0)
FireEvent("COMBAT_LOG_EVENT_UNFILTERED", 0, "SWING_DAMAGE", nil, "GUID-target", "Dummy", 0, 0, "GUID-player", "Kahuchan", 0, 0, 300, 0)
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", GetSpellInfo(11129)); AURAS.player = {}; upd()
AURAS.player = { {GetSpellInfo(66), 0, nil, 32612} }; upd(); AURAS.player = {}
upd(200)
INCOMBAT = false
FireEvent("PLAYER_REGEN_ENABLED")
FireEvent("PLAYER_DEAD")
for _, cmd in ipairs({"", "help", "lock", "unlock", "buffs lock", "comb 9", "skips off", "skips on", "utility off", "icelead 1.5", "icecancel off", "buffet 4", "instability 6", "debug", "debug on", "debug off", "analyse start", "analyse stop", "analyse a", "analyse b", "analyse compare", "analyse boss", "analyse death", "report", "autoreport off", "gloves off", "gloves on", "fm Partner", "fm clear", "fm", "molten", "molten reset", "lang", "analyse", "config"}) do
  Slash(cmd)
end
check(OPTIONS_OPENED ~= nil, "/mh config opens the options panel")
for _, n in ipairs({"MageHelperOneButton", "MageHelperMinimapButton", "MageHelperBuffMinimapButton", "MageHelperAnalyzerMinimapButton", "MageHelperBuff_FMSet", "MageHelperBuff_armor", "MageHelperBuff_brilliance", "MageHelperBuff_fmin", "MageHelperBuff_fmout", "MageHelperBuff_flask", "MageHelperBuff_wild"}) do
  local f = FRAMES[n]; if f and f.__scripts.OnEnter then f.__scripts.OnEnter(f) end
end
FRAMES.MageHelperOneButton.__scripts.OnClick(FRAMES.MageHelperOneButton)
FRAMES.MageHelperAnalyzerMinimapButton.__scripts.OnClick(FRAMES.MageHelperAnalyzerMinimapButton, "RightButton")
upd()
check(MH.db.profile.combustionLB == 9, "slash commands write into the profile")
'''

# Options window (AceConfig validates the table) and profile switching.
OPTIONS = r'''
-- With a uiType, AceConfigRegistry validates the table and errors on a malformed option.
local o = LibStub("AceConfigRegistry-3.0"):GetOptionsTable("MageHelper", "dialog", "MyLib-1.0")
check(type(o) == "table", "options table registered and valid")
local KR = MageHelperFrame
o.args.rotation.set({ "rotation", "combustionLB" }, 8)
check(MH.db.profile.combustionLB == 8, "range option writes profile")
o.args.general.args.shown.set({ "general", "shown" }, false)
check(not KR.__shown and MH.db.profile.shown == false, "hide bar via options")
o.args.general.args.shown.set({ "general", "shown" }, true)
check(KR.__shown, "show bar via options")
o.args.rotation.args.useGloves.set({ "rotation", "useGloves" }, false)
check(not FRAMES.MageHelperButton_fireball.__attr.macrotext:find("/use 10", 1, true), "gloves off rebuilds macros")
o.args.rotation.args.useGloves.set({ "rotation", "useGloves" }, true)
check(FRAMES.MageHelperButton_fireball.__attr.macrotext:find("/use 10", 1, true), "gloves on rebuilds macros")
o.args.focusMagic.args.partner.set({ "focusMagic", "partner" }, " Anya ")
check(MH.db.char.focusMagicPartner == "Anya", "FM partner via options")
check(type(o.args.focusMagic.args.status.name()) == "string", "FM status text")
check(o.args.profiles ~= nil, "profiles page")

local own = MH.db:GetCurrentProfile()
MH.db:SetProfile("Raid")
check(MH.db.profile.combustionLB == 10, "new profile starts with defaults")
Slash("comb 4")
check(MH.db.profile.combustionLB == 4 and MH.db.profiles[own].combustionLB == 8, "addon follows the active profile")
MH.db:SetProfile(own)
check(MH.db.profile.combustionLB == 8, "back to own profile")
MH.db:CopyProfile("Raid")
check(MH.db.profile.combustionLB == 4, "copy profile")
check(MH.db.char.focusMagicPartner == "Anya", "character data unaffected by profiles")
OUT[#OUT + 1] = "OPTIONS OK"
'''

# Focus Magic picker: raid of 8, inspect, filters, target/partner/back, change in combat.
PICKER = r'''
RAID = {
  { name = "Kahuchan", class = "MAGE" },
  { name = "Anya", class = "MAGE" },
  { name = "Bheal", class = "PRIEST", talents = { 5, 51, 15 } },     -- holy
  { name = "Cshadow", class = "PRIEST", talents = { 13, 0, 58 } },   -- shadow
  { name = "Dresto", class = "DRUID", talents = { 0, 15, 56 } },     -- resto, already has FM from Anya
  { name = "Ehpala", class = "PALADIN", talents = { 51, 5, 15 }, range = false }, -- holy but out of range
  { name = "Fwar", class = "WARRIOR" },
  { name = "Gsham", class = "SHAMAN", talents = { 0, 0, 57 }, online = false },
}
AURAS.raid5 = { { "Focus Magic", 0, nil, 54646, "raid2" } }
INCOMBAT = false
if FRAMES.MageHelperFMPicker then FRAMES.MageHelperFMPicker:Hide() end -- the main scenario may have opened it
Slash("fm")
local P = FRAMES.MageHelperFMPicker
check(P and P.__shown, "picker opens with /mh fm")
for i = 1, 40 do
  Tick(0.4)
  if INSPECT_PENDING then INSPECT_PENDING = false; FireEvent("INSPECT_TALENT_READY") end
end
local function rows()
  local t = {}
  for _, r in ipairs(P.rows) do if r.__shown then t[#t + 1] = r.name.__text .. " [" .. r.info.__text .. "]" end end
  return t
end
local function dump(label) OUT[#OUT + 1] = "ROWS " .. label .. ": " .. table.concat(rows(), " | ") end
local function shownNames() local t = {}; for _, r in ipairs(P.rows) do if r.__shown then t[#t + 1] = r.name.__text end end; return table.concat(t, ",") end
dump("all")
check(shownNames() == "Anya,Bheal,Cshadow,Dresto,Ehpala,Fwar,Gsham", "all members except me, alphabetical: " .. shownNames())
-- healing classes that are online and in range: Bheal, Cshadow, Dresto
check(INSPECT_COUNT == 3, "inspected healing classes in range, got " .. INSPECT_COUNT)

local function setFilter(name, on)
  local cb = FRAMES[name]; cb:SetChecked(on); cb.__scripts.OnClick(cb)
end
setFilter("MageHelperFMFilterHealers", true); dump("healers")
-- Bheal healer; Ehpala/Gsham unknown (shown as Healer?); Cshadow is shadow; Dresto already has FM
check(shownNames() == "Bheal,Ehpala,Gsham", "healers without FM: " .. shownNames())
setFilter("MageHelperFMFilterHealers", false); setFilter("MageHelperFMFilterMages", true); dump("mages")
check(shownNames() == "Anya", "only mages: " .. shownNames())
setFilter("MageHelperFMFilterMages", false)

local C = MH.db.char
local function rowFor(name) for _, r in ipairs(P.rows) do if r.__shown and r.entryName == name then return r end end end
local function fmMacro() return FRAMES.MageHelperBuff_fmout.__attr.macrotext end
rowFor("Anya").partnerButton.__scripts.OnClick()
check(C.focusMagicPartner == "Anya" and fmMacro():find("/targetexact Anya", 1, true), "partner Anya set and used by FM OUT")
rowFor("Bheal").targetButton.__scripts.OnClick()
check(C.focusMagicTarget == "Bheal" and C.focusMagicPartner == "Anya", "temporary target keeps partner")
check(fmMacro():find("/targetexact Bheal", 1, true), "FM OUT now targets Bheal")
OUT[#OUT + 1] = "LABEL " .. FRAMES.MageHelperBuffBar.fmTargetText.__text
OUT[#OUT + 1] = "STATUS " .. P.status.__text
P.backButton.__scripts.OnClick()
check(C.focusMagicTarget == "Anya" and fmMacro():find("/targetexact Anya", 1, true), "back to partner")

-- in combat: secure button keeps the old target until combat ends
INCOMBAT = true
rowFor("Bheal").targetButton.__scripts.OnClick()
check(fmMacro():find("/targetexact Anya", 1, true), "macro unchanged in combat")
OUT[#OUT + 1] = "STATUS-COMBAT " .. P.status.__text
INCOMBAT = false
FireEvent("PLAYER_REGEN_ENABLED")
check(fmMacro():find("/targetexact Bheal", 1, true), "macro applied after combat")
OUT[#OUT + 1] = "PICKER OK"
'''

# Molten Armor with the T9 2-piece bonus: equip from bags by ID, cast, swap back, colors.
T9 = r'''
local B = FRAMES.MageHelperBuff_armor
local de = GetLocale() == "deDE"
local L_T9_ON, L_T9_CAST, L_ARMOR = de and "T9 an" or "T9 on", de and "Casten" or "Cast", de and "Rüstung" or "Armor"
local MOLTEN = GetSpellInfo(43046)
local T10 = { [1] = "|cffa335ee|Hitem:51281:0:0:0:0:0:0:0|h[T10 Head]|h|r", [3] = "|Hitem:51284|h[T10 Shoulders]|h",
              [5] = "|Hitem:51283|h[T10 Robe]|h", [7] = "|Hitem:51282:3719:0:0:0|h[T10 Legs heroic]|h", [10] = "|Hitem:51280|h[T10 Gloves]|h" }
local function reset()
  INCOMBAT = false; AURAS.player = {}; CASTS = {}
  EQUIPPED = {}; for s, l in pairs(T10) do EQUIPPED[s] = l end
  BAGS = { [0] = { "|Hitem:47760|h[Khadgar's Leggings of Triumph]|h", "|Hitem:12345|h[Junk]|h", "|Hitem:47753|h[Khadgar's Gauntlets of Triumph]|h" } }
  wipe(MH.db.char.moltenSwap); MH.db.char.moltenBonus = nil
  Tick(0.6)
end
-- a secure click: PreClick, the action the attributes describe, PostClick
local function click()
  if B.__scripts.PreClick then B.__scripts.PreClick(B, "LeftButton") end
  if B.__attr.type == "spell" then CASTS[#CASTS + 1] = B.__attr.spell end
  if B.__scripts.PostClick then B.__scripts.PostClick(B, "LeftButton") end
  Tick(0.6)
end
local function state() return B.text.__text .. " " .. B.timer.__text end
local function itemAt(slot) return tonumber((EQUIPPED[slot] or ""):match("item:(%d+)")) end

reset()
check(B.text.__text == L_T9_ON, "blue state before the swap: " .. state())
OUT[#OUT + 1] = "T9 start: " .. state()
click()
check(#CASTS == 0, "click 1 does not cast")
check(itemAt(7) == 47760 and itemAt(10) == 47753 and itemAt(1) == 51281, "click 1 equips T9 legs + hands only")
check(B.text.__text == L_T9_CAST and B.__attr.type == "spell", "orange state, cast action restored: " .. state())
OUT[#OUT + 1] = "T9 after click 1: " .. state()
click()
check(#CASTS == 1 and CASTS[1] == MOLTEN, "click 2 casts Molten Armor")
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)
check(EQUIPPED[7] == T10[7] and EQUIPPED[10] == T10[10], "exact original items back (heroic legs with enchant)")
check(next(MH.db.char.moltenSwap) == nil and MH.db.char.moltenBonus == true, "swap cleared, bonus remembered")
AURAS.player = { { MOLTEN, 0, GetTime() + 1800, 43046 } }; Tick(0.6)
check(B.text.__text == L_ARMOR, "green state with bonus: " .. state())
OUT[#OUT + 1] = "T9 with bonus: " .. state()

-- buff without bonus: cast while wearing no T9
reset(); MH.db.profile.moltenT9 = false; click()
check(#CASTS == 1 and itemAt(7) == 51282, "option off: casts without swapping")
FireEvent("UNIT_SPELLCAST_SUCCEEDED", "player", MOLTEN)
check(MH.db.char.moltenBonus == false, "cast without T9 is remembered as no bonus")
MH.db.profile.moltenT9 = true

-- in combat the button only casts
reset(); INCOMBAT = true; click()
check(#CASTS == 1 and itemAt(7) == 51282, "in combat: cast only, no swap")
INCOMBAT = false

-- fewer than 2 T9: grey, click casts without bonus
reset(); BAGS = { [0] = { "|Hitem:47760|h[Khadgar's Leggings of Triumph]|h" } }; Tick(0.6)
check(B.timer.__text == "1/2", "missing state shows 1/2: " .. state())
click()
check(#CASTS == 1, "not enough T9: plain cast")

-- one T9 piece already worn: only one more is swapped in
reset(); EQUIPPED[1] = "|Hitem:47761|h[Khadgar's Hood of Triumph]|h"; click()
check(#CASTS == 0 and itemAt(7) == 47760 and itemAt(10) == 51280, "only the missing second piece is equipped")
check(MH.db.char.moltenSwap[1] == nil and MH.db.char.moltenSwap[7] == T10[7], "worn T9 is not part of the swap")
Slash("t9")
OUT[#OUT + 1] = "T9 OK"
'''

GERMAN = re.compile(r"[äöüßÄÖÜ]|\b(Klick|Linksklick|Rechtsklick|gesetzt|gespeichert|Befehle|Ziel|Hose|Eisblock|Feuerball|Kampf|Lauf|keine?|nach|anzeigen|AUS|AN)\b")

version, files = toc_files()
failed = False
for loc in ("deDE", "enUS"):
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    g.LOCALE, g.ADDON_VERSION = loc, version
    lua.execute(STUB)
    # SavedVariables as the client provides them before ADDON_LOADED
    legacy = lua.execute(LEGACY)
    if loc == "deDE": g.MageHelperLegacyDB = legacy
    else: g.MageHelperDB = legacy  # variant: per-character file was not renamed
    for f in files:
        g.LoadAddonFile(open(f, encoding="utf-8-sig").read(), os.path.relpath(f, ROOT), "MageHelper")
    g.FireEvent("ADDON_LOADED", "MageHelper")
    g.LOGGEDIN = True
    g.FireEvent("PLAYER_LOGIN")
    g.FireEvent("PLAYER_ENTERING_WORLD")
    try:
        for name, part in (("migration", MIGRATION), ("main", SCRIPT), ("options", OPTIONS), ("picker", PICKER), ("t9", T9)):
            lua.execute(COMMON + part)
    except Exception as e:
        failed = True
        print(f"!!!!! {loc} scenario '{name}' failed: {e}")
    out = list(g.OUT.values())
    for l in out:
        if l.startswith(("ROWS", "LABEL", "STATUS", "PICKER", "MIGRATION", "OPTIONS", "T9", "|cffff7d0aMageHelper v")): print("  " + l)
    errors = list(g.ERRORS.values())
    for e in errors: print("  LUA ERROR:", e)
    failed = failed or bool(errors)
    print(f"===== {loc}: {len(files)} files, {len(out)} output lines, {len(errors)} Lua errors, unknown globals: {sorted(g.MISSING.keys())}")
    if loc == "enUS":
        bad = [l for l in out if GERMAN.search(l)]
        print("  German-looking lines in English output:", len(bad))
        for l in bad: print("    ", l)
    if "-v" in sys.argv:
        frames = g.FRAMES
        for k in sorted(k for k in frames.keys() if isinstance(k, str)):
            mt = frames[k]["__attr"]["macrotext"]
            if mt: print("  MACRO", k, "->", mt.replace("\n", " | "))
        for l in out: print("   ", l)
sys.exit(1 if failed else 0)
