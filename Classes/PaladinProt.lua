-- ClassHelper: Protection Paladin rotation (see the spec's "Protection" part).
--
-- Contract (called by M.Pal.Update every 0.1 s while the Prot bar is shown):
--   M.PalProtReco(S) -> key, urgent, note, prep
--     S     = M.PalState(): now, rota, aoe, usingPP, targetOK, targetHpPct, hpPct, manaPct, moving,
--             inCombat, sealWantedId, sealId, sealRemain, sealOK, rfWanted, rfActive, judgementId,
--             forbearance; this file adds boss, bossRule, bossTarget, bossTargetIsMe, bossOnTarget,
--             bossTargetStable, isTanking (see M.PalProtBossState)
--     key   = a button key of M.ROTA_SETS.prot (hor, rd, dprot, loh, dshield, rf, seal, sealaoe, hs,
--             judge, hotr, cons, sor, how, avs, plea) or nil (no glow, one-button idle)
--     urgent = red glow instead of green; note = text for the info line (German key through M.L)
--     prep  = show the button blue ("not yet") even when it is clickable
--   M.PalProtCombatLog(...) gets every combat log event (3.3.5 layout) while in Prot mode.
--
-- Priority: defensive slot (M.PalProtDefensiveReco) > taunt (M.PalProtTauntReco) > Righteous Fury >
-- seal > Avenger's Shield on the pull > Holy Shield > 969 (Judgement > Hammer of the Righteous >
-- Consecration > Shield of Righteousness; AoE mode: Hammer, Consecration first) > Hammer of Wrath
-- (target <= 20 %) > Avenger's Shield > Divine Plea > the ability that comes off cooldown next.
-- Readiness = known, usable (IsUsableSpell), in range where the spell has one, and its cooldown
-- (the GCD ignored, like M.KnownReady for the Mage) ends within LOOKAHEAD s; the button shows blue
-- ("prep") until it is really clickable, so the glow doesn't jump to a lower spell for 0.3 s.
--
-- All boss spell and NPC IDs were checked against the local DBM-Icecrown / DBM-Coliseum modules
-- (2026-11-11); names only ever come from GetSpellInfo(id).
local M = select(2, ...).M
if not M then return end
local L, E, LF = M.L, M.L_EN, M.LF
local ID = M.PAL_ID

M.PAL_PROT_LOOKAHEAD = 0.3   -- a spell ready within this many seconds still counts as "next"
M.PAL_TAUNT_SETTLE = 1.5     -- after a taunt cast: no further taunt this long (boss target updates)
M.PAL_OWN_FADE = 1.5         -- my own swap debuff about to fall off: taunt shown blue (prep), not red
M.PAL_TAUNT_SOON = 2.0       -- taunt wanted but both taunts on cooldown: show the sooner one up to this long
M.PAL_TARGET_STABLE = 0.5    -- the boss's target must be the same this long before a taunt (cast flips)

