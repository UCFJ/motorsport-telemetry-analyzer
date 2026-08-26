## Section Observation Metrics

The analyzer compares each lap against the current reference lap within automatically detected analysis sections.

### Time and Speed

- **Section delta**
  - Positive = comparison lap lost time.
  - Negative = comparison lap gained time.

- **Minimum speed**
  - Difference between the comparison lap's minimum section speed and the reference.
  - Positive = higher minimum speed.
  - Negative = lower minimum speed.

- **Section end speed**
  - Speed difference at the final point of the analysis section.
  - Positive = comparison lap faster.
  - Negative = comparison lap slower.

### Braking

- **Brake applications**
  - Number of distinct meaningful braking events within the section.

- **Initial brake onset**
  - Position difference of the first meaningful braking event.
  - Positive = comparison lap brakes later.
  - Negative = comparison lap brakes earlier.

- **Final brake release**
  - Position difference of the end of the final meaningful braking event.
  - Positive = comparison lap releases later.
  - Negative = comparison lap releases earlier.

### Throttle

- **Throttle applications**
  - Number of distinct meaningful throttle reapplications within the section.

- **Full lift**
  - Whether throttle drops to approximately 10% or below.

- **Final throttle application onset**
  - Position difference where the final meaningful exit-throttle application begins.
  - Positive = comparison lap begins it later.
  - Negative = comparison lap begins it earlier.

- **Full throttle reached**
  - Position difference where the final throttle application reaches the high-throttle threshold.
  - Positive = comparison lap reaches full throttle later.
  - Negative = comparison lap reaches full throttle earlier.

### Racing Line

- **Peak line deviation**
  - Largest signed lateral separation from the reference racing line within the section.
  - Negative = left of the reference from the driver's perspective.
  - Positive = right of the reference from the driver's perspective.