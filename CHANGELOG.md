# v3.0.beta0

Welcome to pyinfra v3! This version is the biggest overhaul of pyinfra since it was created back in 2015. Most v2 deployment code should be automatically compatible, but as always be aware. Major changes:

## Runtime operation execution

pyinfra now executes operations at runtime, rather than pre-generating commands. Although the change isn't noticeable this fixes an entire class of bugs and confusion. See the [limitations](https://docs.pyinfra.com/en/2.x/deploy-process.html#limitations) section in the v2 docs. All of those issues are now a thing of the past.

This represents a huge overhaul of pyinfra's internals and should be a huge improvement for users.

Care has been taken to reduce the overhead of this change which still supports the same diffs and change proposal mechanism.

## CLI flow & prompts

The pyinfra CLI will now prompt (instead of ignore, or immediately exit) when problems are encountered, allowing the user to choose to continue. Additionally an approval step is added before executing changes (skip with `-y`).

## Extendable connectors API, typing overhaul

v3 of pyinfra includes for the first time a (mostly) typed internal API with proper support for IDE linting. There's a whole new connectors API that provides a framework for building new connectors.

More TBC...

# v2.x

[See this file in the `2.x` branch](https://github.com/Fizzadar/pyinfra/blob/2.x/CHANGELOG.md).

# v1.x

[See this file in the `1.x` branch](https://github.com/Fizzadar/pyinfra/blob/1.x/CHANGELOG.md).
