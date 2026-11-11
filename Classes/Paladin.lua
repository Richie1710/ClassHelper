-- ClassHelper: Paladin base module (WotLK 3.3.5a).
-- Rotation mode by talent tree (1 Holy = buff bar only, 2 Protection, 3 Retribution), the secure
-- button sets, the Paladin buff bar, the judgement option and the optional, read-only PallyPower
-- integration. The rotations themselves live in PaladinProt.lua (M.PalProtReco) and
-- PaladinRet.lua (M.PalRetReco); this file calls them every 0.1 s with a state snapshot.
--
-- Spell IDs: max ranks for casts, rank 1 IDs where PallyPower uses them; names always come from
-- GetSpellInfo(id) (client language), so a /cast by name picks the highest known rank. All IDs below
-- were checked on Wowhead WotLK (2026-11-11), the flask IDs too.
local M = select(2, ...).M
if not M then return end
local L, E = M.L, M.L_EN
-- Option names/descriptions are functions: built at file load (before the language setting is read),
-- they follow /ch lang at display time (AceConfig r960 accepts functions for name and desc).
function M.LF(s) return function() return L(s) end end
local LF = M.LF

local P = { ICON_SPELL = 20375, BUFF_ICON_SPELL = 20217 } -- minimap icons: Seal of Command, Blessing of Kings
M.CLASS_MODULES.PALADIN = P
M.Pal = P