-- -----------------------------------------------------------------------------------------------
-- Boss rules
-- -----------------------------------------------------------------------------------------------
-- Taunt rules. kind "stacks": the swap debuff is read from the auras (UnitDebuff on the boss's
-- target and on me: stacks 4th, spell ID 11th value), so death, a battle res or a missed combat log
-- event never leaves stale counts. Two modes:
--   mode "clear" (default): taunt when the other tank has >= the threshold and my own stacks are 0
--     (a new stack on top of old ones adds up); while mine fall off within PAL_OWN_FADE s the button
--     is shown blue only.
--   mode "leapfrog": taunt when the other tank has >= the threshold and my stacks are below theirs,
--     or equal and theirs are newer (later expiry = the more recent stack); used where the debuff
--     never falls off before the swap and carrying stacks over is the intended tactic.
-- kind "cast": the boss's cast (or its aura) marks its target for `window` s (combat log); taunt
-- when the boss targets that player.
-- opt = settings key (on/off), opt .. "N" = threshold, opt .. "H" = heroic threshold (when heroic).
--
-- Per boss (durations from the local DBM timers and Wowhead WotLK, tactics from warcraft.wiki.gg):
--   Lady Deathwhisper, Touch of Insignificance: 30 s, a stack about every 9-15 s -> "clear".
--   Festergut, Gastric Bloat: 100 s (DBM timerGastricBloat, Wowhead 1.667 min), a stack about every
--     13 s, 10 stacks explode -> "clear" (own == 0): carrying stacks over would be lethal. With the
--     100 s duration the taunt usually comes at 7-8 stacks on the other tank (own stacks gone).
--   Professor Putricide, Mutated Plague (phase 3): a stack every 10 s on the tank; it lasts 60 s+
--     (Wowhead lists 3 min) and heals Putricide for every stack when it expires or is removed, so it
--     is never left to fall off: the tanks alternate A2/B2/A3/B3/... (warcraft.wiki.gg) -> "leapfrog".
--   Sindragosa, Mystic Buffet (phase 3): 8 s (DBM), refreshed every 6 s -> "clear".
--   Gormok, Impale: 40 s (Wowhead), every 8-10 s -> "clear".
M.PAL_TAUNT_RULES = {
    { key = "dw", opt = "palT_dw", label = "Lady Todeswisper", npc = { 36855 }, kind = "stacks",
      ids = { 71204 }, n = 3, min = 2, max = 5 },                                  -- Touch of Insignificance
    { key = "saurfang", opt = "palT_saurfang", label = "Todesbringer Saurfang", npc = { 37813 }, kind = "cast",
      ids = { 72410 }, window = 20 },                                               -- Rune of Blood
    { key = "fester", opt = "palT_fester", label = "Fauldarm", npc = { 36626 }, kind = "stacks",
      ids = { 72219, 72551, 72552, 72553 }, n = 6, min = 6, max = 9 },             -- Gastric Bloat
    { key = "putri", opt = "palT_putri", label = "Professor Seuchenmord", npc = { 36678 }, kind = "stacks", mode = "leapfrog",
      ids = { 72451, 72463, 72671, 72672 }, n = 2, min = 1, max = 4 },             -- Mutated Plague (P3)
    { key = "sindra", opt = "palT_sindra", label = "Sindragosa", npc = { 36853 }, kind = "stacks",
      ids = { 70127, 72528, 72529, 72530 }, n = 3, min = 2, max = 6 },             -- Mystic Buffet (P3)
    { key = "gormok", opt = "palT_gormok", label = "Gormok der Pfähler", npc = { 34796 }, kind = "stacks",
      ids = { 66331, 67477, 67478, 67479 }, n = 3, min = 1, max = 5, h = 2 },      -- Impale (heroic 2)
    { key = "lk", opt = "palT_lk", label = "Der Lichkönig (heroisch)", npc = { 36597 }, kind = "cast",
      ids = { 69409, 73797, 73798, 73799 }, window = 5, heroicOnly = true, off = true }, -- Soul Reaper
}
M.PAL_RULE_BY_NPC, M.PAL_RULE_BY_SPELL = {}, {}
for _, r in ipairs(M.PAL_TAUNT_RULES) do
    for _, npc in ipairs(r.npc) do M.PAL_RULE_BY_NPC[npc] = r end
    r.idSet = {}
    for _, id in ipairs(r.ids) do M.PAL_RULE_BY_SPELL[id] = r; r.idSet[id] = true end
end

-- Defensive moments from the combat log (Divine Protection). window = seconds the moment lasts.
M.PAL_DEF = {
    frenzy = { opt = "palD_frenzy", ids = { [72737] = true }, window = 8, tanking = true },  -- Saurfang Frenzy (aura on the boss)
    inhale = { ids = { [69166] = true, [71912] = true } },                                  -- Festergut Inhaled Blight (on the boss)
    pungent = { opt = "palD_pungent", ids = { [69195] = true, [71219] = true, [73031] = true, [73032] = true }, window = 4 },
    reaper = { opt = "palD_reaper", ids = { [69409] = true, [73797] = true, [73798] = true, [73799] = true }, window = 6 }, -- on me
    stomp = { opt = "palD_stomp", ids = { [66330] = true, [67647] = true, [67648] = true, [67649] = true }, window = 3 },   -- Gormok
}
M.PAL_PUNGENT_AFTER = 33.5   -- Pungent Blight about this long after the 3rd Inhaled Blight (DBM timer)
M.PAL_PUNGENT_EARLY = 2      -- ... the moment starts this early and ends with the window after it
M.PAL_BUFFET_IDS = { 70127, 72528, 72529, 72530 }

-- Settings (profile)
local D = M.DEFAULTS.profile
D.palTaunt = true
for _, r in ipairs(M.PAL_TAUNT_RULES) do
    D[r.opt] = not r.off
    if r.n then D[r.opt .. "N"] = r.n end
    if r.h then D[r.opt .. "H"] = r.h end
end
D.palDef = true
-- Gormok's Staggering Stomp is off by default: it is a short raid-wide knock-down a tank usually
-- doesn't need Divine Protection for.
D.palD_frenzy, D.palD_pungent, D.palD_reaper, D.palD_stomp = true, true, true, false
D.palD_buffet, D.palD_buffetN = true, 5
D.palDefHp = true
D.palDefDPPct, D.palDefLoHPct = 35, 15
D.palDefDS, D.palDefDSPct = false, 10

