# When plugin updates reach the leads

Owner's words (2026-11-23, P: ClaudeDevKit chat), answering the retro question «випускати оновлення інструментів не частіше раза на день?»: «визначати критичність оновлення. І якщо агенти цілком справляться без нього, то на некст день, а якщо ні то відразу. Запусти обговрення, бо зараз керівники перезапускаються посеред розмови»

Problem (retro item restart-per-version-bump, local file C:/Users/korov/.claude/dev-kit/retro/claudedevkit-ff941a2990/items/restart-per-version-bump.md): every dev-kit version bump restarts every lead (Pult watcher, project-lead "Restart for a plugin update"); bumps come several times an hour (Prishch: 12 restarts on 2026-11-21; Zhratva: two in a minute, 7 identical resend messages to one C), and a lead restarts in the middle of a talk with the owner.

Topics for the talk: who decides if an update is critical and how; what waits for the next day and when that release happens; what «not in the middle of a talk» means for a restart; anything else the owner raises.

Related, already agreed and built separately (do not reopen): a long session moves to a fresh one at a third of its context instead of half (owner «так», 2026-11-23).

Result: the «Owner's approval» section in this file with every agreed point in builder detail.

## How it works now (checked 2026-11-23, investigator)

- Pult watcher (`plugins/pult/scripts/watch-servers.ps1`, every 60 s) compares each live lead's start version with `plugins/dev-kit/.claude-plugin/plugin.json` (`Invoke-LeadVersionCheck`, ~:494-597).
- Idle lead: restarted at once (:562-563). Busy lead: gets `restart requested: <version>`, finishes its step, runs `dev-kit-sessions restart ready`, watcher restarts it (:569-578; project-lead SKILL.md:880-916).
- Only the host idle/busy flag is tested; a lead waiting on an owner answer counts as idle, so it restarts mid-talk.
- Versions are bumped by hand in each plugin-changing commit; no critical flag, no batching except the retro run's one bump.
- After every restart P sends each active C a resend ВКАЗІВКА, so N restarts = N identical messages.

## Owner's approval

Owner «так» to points 1-2 and to point 3 with its wording, 2026-11-23, «Обговорення: update-timing».

1. Who decides. The agent that bumps a plugin version marks that release «critical» or «routine»
   in the same commit, with a one-line reason. Critical = agents cannot cope without it (messages
   lost, sessions stuck or looping, a lead or C cannot do its job, harm to data). Everything else is
   routine. The mark must be machine-readable for the Pult watcher (place left to the builders, for
   example a field next to `version` in `plugin.json`); a missing mark counts as routine.
2. Routine releases. The watcher does not restart a lead for a routine release on the day it
   appears. All routine releases of a day are collected; the lead restarts once on a later day, at
   its first quiet moment (point 3's quiet test), onto the newest version. No fixed hour, no
   scheduled task (owner ruling 2026-11-22: not Pult as a scheduler, no Windows task). Example: five
   routine bumps today = one restart tomorrow. A restart that happens for any other reason (a
   critical release, the move to a fresh session) takes the pending routine versions with it.
3. Critical releases. Restart the same day, but not in the middle of a talk:
   - Quiet: the lead is idle, its last message to the owner is not an open question, and the owner
     has written nothing to it for 5 minutes. Then restart silently, no warning.
   - Active (not quiet): the lead writes into its own chat, as its own message, exactly
     «⚠ ЧЕРЕЗ 30 СЕК БУДЕ ПЕРЕЗАВАНТАЖЕННЯ (ОНОВЛЕННЯ ІНСТРУМЕНТІВ)», marks itself ready, and the
     watcher restarts it 30 seconds after that message. No waiting for a pause. A lead busy mid-turn
     first finishes its current step (existing handshake), then writes the warning.
   - An owner message sent during those 30 seconds is not lost: it is answered after the restart
     (existing handshake behaviour, project-lead SKILL.md ~:898).
4. Side effect expected, not a separate rule: fewer restarts means fewer resend ВКАЗІВКА messages
   from P to each C (one per restart today).

Builders' places (from the check above): watcher version gate `watch-servers.ps1` ~:534-597;
lead handshake project-lead SKILL.md ~:880-916; the rule for whoever bumps versions (manager or
edit-rules skill, and the retro run's «one plugin update a day» line, retro SKILL.md:101).
Not decided (asked, owner closed the talk without an answer): extension plugins (web-kit,
unity-kit) keep their current restart behaviour; these rules cover dev-kit releases only.

Spend: subscription only (discussion + one sonnet investigator); API 0 USD.

## Build (2026-11-23, branch c/update-timing-build, with c/fill-limit-third merged in)

- Mark: `plugins/dev-kit/releases.json` (version -> kind, date, reason); rule for bumping agents in
  `.claude/dev-kit.md`, "All agents"; retro and project-lead point to it. dev-kit stays 0.1.103 (one bump,
  marked routine); pult 0.1.22.
- `sessions.py release` (critical between the lead's version and the installed one) and `sessions.py quiet`
  (owner message under 5 min, or an open question: last line ends with "?" after skipping trailing
  «Рекомендую:» lines).
- Watcher: routine deferred on the day the watcher first saw the lead behind (`staleSince` in
  lead-versions.json, RESTART-DEFERRED), then restart only when quiet; critical: quiet -> restart, else
  RESTART-ASKED; a ready mark is honoured 30 s after it (`-ReadyWarnSec`). Extension-only path unchanged.
- P: no self-started handshake on a noticed version; on `restart requested` it writes the warning line, then
  `restart ready`.
- Known limits: a lead on the old skill may still self-ready once for 0.1.103 (old behaviour, one time);
  a lead below dev-kit 0.1.78 gets no request and restarts only when quiet; a lead with a long-open question
  waits for a routine release until a critical one or another restart.
- Checks: tools/tests 736 passed (1 skipped), lint 0 errors; independent review: one wording conflict fixed.

Spend (build): ~0.5% of the weekly limit, estimate; API: 0 USD.
