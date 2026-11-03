# Independent Notes RC fixture

A standalone Android Compose application authored independently for RC acceptance.
This fixture does not use Android Stack Skills create, project templates, generated app examples,
or files/records removed from a generated project. It starts with no Recipe dependencies or sources.
Existing Application, Activity, repository and test provide preservation baselines.
The RC harness copies this fixture to /tmp, provisions only the checksum-verified Gradle Wrapper,
builds it before installation, then installs the three Recipes incrementally with real builds.
