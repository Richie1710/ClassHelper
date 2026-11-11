-- ClassHelper: Retribution Paladin rotation (SimC 3.3 priority, see the spec's "Retribution" part).
--
-- Contract (called by M.Pal.Update every 0.1 s while the Ret bar is shown):
--   M.PalRetReco(S) -> key, urgent, note
--     S     = M.PalState() (fields listed in PaladinProt.lua)
--     key   = a button key of M.ROTA_SETS.ret (seal, sealaoe, aw, judge, cs, dstorm, cons, how, exo,
--             hwrath, plea) or nil (no glow, one-button idle)
--     urgent = red glow instead of green; note = text for the info line (German key through M.L)
--   M.PalRetCombatLog(...) gets every combat log event (3.3.5 layout) while in Ret mode.
-- Righteous Fury active while not wanted is already shown by Paladin.lua (buff bar entry red, info
-- line warning; PallyPower's rf = true makes it wanted).
--
-- Source of the order: SimulationCraft's default paladin action list at commit 85243e9
-- (engine/sc_paladin.cpp, paladin_t::init_actions), with Ret talents and a two-hander:
--   seal_of_vengeance / use_item (trinkets) / avenging_wrath / judgement / crusader_strike /
--   divine_storm / consecration,if=target.time_to_die>=6 / hammer_of_wrath / exorcism,if=
--   buff.the_art_of_war.react / divine_plea
-- (hammer_of_justice, a stun, is left out: it does nothing on bosses; shield_of_righteousness and
-- holy_shock are not in a 2H Ret list). SimC's hammer_of_wrath_t::ready() only checks target
-- health <= 20 %: in 3.3 Avenging Wrath does not enable Hammer of Wrath (that came in Cataclysm).
--
-- Priority model:
-- 1) No seal -> the wanted seal (urgent); another seal than the wanted one (PallyPower changed, AoE
--    mode switched in combat) -> the wanted seal, not urgent. "sealaoe" in AoE mode, else "seal".
--    An unknown seal falls back to Seal of Righteousness (M.PalSealIndex).
-- 2) Avenging Wrath (in combat with a target) when ready, or an on-use trinket of the AW macro is
--    ready: the AW button's macro also uses the on-use trinkets (like the Frost cooldown button),
--    all off the GCD; the trinket recommendation checks exactly the slots the macro holds.
--    Since patch 3.0.4 Avenging Wrath no longer causes Forbearance; it is blocked for 30 s by the
--    hidden "Avenging Wrath Marker" (61987) that Divine Shield / Divine Protection / Hand of
--    Protection / Lay on Hands on oneself apply. Checked by ID (buff or debuff). Only while the
--    marker has never been seen this session (cores that hide it), a Forbearance younger than 30 s
--    blocks too: more than 90 of its 120 s left, or, without an expiry, seen for less than 30 s.
-- 3) Single target: Judgement > Crusader Strike > Divine Storm > Consecration (target time-to-die
--    >= 6 s or unknown) > Hammer of Wrath (target <= 20 %, and IsUsableSpell) > Exorcism (only with
--    The Art of War) > Holy Wrath (target undead or demon; not in SimC, owner's addition) > Divine
--    Plea (in combat, not active).
--    AoE mode: Divine Storm > Consecration > Holy Wrath (target undead or demon) > Crusader Strike
--    > Hammer of Wrath > Judgement > Exorcism (Art of War) > Divine Plea.
-- Cooldowns are the real ones: a cooldown no longer than the GCD counts as ready (as M.KnownReady
-- does for the Mage), right after its own cast a spell is not ready while the client still shows
-- only the GCD. Wait tolerance (cfg.palRetWait, default 0.4 s): the first ability in priority order
-- that is ready within the tolerance wins, so a higher one about to come off cooldown keeps its glow
-- (the button shows the blue "not yet" state until it is clickable) instead of flickering to a
-- lower one. Out of melee range (Crusader Strike's range check) the melee abilities (CS, DS,
-- Consecration, Holy Wrath) are skipped; Judgement, Hammer of Wrath and Exorcism use their own range.
-- "Not in melee range" is only shown when a skipped melee ability would otherwise have been ready.
local M = select(2, ...).M
if not M then return end
local L, E, LF = M.L, M.L_EN, M.LF
local ID = M.PAL_ID

M.PAL_RET = {
    AW_MARKER = 61987,         -- Avenging Wrath Marker (hidden, 30 s): blocks Avenging Wrath
    FORBEARANCE_FRESH = 90,    -- Forbearance (120 s) with more left than this = applied < 30 s ago
    FORBEARANCE_AGE = 30,      -- ... or, without an expiry, seen for less than this
    CONS_TTD = 6,              -- Consecration only when the target lives at least this long
    HOW_PCT = 20,              -- Hammer of Wrath execute range
    AOW_IDS = { 59578, 53489 },-- The Art of War, rank 2 and 1
    -- UnitCreatureType is localized: Holy Wrath works on undead and demons
    HW_TYPES = { ["Undead"] = true, ["Untoter"] = true, ["Demon"] = true, ["D\195\164mon"] = true },
}
local R = M.PAL_RET

M.DEFAULTS.profile.palRetWait = 0.4 -- seconds a higher-priority ability may still be on cooldown

-- Texts (German keys, English in L_EN)
-- "%s bereit", "%s aktiv: %s" and "Schmuckstück bereit" are shared with the Mage texts in ClassHelper.lua
E["Kein Siegel: %s"] = "No seal: %s"
E["Anderes Siegel aktiv: %s"] = "Another seal active: %s"
E["%s: Ziel unter 20%%"] = "%s: target below 20%%"
E["%s: Untote/Dämonen"] = "%s: undead/demons"
E["Nicht in Nahkampfreichweite"] = "Not in melee range"
E["Vergeltung: Wartetoleranz (s)"] = "Retribution: wait tolerance (s)"
E["Ist eine höher priorisierte Fähigkeit innerhalb dieser Zeit bereit, bleibt sie die Empfehlung statt einer niedrigeren (gegen Flackern). 0 = nur was jetzt bereit ist."] = "If a higher-priority ability is ready within this time, it stays the recommendation instead of a lower one (against flicker). 0 = only what is ready now."
E["Die Taste %s nutzt auch beide Schmuckstück-Plätze (13/14), wenn sie einen Benutzen-Effekt haben."] = "The %s button also uses both trinket slots (13/14) when they have a use effect."

local function Name(id) return GetSpellInfo(id) end

-- -----------------------------------------------------------------------------------------------
-- Avenging Wrath button: Avenging Wrath + on-use trinkets in one click (all off the GCD)
-- -----------------------------------------------------------------------------------------------
-- The slots the current macro uses (rebuilt out of combat only): the trinket recommendation reads
-- this list, so a glow never asks for a click whose macro doesn't use that trinket (e.g. a trinket
-- swapped in combat).
M.palAwSlots = {}
function M.PalAwMacro()
    local n = Name(ID.aw) or tostring(ID.aw)
    local t = { "#showtooltip " .. n, "/cast " .. n }
    local slots = {}
    for _, slot in ipairs(M.TRINKET_SLOTS) do
        if M.OnUseTrinket(slot) then t[#t + 1] = "/use " .. slot; slots[#slots + 1] = slot end
    end
    M.palAwSlots = slots
    return table.concat(t, "\n")
end

-- Trinkets of the AW macro: ready, shortest remaining cooldown (999 = none in the macro).
function M.PalAwTrinkets()
    local ready, best = false, 999
    for _, slot in ipairs(M.palAwSlots) do
        if M.OnUseTrinket(slot) then -- still the same kind of item in that slot
            local r, remain = M.ItemSlotReady(slot)
            ready = ready or r
            best = math.min(best, r and 0 or remain)
        end
    end
    return ready, best
end

-- The button is clickable as soon as Avenging Wrath or a trinket of its macro is.
function M.PalAwRemaining()
    local r = M.SpellCooldownRemaining(Name(ID.aw))
    local _, trinket = M.PalAwTrinkets()
    return math.min(r, trinket)
end

-- Paladin.lua creates the buttons; the AW button gets its builder here (rebuilt out of combat by
-- RebuildSpellMacros, e.g. on UNIT_INVENTORY_CHANGED when a trinket is swapped).
local createButtons = M.Pal.CreateButtons
M.Pal.CreateButtons = function(...)
    createButtons(...)
    local btn = M.buttons.aw
    if btn then
        btn.macroBuilder = M.PalAwMacro
        btn.cooldownRemaining = M.PalAwRemaining
        M.SetMacro(btn, M.PalAwMacro())
    end
end

-- -----------------------------------------------------------------------------------------------
-- State helpers
-- -----------------------------------------------------------------------------------------------
-- Remaining real cooldown of a spell, 999 when unknown or not available. A cooldown no longer than
-- the GCD counts as 0; right after the spell's own cast (M.JUST_CAST) while the client still shows
-- only the GCD, it isn't ready.
function M.PalRetRemain(id, now)
    if not M.KnowsSpell(id) then return 999 end
    local name = Name(id)
    local start, duration, enabled = GetSpellCooldown(name)
    if not start or enabled == 0 then return 999 end
    local gcdOnly = start == 0 or duration == 0 or duration <= M.GCD_MAX
    if gcdOnly then
        if now - (M.lastCastAt[name] or -100) < M.JUST_CAST then return 999 end
        return 0
    end
    return math.max(start + duration - now, 0)
end

local function Usable(id)
    local n = Name(id)
    if not n or not IsUsableSpell then return true end
    return IsUsableSpell(n) and true or false
end

-- In range of the target: false only when the client says so (nil = no range info).
local function InRange(id)
    local n = Name(id)
    return not (n and IsSpellInRange and IsSpellInRange(n, "target") == 0)
end

-- Avenging Wrath blocked by its marker (buff or debuff, by ID) or, only while the marker has never
-- been seen this session, a fresh Forbearance.
function M.PalAwBlocked()
    if M.PalBuffById(R.AW_MARKER) or M.PalDebuffById(R.AW_MARKER) then M.palAwMarkerSeen = true; return true end
    if M.palAwMarkerSeen then return false end
    local fb, remain, since = M.PalForbearance()
    if not fb then return false end
    if remain >= 999 then return GetTime() - (since or GetTime()) < R.FORBEARANCE_AGE end -- no expiry: own age
    return remain > R.FORBEARANCE_FRESH
end

-- Time to die of the target itself (its own health samples, not the boss unit the Mage's Arcane
-- burn model prefers): Consecration is about the mob in front of me. nil = unknown.
function M.PalTargetTTD(now, targetOK)
    M.SampleTargetHealth(now, targetOK)
    if not targetOK then return nil end
    local guid = UnitGUID("target")
    M.ttdGuid, M.ttdSamples = guid, (guid and M.ttdByGuid[guid]) or {}
    return (M.TimeToDie())
end

function M.PalRetCombatLog(...) end

-- -----------------------------------------------------------------------------------------------
-- Priority
-- -----------------------------------------------------------------------------------------------
-- Each entry: key, spell ID ("judgementId" = S.judgementId), melee (needs Crusader Strike range),
-- condition(S) -> ok, note, self-cast (no range check).
local ENTRIES = {
    judge = { "judge", "judgementId", false, function(S) return true end },
    cs = { "cs", ID.cs, true, function(S) return true end },
    dstorm = { "dstorm", ID.dstorm, true, function(S) return true end },
    cons = { "cons", ID.cons, true, function(S) return S.ttd == nil or S.ttd >= R.CONS_TTD end },
    how = { "how", ID.how, false, function(S)
        if S.targetHpPct <= R.HOW_PCT then return true, string.format(L("%s: Ziel unter 20%%"), Name(ID.how) or "?") end
        return false
    end },
    exo = { "exo", ID.exo, false, function(S)
        if S.aow then return true, string.format(L("%s aktiv: %s"), S.aowName or Name(ID.aow) or "?", Name(ID.exo) or "?") end
        return false
    end },
    hwrath = { "hwrath", ID.hwrath, true, function(S)
        if S.undeadOrDemon then return true, string.format(L("%s: Untote/Dämonen"), Name(ID.hwrath) or "?") end
        return false
    end },
    plea = { "plea", ID.plea, false, function(S) return S.inCombat and not S.pleaUp end, true },
}
M.PAL_RET_ORDER = {
    single = { "judge", "cs", "dstorm", "cons", "how", "exo", "hwrath", "plea" },
    aoe = { "dstorm", "cons", "hwrath", "cs", "how", "judge", "exo", "plea" },
}

function M.PalRetReco(S)
    local now = S.now
    -- 1) seal
    local sealKey = S.aoe and "sealaoe" or "seal"
    if not S.sealId then
        return sealKey, true, string.format(L("Kein Siegel: %s"), Name(S.sealWantedId) or "?")
    elseif not S.sealOK then
        return sealKey, false, string.format(L("Anderes Siegel aktiv: %s"), Name(S.sealWantedId) or "?")
    end
    if not S.targetOK then return nil end

    -- state for the conditions
    S.awUp = M.PalBuffById(ID.aw) and true or false -- by ID only: the hidden marker may carry the same name
    S.pleaUp = M.PalHasAura(ID.plea) and true or false
    local aow, _, aowName = M.PalHasAura(R.AOW_IDS)
    S.aow, S.aowName = aow and true or false, aowName
    local ctype = UnitCreatureType and UnitCreatureType("target")
    S.undeadOrDemon = ctype ~= nil and R.HW_TYPES[ctype] == true
    S.ttd = M.PalTargetTTD(now, true)
    S.inMelee = InRange(ID.cs)
    S.wait = math.max(0, math.min(tonumber(M.cfg.palRetWait) or 0.4, 1))

    -- 2) Avenging Wrath + trinkets (only the ones its macro uses)
    if S.inCombat then
        local awReady = M.PalRetRemain(ID.aw, now) <= 0 and Usable(ID.aw) and not M.PalAwBlocked() and not S.awUp
        if awReady then return "aw", true, string.format(L("%s bereit"), Name(ID.aw) or "?") end
        if M.PalAwTrinkets() then return "aw", true, L("Schmuckstück bereit") end
    end

    -- 3) rotation: first ability ready within the wait tolerance
    local skippedRange = false
    for _, key in ipairs(S.aoe and M.PAL_RET_ORDER.aoe or M.PAL_RET_ORDER.single) do
        local e = ENTRIES[key]
        local id = e[2] == "judgementId" and S.judgementId or e[2]
        local ok, note = e[4](S)
        if ok and M.KnowsSpell(id) and Usable(id) then
            local inRange = e[5] or (e[3] and S.inMelee) or (not e[3] and InRange(id))
            local ready = M.PalRetRemain(id, now) <= S.wait
            if not inRange then
                skippedRange = skippedRange or ready -- only worth a note when it would be next
            elseif ready then
                return e[1], false, note or Name(id)
            end
        end
    end
    if skippedRange then return nil, false, L("Nicht in Nahkampfreichweite") end
    return nil
end

-- -----------------------------------------------------------------------------------------------
-- Options
-- -----------------------------------------------------------------------------------------------
M.CLASS_OPTIONS.palret = { type = "group", name = LF("Vergeltung"), order = 3, hidden = function() return M.CLASS ~= "PALADIN" end,
    get = function(info) return M.cfg[info[#info]] end, set = function(info, v) M.cfg[info[#info]] = v end, args = {
    palRetWait = { type = "range", name = LF("Vergeltung: Wartetoleranz (s)"), order = 1, min = 0, max = 1, step = 0.05, width = "full",
        desc = LF("Ist eine höher priorisierte Fähigkeit innerhalb dieser Zeit bereit, bleibt sie die Empfehlung statt einer niedrigeren (gegen Flackern). 0 = nur was jetzt bereit ist.") },
    trinkets = { type = "description", order = 2, fontSize = "medium",
        name = function() return string.format(L("Die Taste %s nutzt auch beide Schmuckstück-Plätze (13/14), wenn sie einen Benutzen-Effekt haben."), Name(ID.aw) or "?") end },
} }