-- -----------------------------------------------------------------------------------------------
-- Texts
-- -----------------------------------------------------------------------------------------------
E["Lady Todeswisper"] = "Lady Deathwhisper"
E["Todesbringer Saurfang"] = "Deathbringer Saurfang"
E["Fauldarm"] = "Festergut"
E["Professor Seuchenmord"] = "Professor Putricide"
E["Sindragosa"] = "Sindragosa"
E["Gormok der Pfähler"] = "Gormok the Impaler"
E["Der Lichkönig (heroisch)"] = "The Lich King (heroic)"
E["Schutz: Spott"] = "Protection: taunt"
E["Schutz: Verteidigung"] = "Protection: defensives"
E["Spott-Empfehlung"] = "Taunt recommendation"
E["Hand der Abrechnung (rot), bei Abklingzeit Rechtschaffene Verteidigung auf das Ziel des Bosses: wenn der Boss einen anderen Spieler angreift, der die Wechsel-Schwächung ab der Schwelle trägt, und deine eigenen Stapel weg sind (Seuchenmord: wenn du weniger Stapel hast). Nie, solange du den Boss tankst. Der Boss muss dein Ziel sein."] =
    "Hand of Reckoning (red), Righteous Defense on the boss's target while it is on cooldown: when the boss attacks another player who carries the swap debuff at the threshold or more and your own stacks are gone (Putricide: when you have fewer stacks). Never while you tank the boss. The boss must be your target."
E["Stapel"] = "Stacks"
E["Stapel (heroisch)"] = "Stacks (heroic)"
E["Verteidigung bei Boss-Mechaniken"] = "Defensives on boss mechanics"
E["Göttlicher Schutz (rot) bei: Saurfangs Raserei (wenn du ihn tankst), Fauldarms Stechender Seuche (auch kurz vor der erwarteten nach dem 3. Einatmen), Seelenernter auf dir, Gormoks Stampfen (Standard aus), Sindragosas Mystischem Puffer auf dir ab den eingestellten Stapeln. Nur wenn bereit und ohne Vorahnung."] =
    "Divine Protection (red) on: Saurfang's Frenzy (when you tank him), Festergut's Pungent Blight (also shortly before the expected one after the 3rd inhale), Soul Reaper on you, Gormok's Stomp (off by default), Sindragosa's Mystic Buffet on you at the set stacks. Only when ready and without Forbearance."
E["Mystischer Puffer: Stapel auf dir"] = "Mystic Buffet: stacks on you"
E["Lebens-Schwellen"] = "Health thresholds"
E["%s bei Leben unter (%%)"] = "%s below health (%%)"
E["Gottesschild als letzte Rettung"] = "Divine Shield as last resort"
E["Standard aus: für Tanks nur als letzte Rettung gedacht."] = "Off by default: for tanks only meant as a last resort."
E["Spott: %s hat %d Stapel %s (du: %d)"] = "Taunt: %s has %d stacks of %s (you: %d)"
E["Spott: %s auf %s"] = "Taunt: %s on %s"
E["%s nicht bereit - %s"] = "%s not ready - %s"
E["Spott nötig - Boss ins Ziel nehmen: %s"] = "Taunt needed - target the boss: %s"
E["Verteidigung: %s"] = "Defensive: %s"
E["Leben %d%%: %s"] = "Health %d%%: %s"
E["%s fehlt"] = "%s missing"
E["Kein Siegel: %s"] = "No seal: %s"
E["Falsches Siegel: %s"] = "Wrong seal: %s"
E["Pull: %s"] = "Pull: %s"
E["Rota: %s"] = "Rotation: %s"
E["AoE: %s"] = "AoE: %s"
E["Ziel unter 20%%: %s"] = "Target below 20%%: %s"
E["Nächste: %s"] = "Next: %s"
E["%s (%s ausgelöst)"] = "%s (%s triggered)"

-- -----------------------------------------------------------------------------------------------
-- Spell helpers
-- -----------------------------------------------------------------------------------------------
local nameCache = {}
local function SN(id)
    local n = nameCache[id]
    if n == nil then n = GetSpellInfo(id) or false; nameCache[id] = n end
    return n or nil
end
M.PalSN = SN

-- Cooldown left (s), the GCD ignored; 999 = not known / not castable. Right after its own cast a
-- spell is not ready for M.JUST_CAST s (the client briefly reports only the GCD then).
function M.PalCD(id, now)
    now = now or GetTime()
    local name = SN(id)
    if not name or not M.KnowsSpell(id) then return 999 end
    local start, duration, enabled = GetSpellCooldown(name)
    if not start or enabled == 0 then return 999 end
    local remain = 0
    if start > 0 and duration > M.GCD_MAX then remain = math.max(start + duration - now, 0) end
    local since = now - (M.lastCastAt[name] or -100)
    if since >= 0 and since < M.JUST_CAST then remain = math.max(remain, M.JUST_CAST - since) end
    return remain
end

local function Usable(id)
    if not IsUsableSpell then return true end
    return IsUsableSpell(SN(id)) and true or false
end

