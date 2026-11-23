# Check and design screens in the browser

Part of the [ClaudeDevKit product](../product.md).

## What it gives

The `web-kit` plugin checks a web application in a browser and designs its screens. It fills the slots
`check-ui`, `check-usability`, `check-look` and `show-idea` ([slots](../../plugins/web-kit/slots.md)).
Its skills `e2e-check`, `user-walk`, `visual-check` and `design-screen` name their agents
(`web-kit:ui-tester`, `web-kit:user`, `web-kit:layout-checker`, `web-kit:designer`) and model themselves;
the manager reaches them through the slots. Who answers which question, and the shared browser rules:
[browser checks](../../plugins/web-kit/browser-checks.md). The checks run in the desktop app's in-app
browser, or, in a background session that lacks it, in a headless browser the plugin ships; they are never
skipped for want of the pane. The project's facts go in its profile
([sections](../tech/project-profile.md)).

## Features

- [Design a screen](../features/design-a-screen.md)
- [Take a wide screenshot](../features/take-a-wide-screenshot.md)

## Not written yet

`e2e-check`, `user-walk` and `visual-check` have no feature files; their rules stay in
`plugins/web-kit/skills` and in `plugins/web-kit/browser-checks.md`.
