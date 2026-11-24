## Raspberry Pi Compatibility — A Mandatory Design Requirement

**Status: MUST — Non-negotiable architectural constraint**

Dennis must run on Raspberry Pi hardware. This is a fundamental requirement, not an optional optimization or a future compatibility goal.

The Raspberry Pi is a first-class deployment target. Dennis must remain lightweight, resource-efficient and practical on modest hardware.

This requirement is one of the principal reasons behind the KISS philosophy:

- Keep dependencies to a minimum.
- Prefer Python's standard library whenever practical.
- Avoid unnecessary abstraction layers and resource-intensive frameworks.
- Prefer reliable native operating-system capabilities over reinventing them.
- Keep background services lean and purposeful.
- Consider CPU, RAM, storage endurance and network requirements throughout development.
- Do not make powerful hardware a prerequisite for functionality that can reasonably run on a Raspberry Pi.

### The Notary Deployment Vision

One intended application is deployment in notary offices and similar professional environments.

The objective is a **plug-config-play** platform: Dennis should be deliverable as a compact, preconfigured hardware appliance, potentially based on a Raspberry Pi.

The demonstration should be simple:

*"This is all the hardware you need to run the platform."*

The customer connects the device to power and their network, completes the initial configuration, registers the necessary keys and verifies the installation.

The platform should not require an expensive server infrastructure or a dedicated team of system administrators for ordinary deployments.

The installer, configuration process, updates, backups and operational verification must support this simplicity.

### Standardized Deployment

The same installation process must be reproducible by different authorized technicians.

Every deployment should follow the same installation plan, stage sequence, validation procedures and reporting format.

The customer should receive and retain the final installation report on their own infrastructure.

### Engineering Consequence

Raspberry Pi compatibility must influence architectural and implementation decisions from the beginning. It must be tested on actual target hardware, not assumed from successful execution on a developer workstation.

The reference hardware may evolve as requirements grow, but the underlying principle remains:

**Dennis must remain accessible, deployable and operational on modest hardware.**

KISS is not an aesthetic preference. It is part of making Dennis practical, portable and affordable.