-- In range of the unit (spells without a range or an unknown answer count as in range).
local function InRange(id, unit)
    if not unit or not IsSpellInRange then return true end
    return IsSpellInRange(SN(id), unit) ~= 0
end

-- Cooldown left when the spell is otherwise castable now (known, usable, in range), else nil.
local function Avail(S, id, unit)
    local cd = M.PalCD(id, S.now)
    if cd >= 999 or not Usable(id) or not InRange(id, unit) then return nil end
    return cd
end
M.PalAvail = Avail

local function Ready(S, id, unit)
    local cd = Avail(S, id, unit)
    return cd ~= nil and cd <= M.PAL_PROT_LOOKAHEAD
end

-- My own debuff from a list of IDs (the per-update aura scan): stacks (0 = none), remaining, expiry.
local function OwnDebuff(ids)
    local up, remain, _, _, count, e = M.PalHasDebuff(ids)
    if not up then return 0, 0, 0 end
    return math.max(count or 0, 1), remain, (e and e.expires) or 0
end

-- Stacks of a rule's debuff on a unit, read from its auras: stacks (0 = none) and expiry (0 = unknown).
-- Matched by spell ID, by name as a fallback (cores with other difficulty IDs).
function M.PalUnitStacks(unit, rule)
    if not unit or not UnitExists(unit) then return 0, 0 end
    if UnitIsUnit(unit, "player") then
        local n, _, exp = OwnDebuff(rule.ids)
        return n, exp
    end
    if not rule.nameSet then
        rule.nameSet = {}
        for _, id in ipairs(rule.ids) do local n = SN(id); if n then rule.nameSet[n] = true end end
    end
    for i = 1, 40 do
        local n, _, _, count, _, _, expires, _, _, _, spellId = UnitDebuff(unit, i)
        if not n then break end
        if (spellId and rule.idSet[spellId]) or rule.nameSet[n] then return math.max(count or 0, 1), expires or 0 end
    end
    return 0, 0
end

-- Heroic: 3/4 (10/25 heroic), or ICC on cores that report 1/2 with the dynamic flag (as DBM-Core).
function M.PalHeroic()
    local _, instType, diff, _, _, dynDiff, isDynamic = GetInstanceInfo()
    if instType ~= "raid" then return false end
    if isDynamic and dynDiff == 1 then return true end
    if GetInstanceDifficulty and (GetInstanceDifficulty() == 3 or GetInstanceDifficulty() == 4) then return true end
    return diff == 3 or diff == 4
end

-- -----------------------------------------------------------------------------------------------
-- Combat log tracking (cast marks, defensive moments)
-- -----------------------------------------------------------------------------------------------
-- T.marks[guid][rule key] = time of the boss cast on that player, T.moments[name] = { at, untilT },
-- T.pungentAt = expected Pungent Blight, T.lastRule = last rule whose spell was seen in a SPELL_*
-- event, T.bossNpc = boss of the current rules, T.tgtGuid / T.tgtSince = the boss's target and since
-- when. Reset on combat end and boss change. Swap-debuff stacks are not tracked here: they come
-- from the auras (M.PalUnitStacks).
M.palProt = { marks = {}, moments = {} }
function M.PalProtReset()
    local T = M.palProt
    T.marks, T.moments = {}, {}
    T.pungentAt, T.lastRule, T.bossNpc, T.tgtGuid, T.tgtSince = nil, nil, nil, nil, nil
end

-- Boss change: drop what other bosses' rules collected (the new boss's own events may arrive
-- before its unit is seen, so they stay).
function M.PalProtKeepOnly(key)
    local T = M.palProt
    for _, perRule in pairs(T.marks) do
        for k in pairs(perRule) do if k ~= key then perRule[k] = nil end end
    end
    if key ~= "fester" then T.pungentAt = nil end
end

local function Moment(name, window, now)
    M.palProt.moments[name] = { at = now, untilT = now + window }
end