-- -----------------------------------------------------------------------------------------------
-- Constants
-- -----------------------------------------------------------------------------------------------
M.PAL_ID = {
    rf = 25780,        -- Righteous Fury (single rank)
    hs = 48952,        -- Holy Shield rank 6
    plea = 54428,      -- Divine Plea
    hotr = 53595,      -- Hammer of the Righteous
    cons = 48819,      -- Consecration rank 8
    sor = 61411,       -- Shield of Righteousness rank 2
    how = 48806,       -- Hammer of Wrath rank 6
    avs = 48827,       -- Avenger's Shield rank 5
    jow = 53408,       -- Judgement of Wisdom
    jol = 20271,       -- Judgement of Light
    hor = 62124,       -- Hand of Reckoning (taunt, 30 yd)
    rd = 31789,        -- Righteous Defense (friendly target: taunts up to 3 mobs off it)
    dprot = 498,       -- Divine Protection
    dshield = 642,     -- Divine Shield
    loh = 48788,       -- Lay on Hands rank 5
    forbearance = 25771,
    ardent = 66233,    -- Ardent Defender lockout aura (AD procced), info only
    aw = 31884,        -- Avenging Wrath
    cs = 35395,        -- Crusader Strike
    dstorm = 53385,    -- Divine Storm
    exo = 48801,       -- Exorcism rank 9
    hwrath = 48817,    -- Holy Wrath rank 5
    aow = 59578,       -- The Art of War buff (rank 2; rank 1 = 53489)
    sealCommand = 20375,
}
M.PAL_AOW_IDS = { [59578] = true, [53489] = true }
-- Seals in PallyPower's order (PallyPower.Seals; opt.seal = this index, 0 or 10 = none).
M.PAL_SEALS = { 20164, 20165, 20166, 21084, 53720, 31801, 20375, 53736, 31892 }
M.PAL_SEAL_INDEX = { justice = 1, light = 2, wisdom = 3, righteousness = 4, martyr = 5, vengeance = 6, command = 7, corruption = 8, blood = 9 }
-- Auras in PallyPower's order (PallyPower.Auras, rank 1 IDs; matched by name, so every rank counts).
M.PAL_AURAS = { 465, 7294, 19746, 19876, 19888, 19891, 32223 }
-- Blessings in PallyPower's order: 1 Wisdom, 2 Might, 3 Kings, 4 Sanctuary. Single and greater
-- version, rank 1 (as PallyPower) and max rank; names come from the rank 1 ID. `extra` = other
-- sources of the same effect: Blessing of Forgotten Kings 72586 (Drums of Forgotten Kings, +8 %
-- stats, 30 min; checked on Wowhead WotLK and in ElvUI's raid buff reminder, 2026-11-11).
M.PAL_BLESSINGS = {
    { single = { 19742, 48936 }, greater = { 25894, 48938 } },
    { single = { 19740, 48932 }, greater = { 25782, 48934 } },
    { single = { 20217 }, greater = { 25898 }, extra = { 72586 } },
    { single = { 20911 }, greater = { 25899 } },
}
-- Own defaults (without PallyPower): blessings, aura, seal per mode. Holy is not in the spec:
-- Kings/Wisdom, Concentration Aura and Seal of Wisdom are the usual raid choice there.
M.PAL_DEFAULT_BLESSINGS = { prot = { 3, 4 }, ret = { 3, 2 }, holy = { 3, 1 } }
M.PAL_DEFAULT_AURA = { prot = 1, ret = 2, holy = 3 }
M.PAL_BLESSING_SLOTS = 4
M.PAL_PP_CLASS = 5 -- PallyPower.ClassToID.PALADIN

-- Button sets (keys of M.buttons, in bar order). Prot starts with the reserved taunt (hor, rd) and
-- defensive (dprot, loh, dshield) slots, which M.PalProtReco puts at the top of its priority.
M.ROTA_SETS.prot = { "hor", "rd", "dprot", "loh", "dshield", "rf", "seal", "sealaoe", "hs", "judge", "hotr", "cons", "sor", "how", "avs", "plea" }
M.ROTA_SETS.ret = { "seal", "sealaoe", "aw", "judge", "cs", "dstorm", "cons", "how", "exo", "hwrath", "plea" }
M.ROTA_SETS.holy = {} -- buff bar only, the rotation bar stays hidden

-- Settings (profile)
M.DEFAULTS.profile.palRotationMode = "auto"   -- "auto" (talent tree), "prot", "ret", "holy"
M.DEFAULTS.profile.palJudgement = "wisdom"    -- "wisdom" or "light" (PallyPower has no judgement setting)
M.DEFAULTS.profile.palUsePallyPower = true    -- take seal, aura, Righteous Fury and blessings from PallyPower
M.DEFAULTS.profile.palAoe = false             -- AoE mode: Seal of Command, AoE priorities

-- -----------------------------------------------------------------------------------------------
-- Texts (German keys, English in L_EN)
-- -----------------------------------------------------------------------------------------------
E["Schutz"] = "Protection"
E["Vergeltung"] = "Retribution"
E["Heilig"] = "Holy"
E["Heilig: nur Buff-Leiste"] = "Holy: buff bar only"
E["Paladin"] = "Paladin"
E["Paladin-Modus"] = "Paladin mode"
E["Paladin-Modus: %s   %s"] = "Paladin mode: %s   %s"
E["Automatisch: der Talentbaum mit den meisten Punkten entscheidet (Heilig = nur Buff-Leiste, Schutz, Vergeltung). Die Buttons wechseln nur außerhalb des Kampfes."] = "Automatic: the talent tree with the most points decides (Holy = buff bar only, Protection, Retribution). The buttons change only out of combat."
E["Richturteil"] = "Judgement"
E["Weisheit"] = "Wisdom"
E["Licht"] = "Light"
E["AoE-Modus (Siegel des Befehls, AoE-Prioritäten)"] = "AoE mode (Seal of Command, AoE priorities)"
E["Einstellungen aus PallyPower übernehmen"] = "Use PallyPower settings"
E["Siegel, Zorn der Gerechtigkeit, Aura und die dir zugewiesenen Segen kommen aus PallyPower (nur gelesen). Ausgegraut, wenn PallyPower nicht geladen ist."] = "Seal, Righteous Fury, aura and the blessings assigned to you come from PallyPower (read only). Greyed out when PallyPower isn't loaded."
E["PallyPower: geladen"] = "PallyPower: loaded"
E["PallyPower: nicht geladen - eigene Vorgaben"] = "PallyPower: not loaded - own defaults"
E["PallyPower: aus - eigene Vorgaben"] = "PallyPower: off - own defaults"
E["Siegel: %s   Aura: %s   Zorn der Gerechtigkeit: %s"] = "Seal: %s   Aura: %s   Righteous Fury: %s"
E["Segen: %s"] = "Blessings: %s"
E["ja"] = "yes"
E["nein"] = "no"
E["Siegel"] = "Seal"
E["Aura"] = "Aura"
E["Zorn"] = "Fury"
E["Segen"] = "Blessing"
E["Schild"] = "Shield"
E["Bitte"] = "Plea"
E["Gewünscht: %s"] = "Wanted: %s"
E["Anderes Siegel aktiv - Klick wirkt das gewünschte"] = "Another seal is active - click casts the wanted one"
E["Andere Aura aktiv - Klick wirkt die gewünschte"] = "Another aura is active - click casts the wanted one"
E["Keine Aura aktiv - Klick wirkt die gewünschte"] = "No aura active - click casts the wanted one"
E["aus PallyPower"] = "from PallyPower"
E["Zorn der Gerechtigkeit gewünscht: Klick wirkt ihn"] = "Righteous Fury wanted: click casts it"
E["Zorn der Gerechtigkeit nicht gewünscht: rot = aktiv, Klick bricht ihn ab"] = "Righteous Fury not wanted: red = active, click cancels it"
E["Von: %s"] = "From: %s"
E["Eigene Vorgabe"] = "Own default"
E["Rota folgt"] = "Rotation follows"
E["ClassHelper: Paladin-Modus = %s"] = "ClassHelper: Paladin mode = %s"
E["ClassHelper: Richturteil = %s"] = "ClassHelper: Judgement = %s"
E["ClassHelper: AoE-Modus %s"] = "ClassHelper: AoE mode %s"
E["ClassHelper: PallyPower-Übernahme %s"] = "ClassHelper: Use PallyPower %s"
E["AN"] = "ON"
E["AUS"] = "OFF"
E["/ch rota auto|schutz|vergeltung|heilig - Paladin-Modus (auto = nach Talenten)"] = "/ch rota auto|prot|ret|holy - Paladin mode (auto = by talents)"
E["/ch richturteil weisheit|licht - welches Richturteil die Rota nutzt"] = "/ch judgement wisdom|light - which Judgement the rotation uses"
E["/ch aoe an|aus - AoE-Modus (Siegel des Befehls)"] = "/ch aoe on|off - AoE mode (Seal of Command)"
E["/ch pallypower an|aus - Siegel, Aura, Zorn und Segen aus PallyPower übernehmen"] = "/ch pallypower on|off - take seal, aura, Fury and blessings from PallyPower"
E["/ch pal - Paladin-Status (Siegel, Aura, Segen, PallyPower)"] = "/ch pal - Paladin status (seal, aura, blessings, PallyPower)"
E["Zorn der Gerechtigkeit aktiv - nicht gewünscht"] = "Righteous Fury active - not wanted"

-- -----------------------------------------------------------------------------------------------
-- Helpers
-- -----------------------------------------------------------------------------------------------
local function Name(id) return GetSpellInfo(id) end
function M.PalName(id) return GetSpellInfo(id) end

-- Righteous Defense on the boss's target (friendly): the "target of target" of my hostile target.
function M.PalMacro(id, cond)
    local n = Name(id) or tostring(id)
    return "#showtooltip " .. n .. "\n/cast " .. (cond and (cond .. " ") or "") .. n
end

-- Talent tree with the most points: 1 Holy, 2 Protection, 3 Retribution (no talents: Retribution).
function P.DesiredRota()
    local mode = M.cfg and M.cfg.palRotationMode or "auto"
    if mode == "prot" or mode == "ret" or mode == "holy" then return mode end
    local group = GetActiveTalentGroup and GetActiveTalentGroup(false, false) or nil
    local best, most = 3, 0
    for tab = 1, 3 do
        local _, _, points = GetTalentTabInfo(tab, false, false, group)
        if (points or 0) > most then best, most = tab, points end
    end
    if best == 1 then return "holy" elseif best == 2 then return "prot" end
    return "ret"
end

function P.RotaName(rota)
    if rota == "prot" then return L("Schutz") elseif rota == "holy" then return L("Heilig") end
    return L("Vergeltung")
end

function M.PalModeText()
    local mode = M.cfg.palRotationMode or "auto"
    if mode == "auto" then return string.format(L("Automatisch (%s)"), P.RotaName(P.DesiredRota())) end
    return P.RotaName(mode)
end

-- Player auras: one scan of buffs and debuffs per update into maps by spell ID and by name (the first
-- aura of a kind wins, as in the aura order). Rescanned when GetTime() moved on or after UNIT_AURA
-- on the player, so the many checks of one tick (seals, aura, blessings, Forbearance, rotation)
-- share a single pass. Entry: { name, remain, count, spellId, caster, expires } (remain 999 = no expiry).
local scan = { buffId = {}, buffName = {}, debuffId = {}, debuffName = {} }
local function ScanList(func, byId, byName, now)
    wipe(byId); wipe(byName)
    for i = 1, 40 do
        local n, _, _, count, _, _, expires, caster, _, _, spellId = func("player", i)
        if not n then break end
        local e = { name = n, count = count or 0, spellId = spellId, caster = caster, expires = expires,
            remain = (expires and expires > 0) and math.max(expires - now, 0) or 999 }
        if spellId and not byId[spellId] then byId[spellId] = e end
        if not byName[n] then byName[n] = e end
    end
end
function M.PalAuraScan()
    local now = GetTime()
    if scan.at ~= now then
        scan.at = now
        ScanList(UnitBuff, scan.buffId, scan.buffName, now)
        ScanList(UnitDebuff, scan.debuffId, scan.debuffName, now)
        M.palAuraScans = (M.palAuraScans or 0) + 1
    end
    return scan
end
function M.PalAuraDirty() scan.at = nil end
function P.UNIT_AURA(unit) if unit == "player" then scan.at = nil end end

-- Aura entry by spell ID only (e.g. a hidden marker that carries the name of a real spell).
function M.PalBuffById(id) return M.PalAuraScan().buffId[id] end
function M.PalDebuffById(id) return M.PalAuraScan().debuffId[id] end

-- Lookup keys per idList (one spell ID or a list): the IDs and their names (every rank, any
-- language), built once per key; the names come from GetSpellInfo and are cached with the key.
local auraKeys = {}
local function Keys(idList)
    local k = auraKeys[idList]
    if not k then
        k = { ids = {}, names = {} }
        for _, id in ipairs(type(idList) == "table" and idList or { idList }) do
            k.ids[#k.ids + 1] = id
            local n = Name(id)
            if n then k.names[#k.names + 1] = n end
        end
        auraKeys[idList] = k
    end
    return k
end
local function Find(idList, byId, byName)
    local k = Keys(idList)
    for _, id in ipairs(k.ids) do
        local e = byId[id]
        if e then return true, e.remain, e.name, e.spellId, e.count, e end
    end
    for _, n in ipairs(k.names) do
        local e = byName[n]
        if e then return true, e.remain, e.name, e.spellId, e.count, e end
    end
    return false, 0, nil, nil, 0
end

-- Buff / debuff on the player by any of the IDs or their names: up, remain, name, spellId, count, entry.
function M.PalHasAura(idList) local s = M.PalAuraScan(); return Find(idList, s.buffId, s.buffName) end
function M.PalHasDebuff(idList) local s = M.PalAuraScan(); return Find(idList, s.debuffId, s.debuffName) end

-- -----------------------------------------------------------------------------------------------
-- PallyPower (optional, read only: nothing here ever writes its tables)
-- -----------------------------------------------------------------------------------------------
-- PallyPower v3.2.20 (Ace2) globals: PallyPower.opt (its profile: seal index, rf), the saved
-- tables PallyPower_Assignments[paladin][classID] (greater blessing index), PallyPower_NormalAssignments
-- [paladin][classID][player] (single blessing for one player, wins over that paladin's greater one)
-- and PallyPower_AuraAssignments[paladin] (aura index). Keys are plain player names.
function M.PalPPLoaded()
    return type(PallyPower) == "table" and type(PallyPower.opt) == "table"
end

function M.PalUsingPP()
    return M.cfg ~= nil and M.cfg.palUsePallyPower and M.PalPPLoaded() or false
end

local function PlayerName() return UnitName("player") end

-- PallyPower's seal index (1-9), nil when none set.
function M.PalPPSeal()
    if not M.PalUsingPP() then return nil end
    local s = tonumber(PallyPower.opt.seal)
    if s and M.PAL_SEALS[s] then return s end
end

-- Aura index assigned to me, nil when none.
function M.PalPPAura()
    if not M.PalUsingPP() or type(PallyPower_AuraAssignments) ~= "table" then return nil end
    local a = tonumber(PallyPower_AuraAssignments[PlayerName()])
    if a and M.PAL_AURAS[a] then return a end
end

-- Blessings assigned to me: { { index, from = paladin, single = true/nil }, ... } (each blessing once).
-- Paladins PallyPower knows are no longer around (AllPallys) are skipped: its saved tables keep them.
function M.PalPPBlessings()
    if not M.PalUsingPP() or type(PallyPower_Assignments) ~= "table" then return nil end
    local me, list, seen = PlayerName(), {}, {}
    local normal = type(PallyPower_NormalAssignments) == "table" and PallyPower_NormalAssignments or {}
    local present = type(AllPallys) == "table" and next(AllPallys) ~= nil and AllPallys or nil
    local names = {}
    for pally in pairs(PallyPower_Assignments) do names[#names + 1] = pally end
    for pally in pairs(normal) do if not PallyPower_Assignments[pally] then names[#names + 1] = pally end end
    table.sort(names)
    for _, pally in ipairs(names) do
        if not present or present[pally] then
            local classes = PallyPower_Assignments[pally]
            local b, single = classes and tonumber(classes[M.PAL_PP_CLASS]) or 0, nil
            local n = normal[pally] and normal[pally][M.PAL_PP_CLASS] and tonumber(normal[pally][M.PAL_PP_CLASS][me])
            if n and n > 0 then b, single = n, true end
            if M.PAL_BLESSINGS[b] and not seen[b] then
                seen[b] = true
                list[#list + 1] = { index = b, from = pally, single = single }
            end
        end
    end
    if #list == 0 then return nil end -- nothing assigned to me (e.g. solo): own defaults
    table.sort(list, function(x, y) return x.index < y.index end) -- fixed order: Wisdom, Might, Kings, Sanctuary
    return list
end

-- -----------------------------------------------------------------------------------------------
-- What the paladin wants (PallyPower when used, else own defaults)
-- -----------------------------------------------------------------------------------------------
-- Seal index for the current mode. AoE mode: Seal of Command. Own default: Seal of Vengeance
-- (Alliance) / Corruption (Horde) for Prot and Ret, Seal of Wisdom for Holy. A seal the paladin
-- doesn't know (Seal of Command untalented, Vengeance/Corruption before level 64, a PallyPower
-- choice of another paladin's spec) falls back to Seal of Righteousness, which every paladin has.
-- All seals are single-rank spells in 3.3, so M.KnowsSpell(id) is exact.
function M.PalSealIndex(aoe)
    if aoe == nil then aoe = M.cfg and M.cfg.palAoe end
    local idx
    if aoe and M.activeRota ~= "holy" then idx = M.PAL_SEAL_INDEX.command
    else
        idx = M.PalPPSeal()
        if not idx then
            if M.activeRota == "holy" then idx = M.PAL_SEAL_INDEX.wisdom
            else idx = UnitFactionGroup("player") == "Horde" and M.PAL_SEAL_INDEX.corruption or M.PAL_SEAL_INDEX.vengeance end
        end
    end
    if not M.KnowsSpell(M.PAL_SEALS[idx]) then return M.PAL_SEAL_INDEX.righteousness end
    return idx
end
function M.PalSealId(aoe) return M.PAL_SEALS[M.PalSealIndex(aoe)] end

-- Active seal: spell ID (or name) and remaining time; nil when no seal is up (lookups in the scan).
function M.PalActiveSeal()
    for _, id in ipairs(M.PAL_SEALS) do
        local up, remain, name = M.PalHasAura(id)
        if up then return id, remain, name end
    end
end

-- Righteous Fury wanted: always in Protection (owner's decision: PallyPower's rf defaults to false
-- and most tanks never set it); in the other modes PallyPower's opt.rf when used, else not.
function M.PalRFWanted()
    if M.activeRota == "prot" then return true end
    if M.PalUsingPP() then return PallyPower.opt.rf == true end
    return false
end
function M.PalRFActive() return (M.PalHasAura(M.PAL_ID.rf)) end

function M.PalAuraIndex()
    return M.PalPPAura() or M.PAL_DEFAULT_AURA[M.activeRota] or 1
end
function M.PalAuraId() return M.PAL_AURAS[M.PalAuraIndex()] end

-- Blessings I should have: list of { index, from, single }.
function M.PalWantedBlessings()
    local pp = M.PalPPBlessings()
    if pp then return pp end
    local list = {}
    for _, b in ipairs(M.PAL_DEFAULT_BLESSINGS[M.activeRota] or M.PAL_DEFAULT_BLESSINGS.ret) do list[#list + 1] = { index = b } end
    return list
end

-- Blessing up (greater or single version)?
function M.PalBlessingActive(index)
    local b = M.PAL_BLESSINGS[index]
    if not b.all then
        b.all = {}
        for _, id in ipairs(b.single) do b.all[#b.all + 1] = id end
        for _, id in ipairs(b.greater) do b.all[#b.all + 1] = id end
        for _, id in ipairs(b.extra or {}) do b.all[#b.all + 1] = id end
    end
    return M.PalHasAura(b.all)
end

function M.PalJudgementId()
    return (M.cfg and M.cfg.palJudgement == "light") and M.PAL_ID.jol or M.PAL_ID.jow
end

-- Forbearance on me (blocks Divine Protection, Divine Shield, Lay on Hands, Avenging Wrath): up,
-- remaining, and since when it has been seen (for a Forbearance without expiry, see M.PalAwBlocked).
function M.PalForbearance()
    local up, remain = M.PalHasDebuff(M.PAL_ID.forbearance)
    if up then M.palFbSince = M.palFbSince or GetTime() else M.palFbSince = nil end
    return up, remain, M.palFbSince
end

-- My own active aura: name and remaining time, nil when none of mine is up. The stance bar knows
-- which aura is mine (active flag); without stance info, an aura buff cast by myself counts. Another
-- paladin's aura on me is not mine.
function M.PalMyAura()
    local n = GetNumShapeshiftForms and GetNumShapeshiftForms() or 10
    for i = 1, n do
        local _, name, active = GetShapeshiftFormInfo(i)
        if name and active then
            local e = M.PalAuraScan().buffName[name]
            return name, e and e.remain or 999
        end
    end
    local s = M.PalAuraScan()
    for _, id in ipairs(M.PAL_AURAS) do
        local e = s.buffName[Name(id) or ""]
        if e and e.caster == "player" then return e.name, e.remain end
    end
end

-- -----------------------------------------------------------------------------------------------
-- Rotation buttons (secure, fixed macros; only the glow follows the recommendation)
-- -----------------------------------------------------------------------------------------------
-- { key, label, spell ID, macro condition }. The macros never change in combat; seal and judgement
-- follow PallyPower / the option out of combat (macroBuilder, M.PalRefreshMacros).
M.PAL_BUTTONS = {
    { "hor", "HoR", M.PAL_ID.hor, "[@target,harm,nodead]" },
    { "rd", "RD", M.PAL_ID.rd, "[@targettarget,help,nodead]" }, -- the boss's target (the other tank)
    { "dprot", "DP", M.PAL_ID.dprot },
    { "loh", "LoH", M.PAL_ID.loh, "[@player]" },
    { "dshield", "Bubble", M.PAL_ID.dshield },
    { "rf", "RF", M.PAL_ID.rf },
    { "seal", "Seal", M.PAL_SEALS[6] },                -- macro from M.PalSealId(false), see below
    { "sealaoe", "AoE", M.PAL_ID.sealCommand },        -- Seal of Command for AoE (switchable in combat; Righteousness when Command is unknown)
    { "hs", "HS", M.PAL_ID.hs },
    { "judge", "Judge", M.PAL_ID.jow },                -- macro from M.PalJudgementId()
    { "hotr", "HotR", M.PAL_ID.hotr },
    { "cons", "Cons", M.PAL_ID.cons },
    { "sor", "SoR", M.PAL_ID.sor },
    { "how", "HoW", M.PAL_ID.how },
    { "avs", "AS", M.PAL_ID.avs },
    { "plea", "Plea", M.PAL_ID.plea },
    { "aw", "AW", M.PAL_ID.aw },
    { "cs", "CS", M.PAL_ID.cs },
    { "dstorm", "Storm", M.PAL_ID.dstorm },
    { "exo", "Exo", M.PAL_ID.exo },
    { "hwrath", "HW", M.PAL_ID.hwrath },
}

-- Button whose spell follows a function (seal, judgement): macro, spell name and icon are rebuilt
-- by RebuildSpellMacros (out of combat only).
local function Dynamic(key, idFn)
    local btn = M.buttons[key]
    btn.macroBuilder = function()
        local id = idFn()
        btn.palSpellId, btn.spellName = id, Name(id)
        btn.icon:SetTexture(select(3, GetSpellInfo(id)) or "Interface\\Icons\\INV_Misc_QuestionMark")
        return M.PalMacro(id)
    end
    M.SetMacro(btn, btn.macroBuilder())
end

function P.CreateButtons()
    for _, d in ipairs(M.PAL_BUTTONS) do
        M.CreateSpellButton(M.KR, d[1], d[2], Name(d[3]) or ("spell:" .. d[3]), M.PalMacro(d[3], d[4]))
    end
    Dynamic("seal", function() return M.PalSealId(false) end)
    Dynamic("sealaoe", function() return M.PalSealId(true) end)
    Dynamic("judge", M.PalJudgementId)
end

-- Out of combat: seal/judgement macros follow PallyPower and the options.
function M.PalRefreshMacros()
    if InCombatLockdown() then return end
    local b = M.buttons
    if (b.seal and b.seal.palSpellId ~= M.PalSealId(false)) or (b.sealaoe and b.sealaoe.palSpellId ~= M.PalSealId(true))
        or (b.judge and b.judge.palSpellId ~= M.PalJudgementId()) then
        M.RebuildSpellMacros()
    end
end

-- -----------------------------------------------------------------------------------------------
-- Buff bar
-- -----------------------------------------------------------------------------------------------
-- Secure entries (seal, aura, Righteous Fury, Holy Shield, Divine Plea) keep their spell in combat;
-- seal/aura/Fury follow PallyPower out of combat. Blessing slots are plain status icons, shown
-- for every blessing I should have (PallyPower assignment or own defaults), at the end of the bar.
local ALL = { prot = true, ret = true, holy = true }

-- Out of combat: point a secure buff button at another spell.
local function SyncSpell(btn, id)
    if InCombatLockdown() or btn.palSpellId == id then return end
    btn.palSpellId = id
    btn:SetAttribute("type", "spell")
    btn:SetAttribute("spell", Name(id))
    btn.icon:SetTexture(select(3, GetSpellInfo(id)) or "Interface\\Icons\\INV_Misc_QuestionMark")
end

local function CheckSeal(data, btn)
    local want = M.PalSealId()
    SyncSpell(btn, want)
    local id, remain, name = M.PalActiveSeal()
    if not id then return false, 0 end
    return true, remain, name, false, id ~= want
end

local function CheckAura(data, btn)
    local want = M.PalAuraId()
    SyncSpell(btn, want)
    local mine, remain = M.PalMyAura()
    if not mine then return false, 0 end
    if mine == Name(want) then return true, remain, mine end
    return true, remain, mine, false, true -- another of my auras: yellow "?"
end

-- Wanted: click casts it, red while missing. Not wanted: click cancels it, red while active, grey otherwise.
local function CheckRF(data, btn)
    local wanted, active = M.PalRFWanted(), M.PalRFActive()
    if not InCombatLockdown() and btn.palRFWanted ~= wanted then
        btn.palRFWanted = wanted
        local n = Name(M.PAL_ID.rf) or ""
        btn:SetAttribute("type", "macro")
        btn:SetAttribute("macrotext", wanted and ("/cast " .. n) or ("/cancelaura " .. n))
    end
    if wanted then return active, active and 999 or 0 end
    if active then return false, 0 end
    return false, 0, nil, true
end

-- Wanted blessings, recomputed at most every 0.5 s (four slots ask each tick).
local blessCache, blessAt = nil, -10
function M.PalBlessingSlots()
    local now = GetTime()
    if not blessCache or now - blessAt >= 0.5 or now < blessAt then blessCache, blessAt = M.PalWantedBlessings(), now end
    return blessCache
end
function M.PalBlessingSlotsReset() blessCache = nil end

local function CheckBlessing(data, btn)
    local entry = M.PalBlessingSlots()[data.slot]
    if not entry then
        if btn:IsShown() then btn:Hide() end
        return false, 0, nil, true
    end
    if not btn:IsShown() then btn:Show() end
    local b = M.PAL_BLESSINGS[entry.index]
    local iconId = (entry.from and not entry.single) and b.greater[1] or b.single[1]
    if btn.palIcon ~= iconId then
        btn.palIcon = iconId
        btn.icon:SetTexture(select(3, GetSpellInfo(iconId)) or "Interface\\Icons\\INV_Misc_QuestionMark")
    end
    local up, remain, name = M.PalBlessingActive(entry.index)
    return up, remain, name
end

local function Tip(lines)
    return function(self)
        for _, l in ipairs(lines(self)) do GameTooltip:AddLine(l, 0.7, 0.9, 1, true) end
    end
end

function P.BuffList()
    local list = {
        { key = "pal_seal", label = "Siegel", cast = Name(M.PalSealId(false)), iconSpellId = M.PalSealId(false), required = true,
          warnText = "?", rotas = ALL, check = CheckSeal, tooltip = Tip(function()
              local id = M.PalActiveSeal()
              local t = { string.format(L("Gewünscht: %s"), Name(M.PalSealId()) or "?") }
              if id and id ~= M.PalSealId() then t[#t + 1] = L("Anderes Siegel aktiv - Klick wirkt das gewünschte") end
              t[#t + 1] = L("Klick: Buff wirken")
              return t
          end) },
        { key = "pal_aura", label = "Aura", cast = Name(M.PAL_AURAS[1]), iconSpellId = M.PAL_AURAS[1], required = true,
          warnText = "?", rotas = ALL, check = CheckAura, tooltip = Tip(function()
              -- the source is shown, not second-guessed: after a PallyPower spec switch its aura index
              -- can be the untouched default 1 (Devotion)
              local t = { string.format(L("Gewünscht: %s"), Name(M.PalAuraId()) or "?"),
                  M.PalPPAura() and L("aus PallyPower") or L("Eigene Vorgabe") }
              local mine = M.PalMyAura()
              if not mine then t[#t + 1] = L("Keine Aura aktiv - Klick wirkt die gewünschte")
              elseif mine ~= Name(M.PalAuraId()) then t[#t + 1] = L("Andere Aura aktiv - Klick wirkt die gewünschte") end
              t[#t + 1] = L("Klick: Buff wirken")
              return t
          end) },
        { key = "pal_rf", label = "Zorn", macro = "/cast " .. (Name(M.PAL_ID.rf) or ""), iconSpellId = M.PAL_ID.rf, required = true,
          rotas = ALL, check = CheckRF, tooltip = Tip(function()
              return { M.PalRFWanted() and L("Zorn der Gerechtigkeit gewünscht: Klick wirkt ihn")
                  or L("Zorn der Gerechtigkeit nicht gewünscht: rot = aktiv, Klick bricht ihn ab") }
          end) },
        { key = "pal_hs", label = "Schild", cast = Name(M.PAL_ID.hs), iconSpellId = M.PAL_ID.hs, required = true,
          names = M.SpellNames(M.PAL_ID.hs), ids = { [M.PAL_ID.hs] = true }, rotas = { prot = true } },
        { key = "pal_plea", label = "Bitte", cast = Name(M.PAL_ID.plea), iconSpellId = M.PAL_ID.plea, required = true,
          names = M.SpellNames(M.PAL_ID.plea), ids = { [M.PAL_ID.plea] = true }, rotas = { prot = true } },
    }
    for _, data in ipairs(M.SHARED_BUFFS) do list[#list + 1] = data end -- flask, food
    for i = 1, M.PAL_BLESSING_SLOTS do
        list[#list + 1] = { key = "pal_bless" .. i, label = "Segen", slot = i, iconSpellId = M.PAL_BLESSINGS[3].single[1],
            required = true, statusOnly = true, blessing = true, check = CheckBlessing, tooltip = Tip(function(self)
                local e = M.PalBlessingSlots()[self.data.slot]
                if not e then return {} end
                local b = M.PAL_BLESSINGS[e.index]
                return { Name((e.from and not e.single) and b.greater[1] or b.single[1]) or "?",
                    e.from and string.format(L("Von: %s"), e.from) or L("Eigene Vorgabe"), L("Statusanzeige: rot fehlt, grün aktiv") }
            end) }
    end
    return list
end

-- Show the entries of the mode in a row (out of combat: secure buttons), blessing slots last.
-- In combat (e.g. /reload in combat) the layout waits for PLAYER_REGEN_ENABLED.
function P.LayoutBuffs(rota)
    if not M.buffBar then return end
    if InCombatLockdown() then M.palLayoutPending = true; return end
    M.palLayoutPending = nil
    local x = 8
    for _, data in ipairs(M.buffList) do
        local btn = M.buffButtons[data.key]
        if btn and not data.blessing then
            if not data.rotas or data.rotas[rota] then
                btn:ClearAllPoints(); btn:SetPoint("TOPLEFT", M.buffBar, "TOPLEFT", x, -8); btn:Show()
                x = x + 43
            else
                btn:Hide()
            end
        end
    end
    for _, data in ipairs(M.buffList) do
        local btn = M.buffButtons[data.key]
        if btn and data.blessing then
            btn:ClearAllPoints(); btn:SetPoint("TOPLEFT", M.buffBar, "TOPLEFT", x, -8)
            x = x + 43
        end
    end
    M.buffBar:SetWidth(x + 8)
    M.PalBlessingSlotsReset() -- own default blessings depend on the mode
end

-- -----------------------------------------------------------------------------------------------
-- Recommendation (every 0.1 s while the bar is shown)
-- -----------------------------------------------------------------------------------------------
-- State snapshot handed to M.PalProtReco / M.PalRetReco (a new table each tick; they may add fields).
function M.PalState(now)
    local S = { now = now or GetTime(), rota = M.activeRota, aoe = M.cfg.palAoe and true or false, usingPP = M.PalUsingPP() }
    S.targetOK = UnitExists("target") and not UnitIsDead("target") and UnitCanAttack("player", "target") and true or false
    S.targetHpPct = S.targetOK and (UnitHealth("target") / math.max(UnitHealthMax("target") or 1, 1) * 100) or 100
    S.hpPct = UnitHealth("player") / math.max(UnitHealthMax("player") or 1, 1) * 100
    S.manaPct = (UnitPowerMax("player") or 0) > 0 and (UnitPower("player") / UnitPowerMax("player") * 100) or 100
    S.moving = M.PlayerMoving() and true or false
    S.inCombat = UnitAffectingCombat("player") and true or false
    S.sealWantedId = M.PalSealId()                 -- seal to keep up (PallyPower / default; Command in AoE mode)
    S.sealId, S.sealRemain = M.PalActiveSeal()     -- active seal (nil = none)
    S.sealOK = S.sealId ~= nil and S.sealId == S.sealWantedId
    S.rfWanted, S.rfActive = M.PalRFWanted(), M.PalRFActive()
    S.judgementId = M.PalJudgementId()             -- 53408 Wisdom / 20271 Light
    S.forbearance = M.PalForbearance() and true or false
    return S
end

function P.Update(now)
    M.PalRefreshMacros()
    local S = M.PalState(now)
    local reco, urgent, note, prep
    if S.rota == "prot" and M.PalProtReco then reco, urgent, note, prep = M.PalProtReco(S)
    elseif S.rota == "ret" and M.PalRetReco then reco, urgent, note = M.PalRetReco(S) end
    M.MarkRecommended(reco, urgent, prep) -- prep: blue "not yet" even when clickable
    if not reco then M.OneButtonIdle(L("Rota folgt")) end
    M.NoteRecommendation(reco, note)
    M.palReco, M.palNote = reco, note

    local seal = S.sealId and ((S.sealOK and "|cff33ff33" or "|cffffff33") .. (Name(S.sealId) or "?") .. "|r") or ("|cffff3333" .. L("keine") .. "|r")
    local rfWarn = (S.rfActive and not S.rfWanted) and ("  |cffff3333" .. L("Zorn der Gerechtigkeit aktiv - nicht gewünscht") .. "|r") or ""
    local aoe = S.aoe and "  |cffffaa00AoE|r" or ""
    M.KR.info:SetText(string.format("%s  %s: %s%s  %s%s", P.RotaName(S.rota), L("Siegel"), seal, aoe, note or "", rfWarn))
    if M.KR.debugInfo then
        if M.cfg.debugMode then
            M.KR.debugInfo:SetText(string.format("DBG reco=%s reason=%s | rota=%s seal=%s/%s rf=%s/%s PP=%s", tostring(reco), tostring(note),
                tostring(S.rota), tostring(S.sealId), tostring(S.sealWantedId), tostring(S.rfActive), tostring(S.rfWanted), tostring(S.usingPP)))
        else
            M.KR.debugInfo:SetText("")
        end
    end
end

-- Combat log for the rotation files (taunt/defensive triggers): M.PalProtCombatLog / M.PalRetCombatLog
-- get the raw 3.3.5 arguments (timestamp, event, sourceGUID, ..., then the event's own parameters).
function P.COMBAT_LOG_EVENT_UNFILTERED(...)
    if M.activeRota == "prot" and M.PalProtCombatLog then M.PalProtCombatLog(...) end
    if M.activeRota == "ret" and M.PalRetCombatLog then M.PalRetCombatLog(...) end
end

-- -----------------------------------------------------------------------------------------------
-- Status, options, slash commands
-- -----------------------------------------------------------------------------------------------
function M.PalStatusLines()
    local pp = not M.PalPPLoaded() and L("PallyPower: nicht geladen - eigene Vorgaben")
        or (M.PalUsingPP() and L("PallyPower: geladen") or L("PallyPower: aus - eigene Vorgaben"))
    local bless = {}
    for _, e in ipairs(M.PalWantedBlessings()) do
        local b = M.PAL_BLESSINGS[e.index]
        bless[#bless + 1] = (Name((e.from and not e.single) and b.greater[1] or b.single[1]) or "?") .. (e.from and (" (" .. e.from .. ")") or "")
    end
    return {
        string.format(L("Paladin-Modus: %s   %s"), M.PalModeText(), pp),
        string.format(L("Siegel: %s   Aura: %s   Zorn der Gerechtigkeit: %s"), Name(M.PalSealId()) or "?", Name(M.PalAuraId()) or "?",
            M.PalRFWanted() and L("ja") or L("nein")),
        string.format(L("Segen: %s"), #bless > 0 and table.concat(bless, ", ") or L("keine")),
    }
end

local function InCombatRefuse()
    if InCombatLockdown() then print(L("ClassHelper: Einstellungen sind im Kampf gesperrt.")); return true end
end

function M.PalSetMode(mode)
    M.cfg.palRotationMode = mode
    if not M.ApplyRotaMode() then print(L("ClassHelper: Im Kampf - die Buttons wechseln nach dem Kampf.")) end
end
function M.PalSetJudgement(v)
    if InCombatRefuse() then return end
    M.cfg.palJudgement = v
    M.RebuildSpellMacros()
end

M.CLASS_OPTIONS.paladin = { type = "group", name = LF("Paladin"), order = 2, hidden = function() return M.CLASS ~= "PALADIN" end,
    get = function(info) return M.cfg[info[#info]] end, set = function(info, v) M.cfg[info[#info]] = v end, args = {
    palRotationMode = { type = "select", name = LF("Paladin-Modus"), order = 1,
        desc = LF("Automatisch: der Talentbaum mit den meisten Punkten entscheidet (Heilig = nur Buff-Leiste, Schutz, Vergeltung). Die Buttons wechseln nur außerhalb des Kampfes."),
        values = function()
            return { auto = string.format(L("Automatisch (%s)"), P.RotaName(P.DesiredRota())), prot = L("Schutz"), ret = L("Vergeltung"), holy = L("Heilig: nur Buff-Leiste") }
        end,
        set = function(_, v) M.PalSetMode(v) end },
    palJudgement = { type = "select", name = LF("Richturteil"), order = 2,
        values = function() return { wisdom = Name(M.PAL_ID.jow) or L("Weisheit"), light = Name(M.PAL_ID.jol) or L("Licht") } end,
        set = function(_, v) M.PalSetJudgement(v) end },
    palAoe = { type = "toggle", name = LF("AoE-Modus (Siegel des Befehls, AoE-Prioritäten)"), order = 3, width = "full" },
    palUsePallyPower = { type = "toggle", name = LF("Einstellungen aus PallyPower übernehmen"), order = 4, width = "full",
        desc = LF("Siegel, Zorn der Gerechtigkeit, Aura und die dir zugewiesenen Segen kommen aus PallyPower (nur gelesen). Ausgegraut, wenn PallyPower nicht geladen ist."),
        disabled = function() return not M.PalPPLoaded() end,
        set = function(_, v) M.cfg.palUsePallyPower = v; M.PalBlessingSlotsReset() end },
    status = { type = "description", order = 5, fontSize = "medium", name = function() return table.concat(M.PalStatusLines(), "\n") end },
} }

local function OnOff(a)
    if a == "an" or a == "on" then return true elseif a == "aus" or a == "off" then return false end
end

-- /ch commands of the Paladin module; true = handled.
function P.Slash(cmd, arg)
    local a = string.lower(arg or "")
    if cmd == "rota" or cmd == "rotation" then
        local mode = ({ auto = "auto", prot = "prot", schutz = "prot", ret = "ret", vergeltung = "ret", holy = "holy", heilig = "holy" })[a]
        if mode then M.PalSetMode(mode) end
        print(string.format(L("ClassHelper: Paladin-Modus = %s"), M.PalModeText()))
        if not mode then print(L("/ch rota auto|schutz|vergeltung|heilig - Paladin-Modus (auto = nach Talenten)")) end
        return true
    elseif cmd == "richturteil" or cmd == "judgement" or cmd == "judgment" then
        local v = ({ weisheit = "wisdom", wisdom = "wisdom", licht = "light", light = "light" })[a]
        if v then M.PalSetJudgement(v) end
        print(string.format(L("ClassHelper: Richturteil = %s"), Name(M.PalJudgementId()) or "?"))
        if not v then print(L("/ch richturteil weisheit|licht - welches Richturteil die Rota nutzt")) end
        return true
    elseif cmd == "aoe" then
        local v = OnOff(a)
        if v == nil then v = not M.cfg.palAoe end
        M.cfg.palAoe = v
        print(string.format(L("ClassHelper: AoE-Modus %s"), v and L("AN") or L("AUS")))
        return true
    elseif cmd == "pallypower" or cmd == "pp" then
        local v = OnOff(a)
        if v ~= nil then M.cfg.palUsePallyPower = v; M.PalBlessingSlotsReset() end
        print(string.format(L("ClassHelper: PallyPower-Übernahme %s"), M.cfg.palUsePallyPower and L("AN") or L("AUS")))
        for _, l in ipairs(M.PalStatusLines()) do print(l) end
        return true
    elseif cmd == "pal" or cmd == "paladin" then
        for _, l in ipairs(M.PalStatusLines()) do print(l) end
        return true
    end
end

function P.SlashHelp()
    print(L("/ch rota auto|schutz|vergeltung|heilig - Paladin-Modus (auto = nach Talenten)"))
    print(L("/ch richturteil weisheit|licht - welches Richturteil die Rota nutzt"))
    print(L("/ch aoe an|aus - AoE-Modus (Siegel des Befehls)"))
    print(L("/ch pallypower an|aus - Siegel, Aura, Zorn und Segen aus PallyPower übernehmen"))
    print(L("/ch pal - Paladin-Status (Siegel, Aura, Segen, PallyPower)"))
end

function P.PLAYER_REGEN_ENABLED()
    if M.palLayoutPending then P.LayoutBuffs(M.activeRota) end
end

-- Talent change: the automatic flask follows the new tree at once (its cache holds 5 s otherwise).
function P.PLAYER_TALENT_UPDATE() M.autoFlaskCache = nil end
P.ACTIVE_TALENT_GROUP_CHANGED = P.PLAYER_TALENT_UPDATE
