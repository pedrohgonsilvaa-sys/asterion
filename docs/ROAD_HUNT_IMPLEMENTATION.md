# Road Hunt/Explore implementation

The `RoadService` owns the post-P1 loop for the Estrada das Cinzas. It locks the
character before checking the persistent WorldState, unlocks and foreground,
then materializes a hunt or exploration attempt once. A hunt stores its
creature, level, variant, seed and loot profile in `HuntContext`; an exploration
stores its selected result in `ExplorationAttempt`. Reconnects decode the
persisted `CombatRecord` and never roll a new creature or result.

The `20260922_0006` migration adds the generic hunt, exploration, Bestiary,
Codex fragment, equipment, rune and pending-delivery tables. Its downgrade
refuses to remove populated state. Reward events use the activity identity as
their idempotency source and familiaridade is represented by the existing
unique `Unlock` table. `exploration_combat` deliberately uses the reduced
economy from the focused Road specification and never rolls Equipment or Rune.

The implementation stops at Solo Road content. Automatic Ronda, Group hunts,
other exploration locations, P2/S1, and full Inventory/Bestiary/Codex screens
remain outside this block.