-- 3.3.5: timestamp, event, srcGUID, srcName, srcFlags, dstGUID, dstName, dstFlags, spellId,
-- spellName, school, then auraType and amount for the aura events (APPLIED has no amount).
-- Only SPELL_* events carry a spell ID in the 9th place (SWING_DAMAGE has the damage there).
function M.PalProtCombatLog(_, event, srcGUID, srcName, srcFlags, dstGUID, dstName, dstFlags, spellId, spellName, school, auraType, amount)
    if not spellId or type(event) ~= "string" or event:sub(1, 6) ~= "SPELL_" then return end
    local T, now = M.palProt, GetTime()
    local rule = M.PAL_RULE_BY_SPELL[spellId]
    if rule then
        T.lastRule = rule
        if rule.kind == "cast" then
            if dstGUID and (event == "SPELL_CAST_SUCCESS" or event == "SPELL_AURA_APPLIED") then
                T.marks[dstGUID] = T.marks[dstGUID] or {}
                T.marks[dstGUID][rule.key] = now
            elseif dstGUID and event == "SPELL_AURA_REMOVED" and T.marks[dstGUID] then
                T.marks[dstGUID][rule.key] = nil
            end
        end
    end
    local DF = M.PAL_DEF
    if DF.frenzy.ids[spellId] and event == "SPELL_AURA_APPLIED" then
        Moment("frenzy", DF.frenzy.window, now)
    elseif DF.inhale.ids[spellId] and (event == "SPELL_AURA_APPLIED" or event == "SPELL_AURA_APPLIED_DOSE") then
        if (tonumber(amount) or 1) >= 3 then T.pungentAt = now + M.PAL_PUNGENT_AFTER end
    elseif DF.pungent.ids[spellId] and event == "SPELL_CAST_START" then
        Moment("pungent", DF.pungent.window, now)
        T.pungentAt = nil
    elseif DF.reaper.ids[spellId] and (event == "SPELL_CAST_SUCCESS" or event == "SPELL_AURA_APPLIED") and dstGUID and dstGUID == UnitGUID("player") then
        Moment("reaper", DF.reaper.window, now)
    elseif DF.stomp.ids[spellId] and event == "SPELL_CAST_START" then
        Moment("stomp", DF.stomp.window, now)
    end
end

-- -----------------------------------------------------------------------------------------------
-- The boss and its target
-- -----------------------------------------------------------------------------------------------
local BOSS_UNITS = { "target", "boss1", "boss2", "boss3", "boss4", "focus" }
local function Hostile(u) return UnitExists(u) and not UnitIsDead(u) and UnitCanAttack("player", u) end

-- Boss unit and its rule: a unit whose NPC ID belongs to a rule (target first); otherwise the target
-- when its GUID gives no NPC ID at all (unusual GUIDs) with the rule last seen in the combat log.
function M.PalProtFindBoss()
    for _, u in ipairs(BOSS_UNITS) do
        if Hostile(u) then
            local rule = M.PAL_RULE_BY_NPC[M.NpcIdFromGUID(UnitGUID(u)) or 0]
            if rule then return u, rule, M.NpcIdFromGUID(UnitGUID(u)) end
        end
    end
    if Hostile("target") and not M.NpcIdFromGUID(UnitGUID("target")) and M.palProt.lastRule then
        return "target", M.palProt.lastRule, nil
    end
end

