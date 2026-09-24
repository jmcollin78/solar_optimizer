# Review of Issue #213 and PR #214

## References

- Issue: [#213 — on_time counter is inverted when check_active_template depends on a sensor updated after the switch](https://github.com/jmcollin78/solar_optimizer/issues/213)
- Related pull request: [#214 — Fix on_time counter inverted when check_active_template depends on a lagging sensor](https://github.com/jmcollin78/solar_optimizer/pull/214)
- Reviewed status: issue and PR open, with no label, assignee, review, or CI check displayed.

## Faithful summary

The issue reports a defect in the daily `on_time` sensor when a `check_active_template` depends on an entity updated after the controlled entity, for example a power sensor after switching a contactor.

When the switch changes, the template still reflects the previous value. The counter therefore incorrectly infers an opposite transition: it stores a start time when switching off, then counts an off period as an active period. After the daily reset, this can immediately exceed `max_on_time_per_day_min`, prevent any new activation, and prevent forcing during off-peak hours.

PR #214 replaces transition detection with sampling: it credits the elapsed interval if the device was active during the previous check, then starts a new interval only if it is currently active. This sampling runs when the underlying entity state changes and every minute. Switch changes are therefore handled immediately; only a subsequent change to a template dependency, without a new switch event, is observed during the next periodic run, at most one minute later.

## Sources and verified elements

### Issue and PR

- The issue provides a reproducible scenario involving a water heater, a delayed power sensor, `max_on_time_per_day_min: 180`, and a reset at 06:00.
- Its author explicitly proposes sampling `is_active` at every underlying entity change and every minute.
- The owner indicates that, for a standard switch, using a `check_active_template` can be avoided; this comment provides a workaround, but does not invalidate the counter defect for existing configurations or devices with a separate active state.
- The PR contains two commits and modifies two files: `sensor.py` and `test_max_on_time.py` (+143 / -32 according to GitHub). It states that the full suite produces 89 passing tests and 11 skipped tests. This run was not reproduced locally in this review.

### Local repository

- `TodayOnTimeSensor._on_state_change` currently evaluates `self._device.is_active` synchronously in the callback for changes to the monitored entity and uses `_old_state` to derive transitions. The mechanism matches the described cause.
- `ManagedDevice.is_active` returns the `check_active_template`; it can therefore depend on another entity updated later.
- The periodic update currently credits time only if `_last_datetime_on` is defined and `is_active` is true. It does not correct an already inverted start time.
- The local test covers the nominal case of starting, stopping, periodic updating, and resetting, but not the delay between the switch and the power sensor. The PR adds a regression test for this case.
- The documentation indicates that the active template is optional when the entity's `on`/`off` state corresponds to its actual activity, especially for switches and input booleans.

## Relevance and recommendation

**Recommendation: retain the fix from PR #214, subject to a targeted review and independent test execution.**

The defect is reproducible when reading the current code, affects a functional safety feature (`max_on_time_per_day_min`), and can make equipment unavailable for an entire day. The fix is localized, follows the issue proposal, and includes a regression test that documents the failing scenario.

## Proposed scope

### Included

- Correct the daily counting of `TodayOnTimeSensor` when activity evaluation is delayed relative to the underlying entity change.
- Preserve counter behavior for devices whose activity immediately follows the underlying entity.
- Add and maintain the regression test with a delayed power sensor.

### Excluded

- Modify the general semantics of `check_active_template`.
- Prohibit the active template on switches.
- Modify the optimization engine, power strategies, or configured thresholds.
- Configuration migration or dependency changes.

## Impacts and risks

| Area                       | Impact / risk                                                                                                                                                                                                            | Severity | Likelihood                                   | Proposed measure                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | -------------------------------------------- | ------------------------------------------------------------------------------- |
| Functional                 | The current bug can count several hours of inactivity as activity and block the equipment for the day.                                                                                                                   | High     | High for delayed templates                   | Integrate the fix with the regression test.                                     |
| Counter accuracy           | Switch changes are handled immediately. A delay, bounded by the one-minute periodic interval, remains only if a `check_active_template` dependency changes after the switch without causing a new event from the latter. | Low      | High for templates with delayed dependencies | Verify that this bound is acceptable near daily limits.                         |
| Regression                 | The new routine is called both on events and periodically; double counting must be excluded.                                                                                                                             | Moderate | Low to moderate                              | Run existing tests and add a test for very close events if necessary.           |
| Persistence / reset        | `last_datetime_on` is restored and reset daily; an inconsistent intermediate state could propagate after restart.                                                                                                        | Moderate | Low                                          | Explicitly verify stopping, reset, then restart in tests or acceptance testing. |
| Performance                | Template evaluation is already periodic; refactoring does not create a new interval.                                                                                                                                     | Low      | Low                                          | Check that no additional unbounded work is introduced.                          |
| Security / confidentiality | No identified impact: local counting change, with no new input or data transmission.                                                                                                                                     | Low      | Low                                          | No additional action.                                                           |
| Compatibility              | No exposed schema or API change identified.                                                                                                                                                                              | Low      | Low                                          | Validate against supported Home Assistant versions.                             |

## Alternatives considered

1. **Remove `check_active_template` for the affected switches**
   - Advantage: immediate workaround for devices whose switch genuinely reflects activity.
   - Disadvantage: does not cover installations where the switch does not reflect physical activity, nor other entity domains; does not correct the fragility of the current logic.

2. **Also listen to template dependencies**
   - Advantage: potentially more accurate detection than one minute.
   - Disadvantage: template dependencies and listening to them are more complex; higher risk of coupling and regressions. This is not the solution proposed by the PR.

3. **Adopt the PR's periodic sampling**
   - Advantage: localized fix, robust against event arrival order, understandable behavior, and tested by the reported scenario.
   - Disadvantage: accuracy bounded by the interval frequency.

## Assumptions, required decisions, and open questions

### Assumptions

- Observing, no later than the next minute, a delayed change in a `check_active_template` dependency is acceptable for displaying `on_time` and applying daily thresholds.
- The active template may legitimately depend on entities distinct from the controlled entity.

### Open questions

1. Is the one-minute bound, only for delayed changes to template dependencies, acceptable for cases close to `max_on_time_per_day_min`?
2. Should the documentation be extended to discourage `check_active_template` on a switch when its state is sufficient, while specifying that delayed templates are supported?
3. Should the PR include a persistence test after restart, or is the existing coverage considered sufficient?

### Required decisions

- Validate adoption of the PR's sampling approach rather than tracking template dependencies.
- Decide whether a documentation update is part of this fix.

## Criteria for proceeding to development

1. The scope above is approved.
2. Blocking questions, particularly the acceptability of one-minute accuracy, receive a decision.
3. Existing tests and the new regression test are run successfully in the target environment.
4. A review confirms that stopping, the daily reset, and closely spaced state changes do not lead to double counting.

## Proposed next steps

After approval of this report, produce aligned functional specifications and technical design, then request explicit authorization before any development or integration.

## Follow-up decision

The requester does not approve opening the specification and design phases. They plan to validate PR #214 directly. No development step or code modification is undertaken as part of this review.