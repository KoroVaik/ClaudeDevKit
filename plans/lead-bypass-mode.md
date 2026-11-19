# Leads run in the same permission mode as their C sessions

Owner's words (2026-11-19): «Тіки керівник керує сесійой розробки, я туди не маю лизти взагалі»; «Так» to «Запустити сесію, яка переведе керівників у режим без запитів дозволів?».

## Problem
BACKLOG.md entry «P cannot message a C started with bypassPermissions (from P: Zhratva)». P starts C with bypassPermissions after the hard bans; P itself runs in another mode, so every P message to that C is held for the owner's approval in the C's chat. The SendMessage tool says a session in a different permission mode holds cross-session messages for its user's approval.

## Goal
P sessions run in the same mode as their C sessions (bypassPermissions where the project's hard bans are in place), so P -> C messages arrive with no owner step and the owner never opens a C's chat. Cover every way a P starts: Pult launch and autorun (plugins/pult/scripts), plugin-update restart and resume, P's own refresh and the project-lead skill text. Remove the BACKLOG entry when built.

## Success criterion
A P and a C both in bypassPermissions: one P -> C message is delivered with no approval (live check on a throwaway pair), and the launch code for P passes the same mode C gets.

## Paid spend
0