-- Adds S.boss (unit), S.bossRule, S.bossTarget (unit of the boss's target), S.bossTargetIsMe,
-- S.bossTargetStable (the same target for PAL_TARGET_STABLE s), S.isTanking (threat API: I am the
-- boss's tank; a brief target flip during a cast doesn't change it), S.bossOnTarget (the boss is my
-- target, so the fixed taunt macros hit it). Resets the tracking on combat end and when another boss
-- with rules shows up.
function M.PalProtBossState(S)
    local T = M.palProt
    if S.inCombat then T.inCombat = true elseif T.inCombat then T.inCombat = false; M.PalProtReset() end
    local u, rule, npc = M.PalProtFindBoss()
    if npc then
        if T.bossNpc and T.bossNpc ~= npc then M.PalProtKeepOnly(rule.key) end
        T.bossNpc = npc
    end
    S.boss, S.bossRule, S.isTanking = u, rule, false
    if u then
        S.isTanking = UnitDetailedThreatSituation and UnitDetailedThreatSituation("player", u) and true or false
        local tu = (u == "target") and "targettarget" or (u .. "target")
        if UnitExists(tu) then
            S.bossTarget = tu
            S.bossTargetIsMe = UnitIsUnit(tu, "player") and true or false
            local g = UnitGUID(tu)
            if g ~= T.tgtGuid then T.tgtGuid, T.tgtSince = g, S.now end
            S.bossTargetStable = S.now - (T.tgtSince or S.now) >= M.PAL_TARGET_STABLE
        else
            T.tgtGuid = nil
        end
        S.bossOnTarget = (u == "target") or (UnitExists("target") and UnitIsUnit("target", u)) or false
    end
end

-- -----------------------------------------------------------------------------------------------
-- Defensive slot
-- -----------------------------------------------------------------------------------------------
local function BuffUp(id) return (M.PalHasAura(id)) end

-- Divine Protection / Divine Shield / Lay on Hands castable now (not under Forbearance).
local function DefReady(S, id)
    if S.forbearance then return false end
    return Ready(S, id)
end

-- Text of the current boss moment for Divine Protection, nil when none.
function M.PalProtMoment(S)
    local cfg, T, now = M.cfg, M.palProt, S.now
    if not cfg.palDef then return nil end
    local function active(name)
        local m = T.moments[name]
        return m and now <= m.untilT and now >= m.at
    end
    if cfg.palD_reaper and active("reaper") then return SN(69409) end
    if cfg.palD_pungent and (active("pungent")
        or (T.pungentAt and now >= T.pungentAt - M.PAL_PUNGENT_EARLY and now <= T.pungentAt + M.PAL_DEF.pungent.window)) then
        return SN(69195)
    end
    -- Frenzy only when the boss is found and I am its tank (threat API)
    if cfg.palD_frenzy and active("frenzy") and S.boss and S.isTanking then return SN(72737) end
    if cfg.palD_stomp and active("stomp") then return SN(66330) end
    if cfg.palD_buffet then
        local n = OwnDebuff(M.PAL_BUFFET_IDS)
        if n >= (tonumber(cfg.palD_buffetN) or 5) then return string.format("%s %d", SN(70127) or "?", n) end
    end
end

function M.PalProtDefensiveReco(S)
    if not S.inCombat then return nil end
    local cfg = M.cfg
    local hp = S.hpPct
    local shielded = BuffUp(ID.dprot) or BuffUp(ID.dshield)
    local ad = M.PalHasDebuff(ID.ardent) and SN(ID.ardent) or nil -- Ardent Defender's lockout is a debuff
    local function hpNote(id)
        local n = string.format(L("Leben %d%%: %s"), math.floor(hp + 0.5), SN(id) or "?")
        if ad then n = string.format(L("%s (%s ausgelöst)"), n, ad) end
        return n
    end
    if cfg.palDefHp then
        if hp <= (tonumber(cfg.palDefLoHPct) or 15) and DefReady(S, ID.loh) then return "loh", true, hpNote(ID.loh) end
        if cfg.palDefDS and not shielded and hp <= (tonumber(cfg.palDefDSPct) or 10) and DefReady(S, ID.dshield) then
            return "dshield", true, hpNote(ID.dshield)
        end
    end
    if shielded or not DefReady(S, ID.dprot) then return nil end
    local why = M.PalProtMoment(S)
    if why then return "dprot", true, string.format(L("Verteidigung: %s"), why) end
    if cfg.palDefHp and hp <= (tonumber(cfg.palDefDPPct) or 35) then return "dprot", true, hpNote(ID.dprot) end
end

-- -----------------------------------------------------------------------------------------------
-- Taunt slot
-- -----------------------------------------------------------------------------------------------
function M.PalTauntThreshold(rule)
    local cfg = M.cfg
    if rule.h and M.PalHeroic() then return tonumber(cfg[rule.opt .. "H"]) or rule.h end
    return tonumber(cfg[rule.opt .. "N"]) or rule.n
end

-- Why the other player needs to be taunted off: note text and prep (true = not yet, show blue), nil
-- when not. See the rule modes above.
function M.PalTauntReason(S, rule, unit)
    local name = UnitName(unit) or "?"
    if rule.kind == "stacks" then
        local n, theirExp = M.PalUnitStacks(unit, rule)
        if n < M.PalTauntThreshold(rule) then return nil end
        local mine, remain, myExp = OwnDebuff(rule.ids)
        local why = string.format(L("Spott: %s hat %d Stapel %s (du: %d)"), name, n, SN(rule.ids[1]) or "?", mine)
        if rule.mode == "leapfrog" then
            if mine < n or (mine == n and theirExp > myExp) then return why end
            return nil
        end
        if mine == 0 then return why end
        if remain <= M.PAL_OWN_FADE then return why, true end -- mine are about to fall off: blue only
        return nil
    end
    local guid = UnitGUID(unit)
    local marks = M.palProt.marks[guid]
    local at = marks and marks[rule.key]
    if not at or S.now - at > rule.window then return nil end
    local mine = M.palProt.marks[UnitGUID("player")]
    if mine and mine[rule.key] and S.now - mine[rule.key] <= rule.window then return nil end
    return string.format(L("Spott: %s auf %s"), SN(rule.ids[1]) or "?", name)
end

-- -> key, urgent, note, prep
function M.PalProtTauntReco(S)
    local cfg = M.cfg
    local rule, tu = S.bossRule, S.bossTarget
    if not cfg.palTaunt or not S.inCombat or not rule or not tu or S.bossTargetIsMe or S.isTanking then return nil end
    if not cfg[rule.opt] or (rule.heroicOnly and not M.PalHeroic()) then return nil end
    if not UnitIsPlayer(tu) then return nil end
    if not S.bossTargetStable then return nil end -- a brief target flip during a cast
    local reason, prep = M.PalTauntReason(S, rule, tu)
    if not reason then return nil end
    if not S.bossOnTarget then S.tauntHint = reason; return nil end -- the macros work on my target only
    for _, id in ipairs({ ID.hor, ID.rd }) do -- a taunt just cast: wait for the boss to turn
        if S.now - (M.lastCastAt[SN(id) or ""] or -100) < M.PAL_TAUNT_SETTLE then return nil end
    end
    local hor = Avail(S, ID.hor, "target")
    if hor and hor <= M.PAL_PROT_LOOKAHEAD then return "hor", not prep, reason, prep end
    local rd = Avail(S, ID.rd, tu)
    local rdNote = string.format(L("%s nicht bereit - %s"), SN(ID.hor) or "?", reason)
    if rd and rd <= M.PAL_PROT_LOOKAHEAD then return "rd", not prep, rdNote, prep end
    -- both cooling down: the sooner one (blue until ready)
    if hor and hor <= M.PAL_TAUNT_SOON and (not rd or hor <= rd) then return "hor", not prep, reason, prep end
    if rd and rd <= M.PAL_TAUNT_SOON then return "rd", not prep, rdNote, prep end
    S.tauntHint = reason
end

-- -----------------------------------------------------------------------------------------------
-- Rotation
-- -----------------------------------------------------------------------------------------------
-- { key, spell ID (function: from the state), range unit, melee only }
local function Judge(S) return S.judgementId end
M.PAL_PROT_ORDER = {
    { "judge", Judge, "target" }, { "hotr", ID.hotr, "target" }, { "cons", ID.cons, nil, true }, { "sor", ID.sor, "target" },
}
M.PAL_PROT_ORDER_AOE = {
    { "hotr", ID.hotr, "target" }, { "cons", ID.cons, nil, true }, { "judge", Judge, "target" }, { "sor", ID.sor, "target" },
}

function M.PalProtRotation(S)
    local LA = M.PAL_PROT_LOOKAHEAD
    -- 1) Righteous Fury (always wanted in Protection)
    if S.rfWanted and not S.rfActive and Ready(S, ID.rf) then
        return "rf", S.inCombat, string.format(L("%s fehlt"), SN(ID.rf) or "?")
    end
    -- 2) seal (AoE mode: Seal of Command via its own button)
    if not S.sealOK and S.sealWantedId and Ready(S, S.sealWantedId) then
        local key = S.aoe and "sealaoe" or "seal"
        if S.sealId then return key, false, string.format(L("Falsches Siegel: %s"), SN(S.sealId) or "?") end
        return key, S.inCombat, string.format(L("Kein Siegel: %s"), SN(S.sealWantedId) or "?")
    end
    if not S.targetOK then return nil end
    local melee = InRange(ID.hotr, "target")
    -- 3) Avenger's Shield on the pull (out of combat or not in melee range yet)
    if (not S.inCombat or not melee) and Ready(S, ID.avs, "target") then
        return "avs", false, string.format(L("Pull: %s"), SN(ID.avs) or "?")
    end
    -- 4) Holy Shield
    local hsUp = BuffUp(ID.hs)
    if not hsUp and (S.inCombat or melee) and Ready(S, ID.hs) then
        return "hs", false, string.format(L("%s fehlt"), SN(ID.hs) or "?")
    end
    -- 5) 969: the first one ready within the look-ahead
    local order = S.aoe and M.PAL_PROT_ORDER_AOE or M.PAL_PROT_ORDER
    local fmt = S.aoe and L("AoE: %s") or L("Rota: %s")
    local soonKey, soonId, soonCd = nil, nil, 999
    for _, e in ipairs(order) do
        local id = type(e[2]) == "function" and e[2](S) or e[2]
        local cd = (not e[4] or melee) and Avail(S, id, e[3]) or nil
        if cd and cd <= LA then return e[1], false, string.format(fmt, SN(id) or "?") end
        if cd and cd < soonCd then soonKey, soonId, soonCd = e[1], id, cd end
    end
    -- 6) Hammer of Wrath (target <= 20 %), 7) Avenger's Shield, 8) Divine Plea
    if S.targetHpPct <= 20 and Ready(S, ID.how, "target") then
        return "how", false, string.format(L("Ziel unter 20%%: %s"), SN(ID.how) or "?")
    end
    if Ready(S, ID.avs, "target") then return "avs", false, string.format(fmt, SN(ID.avs) or "?") end
    if S.inCombat and not BuffUp(ID.plea) and Ready(S, ID.plea) then
        return "plea", false, string.format(L("%s fehlt"), SN(ID.plea) or "?")
    end
    -- nothing ready: the one that comes off cooldown next (blue until it is)
    if not hsUp and (S.inCombat or melee) then
        local cd = Avail(S, ID.hs)
        if cd and cd < soonCd then soonKey, soonId, soonCd = "hs", ID.hs, cd end
    end
    if soonKey then return soonKey, false, string.format(L("Nächste: %s"), SN(soonId) or "?") end
