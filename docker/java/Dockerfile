# Java 21 judge for CodeWorkout submissions: compiles and runs one program per container, as an unprivileged user.
FROM eclipse-temurin:21.0.10_7-jdk-noble
RUN apt-get update && apt-get install -y --no-install-recommends time && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 10001 runner && mkdir -p /workspace && chown -R runner:runner /workspace
RUN printf '#!/bin/sh\njavac Main.java && java -cp . Main\n' > /usr/local/bin/run-code && chmod +x /usr/local/bin/run-code
USER runner
WORKDIR /workspace