end

-- The info line shows the taunt reason (who, how many stacks, mine) together with the rotation note.
function M.PalProtReco(S)
    M.PalProtBossState(S)
    local key, urgent, note = M.PalProtDefensiveReco(S)
    if key then return key, urgent, note end
    local tkey, turgent, tnote, tprep = M.PalProtTauntReco(S)
    key, urgent, note = M.PalProtRotation(S)
    if tkey then
        if note then tnote = tnote .. " | " .. note end
        return tkey, turgent, tnote, tprep
    end
    if S.tauntHint then
        local hint = string.format(L("Spott nötig - Boss ins Ziel nehmen: %s"), S.tauntHint)
        note = note and (hint .. " | " .. note) or hint
    end
    return key, urgent, note
end

-- -----------------------------------------------------------------------------------------------
-- Options
-- -----------------------------------------------------------------------------------------------
local function hidden() return M.CLASS ~= "PALADIN" end
local tauntArgs = {
    palTaunt = { type = "toggle", name = LF("Spott-Empfehlung"), order = 1, width = "full",
        desc = LF("Hand der Abrechnung (rot), bei Abklingzeit Rechtschaffene Verteidigung auf das Ziel des Bosses: wenn der Boss einen anderen Spieler angreift, der die Wechsel-Schwächung ab der Schwelle trägt, und deine eigenen Stapel weg sind (Seuchenmord: wenn du weniger Stapel hast). Nie, solange du den Boss tankst. Der Boss muss dein Ziel sein.") },
}
for i, r in ipairs(M.PAL_TAUNT_RULES) do
    local base = 10 * i
    local off = function() return not M.cfg.palTaunt or not M.cfg[r.opt] end
    tauntArgs[r.opt] = { type = "toggle", order = base, width = r.n and "double" or "full", disabled = function() return not M.cfg.palTaunt end,
        name = function() return L(r.label) .. " - " .. (SN(r.ids[1]) or "?") end }
    if r.n then
        tauntArgs[r.opt .. "N"] = { type = "range", name = LF("Stapel"), order = base + 1, min = r.min, max = r.max, step = 1, disabled = off }
    end
    if r.h then
        tauntArgs[r.opt .. "H"] = { type = "range", name = LF("Stapel (heroisch)"), order = base + 2, min = r.min, max = r.max, step = 1, disabled = off }
    end
end

local function pct(id, key, order, maxV)
    return { type = "range", order = order, min = 5, max = maxV or 60, step = 1, disabled = function() return not M.cfg.palDefHp end,
        name = function() return string.format(L("%s bei Leben unter (%%)"), SN(id) or "?") end }
end
local function ev(order, spell)
    return { type = "toggle", order = order, width = "full", disabled = function() return not M.cfg.palDef end,
        name = function() return SN(spell) or "?" end }
end

M.CLASS_OPTIONS.paladinProtTaunt = { type = "group", name = LF("Schutz: Spott"), order = 2.1, hidden = hidden,
    get = function(info) return M.cfg[info[#info]] end, set = function(info, v) M.cfg[info[#info]] = v end, args = tauntArgs }

M.CLASS_OPTIONS.paladinProtDef = { type = "group", name = LF("Schutz: Verteidigung"), order = 2.2, hidden = hidden,
    get = function(info) return M.cfg[info[#info]] end, set = function(info, v) M.cfg[info[#info]] = v end, args = {
    palDef = { type = "toggle", name = LF("Verteidigung bei Boss-Mechaniken"), order = 1, width = "full",
        desc = LF("Göttlicher Schutz (rot) bei: Saurfangs Raserei (wenn du ihn tankst), Fauldarms Stechender Seuche (auch kurz vor der erwarteten nach dem 3. Einatmen), Seelenernter auf dir, Gormoks Stampfen (Standard aus), Sindragosas Mystischem Puffer auf dir ab den eingestellten Stapeln. Nur wenn bereit und ohne Vorahnung.") },
    palD_frenzy = ev(2, 72737),
    palD_pungent = ev(3, 69195),
    palD_reaper = ev(4, 69409),
    palD_stomp = ev(5, 66330),
    palD_buffet = ev(6, 70127),
    palD_buffetN = { type = "range", name = LF("Mystischer Puffer: Stapel auf dir"), order = 7, min = 2, max = 10, step = 1,
        disabled = function() return not M.cfg.palDef or not M.cfg.palD_buffet end },
    palDefHp = { type = "toggle", name = LF("Lebens-Schwellen"), order = 10, width = "full" },
    palDefDPPct = pct(ID.dprot, "palDefDPPct", 11),
    palDefLoHPct = pct(ID.loh, "palDefLoHPct", 12, 40),
    palDefDS = { type = "toggle", name = LF("Gottesschild als letzte Rettung"), order = 13, width = "full",
        desc = LF("Standard aus: für Tanks nur als letzte Rettung gedacht."),
        disabled = function() return not M.cfg.palDefHp end },
    palDefDSPct = pct(ID.dshield, "palDefDSPct", 14, 40),
} }
M.CLASS_OPTIONS.paladinProtDef.args.palDefDSPct.disabled = function() return not M.cfg.palDefHp or not M.cfg.palDefDS end
